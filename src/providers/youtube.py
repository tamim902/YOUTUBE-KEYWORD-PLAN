"""YouTube Autocomplete Provider.

Communicates with the free-first unofficial YouTube autocomplete endpoint:
https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q=KEYWORD

Features:
- Proper query parameter URL encoding
- Configurable connection/read timeouts
- Bounded exponential backoff retries for transient 5xx and network failures
- Respect for HTTP 429 and Retry-After headers
- Immediate HTTP 403 handling without futile retries
- Rate limiting and local TTL caching
- Cancellation token support
- Bangla and multi-lingual Unicode NFC normalization
"""

import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, Union
import threading
import requests

from src.config import config
from src.models.keyword import AutocompleteResult
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import (
    AccessForbiddenError,
    AutocompleteError,
    MalformedResponseError,
    NetworkConnectionError,
    NetworkTimeoutError,
    OperationCancelledError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.providers.rate_limiter import RateLimiter
from src.storage.database import DatabaseManager, db_manager
from src.utils.logging import get_logger

logger = get_logger("youtube_provider")


class YouTubeAutocompleteProvider(BaseAutocompleteProvider):
    """Reliable YouTube suggestions client with bounded retries and local caching."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: float = 0.3,
        rate_limiter: Optional[RateLimiter] = None,
        cache_ttl_seconds: Optional[int] = None,
        database_manager: Optional[DatabaseManager] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.endpoint = endpoint or config.autocomplete_endpoint
        self.connect_timeout = (
            connect_timeout
            if connect_timeout is not None
            else config.connect_timeout_seconds
        )
        self.read_timeout = (
            read_timeout if read_timeout is not None else config.read_timeout_seconds
        )
        self.max_retries = (
            max_retries if max_retries is not None else config.max_retries
        )
        self.backoff_factor = max(0.05, float(backoff_factor))
        self.rate_limiter = rate_limiter or RateLimiter(
            config.rate_limit_min_interval_seconds
        )
        self.cache_ttl_seconds = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else config.cache_ttl_seconds
        )
        self.db = database_manager or db_manager
        self._session = session or requests.Session()

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "youtube_autocomplete"

    @property
    def timeout(self) -> Tuple[float, float]:
        """(connect_timeout, read_timeout) tuple."""
        return (self.connect_timeout, self.read_timeout)

    def get_suggestions(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        use_cache: bool = True,
        cancellation_token: Optional[threading.Event] = None,
    ) -> List[AutocompleteResult]:
        """Fetch autocomplete suggestions with retries, caching, and Unicode normalization."""
        stripped = unicodedata.normalize("NFC", query).strip()
        if not stripped:
            return []
        words = stripped.split()
        base = " ".join(words).strip("\"'`[]{}()*;^~")
        if not base:
            return []
        # Preserve single trailing space if query was a deliberate space expansion (starts without space, ends with space)
        is_space_expansion = query.endswith(" ") and not query.startswith(" ")
        cleaned_query = f"{base} " if is_space_expansion else base

        lang_code = language.strip().lower() or "en"
        country_code = country.strip().upper() or "US"

        # 1. Check local SQLite cache if enabled
        if use_cache and self.db:
            try:
                cached_strings = self.db.get_cached_suggestions(
                    query=cleaned_query,
                    language=lang_code,
                    country=country_code,
                    max_age_seconds=self.cache_ttl_seconds,
                )
                if cached_strings is not None:
                    logger.debug("Cache hit for query '%s' [%s/%s]", cleaned_query, lang_code, country_code)
                    now_iso = datetime.now(timezone.utc).isoformat()
                    return [
                        AutocompleteResult(
                            keyword=s,
                            source_type="autocomplete",
                            source_name=self.provider_name,
                            language=lang_code,
                            country=country_code,
                            retrieved_at=now_iso,
                            discovery_query=cleaned_query,
                            is_cached=True,
                        )

                        for s in cached_strings
                    ]
            except Exception as exc:
                logger.warning("Cache lookup failed for '%s': %s", cleaned_query, exc)

        # 2. Perform live network request with bounded retries
        raw_suggestions = self._execute_request_with_retries(
            query=cleaned_query,
            language=lang_code,
            country=country_code,
            cancellation_token=cancellation_token,
        )

        # 3. Deduplicate and normalize suggestions while preserving order
        unique_keywords: List[str] = []
        seen = set()
        for item in raw_suggestions:
            if not isinstance(item, str):
                continue
            normalized = unicodedata.normalize("NFC", item).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_keywords.append(normalized)

        # 4. Save to local SQLite cache
        if self.db and unique_keywords:
            try:
                self.db.set_cached_suggestions(
                    query=cleaned_query,
                    language=lang_code,
                    country=country_code,
                    results=unique_keywords,
                )
            except Exception as exc:
                logger.warning("Failed to cache suggestions for '%s': %s", cleaned_query, exc)

        # 5. Build structured results
        now_iso = datetime.now(timezone.utc).isoformat()
        return [
            AutocompleteResult(
                keyword=kw,
                source_type="autocomplete",
                source_name=self.provider_name,
                language=lang_code,
                country=country_code,
                retrieved_at=now_iso,
                discovery_query=cleaned_query,
            )
            for kw in unique_keywords
        ]

    def _execute_request_with_retries(
        self,
        query: str,
        language: str,
        country: str,
        cancellation_token: Optional[threading.Event],
    ) -> List[str]:
        """Perform outbound HTTP request with exponential backoff and error handling."""
        params = {
            "client": "firefox",
            "ds": "yt",
            "q": query,
            "hl": language,
            "gl": country,
        }
        headers = {
            "User-Agent": config.user_agent,
            "Accept": "application/json, text/javascript, */*",
        }

        attempts = 0
        last_error: Optional[Exception] = None

        while attempts <= self.max_retries:
            if cancellation_token and cancellation_token.is_set():
                raise OperationCancelledError("Request cancelled by user.")

            self.rate_limiter.acquire()
            attempts += 1

            try:
                response = self._session.get(
                    self.endpoint,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )

                # Status Code Handling
                if response.status_code == 200:
                    return self._parse_response(response)

                elif response.status_code == 403:
                    logger.error("Provider returned HTTP 403 Forbidden for query '%s'", query)
                    raise AccessForbiddenError(
                        "Access forbidden by autocomplete provider (HTTP 403)."
                    )

                elif response.status_code == 429:
                    retry_after_val = self._parse_retry_after(response)
                    logger.warning(
                        "HTTP 429 Rate Limited. Attempt %d/%d. Retry-After: %s",
                        attempts,
                        self.max_retries,
                        retry_after_val,
                    )
                    if (
                        attempts <= self.max_retries
                        and retry_after_val is not None
                        and retry_after_val <= 5.0
                    ):
                        time.sleep(retry_after_val)
                        continue
                    raise RateLimitError(
                        "Rate limit exceeded by autocomplete provider (HTTP 429).",
                        retry_after=retry_after_val,
                    )

                elif 500 <= response.status_code < 600:
                    last_error = ProviderUnavailableError(
                        f"Provider server error (HTTP {response.status_code}).",
                        status_code=response.status_code,
                    )
                    logger.warning(
                        "HTTP %d from provider on attempt %d/%d",
                        response.status_code,
                        attempts,
                        self.max_retries,
                    )

                else:
                    raise AutocompleteError(
                        f"Unexpected HTTP status {response.status_code} from provider.",
                        status_code=response.status_code,
                    )

            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as exc:
                last_error = NetworkTimeoutError(
                    f"Connection timed out contacting provider: {exc}"
                )
                logger.warning("Timeout on attempt %d/%d: %s", attempts, self.max_retries, exc)

            except requests.exceptions.ConnectionError as exc:
                last_error = NetworkConnectionError(
                    f"Network connection failed: {exc}"
                )
                logger.warning("Connection failure on attempt %d/%d: %s", attempts, self.max_retries, exc)

            except (AccessForbiddenError, RateLimitError, MalformedResponseError, OperationCancelledError):
                raise

            except Exception as exc:
                last_error = AutocompleteError(f"Unexpected request failure: {exc}")
                logger.warning("Request exception on attempt %d/%d: %s", attempts, self.max_retries, exc)

            # Sleep with exponential backoff before retrying
            if attempts <= self.max_retries:
                wait_time = self.backoff_factor * (2 ** (attempts - 1))
                time.sleep(wait_time)

        if last_error:
            raise last_error
        raise AutocompleteError("Max retries exceeded without successful response.")

    def _parse_response(self, response: requests.Response) -> List[str]:
        """Validate and parse raw JSON array format: [query, [suggestions...]]."""
        try:
            data = response.json()
        except Exception as exc:
            raise MalformedResponseError(
                f"Failed to parse provider response as JSON: {exc}"
            ) from exc

        if not isinstance(data, list):
            raise MalformedResponseError(
                f"Expected top-level JSON array from provider, got {type(data).__name__}."
            )

        if len(data) < 2:
            raise MalformedResponseError(
                f"Provider response array too short (length {len(data)}, expected at least 2)."
            )

        suggestions = data[1]
        if not isinstance(suggestions, list):
            raise MalformedResponseError(
                f"Expected list of suggestions at index 1, got {type(suggestions).__name__}."
            )

        return [str(s) for s in suggestions]

    @staticmethod
    def _parse_retry_after(response: requests.Response) -> Optional[float]:
        """Parse the Retry-After header as seconds if present."""
        retry_header = response.headers.get("Retry-After")
        if not retry_header:
            return None
        try:
            return max(0.0, float(retry_header.strip()))
        except ValueError:
            return None
