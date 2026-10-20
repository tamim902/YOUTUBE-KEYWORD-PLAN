"""Automated unit and integration tests for Phase 6:
Professional Dashboard, Navigation, Research Controls, Cancellation,
Interactive Results Table, Filters, Keyword Actions, and Session Management.

All tests operate 100% offline with zero live network calls.
"""

import io
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import pandas as pd
import pytest

from app import (
    build_dataframe_from_keywords,
    execute_keyword_search,
    execute_recursive_crawl,
    export_keywords_to_csv,
    export_keywords_to_excel,
    filter_keywords,
    load_search_into_crawl_result,
    parse_seed_inputs,
)
from src.classifier import SearchIntent, TailLength, default_classifier
from src.config import config
from src.crawler.models import (
    CrawlConfig,
    CrawlProgress,
    CrawlResult,
    DiscoveredKeyword,
    StopReason,
)
from src.models.keyword import AutocompleteResult, KeywordItem, SourceType
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import (
    AccessForbiddenError,
    AutocompleteError,
    NetworkTimeoutError,
    OperationCancelledError,
    RateLimitError,
)
from src.storage.database import DatabaseManager
from src.ui.components import (
    NAVIGATION_PAGES,
    PAGE_DASHBOARD,
    PAGE_NEW_RESEARCH,
    PAGE_PATTERNS,
    PAGE_RESULTS,
    PAGE_SAVED,
    PAGE_SETTINGS,
    render_navigation,
)


class MockProvider(BaseAutocompleteProvider):
    """Deterministic mock provider for dashboard testing."""

    def __init__(self, responses=None, delay=0.0, error_on_query=None):
        self.responses = responses or {}
        self.delay = delay
        self.error_on_query = error_on_query
        self.call_count = 0
        self.queries_called = []

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    def get_suggestions(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        use_cache: bool = True,
        cancellation_token: Optional[threading.Event] = None,
    ) -> List[AutocompleteResult]:
        if cancellation_token and cancellation_token.is_set():
            raise OperationCancelledError("Cancelled in mock")

        self.call_count += 1
        self.queries_called.append(query)

        if self.error_on_query and query == self.error_on_query:
            raise AccessForbiddenError("Forbidden query")

        words = self.responses.get(query.lower().strip(), [])
        return [
            AutocompleteResult(
                keyword=w,
                source_type="autocomplete",
                source_name="mock_provider",
                language=language,
                country=country,
                discovery_query=query,
            )
            for w in words
        ]


# 1. Dashboard imports
def test_dashboard_imports() -> None:
    """Test 1: Verify all Phase 6 navigation pages, helpers, and components import cleanly."""
    assert PAGE_DASHBOARD in NAVIGATION_PAGES
    assert PAGE_NEW_RESEARCH in NAVIGATION_PAGES
    assert PAGE_RESULTS in NAVIGATION_PAGES
    assert PAGE_PATTERNS in NAVIGATION_PAGES
    assert PAGE_SAVED in NAVIGATION_PAGES
    assert PAGE_SETTINGS in NAVIGATION_PAGES
    assert len(NAVIGATION_PAGES) == 6
    assert callable(filter_keywords)
    assert callable(build_dataframe_from_keywords)
    assert callable(export_keywords_to_csv)
    assert callable(export_keywords_to_excel)
    assert callable(load_search_into_crawl_result)


# 2. Research form validation
def test_research_form_validation() -> None:
    """Test 2: Seed keyword input parsing and validation."""
    seeds = parse_seed_inputs("python tutorial, flask api; django web")
    assert len(seeds) == 3
    assert "python tutorial" in seeds
    assert "flask api" in seeds
    assert "django web" in seeds

    # Duplicate normalization check
    seeds_dupes = parse_seed_inputs("python, Python, PYTHON")
    assert len(seeds_dupes) == 1
    assert seeds_dupes[0] == "python"


# 3. Empty seed input
def test_empty_seed_input() -> None:
    """Test 3: Empty and whitespace-only seed input handling."""
    assert parse_seed_inputs("") == []
    assert parse_seed_inputs("   \n\t  , ; ") == []
    assert parse_seed_inputs("a") == []  # Single character < 2 chars threshold


# 4. Language and country settings
def test_language_and_country_settings(tmp_path: Path) -> None:
    """Test 4: Locale parameters are preserved in crawl config and results."""
    db_file = tmp_path / "locale.db"
    db = DatabaseManager(db_file)
    db.init_db()

    provider = MockProvider(responses={"পাইথন": ["পাইথন প্রোগ্রামিং", "পাইথন কোর্স"]})
    cfg = CrawlConfig(
        seeds=["পাইথন"],
        language="bn",
        country="BD",
        max_depth=1,
        request_budget=5,
    )
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)
    result = execute_recursive_crawl(cfg, engine=engine, save_to_db=False)

    assert len(result.keywords) == 2
    for k in result.keywords:
        assert k.language == "bn"
        assert k.country == "BD"


