"""Controlled YouTube Autocomplete Keyword Expansion Engine.

Provides systematic query expansion beyond seed keywords:
- Alphabet expansion (a-z)
- Number expansion (0-9)
- Preposition & modifier expansion (for, in, with, vs, best, review, etc.)
- Bangla Unicode expansion modifiers (কীভাবে, কেন, সেরা, রিভিউ, ইত্যাদি)
- Strict bounds: request budget, rate limiting, and cancellation
- Accurate provenance tracking: LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, GENERATED_PATTERN
- Zero synthetic metrics (no search volume, CPC, or difficulty scores)
"""

import collections
import string
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.classifier import default_classifier
from src.crawler.models import CrawlProgress, DiscoveredKeyword, StopReason, normalize_keyword_key
from src.intelligence.clustering import default_clusterer
from src.intelligence.scoring import default_scorer
from src.models.keyword import AutocompleteResult, KeywordItem, SourceType
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import AutocompleteError, OperationCancelledError
from src.providers.rate_limiter import RateLimiter
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import DatabaseManager, db_manager
from src.utils.logging import get_logger

logger = get_logger("expansion_engine")


ENGLISH_PREPOSITIONS = [
    "for", "in", "with", "without", "to", "from", "vs", "versus",
    "at", "by", "on", "near", "about", "like", "under"
]

ENGLISH_PREFIX_INTENT = [
    "for", "in", "with", "without", "vs", "versus", "review", "comparison"
]

ENGLISH_QUESTIONS = [
    "how", "why", "what", "where", "when", "who", "which", "can", "will", "is"
]

ENGLISH_QUESTION_PATTERNS = [
    "how to choose the {seed}",
    "which {seed} is best",
    "what is the best {seed}",
    "why use {seed}",
    "when to apply {seed}",
    "how to apply {seed}",
]

ENGLISH_AUDIENCE_USECASE = [
    "for beginners",
    "for black cars",
    "for white cars",
    "for old cars",
    "for new cars",
    "for daily drivers",
    "for dark cars",
]

ENGLISH_MODIFIERS = [
    "best", "top", "review", "reviews", "price", "tutorial", "guide",
    "tips", "tricks", "diy", "beginners", "comparison", "alternative",
    "cheap", "worth it"
]

BANGLA_MODIFIERS = [
    "কীভাবে", "কেন", "কি", "দাম", "রিভিউ", "সেরা", "টিউটোরিয়াল",
    "নিয়ম", "পদ্ধতি", "উপায়", "এর", "বনাম"
]

BANGLA_AUDIENCE_USECASE = [
    "নতুনদের জন্য",
    "কালো গাড়ির জন্য",
    "সাদা গাড়ির জন্য",
    "পুরাতন গাড়ির জন্য",
]

BANGLA_QUESTION_PATTERNS = [
    "কীভাবে {seed} ব্যবহার করবেন",
    "কোন {seed} সবচেয়ে ভালো",
    "কেন {seed} ব্যবহার করবেন",
    "কখন {seed} লাগাতে হয়",
]


def is_bangla_text(text: str) -> bool:
    """Detect whether text contains Bangla Unicode characters (U+0980 to U+09FF)."""
    return any("\u0980" <= ch <= "\u09ff" for ch in text)


@dataclass
class ExpansionConfig:
    """Configuration for controlled autocomplete expansion."""

    seeds: List[str]
    language: str = "en"
    country: str = "US"
    include_seed: bool = True
    include_alphabet: bool = True
    include_prefix_intent: bool = False
    include_questions: bool = True
    include_audience_usecase: bool = False
    include_numbers: bool = True
    include_prepositions: bool = True
    include_modifiers: bool = True
    custom_modifiers: List[str] = field(default_factory=list)
    request_budget: int = 50
    min_delay_seconds: float = 0.2
    max_unique_keywords: int = 250
    use_cache: bool = True
    max_depth: int = 1

    def __post_init__(self) -> None:
        if not self.seeds:
            raise ValueError("At least one seed keyword is required.")
        if self.request_budget <= 0:
            raise ValueError("request_budget must be positive.")
        if self.max_unique_keywords <= 0:
            raise ValueError("max_unique_keywords must be positive.")
        if self.min_delay_seconds < 0:
            raise ValueError("min_delay_seconds cannot be negative.")
        if self.max_depth < 0:
            raise ValueError("max_depth cannot be negative.")


