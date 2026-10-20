"""Deterministic automated tests for RecursiveKeywordEngine (Phase 3).

All tests utilize mock providers and isolated fixtures. Zero live network calls.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import pytest

from src.crawler.engine import RecursiveKeywordEngine
from src.crawler.models import (
    CrawlConfig,
    CrawlProgress,
    CrawlResult,
    DiscoveredKeyword,
    StopReason,
    normalize_keyword_key,
)
from src.models.keyword import AutocompleteResult
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import (
    AutocompleteError,
    OperationCancelledError,
    ProviderUnavailableError,
)


class MockAutocompleteProvider(BaseAutocompleteProvider):
    """Deterministic mock provider returning mapped suggestions."""

    def __init__(
        self,
        mapping: Optional[Dict[str, List[str]]] = None,
        default_suggestions: Optional[List[str]] = None,
        error_to_raise: Optional[Exception] = None,
        fail_after_n_calls: Optional[int] = None,
    ) -> None:
        self.mapping = mapping or {}
        self.default_suggestions = default_suggestions or []
        self.error_to_raise = error_to_raise
        self.fail_after_n_calls = fail_after_n_calls
        self.call_history: List[Tuple[str, str, str]] = []

    @property
    def provider_name(self) -> str:
        return "mock_autocomplete"

    def get_suggestions(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        use_cache: bool = True,
        cancellation_token: Optional[threading.Event] = None,
    ) -> List[AutocompleteResult]:
        if cancellation_token and cancellation_token.is_set():
            raise OperationCancelledError("Operation cancelled.")

        self.call_history.append((query, language, country))

        if self.fail_after_n_calls is not None and len(self.call_history) >= self.fail_after_n_calls:
            raise self.error_to_raise or ProviderUnavailableError("Simulated failure")

        if self.error_to_raise and self.fail_after_n_calls is None:
            raise self.error_to_raise

        suggestions = self.mapping.get(query, self.default_suggestions)
        now_iso = datetime.now(timezone.utc).isoformat()
        return [
            AutocompleteResult(
                keyword=s,
                source_type="autocomplete",
                source_name=self.provider_name,
                language=language,
                country=country,
                retrieved_at=now_iso,
                discovery_query=query,
            )
            for s in suggestions
        ]


# Test 1: One seed with several suggestions
def test_one_seed_with_several_suggestions() -> None:
    provider = MockAutocompleteProvider(
        mapping={"python": ["python tutorial", "python for beginners", "python basics"]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python"], max_depth=1, max_unique_keywords=20, request_budget=10)

    result = engine.crawl(config)
    assert result.stop_reason in (StopReason.QUEUE_EXHAUSTED, StopReason.MAX_DEPTH_REACHED)
    assert len(result.keywords) == 3
    assert all(k.depth == 1 for k in result.keywords)
    assert all("python" in k.parent_queries for k in result.keywords)


# Test 2: Multiple seeds
def test_multiple_seeds() -> None:
    provider = MockAutocompleteProvider(
        mapping={
            "python": ["python tutorial"],
            "javascript": ["javascript tutorial"],
        }
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python", "javascript"], max_depth=0, request_budget=10)

    result = engine.crawl(config)
    assert len(result.keywords) == 2
    keywords = [k.keyword for k in result.keywords]
    assert "python tutorial" in keywords
    assert "javascript tutorial" in keywords
    assert len(provider.call_history) == 2


# Test 3: Depth-zero behavior
def test_depth_zero_behavior() -> None:
    provider = MockAutocompleteProvider(
        mapping={"python": ["python tutorial", "python course"]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python"], max_depth=0, request_budget=10)

    result = engine.crawl(config)
    # Only depth 0 query executed
    assert result.total_requests_made == 1
    assert len(result.keywords) == 2
    assert result.stop_reason in (StopReason.MAX_DEPTH_REACHED, StopReason.QUEUE_EXHAUSTED)


# Test 4: Maximum depth enforcement
def test_maximum_depth_enforcement() -> None:
    provider = MockAutocompleteProvider(
        mapping={
            "python": ["python level 1"],
            "python level 1": ["python level 2"],
            "python level 2": ["python level 3"],
        }
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python"], max_depth=1, max_unique_keywords=20, request_budget=10)

    result = engine.crawl(config)
    keywords = [k.keyword for k in result.keywords]
    assert "python level 1" in keywords
    assert "python level 2" in keywords
    assert "python level 3" not in keywords  # Exceeds max_depth=1
    assert result.stop_reason in (StopReason.MAX_DEPTH_REACHED, StopReason.QUEUE_EXHAUSTED)


# Test 5: Request budget enforcement
def test_request_budget_enforcement() -> None:
    provider = MockAutocompleteProvider(
        default_suggestions=["suggestion a", "suggestion b", "suggestion c"]
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["seed"], max_depth=3, max_unique_keywords=100, request_budget=2)

    result = engine.crawl(config)
    assert result.total_requests_made == 2
    assert result.stop_reason == StopReason.BUDGET_EXHAUSTED
    assert result.is_partial is True


# Test 6: Unique result target enforcement
def test_unique_result_target_enforcement() -> None:
    provider = MockAutocompleteProvider(
        mapping={"python": [f"keyword {i}" for i in range(20)]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python"], max_depth=2, max_unique_keywords=5, request_budget=10)

    result = engine.crawl(config)
    assert len(result.keywords) == 5
    assert result.stop_reason == StopReason.TARGET_REACHED
    assert result.is_partial is False


# Test 7: Duplicate suggestions deduplication
def test_duplicate_suggestions() -> None:
    provider = MockAutocompleteProvider(
        mapping={"python": ["python code", "  python code  ", "PYTHON CODE", "python coding"]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python"], max_depth=1)

    result = engine.crawl(config)
    assert len(result.keywords) == 2
    assert {k.keyword for k in result.keywords} == {"python code", "python coding"}


# Test 8: Multiple discovery paths for one keyword
def test_multiple_discovery_paths_for_one_keyword() -> None:
    provider = MockAutocompleteProvider(
        mapping={
            "python": ["common keyword"],
            "coding": ["common keyword"],
        }
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["python", "coding"], max_depth=1)

    result = engine.crawl(config)
    assert len(result.keywords) == 1
    kw = result.keywords[0]
    assert kw.keyword == "common keyword"
    assert kw.discovery_paths == 2
    assert "python" in kw.parent_queries
    assert "coding" in kw.parent_queries


# Test 9: Bangla Unicode keywords
def test_bangla_unicode_keywords() -> None:
    provider = MockAutocompleteProvider(
        mapping={"পাইথন": ["পাইথন টিউটোরিয়াল", "পাইথন প্রোগ্রামিং"]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["পাইথন"], language="bn", country="BD", max_depth=1)

    result = engine.crawl(config)
    assert len(result.keywords) == 2
    assert any("টিউটোরিয়াল" in k.keyword for k in result.keywords)
    assert any("প্রোগ্রামিং" in k.keyword for k in result.keywords)


# Test 10: Cache hits integration
def test_cache_hits(test_db_manager) -> None:
    from src.providers.youtube import YouTubeAutocompleteProvider
    test_db_manager.set_cached_suggestions("cached query", "en", "US", ["cached item 1", "cached item 2"])
    provider = YouTubeAutocompleteProvider(database_manager=test_db_manager)
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["cached query"], max_depth=0, use_cache=True)

    result = engine.crawl(config)
    assert len(result.keywords) == 2
    assert result.keywords[0].keyword == "cached item 1"


# Test 11: Provider failures preserve partial results
def test_provider_failures_preserve_partial_results() -> None:
    provider = MockAutocompleteProvider(
        mapping={"seed1": ["result 1", "result 2"]},
        error_to_raise=ProviderUnavailableError("Server down"),
        fail_after_n_calls=2,  # 1st call succeeds, 2nd call fails
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["seed1", "seed2"], max_depth=1)

    result = engine.crawl(config)
    assert result.stop_reason == StopReason.PROVIDER_ERROR
    assert result.is_partial is True
    assert len(result.keywords) == 2  # Partial results from seed1 retained!
    assert "Server down" in (result.error_message or "")


# Test 12: Bounded retries
def test_bounded_retries() -> None:
    from unittest.mock import MagicMock
    import requests
    mock_session = MagicMock(spec=requests.Session)
    # Fail once with 500, then succeed with 200
    mock_session.get.side_effect = [
        MagicMock(status_code=500, json=lambda: {}),
        MagicMock(status_code=200, json=lambda: ["retry_seed", ["success item"]]),
    ]
    from src.providers.youtube import YouTubeAutocompleteProvider
    from src.providers.rate_limiter import RateLimiter
    provider = YouTubeAutocompleteProvider(
        max_retries=2,
        backoff_factor=0.01,
        rate_limiter=RateLimiter(0.0),
        session=mock_session,
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["retry_seed"], max_depth=0)

    result = engine.crawl(config)
    assert len(result.keywords) == 1
    assert result.keywords[0].keyword == "success item"


# Test 13: Cancellation stops new requests and preserves partial results
def test_cancellation() -> None:
    token = threading.Event()

    def progress_callback(p: CrawlProgress) -> None:
        if p.keywords_discovered >= 2:
            token.set()  # Cancel after 1st query's keywords are discovered

    provider = MockAutocompleteProvider(
        mapping={
            "seed1": ["result a", "result b"],
            "seed2": ["result c", "result d"],
        }
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["seed1", "seed2"], max_depth=0)

    result = engine.crawl(config, cancellation_token=token, on_progress=progress_callback)
    assert result.stop_reason == StopReason.CANCELLED
    assert result.is_partial is True
    assert len(result.keywords) == 2  # Results from seed1 preserved!
    assert result.total_requests_made == 1


# Test 14: Empty queue termination
def test_empty_queue_termination() -> None:
    provider = MockAutocompleteProvider(default_suggestions=[])
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["empty_seed"], max_depth=2)

    result = engine.crawl(config)
    assert result.stop_reason == StopReason.QUEUE_EXHAUSTED
    assert len(result.keywords) == 0


# Test 15: Maximum queue size enforcement
def test_maximum_queue_size() -> None:
    provider = MockAutocompleteProvider(
        mapping={"seed": [f"item {i}" for i in range(10)]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["seed"], max_depth=2, max_queue_size=3)

    result = engine.crawl(config)
    assert result.stop_reason == StopReason.MAX_QUEUE_SIZE_REACHED


# Test 16: No repeated processing of completed queries
def test_no_repeated_processing_of_completed_queries() -> None:
    provider = MockAutocompleteProvider(
        mapping={
            "seed1": ["shared branch"],
            "seed2": ["shared branch"],
            "shared branch": ["branch child"],
        }
    )
    engine = RecursiveKeywordEngine(provider=provider)
    config = CrawlConfig(seeds=["seed1", "seed2"], max_depth=2)

    result = engine.crawl(config)
    # "shared branch" should only be queried ONCE by provider
    branch_calls = [c for c in provider.call_history if c[0] == "shared branch"]
    assert len(branch_calls) == 1


# Test 17: Correct stop reasons
def test_correct_stop_reasons() -> None:
    # 1. Target reached
    provider = MockAutocompleteProvider(default_suggestions=["a", "b", "c", "d"])
    engine = RecursiveKeywordEngine(provider=provider)
    res = engine.crawl(CrawlConfig(seeds=["s"], max_depth=2, max_unique_keywords=2))
    assert res.stop_reason == StopReason.TARGET_REACHED

    # 2. Budget exhausted
    res = engine.crawl(CrawlConfig(seeds=["s"], max_depth=2, request_budget=1))
    assert res.stop_reason == StopReason.BUDGET_EXHAUSTED


# Test 18: Partial-result preservation
def test_partial_result_preservation() -> None:
    provider = MockAutocompleteProvider(
        mapping={"s1": ["k1", "k2"]},
        error_to_raise=AutocompleteError("Network drop"),
        fail_after_n_calls=2,
    )
    engine = RecursiveKeywordEngine(provider=provider)
    res = engine.crawl(CrawlConfig(seeds=["s1", "s2"], max_depth=1))
    assert res.is_partial is True
    assert len(res.keywords) == 2
    assert [k.keyword for k in res.keywords] == ["k1", "k2"]


def test_parse_seed_inputs() -> None:
    from app import parse_seed_inputs
    raw = "python tutorial, learn python\npython tutorial; পাইথন প্রোগ্রামিং, "
    seeds = parse_seed_inputs(raw)
    assert len(seeds) == 3
    assert "python tutorial" in seeds
    assert "learn python" in seeds
    assert "পাইথন প্রোগ্রামিং" in seeds


def test_execute_recursive_crawl_app_integration(test_db_manager) -> None:
    from app import execute_recursive_crawl
    provider = MockAutocompleteProvider(
        mapping={"seed_app": ["result 1", "result 2"]}
    )
    engine = RecursiveKeywordEngine(provider=provider)
    cfg = CrawlConfig(seeds=["seed_app"], max_depth=0)
    result = execute_recursive_crawl(cfg, engine=engine, save_to_db=False)
    assert len(result.keywords) == 2
    assert result.stop_reason in (StopReason.QUEUE_EXHAUSTED, StopReason.MAX_DEPTH_REACHED)


def test_execute_recursive_crawl_default_engine_instantiation(test_db_manager) -> None:
    """Verify that execute_recursive_crawl instantiates RecursiveKeywordEngine without errors when engine=None."""
    from app import execute_recursive_crawl
    provider = MockAutocompleteProvider(
        mapping={"python basics": ["python basics tutorial", "python basics for beginners"]}
    )
    cfg = CrawlConfig(seeds=["python basics"], max_depth=0)
    result = execute_recursive_crawl(
        cfg,
        provider=provider,
        engine=None,
        save_to_db=True,
        project_name="Test Project Init",
        database_manager=test_db_manager,
    )
    assert len(result.keywords) == 2
    assert result.search_id is not None
    # Verify records were persisted into DB
    saved_keywords = test_db_manager.get_keywords_by_search_id(result.search_id)
    assert len(saved_keywords) == 2