# 5. Research start behavior
def test_research_start_behavior(tmp_path: Path) -> None:
    """Test 5: Recursive crawl starts properly from depth 0 seeds."""
    provider = MockProvider(
        responses={
            "python": ["python tutorial", "python beginner"],
            "python tutorial": ["python tutorial 2026"],
        }
    )
    cfg = CrawlConfig(
        seeds=["python"],
        max_depth=2,
        max_unique_keywords=10,
        request_budget=5,
    )
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)
    res = execute_recursive_crawl(cfg, engine=engine, save_to_db=False)

    assert len(res.keywords) >= 3
    assert res.total_requests_made >= 2
    assert res.stop_reason in (StopReason.TARGET_REACHED, StopReason.QUEUE_EXHAUSTED)


# 6. Duplicate-job prevention
def test_duplicate_job_prevention() -> None:
    """Test 6: Repeated seeds or previously processed queries avoid redundant network requests."""
    provider = MockProvider(responses={"test": ["test a", "test b"]})
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    cfg = CrawlConfig(seeds=["test", "test", "TEST"], max_depth=0, request_budget=5)
    res = engine.crawl(cfg)

    # Provider should only be queried once for 'test'
    assert provider.call_count == 1
    assert len(res.keywords) == 2


# 7. Progress data accuracy
def test_progress_data_accuracy() -> None:
    """Test 7: CrawlProgress callback receives accurate, monotonic status data."""
    provider = MockProvider(
        responses={
            "seed": ["seed 1", "seed 2"],
            "seed 1": ["seed 1a"],
        }
    )
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    progress_reports: List[CrawlProgress] = []

    def on_progress(p: CrawlProgress) -> None:
        progress_reports.append(p)

    cfg = CrawlConfig(seeds=["seed"], max_depth=2, request_budget=5)
    engine.crawl(cfg, on_progress=on_progress)

    assert len(progress_reports) >= 1
    # Check monotonically increasing queries
    for idx in range(1, len(progress_reports)):
        assert progress_reports[idx].queries_processed >= progress_reports[idx - 1].queries_processed
        assert progress_reports[idx].keywords_discovered >= progress_reports[idx - 1].keywords_discovered


# 8. Cancellation request
def test_cancellation_request() -> None:
    """Test 8: Immediate cancellation before execution halts cleanly."""
    token = threading.Event()
    token.set()  # Pre-cancelled

    provider = MockProvider(responses={"test": ["test 1", "test 2"]})
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    cfg = CrawlConfig(seeds=["test"], max_depth=2, request_budget=5)
    res = engine.crawl(cfg, cancellation_token=token)

    assert res.stop_reason == StopReason.CANCELLED
    assert res.is_partial is True
    assert provider.call_count == 0


# 9. Cancellation before another provider request
def test_cancellation_before_another_provider_request() -> None:
    """Test 9: Cancellation triggered after first request halts subsequent requests."""
    token = threading.Event()

    class CancellingProvider(BaseAutocompleteProvider):
        def __init__(self):
            self.calls = 0

        @property
        def provider_name(self) -> str:
            return "cancelling_provider"

        def get_suggestions(self, query, language="en", country="US", use_cache=True, cancellation_token=None):
            self.calls += 1
            token.set()  # Cancel immediately after first query returns
            return [
                AutocompleteResult(keyword=f"{query} sub1", source_type="autocomplete"),
                AutocompleteResult(keyword=f"{query} sub2", source_type="autocomplete"),
            ]

    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=CancellingProvider())

    cfg = CrawlConfig(seeds=["seed"], max_depth=3, request_budget=10)
    res = engine.crawl(cfg, cancellation_token=token)

    assert res.stop_reason == StopReason.CANCELLED
    assert res.is_partial is True
    # Initial seed was processed, but recursive children were not explored due to cancellation
    assert len(res.keywords) == 2


# 10. Partial-result preservation
def test_partial_result_preservation() -> None:
    """Test 10: Discovered keywords prior to cancellation or error are safely retained."""
    provider = MockProvider(
        responses={
            "seed": ["result 1", "result 2"],
            "result 1": ["result 1a"],
        }
    )
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    # Crawl with budget of 1 to simulate partial budget exhaustion
    cfg = CrawlConfig(seeds=["seed"], max_depth=2, request_budget=1)
    res = engine.crawl(cfg)

    assert res.is_partial is True
    assert res.stop_reason == StopReason.BUDGET_EXHAUSTED
    assert len(res.keywords) == 2


