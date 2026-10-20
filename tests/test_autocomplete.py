"""Automated unit and integration tests for YouTube Autocomplete Provider.

All tests utilize mocked HTTP sessions and local database fixtures.
Zero live internet requests are made during automated test execution.
"""

import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pytest
import requests

from src.models.keyword import AutocompleteResult
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
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import DatabaseManager


class MockResponse:
    """Mock HTTP Response for requests session."""

    def __init__(
        self,
        json_data: Optional[Any] = None,
        status_code: int = 200,
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.text = text or (json.dumps(json_data) if json_data is not None else "")
        self.headers = headers or {}

    def json(self) -> Any:
        if self._json_data is not None:
            return self._json_data
        raise json.JSONDecodeError("Expecting value", self.text, 0)


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock requests Session."""
    return MagicMock(spec=requests.Session)


@pytest.fixture
def fast_provider(test_db_manager: DatabaseManager, mock_session: MagicMock) -> YouTubeAutocompleteProvider:
    """Provide a YouTubeAutocompleteProvider with fast backoff and zero min-interval for testing."""
    return YouTubeAutocompleteProvider(
        max_retries=2,
        backoff_factor=0.01,
        rate_limiter=RateLimiter(min_interval_seconds=0.0),
        cache_ttl_seconds=3600,
        database_manager=test_db_manager,
        session=mock_session,
    )


# Test 1: Valid response parsing
def test_valid_response_parsing(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(
        json_data=["python", ["python tutorial", "python for beginners", "python crash course"]]
    )
    results = fast_provider.get_suggestions("python", language="en", country="US", use_cache=False)

    assert len(results) == 3
    assert results[0].keyword == "python tutorial"
    assert results[0].source_type == "autocomplete"
    assert results[0].source_name == "youtube_autocomplete"
    assert results[0].language == "en"
    assert results[0].country == "US"
    assert results[0].discovery_query == "python"
    assert results[1].keyword == "python for beginners"


# Test 2: Empty suggestions
def test_empty_suggestions(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data=["nonexistentqueryxyz123", []])
    results = fast_provider.get_suggestions("nonexistentqueryxyz123", use_cache=False)
    assert results == []


# Test 3: Malformed response (non-JSON HTML or empty body)
def test_malformed_response_non_json(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(text="<html><head><title>Error</title></head></html>")
    with pytest.raises(MalformedResponseError, match="JSON"):
        fast_provider.get_suggestions("test", use_cache=False)


# Test 4: URL encoding and parameter passing
def test_url_encoding_and_parameters(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data=["c++ & c#", ["c++ tutorial", "c# tutorial"]])
    fast_provider.get_suggestions("c++ & c#", language="en", country="US", use_cache=False)

    call_args = mock_session.get.call_args
    assert call_args is not None
    params = call_args.kwargs["params"]
    assert params["q"] == "c++ & c#"
    assert params["client"] == "firefox"
    assert params["ds"] == "yt"


# Test 5: Bangla Unicode query and suggestion support
def test_bangla_unicode_support(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    bangla_query = "পাইথন"
    bangla_suggestions = ["পাইথন প্রোগ্রামিং", "পাইথন টিউটোরিয়াল"]
    mock_session.get.return_value = MockResponse(json_data=[bangla_query, bangla_suggestions])

    results = fast_provider.get_suggestions(bangla_query, language="bn", country="BD", use_cache=False)

    assert len(results) == 2
    assert results[0].keyword == "পাইথন প্রোগ্রামিং"
    assert results[0].language == "bn"
    assert results[0].country == "BD"
    assert results[0].discovery_query == bangla_query


# Test 6: Language parameter (hl)
def test_language_parameter(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data=["query", ["suggest 1"]])
    fast_provider.get_suggestions("query", language="es", country="ES", use_cache=False)

    params = mock_session.get.call_args.kwargs["params"]
    assert params["hl"] == "es"


# Test 7: Country parameter (gl)
def test_country_parameter(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data=["query", ["suggest 1"]])
    fast_provider.get_suggestions("query", language="en", country="GB", use_cache=False)

    params = mock_session.get.call_args.kwargs["params"]
    assert params["gl"] == "GB"


# Test 8: Connection timeout
def test_connection_timeout(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Connection timed out")
    with pytest.raises(NetworkTimeoutError, match="timed out"):
        fast_provider.get_suggestions("timeout_query", use_cache=False)


# Test 9: DNS or connection failure
def test_dns_or_connection_failure(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.side_effect = requests.exceptions.ConnectionError("Failed to resolve host")
    with pytest.raises(NetworkConnectionError, match="connection failed"):
        fast_provider.get_suggestions("dns_fail_query", use_cache=False)


# Test 10: HTTP 403 Forbidden (immediate exit without retries)
def test_http_403_forbidden(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(status_code=403, text="Forbidden")
    with pytest.raises(AccessForbiddenError, match="403"):
        fast_provider.get_suggestions("forbidden_query", use_cache=False)

    # Must NOT retry 403
    assert mock_session.get.call_count == 1


# Test 11: HTTP 429 and Retry-After header
def test_http_429_rate_limit_with_retry_after(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    # First attempt: 429 with small Retry-After (0.01s), Second attempt: 200 OK
    mock_session.get.side_effect = [
        MockResponse(status_code=429, headers={"Retry-After": "0.01"}),
        MockResponse(json_data=["rate_query", ["success after retry"]]),
    ]
    results = fast_provider.get_suggestions("rate_query", use_cache=False)
    assert len(results) == 1
    assert results[0].keyword == "success after retry"
    assert mock_session.get.call_count == 2


def test_http_429_exceeded(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(status_code=429, headers={"Retry-After": "60"})
    with pytest.raises(RateLimitError, match="429"):
        fast_provider.get_suggestions("rate_query_exhausted", use_cache=False)


# Test 12: HTTP 5xx transient server error with retry
def test_http_5xx_server_error(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(status_code=503, text="Service Unavailable")
    with pytest.raises(ProviderUnavailableError, match="503"):
        fast_provider.get_suggestions("server_error_query", use_cache=False)

    # 1 initial attempt + 2 retries = 3 attempts total
    assert mock_session.get.call_count == 3


# Test 13: Retry limit enforcement
def test_retry_limit_enforcement(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.side_effect = requests.exceptions.ReadTimeout("Read timed out")
    with pytest.raises(NetworkTimeoutError):
        fast_provider.get_suggestions("retry_query", use_cache=False)

    # Verified bounded attempts (max_retries + 1)
    assert mock_session.get.call_count == fast_provider.max_retries + 1


# Test 14: Cache hit
def test_cache_hit(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock, test_db_manager: DatabaseManager) -> None:
    query = "cached_topic"
    test_db_manager.set_cached_suggestions(query, "en", "US", ["cached item 1", "cached item 2"])

    results = fast_provider.get_suggestions(query, language="en", country="US", use_cache=True)

    assert len(results) == 2
    assert results[0].keyword == "cached item 1"
    # Network session should not be called due to cache hit
    assert mock_session.get.call_count == 0


# Test 15: Cache expiry
def test_cache_expiry(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock, test_db_manager: DatabaseManager) -> None:
    query = "expired_topic"
    # Seed cache with an expired timestamp (2 hours ago, whereas TTL is 1 hour)
    expired_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    results_json = json.dumps(["old expired keyword"])
    with test_db_manager.get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO autocomplete_cache (query, language, country, results_json, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (query, "en", "US", results_json, expired_time),
        )

    # Set mock for fresh network response
    mock_session.get.return_value = MockResponse(json_data=[query, ["fresh keyword from network"]])

    results = fast_provider.get_suggestions(query, language="en", country="US", use_cache=True)

    assert len(results) == 1
    assert results[0].keyword == "fresh keyword from network"
    # Network session MUST be called because cache was expired
    assert mock_session.get.call_count == 1


# Test 16: Duplicate suggestions removal
def test_duplicate_suggestions(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(
        json_data=["dupquery", ["apple pie", "apple juice", "apple pie", "  apple pie  ", "apple cider"]]
    )
    results = fast_provider.get_suggestions("dupquery", use_cache=False)

    assert len(results) == 3
    assert [r.keyword for r in results] == ["apple pie", "apple juice", "apple cider"]


# Test 17: Unexpected response types
def test_unexpected_response_type_not_list(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data={"error": "not a list"})
    with pytest.raises(MalformedResponseError, match="JSON array"):
        fast_provider.get_suggestions("invalid_type", use_cache=False)


def test_unexpected_response_type_index_not_list(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    mock_session.get.return_value = MockResponse(json_data=["query", "not a list"])
    with pytest.raises(MalformedResponseError, match="list of suggestions"):
        fast_provider.get_suggestions("invalid_index1", use_cache=False)


# Test 18: Cancellation token support
def test_cancellation_token(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    token = threading.Event()
    token.set()  # Signaled cancellation before request

    with pytest.raises(OperationCancelledError, match="cancelled"):
        fast_provider.get_suggestions("cancel_query", cancellation_token=token, use_cache=False)

    assert mock_session.get.call_count == 0


# Test 19: Dashboard integration
def test_dashboard_integration_success(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    from app import execute_keyword_search
    mock_session.get.return_value = MockResponse(
        json_data=["dashboard_query", ["dashboard test 1", "dashboard test 2"]]
    )
    results, err = execute_keyword_search("dashboard_query", "en", "US", provider=fast_provider, save_to_db=False)
    assert err is None
    assert len(results) == 2
    assert results[0].keyword == "dashboard test 1"


def test_dashboard_integration_error_handling(fast_provider: YouTubeAutocompleteProvider, mock_session: MagicMock) -> None:
    from app import execute_keyword_search
    mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Timed out")
    results, err = execute_keyword_search("timeout_query", "en", "US", provider=fast_provider, save_to_db=False)
    assert results == []
    assert err is not None
    assert "timed out" in err.lower()