@dataclass
class QueryLogEntry:
    """Audit log entry for an attempted expansion query."""

    seed_keyword: str
    actual_query: str
    category: str
    status: str  # "success", "cached", "cancelled", "failed"
    suggestions_count: int = 0
    error_message: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ExpansionResult:
    """Output of a controlled expansion crawl."""

    keywords: List[DiscoveredKeyword]
    stop_reason: StopReason
    queries_processed: int
    total_requests_made: int
    is_partial: bool
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    query_logs: List[QueryLogEntry] = field(default_factory=list)


class ControlledExpansionEngine:
    """Executes controlled keyword expansion queries (A-Z, 0-9, prepositions, modifiers)."""

    def __init__(
        self,
        provider: Optional[BaseAutocompleteProvider] = None,
        database_manager: Optional[DatabaseManager] = None,
    ) -> None:
        if database_manager is not None:
            self.db = database_manager
        elif provider is not None:
            self.db = getattr(provider, "db", None)
        else:
            self.db = db_manager

        if provider is not None:
            self.provider = provider
        else:
            self.provider = YouTubeAutocompleteProvider(database_manager=self.db)

    def generate_expansion_queries(self, config: ExpansionConfig) -> List[Tuple[str, str, str]]:
        """Generate an ordered list of (actual_query, original_seed, category) tuples."""
        queries: List[Tuple[str, str, str]] = []
        seen_queries: Set[str] = set()

        for seed in config.seeds:
            clean_seed = unicodedata.normalize("NFC", seed).strip()
            if not clean_seed:
                continue

            # 1. Base seed query (instant)
            if config.include_seed:
                norm = clean_seed.lower()
                if norm not in seen_queries:
                    queries.append((clean_seed, clean_seed, "seed"))
                    seen_queries.add(norm)

            # Check if Bangla
            has_bangla = is_bangla_text(clean_seed)

            # 2. Alphabet expansion (a-z)
            if config.include_alphabet:
                for char in string.ascii_lowercase:
                    q = f"{clean_seed} {char}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "alphabet"))
                        seen_queries.add(norm)

            # 3. Prepositions expansion
            if config.include_prepositions:
                for prep in ENGLISH_PREPOSITIONS:
                    q = f"{clean_seed} {prep}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "preposition"))
                        seen_queries.add(norm)

            # 4. Prefix & Intent expansion
            if config.include_prefix_intent:
                for mod in ENGLISH_PREFIX_INTENT:
                    q = f"{clean_seed} {mod}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "prefix_intent"))
                        seen_queries.add(norm)

                if has_bangla:
                    for b_mod in ["জন্য", "বনাম", "রিভিউ", "তুলনা", "দাম"]:
                        q = f"{clean_seed} {b_mod}"
                        norm = q.lower()
                        if norm not in seen_queries:
                            queries.append((q, clean_seed, "prefix_intent"))
                            seen_queries.add(norm)

            # 4. Questions expansion
            if config.include_questions:
                for pat in ENGLISH_QUESTION_PATTERNS:
                    q = pat.format(seed=clean_seed)
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "question"))
                        seen_queries.add(norm)

                for q_word in ENGLISH_QUESTIONS:
                    q = f"{q_word} {clean_seed}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "question"))
                        seen_queries.add(norm)

                if has_bangla:
                    for b_pat in BANGLA_QUESTION_PATTERNS:
                        q = b_pat.format(seed=clean_seed)
                        norm = q.lower()
                        if norm not in seen_queries:
                            queries.append((q, clean_seed, "question"))
                            seen_queries.add(norm)

            # 5. Audience and use-case expansion
            if config.include_audience_usecase:
                for aud in ENGLISH_AUDIENCE_USECASE:
                    q = f"{clean_seed} {aud}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "audience_usecase"))
                        seen_queries.add(norm)

                if has_bangla:
                    for b_aud in BANGLA_AUDIENCE_USECASE:
                        q = f"{clean_seed} {b_aud}"
                        norm = q.lower()
                        if norm not in seen_queries:
                            queries.append((q, clean_seed, "audience_usecase"))
                            seen_queries.add(norm)

            # 6. Numeric expansion (0-9)
            if config.include_numbers:
                for digit in "0123456789":
                    q = f"{clean_seed} {digit}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "numeric"))
                        seen_queries.add(norm)

            # 7. Additional Modifiers (legacy / general)
            if config.include_modifiers:
                for mod in ENGLISH_MODIFIERS:
                    q = f"{clean_seed} {mod}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "modifier"))
                        seen_queries.add(norm)

                if has_bangla:
                    for b_mod in BANGLA_MODIFIERS:
                        q = f"{clean_seed} {b_mod}"
                        norm = q.lower()
                        if norm not in seen_queries:
                            queries.append((q, clean_seed, "bangla_modifier"))
                            seen_queries.add(norm)

            # 8. Custom modifiers
            for c_mod in config.custom_modifiers:
                c_clean = c_mod.strip()
                if c_clean:
                    q = f"{clean_seed} {c_clean}"
                    norm = q.lower()
                    if norm not in seen_queries:
                        queries.append((q, clean_seed, "custom"))
                        seen_queries.add(norm)

        return queries


    def expand(
        self,
        config: ExpansionConfig,
        cancellation_token: Optional[threading.Event] = None,
        on_progress: Optional[Callable[[CrawlProgress], None]] = None,
    ) -> ExpansionResult:
        """Run controlled expansion up to budget and result targets."""
        start_time = time.monotonic()
        planned_queries = self.generate_expansion_queries(config)

        discovered: Dict[str, DiscoveredKeyword] = {}
        query_logs: List[QueryLogEntry] = []
        requests_made = 0
        queries_processed = 0
        stop_reason = StopReason.QUEUE_EXHAUSTED
        error_message: Optional[str] = None
        is_partial = False

        for actual_query, orig_seed, category in planned_queries:
            # 1. Check bounds and cancellation before request
            if cancellation_token and cancellation_token.is_set():
                logger.info("Expansion cancelled by user.")
                stop_reason = StopReason.CANCELLED
                is_partial = True
                break

            if len(discovered) >= config.max_unique_keywords:
                logger.info("Target reached (%d unique keywords).", len(discovered))
                stop_reason = StopReason.TARGET_REACHED
                is_partial = False
                break

            if requests_made >= config.request_budget:
                logger.info("Request budget reached (%d).", requests_made)
                stop_reason = StopReason.BUDGET_EXHAUSTED
                is_partial = True
                break

            # 2. Check if cached
            is_cached = False
            if config.use_cache and self.db:
                try:
                    cached_data = self.db.get_cached_suggestions(
                        query=actual_query,
                        language=config.language,
                        country=config.country,
                    )
                    if cached_data is not None:
                        is_cached = True
                except Exception:
                    pass

            queries_processed += 1

            if on_progress:
                on_progress(
                    CrawlProgress(
                        queries_processed=queries_processed,
                        keywords_discovered=len(discovered),
                        current_depth=1,
                        requests_remaining=max(0, config.request_budget - requests_made),
                        current_query=actual_query,
                    )
                )

            # 3. Execute request
            try:
                requests_made += 1
                suggestions = self.provider.get_suggestions(
                    query=actual_query,
                    language=config.language,
                    country=config.country,
                    use_cache=config.use_cache,
                    cancellation_token=cancellation_token,
                )
                query_has_cached = is_cached or any(getattr(s, "is_cached", False) for s in suggestions)
                source_label = "CACHED_AUTOCOMPLETE" if query_has_cached else "LIVE_AUTOCOMPLETE"
                status_str = "cached" if query_has_cached else "success"

                query_logs.append(
                    QueryLogEntry(
                        seed_keyword=orig_seed,
                        actual_query=actual_query,
                        category=category,
                        status=status_str,
                        suggestions_count=len(suggestions),
                    )
                )

                # Process suggestions
                now_iso = datetime.now(timezone.utc).isoformat()
                for s in suggestions:
                    kw_text = s.keyword.strip()
                    kw_norm = normalize_keyword_key(kw_text)
                    if not kw_norm:
                        continue

                    s_is_cached = is_cached or getattr(s, "is_cached", False) or getattr(s, "source_type", "") == "CACHED_AUTOCOMPLETE"
                    item_source_label = "CACHED_AUTOCOMPLETE" if s_is_cached else source_label

                    if kw_norm in discovered:
                        existing = discovered[kw_norm]
                        existing.add_discovery_path(actual_query, 1)
                        if item_source_label not in existing.sources:
                            existing.sources.append(item_source_label)
                    else:
                        if len(discovered) < config.max_unique_keywords:
                            cls = default_classifier.classify(kw_text)
                            rel = default_scorer.score(
                                keyword=kw_text,
                                seed_keyword=orig_seed,
                                classification=cls,
                            )
                            dk = DiscoveredKeyword(
                                keyword=kw_text,
                                normalized_key=kw_norm,
                                depth=1,
                                parent_queries=[actual_query],
                                discovery_paths=1,
                                source_type=item_source_label,
                                source_name="youtube_autocomplete",
                                language=config.language,
                                country=config.country,
                                first_discovered_at=now_iso,
                                last_discovered_at=now_iso,
                                sources=[item_source_label],
                                tail_length=cls.tail_length.value,
                                intent_labels=[i.value for i in cls.intent_labels],
                                word_count=cls.word_count,
                                discovery_query=actual_query,
                                is_cached=s_is_cached,
                                relevance_score=rel.total_score,
                                intent_explanation=cls.primary_explanation,
                            )
                            discovered[kw_norm] = dk

            except OperationCancelledError:
                logger.info("Cancelled during suggestion retrieval.")
                stop_reason = StopReason.CANCELLED
                is_partial = True
                query_logs.append(
                    QueryLogEntry(
                        seed_keyword=orig_seed,
                        actual_query=actual_query,
                        category=category,
                        status="cancelled",
                    )
                )
                break
            except AutocompleteError as exc:
                logger.warning("Provider error for '%s': %s", actual_query, exc)
                query_logs.append(
                    QueryLogEntry(
                        seed_keyword=orig_seed,
                        actual_query=actual_query,
                        category=category,
                        status="failed",
                        error_message=str(exc),
                    )
                )
                if "403" in str(exc):
                    stop_reason = StopReason.PROVIDER_ERROR
                    error_message = str(exc)
                    is_partial = True
                    break
            except Exception as exc:
                logger.error("Unexpected error expanding '%s': %s", actual_query, exc)
                query_logs.append(
                    QueryLogEntry(
                        seed_keyword=orig_seed,
                        actual_query=actual_query,
                        category=category,
                        status="failed",
                        error_message=str(exc),
                    )
                )

            # Respect polite delay between outbound requests
            if not is_cached and config.min_delay_seconds > 0:
                time.sleep(config.min_delay_seconds)

        # Apply topic clustering across all discovered keywords
        if discovered:
            seed_kw = config.seeds[0] if config.seeds else ""
            clusters = default_clusterer.cluster_keywords(list(discovered.values()), seed_keyword=seed_kw)
            cluster_map = {}
            for c in clusters:
                for kw in c.keywords:
                    cluster_map[normalize_keyword_key(kw)] = c.name
            for k_norm, dk in discovered.items():
                if k_norm in cluster_map:
                    dk.cluster_name = cluster_map[k_norm]

        duration = round(time.monotonic() - start_time, 2)
        return ExpansionResult(
            keywords=list(discovered.values()),
            stop_reason=stop_reason,
            queries_processed=queries_processed,
            total_requests_made=requests_made,
            is_partial=is_partial,
            duration_seconds=duration,
            error_message=error_message,
            query_logs=query_logs,
        )