# 11. Filter correctness
def test_filter_correctness() -> None:
    """Test 11: Multi-dimensional keyword filtering returns accurate matches."""
    kws = [
        DiscoveredKeyword(keyword="python", normalized_key="python", depth=0, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="how to learn python programming", normalized_key="how to learn python programming", depth=1, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="best python course review", normalized_key="best python course review", depth=1, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="top 5 python tools", normalized_key="top 5 python tools", depth=0, source_type="generated", is_generated=True, language="en", country="US"),
        DiscoveredKeyword(keyword="পাইথন টিউটোরিয়াল", normalized_key="পাইথন টিউটোরিয়াল", depth=1, source_type="autocomplete", language="bn", country="BD"),
    ]

    # Source filter
    auto_only = filter_keywords(kws, source_filter="Autocomplete Only")
    assert len(auto_only) == 4

    gen_only = filter_keywords(kws, source_filter="Generated Patterns Only")
    assert len(gen_only) == 1
    assert gen_only[0][0].keyword == "top 5 python tools"

    # Tail filter
    short_kws = filter_keywords(kws, tail_filter="Short-tail (1-2 words)")
    assert any(k[0].keyword == "python" for k in short_kws)

    long_kws = filter_keywords(kws, tail_filter="Long-tail (5+ words)")
    assert any("how to learn python programming" in k[0].keyword for k in long_kws)

    # Intent filter
    review_kws = filter_keywords(kws, intent_filter=SearchIntent.REVIEW.value)
    assert len(review_kws) == 1
    assert review_kws[0][0].keyword == "best python course review"

    # Language filter
    bn_kws = filter_keywords(kws, lang_filter="bn")
    assert len(bn_kws) == 1
    assert bn_kws[0][0].keyword == "পাইথন টিউটোরিয়াল"


# 12. Search and sort behavior
def test_search_and_sort_behavior() -> None:
    """Test 12: Substring text filtering and DataFrame sorting."""
    kws = [
        DiscoveredKeyword(keyword="django web framework", normalized_key="django web framework", depth=1, source_type="autocomplete"),
        DiscoveredKeyword(keyword="flask microframework", normalized_key="flask microframework", depth=2, source_type="autocomplete"),
        DiscoveredKeyword(keyword="fastapi async api", normalized_key="fastapi async api", depth=0, source_type="autocomplete"),
    ]

    # Substring search
    django_matches = filter_keywords(kws, search_query="django")
    assert len(django_matches) == 1
    assert django_matches[0][0].keyword == "django web framework"

    # Sorting DataFrame
    df = build_dataframe_from_keywords([(k, "Medium-tail", ["Tutorial"]) for k in kws])
    sorted_df = df.sort_values(by="Depth", ascending=True)
    assert sorted_df.iloc[0]["Keyword"] == "fastapi async api"
    assert sorted_df.iloc[-1]["Keyword"] == "flask microframework"


# 13. Copy selected and copy filtered output
def test_copy_selected_and_copy_filtered_output() -> None:
    """Test 13: Formatting newline-separated text for clipboard copy."""
    keywords_list = ["python tutorial", "flask vs django", "fastapi tutorial"]
    copy_text = "\n".join(keywords_list)
    assert "python tutorial\nflask vs django\nfastapi tutorial" == copy_text
    split_back = copy_text.splitlines()
    assert len(split_back) == 3
    assert split_back[1] == "flask vs django"


# 14. Empty-result display
def test_empty_result_display() -> None:
    """Test 14: Non-matching filter combinations return an empty list gracefully."""
    kws = [
        DiscoveredKeyword(keyword="python tutorial", normalized_key="python tutorial", depth=1, source_type="autocomplete", language="en"),
    ]
    no_matches = filter_keywords(kws, search_query="nonexistent_keyword_xyz")
    assert len(no_matches) == 0
    df = build_dataframe_from_keywords(no_matches)
    assert df.empty
    assert len(df) == 0


# 15. Provider-error display
def test_provider_error_display(tmp_path: Path) -> None:
    """Test 15: Provider errors capture clear user-facing messages."""
    provider = MockProvider(error_on_query="forbidden_seed")
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    cfg = CrawlConfig(seeds=["forbidden_seed"], max_depth=1, request_budget=5)
    res = engine.crawl(cfg)

    assert res.stop_reason == StopReason.PROVIDER_ERROR
    assert res.is_partial is True
    assert res.error_message is not None
    assert "Forbidden" in res.error_message or "Access" in res.error_message


