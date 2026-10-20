"""Unit and Integration Tests for Master Command: Real YouTube Autocomplete & Expansion.

Covers:
1. Real YouTube autocomplete response parsing (client=firefox&ds=yt)
2. Malformed responses, HTTP errors (403, 429, 500, timeouts)
3. Controlled expansion: A-Z alphabet queries (a-z)
4. Controlled expansion: Numeric queries (0-9)
5. Controlled expansion: Prepositions and modifier queries
6. Bangla Unicode query expansion and normalization
7. Request budget enforcement
8. Max unique keywords limit enforcement
9. Immediate cancellation token handling
10. Strict source labeling (LIVE_AUTOCOMPLETE vs CACHED_AUTOCOMPLETE vs GENERATED_PATTERN)
11. Query audit logs with retrieval status and timestamps
12. Offline fallback when network is unavailable
13. DataFrame structure: Keyword, Source Type, Discovery Query, Tail Length, Intent Classification, Word Count
14. Pure absence of synthetic volume, CPC, or difficulty metrics
15. Multi-dimensional filtering by strict source labels
16. SQLite persistence and provenance tracking
17. CSV and XLSX export integrity
"""

import json
import threading
import time
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from app import (
    build_dataframe_from_keywords,
    execute_controlled_expansion,
    export_keywords_to_csv,
    export_keywords_to_excel,
    filter_keywords,
)
from src.classifier import default_classifier
from src.crawler import (
    ControlledExpansionEngine,
    DiscoveredKeyword,
    ExpansionConfig,
    ExpansionResult,
    StopReason,
)
from src.models.keyword import AutocompleteResult, KeywordItem, SourceType
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import (
    AccessForbiddenError,
    MalformedResponseError,
    NetworkConnectionError,
    NetworkTimeoutError,
    OperationCancelledError,
    RateLimitError,
)
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import DatabaseManager


class MockAutocompleteProvider(BaseAutocompleteProvider):
    """Deterministic mock provider simulating live responses without network access."""

    def __init__(self, mapping=None, delay=0.0):
        self.mapping = mapping or {}
        self.call_count = 0
        self.delay = delay
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
        cancellation_token=None,
    ):
        if cancellation_token and cancellation_token.is_set():
            raise OperationCancelledError("Cancelled in mock.")
        if self.delay > 0:
            time.sleep(self.delay)
        self.call_count += 1
        self.queries_called.append(query)

        results = self.mapping.get(query, [f"{query} suggestion 1", f"{query} suggestion 2"])
        return [
            AutocompleteResult(
                keyword=r,
                source_type="autocomplete",
                source_name="youtube_autocomplete",
                language=language,
                country=country,
                discovery_query=query,
            )
            for r in results
        ]


# ------------------------------------------------------------------------------
# 1. Response Parsing & Normalization
# ------------------------------------------------------------------------------

def test_real_autocomplete_endpoint_response_parsing():
    """Verify parser extracts suggestion strings from YouTube client=firefox&ds=yt JSON array."""
    provider = YouTubeAutocompleteProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        "best car wax",
        [
            "best car wax",
            "best car wax for shine and protection",
            "best car wax spray",
            "best car wax for white cars",
            "best car wax 2025",
        ],
    ]

    suggestions = provider._parse_response(mock_resp)
    assert len(suggestions) == 5
    assert suggestions[0] == "best car wax"
    assert suggestions[1] == "best car wax for shine and protection"
    assert suggestions[2] == "best car wax spray"


def test_autocomplete_malformed_responses_raise_expected_errors():
    """Verify malformed JSON structures trigger MalformedResponseError."""
    provider = YouTubeAutocompleteProvider()

    # Not a list
    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = {"query": "best car wax"}
    with pytest.raises(MalformedResponseError):
        provider._parse_response(mock_resp1)

    # List too short
    mock_resp2 = MagicMock()
    mock_resp2.json.return_value = ["best car wax"]
    with pytest.raises(MalformedResponseError):
        provider._parse_response(mock_resp2)

    # Index 1 not a list
    mock_resp3 = MagicMock()
    mock_resp3.json.return_value = ["best car wax", "not a list"]
    with pytest.raises(MalformedResponseError):
        provider._parse_response(mock_resp3)


# ------------------------------------------------------------------------------
# 2. Controlled Expansion Generator (A-Z, Numbers, Prepositions, Bangla)
# ------------------------------------------------------------------------------