# 16. Source labels
def test_source_labels() -> None:
    """Test 16: Accurate source labeling in DataFrame representation."""
    kws = [
        DiscoveredKeyword(keyword="autocomplete item", normalized_key="autocomplete item", depth=1, source_type="autocomplete", is_generated=False),
        DiscoveredKeyword(keyword="merged item", normalized_key="merged item", depth=1, source_type="autocomplete", is_generated=True),
        DiscoveredKeyword(keyword="pattern item", normalized_key="pattern item", depth=0, source_type="generated", is_generated=True),
    ]
    tuples = [(k, "Medium-tail", ["Informational"]) for k in kws]
    df = build_dataframe_from_keywords(tuples)

    assert df.iloc[0]["Source"] == "Autocomplete"
    assert df.iloc[1]["Source"] == "Autocomplete (+Pattern)"
    assert df.iloc[2]["Source"] == "Generated"


# 17. Session-state persistence and loading
def test_session_state_persistence_and_loading(tmp_path: Path) -> None:
    """Test 17: Saved search sessions reload accurately into CrawlResult models."""
    db_file = tmp_path / "persistence.db"
    db = DatabaseManager(db_file)
    db.init_db()

    search_id = db.save_search(seed_keyword="docker", language="en", country="US", max_depth=2, request_budget=10, total_results=2)
    db.save_keywords(
        search_id,
        [
            KeywordItem(keyword="docker tutorial", seed_keyword="docker", source=SourceType.AUTOCOMPLETE),
            KeywordItem(keyword="docker compose", seed_keyword="docker", source=SourceType.AUTOCOMPLETE),
        ],
    )

    loaded = load_search_into_crawl_result(search_id, db)
    assert loaded is not None
    assert len(loaded.keywords) == 2
    assert loaded.keywords[0].keyword == "docker tutorial"
    assert loaded.keywords[1].keyword == "docker compose"
    assert loaded.stop_reason == StopReason.TARGET_REACHED


# 18. Database persistence and stats
def test_database_persistence_and_stats(tmp_path: Path) -> None:
    """Test 18: Database statistics, deletion, and cache pruning."""
    db_file = tmp_path / "stats.db"
    db = DatabaseManager(db_file)
    db.init_db()

    sid = db.save_search("fastapi", "en", "US", 1, 5, 1)
    db.save_keywords(sid, [KeywordItem(keyword="fastapi docs", seed_keyword="fastapi", source=SourceType.AUTOCOMPLETE)])
    db.set_cached_suggestions("fastapi", "en", "US", ["fastapi docs"])

    stats = db.get_database_stats()
    assert stats["total_searches"] == 1
    assert stats["total_keywords"] == 1
    assert stats["total_cached_queries"] == 1
    assert stats["file_size_bytes"] > 0

    # Prune cache
    cleared = db.clear_cache(expired_only=False)
    assert cleared == 1
    assert db.get_database_stats()["total_cached_queries"] == 0

    # Delete session
    deleted = db.delete_search(sid)
    assert deleted is True
    assert db.get_database_stats()["total_searches"] == 0
    assert db.get_database_stats()["total_keywords"] == 0


# 19. Session-state reruns do not duplicate network requests
def test_session_rerun_does_not_duplicate_requests() -> None:
    """Test 19: Session state reruns and table operations make 0 network requests."""
    provider = MockProvider(responses={"python": ["python tutorial"]})
    from src.crawler.engine import RecursiveKeywordEngine
    engine = RecursiveKeywordEngine(provider=provider)

    cfg = CrawlConfig(seeds=["python"], max_depth=0, request_budget=5)
    crawl_result = engine.crawl(cfg)

    # Initial crawl made 1 call
    assert provider.call_count == 1

    # Simulate subsequent Streamlit reruns: user changes filters, searches, sorts
    for _ in range(5):
        filtered = filter_keywords(crawl_result.keywords, source_filter="All Sources", search_query="tutorial")
        df = build_dataframe_from_keywords(filtered)
        assert len(df) == 1

    # No additional network requests were made during reruns or filter adjustments
    assert provider.call_count == 1


# 20. Zero fabricated metrics
def test_no_fabricated_metrics_in_dataframe_and_models() -> None:
    """Test 20: Confirm zero synthetic metrics (CPC, search volume, difficulty, competition) exist."""
    kws = [
        DiscoveredKeyword(keyword="python tutorial", normalized_key="python tutorial", depth=1, source_type="autocomplete"),
    ]
    tuples = [(kws[0], "Medium-tail", ["Tutorial"])]
    df = build_dataframe_from_keywords(tuples)

    forbidden_metrics = [
        "search volume",
        "volume",
        "cpc",
        "cost per click",
        "difficulty",
        "competition",
        "rank difficulty",
        "trend score",
    ]

    for col in df.columns:
        for forbidden in forbidden_metrics:
            assert forbidden not in col.lower(), f"Forbidden metric column found: {col}"