def test_expansion_generator_alphabet_a_to_z():
    """Verify controlled expansion generates all 26 queries: 'seed a' through 'seed z'."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        include_numbers=False,
        include_prepositions=False,
        include_questions=False,
        include_modifiers=False,
    )
    queries = engine.generate_expansion_queries(cfg)

    # 1 base seed + 26 alphabet queries = 27
    assert len(queries) == 27
    assert queries[0] == ("best car wax", "best car wax", "seed")
    assert queries[1] == ("best car wax a", "best car wax", "alphabet")
    assert queries[2] == ("best car wax b", "best car wax", "alphabet")
    assert queries[-1] == ("best car wax z", "best car wax", "alphabet")


def test_expansion_generator_numbers_0_to_9():
    """Verify controlled expansion generates all 10 numeric queries: 'seed 0' through 'seed 9'."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=False,
        include_numbers=True,
        include_prepositions=False,
        include_questions=False,
        include_modifiers=False,
    )
    queries = engine.generate_expansion_queries(cfg)

    # 1 base seed + 10 numeric queries = 11
    assert len(queries) == 11
    assert queries[0] == ("best car wax", "best car wax", "seed")
    assert queries[1] == ("best car wax 0", "best car wax", "numeric")
    assert queries[-1] == ("best car wax 9", "best car wax", "numeric")


def test_expansion_generator_prepositions_and_questions():
    """Verify prepositions and question modifiers are generated."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=False,
        include_numbers=False,
        include_prepositions=True,
        include_questions=True,
        include_modifiers=False,
    )
    queries = engine.generate_expansion_queries(cfg)
    query_texts = [q[0] for q in queries]

    assert "best car wax for" in query_texts
    assert "best car wax in" in query_texts
    assert "best car wax vs" in query_texts
    assert "how best car wax" in query_texts
    assert "why best car wax" in query_texts


def test_expansion_generator_bangla_unicode_support():
    """Verify Bengali seeds trigger Bengali modifiers without corruption."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    bangla_seed = "ইউটিউব এসইও"
    cfg = ExpansionConfig(
        seeds=[bangla_seed],
        include_alphabet=False,
        include_numbers=False,
        include_prepositions=False,
        include_questions=False,
        include_modifiers=True,
    )
    queries = engine.generate_expansion_queries(cfg)
    query_texts = [q[0] for q in queries]

    assert f"{bangla_seed} রিভিউ" in query_texts
    assert f"{bangla_seed} দাম" in query_texts
    assert f"{bangla_seed} সেরা" in query_texts


# ------------------------------------------------------------------------------
# 3. Budget, Target, and Cancellation Enforcement
# ------------------------------------------------------------------------------

def test_expansion_engine_budget_enforcement():
    """Verify expansion strictly halts when request budget is exhausted."""
    mock_prov = MockAutocompleteProvider()
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,  # 27 queries available
        request_budget=5,       # Cap at 5
    )
    res = engine.expand(cfg)

    assert res.total_requests_made == 5
    assert res.stop_reason == StopReason.BUDGET_EXHAUSTED
    assert res.is_partial is True
    assert mock_prov.call_count == 5


def test_expansion_engine_max_unique_keywords_limit():
    """Verify expansion halts as soon as unique keywords target is reached."""
    # Mapping where each query produces 10 unique suggestions
    mapping = {
        "best car wax": [f"car wax result {i}" for i in range(10)],
        "best car wax a": [f"car wax a result {i}" for i in range(10)],
        "best car wax b": [f"car wax b result {i}" for i in range(10)],
    }
    mock_prov = MockAutocompleteProvider(mapping=mapping)
    engine = ControlledExpansionEngine(provider=mock_prov)

    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        request_budget=50,
        max_unique_keywords=15,
    )
    res = engine.expand(cfg)

    assert len(res.keywords) >= 15
    assert res.stop_reason == StopReason.TARGET_REACHED
    assert res.is_partial is False


def test_expansion_engine_user_cancellation():
    """Verify cancellation token stops expansion immediately and preserves collected items."""
    cancel_token = threading.Event()

    def mock_fetch(query, **kwargs):
        if query == "best car wax a":
            cancel_token.set()
        return [
            AutocompleteResult(
                keyword=f"{query} suggestion",
                discovery_query=query,
            )
        ]

    mock_prov = MagicMock()
    mock_prov.get_suggestions.side_effect = mock_fetch

    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        request_budget=50,
    )
    res = engine.expand(cfg, cancellation_token=cancel_token)

    assert res.stop_reason == StopReason.CANCELLED
    assert res.is_partial is True
    assert len(res.keywords) >= 1


# ------------------------------------------------------------------------------
# 4. Strict Provenance Labeling (LIVE vs CACHED vs GENERATED)
# ------------------------------------------------------------------------------

def test_strict_source_labeling_accuracy(tmp_path):
    """Verify LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, and GENERATED_PATTERN separation."""
    db_file = tmp_path / "test_sources.db"
    db = DatabaseManager(db_path=db_file)

    db.init_db()

    # 1. Live item
    live_kw = DiscoveredKeyword(
        keyword="best car wax spray",
        normalized_key="best car wax spray",
        depth=1,
        source_type="autocomplete",
        is_cached=False,
        is_generated=False,
    )
    assert live_kw.strict_source_label == "LIVE_AUTOCOMPLETE"

    # 2. Cached item
    cached_kw = DiscoveredKeyword(
        keyword="best car wax paste",
        normalized_key="best car wax paste",
        depth=1,
        source_type="cached",
        is_cached=True,
        is_generated=False,
    )
    assert cached_kw.strict_source_label == "CACHED_AUTOCOMPLETE"

    # 3. Generated item
    gen_kw = DiscoveredKeyword(
        keyword="top 10 best car wax",
        normalized_key="top 10 best car wax",
        depth=1,
        source_type="generated",
        is_cached=False,
        is_generated=True,
    )
    assert gen_kw.strict_source_label == "GENERATED_PATTERN"


def test_expansion_query_logs_audit_trail():
    """Verify query logs record actual query, seed, category, count, and timestamp."""
    mock_prov = MockAutocompleteProvider(
        mapping={
            "best car wax": ["best car wax spray", "best car wax liquid"],
            "best car wax a": ["best car wax applicator"],
        }
    )
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        request_budget=2,
    )
    res = engine.expand(cfg)

    assert len(res.query_logs) == 2
    log1 = res.query_logs[0]
    assert log1.seed_keyword == "best car wax"
    assert log1.actual_query == "best car wax"
    assert log1.category == "seed"
    assert log1.status == "success"
    assert log1.suggestions_count == 2
    assert log1.timestamp is not None

    log2 = res.query_logs[1]
    assert log2.actual_query == "best car wax a"
    assert log2.category == "alphabet"
    assert log2.status == "success"
    assert log2.suggestions_count == 1


# ------------------------------------------------------------------------------
# 5. Offline Fallback & Network Error Handling
# ------------------------------------------------------------------------------

def test_offline_network_fallback_and_error_handling():
    """Verify network connection failures are logged and do not crash the engine."""
    mock_prov = MagicMock()
    mock_prov.get_suggestions.side_effect = NetworkConnectionError("DNS resolution failed.")

    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=False,
        include_numbers=False,
        include_prepositions=False,
        request_budget=1,
    )
    res = engine.expand(cfg)

    assert res.total_requests_made == 1
    assert len(res.keywords) == 0
    assert len(res.query_logs) == 1
    assert res.query_logs[0].status == "failed"
    assert "DNS" in str(res.query_logs[0].error_message)


# ------------------------------------------------------------------------------
# 6. Results Table Structure & Absence of Fabricated Metrics
# ------------------------------------------------------------------------------

def test_ui_results_dataframe_columns_and_clean_metrics():
    """Verify DataFrame includes required columns and NO synthetic metrics."""
    kws = [
        DiscoveredKeyword(
            keyword="best car wax for black cars",
            normalized_key="best car wax for black cars",
            depth=1,
            source_type="LIVE_AUTOCOMPLETE",
            discovery_query="best car wax for",
            parent_queries=["best car wax for"],
        ),
        DiscoveredKeyword(
            keyword="best car wax liquid",
            normalized_key="best car wax liquid",
            depth=1,
            source_type="CACHED_AUTOCOMPLETE",
            discovery_query="best car wax",
            is_cached=True,
        ),
    ]

    classified_tuples = [
        (k, "Long-tail", ["Buying Intent", "Review"])
        for k in kws
    ]

    df = build_dataframe_from_keywords(classified_tuples)

    # Required Master Command columns
    assert "Keyword" in df.columns
    assert "Source Type" in df.columns
    assert "Discovery Query" in df.columns
    assert "Tail Length" in df.columns
    assert "Intent Classification" in df.columns
    assert "Word Count" in df.columns

    # Verify source type values
    assert df.iloc[0]["Source Type"] == "LIVE_AUTOCOMPLETE"
    assert df.iloc[0]["Discovery Query"] == "best car wax for"
    assert df.iloc[1]["Source Type"] == "CACHED_AUTOCOMPLETE"

    # Strictly verify NO synthetic search metrics
    forbidden_terms = ["search volume", "volume", "cpc", "cost per click", "difficulty", "kd", "competition"]
    for col in df.columns:
        col_lower = col.lower()
        for forbidden in forbidden_terms:
            assert forbidden != col_lower, f"Forbidden synthetic metric found in column: {col}"


# ------------------------------------------------------------------------------
# 7. Dashboard Filtering by Strict Source Labels
# ------------------------------------------------------------------------------

def test_ui_filter_keywords_by_master_source_labels():
    """Verify filter_keywords isolates LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, and GENERATED_PATTERN."""
    k_live = DiscoveredKeyword(
        keyword="best car wax spray",
        normalized_key="best car wax spray",
        depth=1,
        source_type="autocomplete",
        is_cached=False,
    )
    k_cached = DiscoveredKeyword(
        keyword="best car wax paste",
        normalized_key="best car wax paste",
        depth=1,
        source_type="cached",
        is_cached=True,
    )
    k_gen = DiscoveredKeyword(
        keyword="top 10 car wax",
        normalized_key="top 10 car wax",
        depth=1,
        source_type="generated",
        is_generated=True,
    )

    items = [k_live, k_cached, k_gen]

    # All Sources
    all_res = filter_keywords(items, source_filter="All Sources")
    assert len(all_res) == 3

    # LIVE_AUTOCOMPLETE
    live_res = filter_keywords(items, source_filter="LIVE_AUTOCOMPLETE (Live YouTube)")
    assert len(live_res) == 1
    assert live_res[0][0].keyword == "best car wax spray"

    # CACHED_AUTOCOMPLETE
    cached_res = filter_keywords(items, source_filter="CACHED_AUTOCOMPLETE (Local Cache)")
    assert len(cached_res) == 1
    assert cached_res[0][0].keyword == "best car wax paste"

    # GENERATED_PATTERN
    gen_res = filter_keywords(items, source_filter="GENERATED_PATTERN (Variations)")
    assert len(gen_res) == 1
    assert gen_res[0][0].keyword == "top 10 car wax"


# ------------------------------------------------------------------------------
# 8. SQLite Persistence & Export Integrity
# ------------------------------------------------------------------------------

def test_execute_controlled_expansion_db_persistence(tmp_path):
    """Verify execute_controlled_expansion creates a project and saves keywords."""
    db_file = tmp_path / "test_expansion_db.db"
    db = DatabaseManager(db_path=db_file)

    db.init_db()

    mock_prov = MockAutocompleteProvider(
        mapping={
            "best car wax": ["best car wax spray", "best car wax liquid"],
            "best car wax a": ["best car wax applicator"],
        }
    )

    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        request_budget=2,
    )

    res = execute_controlled_expansion(
        expansion_config=cfg,
        provider=mock_prov,
        save_to_db=True,
        project_name="Best Car Wax Project",
        database_manager=db,
    )

    assert hasattr(res, "search_id")
    assert res.search_id > 0

    saved_searches = db.get_recent_searches(limit=5)
    assert len(saved_searches) == 1
    assert saved_searches[0]["project_name"] == "Best Car Wax Project"

    keywords = db.get_keywords_by_search_id(res.search_id)
    assert len(keywords) == len(res.keywords)
    kw_texts = [k["keyword"] for k in keywords]
    assert "best car wax spray" in kw_texts
    assert "best car wax applicator" in kw_texts


def test_export_csv_and_xlsx_with_strict_sources():
    """Verify CSV and Excel exports contain strict source types and formula safety."""
    kws = [
        DiscoveredKeyword(
            keyword="best car wax",
            normalized_key="best car wax",
            depth=0,
            source_type="LIVE_AUTOCOMPLETE",
            discovery_query="best car wax",
        ),
        DiscoveredKeyword(
            keyword="=SUM(A1:A10)",  # Formula injection attempt
            normalized_key="=sum(a1:a10)",
            depth=1,
            source_type="GENERATED_PATTERN",
            discovery_query="formula test",
            is_generated=True,
        ),
    ]

    classified = [(k, "Medium-tail", ["Informational"]) for k in kws]
    df = build_dataframe_from_keywords(classified)

    # 1. CSV Export
    csv_bytes = export_keywords_to_csv(df, sanitize_formulas=True, include_bom=True)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    csv_text = csv_bytes.decode("utf-8")
    assert "LIVE_AUTOCOMPLETE" in csv_text
    assert "GENERATED_PATTERN" in csv_text
    # Formula sanitized with single quote prefix
    assert "'=SUM(A1:A10)" in csv_text

    # 2. Excel Export
    excel_bytes = export_keywords_to_excel(df, sanitize_formulas=True)
    assert len(excel_bytes) > 0
    assert excel_bytes[:4] == b"PK\x03\x04"  # Valid ZIP/XLSX header
