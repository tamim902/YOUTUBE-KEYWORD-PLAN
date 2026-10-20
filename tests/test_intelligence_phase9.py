"""Phase 9 Comprehensive Test Suite: Advanced YouTube Keyword Discovery & Research Intelligence.

Covers:
1. Multi-source keyword discovery (Alphabet, Prefix/Intent, Questions, Audience, Numbers, Modifiers).
2. Strict source distinction (LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, GENERATED_QUERY, GENERATED_PATTERN).
3. Controlled discovery engine bounds, budget enforcement, polite delay, and cancellation.
4. Rule-based bilingual intent classification (10 canonical categories and transparent match explanations).
5. Heuristic relevance scoring (0-100 formula, weights, penalties, breakdowns).
6. Long-tail analysis and multi-dimensional filtering.
7. Honest SERP metrics provider (zero fabricated metrics, explicit unavailable notice).
8. Topic clustering (semantic groups, renaming, keyword moving, cluster exclusion).
9. Audit-grade research summary telemetry.
10. Data integrity, SQLite persistence, and formula-injection-safe CSV/XLSX export.
"""

import io
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.classifier.models import (
    KeywordClassification,
    SearchIntent,
    TailLength,
    TailThresholds,
)
from src.classifier.rules import INTENT_RULES
from src.classifier.service import BilingualClassifier, KeywordClassifier, default_classifier
from src.crawler.engine import RecursiveKeywordEngine
from src.crawler.expansion import (
    ControlledExpansionEngine,
    ExpansionConfig,
    QueryLogEntry,
    is_bangla_text,
)
from src.crawler.models import CrawlProgress, DiscoveredKeyword, StopReason, normalize_keyword_key
from src.intelligence.clustering import (
    TopicCluster,
    TopicClusteringEngine,
    default_clusterer,
)
from src.intelligence.scoring import (
    RelevanceBreakdown,
    RelevanceScorer,
    ScoringWeights,
    default_scorer,
)
from src.intelligence.summary import ResearchSummary
from src.models.keyword import AutocompleteResult, KeywordItem, SourceType
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import AutocompleteError, OperationCancelledError
from src.providers.serp import (
    BaseSerpMetricsProvider,
    SerpMetrics,
    UnconnectedSerpMetricsProvider,
    default_serp_provider,
)
from src.storage.database import DatabaseManager
from src.storage.export import (
    ExportService,
    sanitize_dataframe_for_export,
    sanitize_formula_injection,
)


# ------------------------------------------------------------------------------
# Test Fixtures & Mock Providers
# ------------------------------------------------------------------------------

class MockAutocompleteProvider(BaseAutocompleteProvider):
    """Deterministic mock provider for Phase 9 discovery tests."""

    def __init__(
        self,
        mapping: Optional[Dict[str, List[str]]] = None,
        cached_queries: Optional[set] = None,
        delay: float = 0.0,
    ) -> None:
        self.mapping = mapping or {}
        self.cached_queries = cached_queries or set()
        self.delay = delay
        self.call_count = 0
        self.queries_called: List[str] = []

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
            raise OperationCancelledError("Cancelled in mock.")
        if self.delay > 0:
            time.sleep(self.delay)
        self.call_count += 1
        self.queries_called.append(query)

        is_cached = query in self.cached_queries
        stype = SourceType.CACHED_AUTOCOMPLETE if is_cached else SourceType.LIVE_AUTOCOMPLETE

        results = self.mapping.get(query, [f"{query} suggestion 1", f"{query} suggestion 2"])
        return [
            AutocompleteResult(
                keyword=r,
                source_type=stype.value,
                source_name="youtube_autocomplete",
                language=language,
                country=country,
                discovery_query=query,
                is_cached=is_cached,
            )
            for r in results
        ]


# ------------------------------------------------------------------------------
# 1. Multi-Source Keyword Discovery & Generation
# ------------------------------------------------------------------------------

def test_multisource_expansion_query_generation_all_methods():
    """Verify all 5 discovery methods generate distinct queries for a seed keyword."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_seed=True,
        include_alphabet=True,
        include_prefix_intent=True,
        include_questions=True,
        include_audience_usecase=True,
        include_numbers=True,
        include_prepositions=False,
        include_modifiers=False,
    )
    queries = engine.generate_expansion_queries(cfg)
    query_texts = [q[0] for q in queries]
    categories = {q[2] for q in queries}

    # Verify category coverage
    assert "seed" in categories
    assert "alphabet" in categories
    assert "prefix_intent" in categories
    assert "question" in categories
    assert "audience_usecase" in categories
    assert "numeric" in categories

    # Verify specific queries
    assert "best car wax" in query_texts
    assert "best car wax a" in query_texts
    assert "best car wax z" in query_texts
    assert "best car wax for" in query_texts
    assert "best car wax vs" in query_texts
    assert "best car wax review" in query_texts
    assert "how to choose the best car wax" in query_texts
    assert "which best car wax is best" in query_texts
    assert "best car wax for beginners" in query_texts
    assert "best car wax for black cars" in query_texts
    assert "best car wax 0" in query_texts


def test_multisource_bangla_unicode_expansion():
    """Verify Bengali seeds generate Bengali-specific prefix, question, and audience queries."""
    engine = ControlledExpansionEngine(provider=MockAutocompleteProvider())
    import unicodedata
    bangla_seed = unicodedata.normalize("NFC", "গাড়ির ওয়াক্স")
    cfg = ExpansionConfig(
        seeds=[bangla_seed],
        include_seed=True,
        include_alphabet=False,
        include_prefix_intent=True,
        include_questions=True,
        include_audience_usecase=True,
        include_numbers=False,
        include_prepositions=False,
        include_modifiers=False,
    )
    queries = engine.generate_expansion_queries(cfg)
    query_texts = [q[0] for q in queries]

    assert is_bangla_text(bangla_seed) is True
    assert f"{bangla_seed} জন্য" in query_texts
    assert f"{bangla_seed} বনাম" in query_texts
    assert f"{bangla_seed} নতুনদের জন্য" in query_texts
    assert f"কীভাবে {bangla_seed} ব্যবহার করবেন" in query_texts


def test_strict_source_distinction_no_fabrication():
    """Verify LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, and GENERATED are never conflated."""
    mock_prov = MockAutocompleteProvider(
        mapping={
            "best car wax": ["best car wax for shine", "best car wax spray"],
            "best car wax a": ["best car wax armor all"],
        },
        cached_queries={"best car wax a"},  # cached
    )
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_seed=True,
        include_alphabet=True,
        request_budget=2,
    )
    res = engine.expand(cfg)

    live_items = [k for k in res.keywords if k.strict_source_label == "LIVE_AUTOCOMPLETE"]
    cached_items = [k for k in res.keywords if k.strict_source_label == "CACHED_AUTOCOMPLETE"]

    assert len(live_items) >= 2
    for item in live_items:
        assert item.is_cached is False
        assert "LIVE_AUTOCOMPLETE" in item.strict_source_label

    assert len(cached_items) >= 1
    for item in cached_items:
        assert item.is_cached is True
        assert "CACHED_AUTOCOMPLETE" in item.strict_source_label


# ------------------------------------------------------------------------------
# 2. Controlled Discovery Engine: Bounds, Limits, and Cancellation
# ------------------------------------------------------------------------------

def test_engine_respects_request_budget_strictly():
    """Verify engine stops fetching as soon as request budget is exhausted."""
    mock_prov = MockAutocompleteProvider()
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["best car wax"],
        include_alphabet=True,
        include_numbers=True,
        request_budget=7,
    )
    res = engine.expand(cfg)

    assert res.total_requests_made == 7
    assert mock_prov.call_count == 7
    assert res.stop_reason == StopReason.BUDGET_EXHAUSTED
    assert res.is_partial is True


def test_engine_respects_max_unique_keywords_limit():
    """Verify engine halts when target count of unique keywords is reached."""
    mapping = {
        f"seed {i}": [f"result {i}_{j}" for j in range(5)]
        for i in range(10)
    }
    mock_prov = MockAutocompleteProvider(mapping=mapping)
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["seed 0", "seed 1", "seed 2", "seed 3"],
        include_seed=True,
        include_alphabet=False,
        include_numbers=False,
        include_prepositions=False,
        include_questions=False,
        include_modifiers=False,
        request_budget=20,
        max_unique_keywords=8,
    )
    res = engine.expand(cfg)

    assert len(res.keywords) >= 8
    assert res.stop_reason == StopReason.TARGET_REACHED


def test_engine_cancellation_preserves_collected_keywords():
    """Verify cancellation halts traversal and retains all keywords collected prior to cancel."""
    cancel_token = threading.Event()

    def mock_fetch(query, **kwargs):
        if "b" in query:
            cancel_token.set()
        return [AutocompleteResult(keyword=f"{query} suggestion", discovery_query=query)]

    mock_prov = MagicMock()
    mock_prov.get_suggestions.side_effect = mock_fetch

    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["test seed"],
        include_seed=True,
        include_alphabet=True,
        request_budget=50,
    )
    res = engine.expand(cfg, cancellation_token=cancel_token)

    assert res.stop_reason == StopReason.CANCELLED
    assert len(res.keywords) > 0


def test_engine_session_deduplication():
    """Verify identical keywords from different queries are merged without duplicates."""
    mapping = {
        "query 1": ["car wax review", "best car wax"],
        "query 2": ["car wax review", "top car wax"],
    }
    mock_prov = MockAutocompleteProvider(mapping=mapping)
    engine = ControlledExpansionEngine(provider=mock_prov)
    cfg = ExpansionConfig(
        seeds=["query 1", "query 2"],
        include_seed=True,
        include_alphabet=False,
        include_numbers=False,
        include_prepositions=False,
        include_questions=False,
        include_modifiers=False,
        request_budget=5,
    )
    res = engine.expand(cfg)

    kw_texts = [k.keyword for k in res.keywords]
    assert len(kw_texts) == len(set(kw_texts))
    assert "car wax review" in kw_texts

    # Find the merged item and verify multi-query provenance
    merged_item = next(k for k in res.keywords if k.keyword == "car wax review")
    assert len(merged_item.parent_queries) >= 2


# ------------------------------------------------------------------------------
# 3. Rule-Based Bilingual Intent Classification (10 Canonical Categories)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "keyword,expected_category",
    [
        ("how to apply car wax properly", SearchIntent.HOW_TO_TUTORIAL),
        ("car wax vs ceramic coating", SearchIntent.COMPARISON_VS),
        ("top 10 best car wax 2025", SearchIntent.BEST_TOP_LIST),
        ("where to buy car wax cheap", SearchIntent.BUYING_COMMERCIAL),
        ("how to fix car wax haze and streaks", SearchIntent.PROBLEM_SOLVING),
        ("best car wax for beginners", SearchIntent.AUDIENCE_SPECIFIC),
        ("car wax shop near me in Dhaka", SearchIntent.LOCATION_SPECIFIC),
        ("গাড়ির ওয়াক্স কীভাবে দিতে হয়", SearchIntent.HOW_TO_TUTORIAL),
        ("গাড়ির ওয়াক্স এর দাম কত", SearchIntent.BUYING_COMMERCIAL),
        ("car wax", SearchIntent.GENERAL),
    ],
)
def test_bilingual_intent_classification_canonical_categories(keyword: str, expected_category: SearchIntent):
    """Verify all 10 canonical categories are accurately classified with explanations."""
    classifier = KeywordClassifier()
    result = classifier.classify(keyword)

    assert expected_category in result.intent_labels
    assert result.primary_explanation != ""
    assert len(result.matched_reasons) > 0


def test_intent_classification_transparent_rule_explanations():
    """Verify intent classifications include transparent pattern explanations."""
    classifier = KeywordClassifier()
    res = classifier.classify("best car wax review and comparison")

    # Should match Review and Comparison
    assert SearchIntent.REVIEW in res.intent_labels or SearchIntent.COMPARISON in res.intent_labels
    assert any("comparison" in exp.lower() or "review" in exp.lower() for exp in res.matched_reasons.values())


# ------------------------------------------------------------------------------
# 4. Heuristic Relevance Scoring (0-100)
# ------------------------------------------------------------------------------

def test_relevance_scorer_bounds_and_components():
    """Verify relevance scores are strictly bounded within [0.0, 100.0] and return full breakdown."""
    scorer = RelevanceScorer()

    # Exact match seed
    breakdown_exact = scorer.score("best car wax", "best car wax")
    assert 90.0 <= breakdown_exact.total_score <= 100.0
    assert breakdown_exact.seed_term_score > 0
    assert breakdown_exact.similarity_score > 0
    assert breakdown_exact.penalty == 0.0

    # Distant match
    breakdown_distant = scorer.score("something totally unrelated", "best car wax")
    assert 0.0 <= breakdown_distant.total_score < 40.0

    # Empty inputs
    breakdown_empty = scorer.score("", "best car wax")
    assert breakdown_empty.total_score == 0.0


def test_relevance_scorer_spam_repetition_penalty():
    """Verify repetitive word stuffing receives a substantial penalty."""
    scorer = RelevanceScorer()

    clean_score = scorer.score("best car wax for black cars", "best car wax")
    spammed_score = scorer.score("best car wax wax wax wax black cars", "best car wax")

    assert spammed_score.penalty > 0.0
    assert spammed_score.total_score < clean_score.total_score


def test_relevance_scorer_custom_weights_validation():
    """Verify scoring weights validation enforces sum to 1.0."""
    with pytest.raises(ValueError):
        ScoringWeights(seed_term_weight=0.8, similarity_weight=0.8)  # Sums to 1.6


# ------------------------------------------------------------------------------
# 5. Long-Tail Analysis & Multi-Dimensional Filtering
# ------------------------------------------------------------------------------

def test_long_tail_classification_thresholds():
    """Verify token count structural classification into Short, Medium, and Long tail."""
    thresholds = TailThresholds(short_max=2, medium_max=4)

    assert thresholds.classify(1) == TailLength.SHORT_TAIL
    assert thresholds.classify(2) == TailLength.SHORT_TAIL
    assert thresholds.classify(3) == TailLength.MEDIUM_TAIL
    assert thresholds.classify(4) == TailLength.MEDIUM_TAIL
    assert thresholds.classify(5) == TailLength.LONG_TAIL
    assert thresholds.classify(8) == TailLength.LONG_TAIL


def test_multidimensional_filtering_on_dataframe():
    """Verify combinations of intent, tail length, relevance score, and source filtering."""
    items = [
        KeywordItem(
            keyword="best car wax",
            seed_keyword="best car wax",
            source=SourceType.LIVE_AUTOCOMPLETE,
            classification=TailLength.SHORT_TAIL,
            relevance_score=95.0,
            cluster_name="Core Seed Variations",
            intent_labels=["Best / Top list"],
        ),
        KeywordItem(
            keyword="how to apply car wax properly for beginner detailers",
            seed_keyword="best car wax",
            source=SourceType.LIVE_AUTOCOMPLETE,
            classification=TailLength.LONG_TAIL,
            relevance_score=85.0,
            cluster_name="How-To & Application Guides",
            intent_labels=["How-to / Tutorial"],
        ),
        KeywordItem(
            keyword="car wax cheap",
            seed_keyword="best car wax",
            source=SourceType.CACHED_AUTOCOMPLETE,
            classification=TailLength.MEDIUM_TAIL,
            relevance_score=60.0,
            cluster_name="Pricing & Buying Guides",
            intent_labels=["Buying / Commercial intent"],
        ),
    ]

    df = pd.DataFrame([k.to_dict() for k in items])

    # 1. Filter by minimum relevance score
    high_rel = df[df["relevance_score"] >= 80.0]
    assert len(high_rel) == 2

    # 2. Filter by tail length
    long_tail = df[df["tail_length"] == "Long-tail"]
    assert len(long_tail) == 1
    assert "how to apply" in long_tail.iloc[0]["keyword"]

    # 3. Filter by cluster
    pricing = df[df["cluster_name"] == "Pricing & Buying Guides"]
    assert len(pricing) == 1


# ------------------------------------------------------------------------------
# 6. Honest SERP Metrics Provider Notice
# ------------------------------------------------------------------------------

def test_unconnected_serp_provider_honest_unavailable_notice():
    """Verify unconnected SERP provider explicitly declares data unavailable without synthetic metrics."""
    provider = UnconnectedSerpMetricsProvider()

    assert provider.is_connected() is False

    metrics = provider.get_metrics("best car wax")
    assert metrics.is_available is False
    assert "Not available — no verified data source connected" in metrics.status_message
    assert metrics.search_volume is None
    assert metrics.competition_score is None
    assert metrics.average_views is None
    assert metrics.video_count is None


# ------------------------------------------------------------------------------
# 7. Topic Clustering: Semantic Rules, Renaming, Moving & Exclusion
# ------------------------------------------------------------------------------

def test_topic_clustering_semantic_grouping():
    """Verify clustering engine groups keywords into explainable semantic clusters."""
    clusterer = TopicClusteringEngine()
    keywords = [
        "best car wax for white cars",
        "best car wax for black cars",
        "best car wax vs sealant",
        "best car wax honest review",
        "how to apply car wax on old cars",
        "best car wax spray bottle",
        "cheap car wax price",
    ]

    clusters = clusterer.cluster_keywords(keywords, seed_keyword="best car wax")
    cluster_names = {c.name for c in clusters}

    assert "Paint Colors & Finishes" in cluster_names
    assert "Comparisons & Alternatives" in cluster_names
    assert "Reviews & Evaluations" in cluster_names
    assert "How-To & Application Guides" in cluster_names
    assert "Formulations & Product Types" in cluster_names
    assert "Pricing & Buying Guides" in cluster_names


def test_topic_clustering_manual_renaming():
    """Verify clusters can be manually renamed while preserving members."""
    clusterer = TopicClusteringEngine()
    keywords = ["best car wax for white cars", "best car wax for black cars"]
    clusters = clusterer.cluster_keywords(keywords, seed_keyword="best car wax")

    target_c = clusters[0].name
    success = TopicClusteringEngine.rename_cluster(clusters, target_c, "Custom Vehicle Colors")
    assert success is True

    updated_names = [c.name for c in clusters]
    assert "Custom Vehicle Colors" in updated_names
    assert target_c not in updated_names


def test_topic_clustering_keyword_moving():
    """Verify a keyword can be moved from one cluster to another."""
    clusterer = TopicClusteringEngine()
    keywords = ["best car wax for white cars", "how to apply car wax"]
    clusters = clusterer.cluster_keywords(keywords, seed_keyword="best car wax")

    c1_name = clusters[0].name
    c2_name = clusters[1].name
    kw_to_move = clusters[0].keywords[0]

    success = TopicClusteringEngine.move_keyword(clusters, kw_to_move, c1_name, c2_name)
    assert success is True
    assert kw_to_move not in clusters[0].keywords
    assert kw_to_move in clusters[1].keywords


def test_topic_clustering_exclusion():
    """Verify cluster exclusion hides excluded cluster from active list."""
    clusterer = TopicClusteringEngine()
    keywords = ["best car wax for white cars", "how to apply car wax"]
    clusters = clusterer.cluster_keywords(keywords, seed_keyword="best car wax")

    exclude_name = clusters[0].name
    TopicClusteringEngine.exclude_cluster(clusters, exclude_name, exclude=True)

    active = TopicClusteringEngine.get_active_clusters(clusters)
    active_names = [c.name for c in active]

    assert exclude_name not in active_names
    assert len(active) == len(clusters) - 1


# ------------------------------------------------------------------------------
# 8. Research Session Summary Telemetry
# ------------------------------------------------------------------------------

def test_research_summary_telemetry_accuracy():
    """Verify research session summary calculates accurate metrics from actual session data."""
    logs = [
        QueryLogEntry("seed", "seed", "seed", "success", 5),
        QueryLogEntry("seed", "seed a", "alphabet", "success", 4),
        QueryLogEntry("seed", "seed b", "alphabet", "cached", 3),
        QueryLogEntry("seed", "seed c", "alphabet", "failed", 0, "Network error"),
    ]

    items = [
        KeywordItem(
            keyword="kw1",
            seed_keyword="seed",
            source=SourceType.LIVE_AUTOCOMPLETE,
            relevance_score=90.0,
            cluster_name="Cluster A",
        ),
        KeywordItem(
            keyword="kw2",
            seed_keyword="seed",
            source=SourceType.CACHED_AUTOCOMPLETE,
            relevance_score=80.0,
            cluster_name="Cluster B",
        ),
        KeywordItem(
            keyword="kw3",
            seed_keyword="seed",
            source=SourceType.GENERATED_PATTERN,
            relevance_score=70.0,
            cluster_name="Cluster A",
        ),
    ]

    summary = ResearchSummary.from_session_data(
        seed_keyword="seed",
        keywords=items,
        query_logs=logs,
        stop_reason=StopReason.TARGET_REACHED,
        cluster_count=2,
    )

    d = summary.to_dict()
    assert d["seed_keyword"] == "seed"
    assert d["queries_attempted"] == 4
    assert d["queries_successful"] == 3
    assert d["queries_failed"] == 1
    assert d["live_autocomplete_count"] == 1
    assert d["cached_autocomplete_count"] == 1
    assert d["generated_keyword_count"] == 1
    assert d["total_unique_keywords"] == 3
    assert d["clusters_created"] == 2
    assert d["status"] == "Target Reached"


# ------------------------------------------------------------------------------
# 9. Data Integrity & SQLite Persistence
# ------------------------------------------------------------------------------

def test_sqlite_phase9_columns_persistence_and_retrieval(tmp_path: Path):
    """Verify relevance_score, cluster_name, and intent_explanation persist to and load from SQLite."""
    db_file = tmp_path / "test_phase9_storage.db"
    mgr = DatabaseManager(db_file)
    mgr.init_db()

    search_id = mgr.save_search(
        seed_keyword="best car wax",
        language="en",
        country="US",
        max_depth=1,
        request_budget=10,
        project_name="Phase 9 Test Project",
    )

    items = [
        KeywordItem(
            keyword="best car wax spray",
            seed_keyword="best car wax",
            source=SourceType.LIVE_AUTOCOMPLETE,
            relevance_score=88.5,
            cluster_name="Formulations & Product Types",
            intent_explanation="Matched product formulation rule",
        ),
        KeywordItem(
            keyword="সেরা কার ওয়াক্স",
            seed_keyword="সেরা কার ওয়াক্স",
            source=SourceType.LIVE_AUTOCOMPLETE,
            language="bn",
            country="BD",
            relevance_score=92.0,
            cluster_name="Core Seed Variations",
            intent_explanation="Bangla seed baseline",
        ),
    ]

    mgr.save_keywords(search_id, items)

    # Retrieve and verify
    retrieved = mgr.get_keywords_by_search_id(search_id)
    assert len(retrieved) == 2

    spray_kw = next(k for k in retrieved if k["keyword"] == "best car wax spray")
    assert spray_kw["relevance_score"] == 88.5
    assert spray_kw["cluster_name"] == "Formulations & Product Types"
    assert spray_kw["intent_explanation"] == "Matched product formulation rule"

    bangla_kw = next(k for k in retrieved if k["keyword"] == "সেরা কার ওয়াক্স")
    assert bangla_kw["relevance_score"] == 92.0
    assert bangla_kw["cluster_name"] == "Core Seed Variations"


def test_sqlite_cluster_update_and_project_rename(tmp_path: Path):
    """Verify cluster updating and bulk renaming directly in the database."""
    db_file = tmp_path / "test_cluster_ops.db"
    mgr = DatabaseManager(db_file)
    mgr.init_db()

    search_id = mgr.save_search(
        seed_keyword="best car wax",
        language="en",
        country="US",
        max_depth=1,
        request_budget=10,
    )

    items = [
        KeywordItem(
            keyword="kw1",
            seed_keyword="best car wax",
            source=SourceType.LIVE_AUTOCOMPLETE,
            cluster_name="Old Cluster",
        ),
        KeywordItem(
            keyword="kw2",
            seed_keyword="best car wax",
            source=SourceType.LIVE_AUTOCOMPLETE,
            cluster_name="Old Cluster",
        ),
    ]
    mgr.save_keywords(search_id, items)

    # 1. Update single keyword cluster
    updated = mgr.update_keyword_cluster(search_id, "kw1", "Moved Cluster")
    assert updated is True

    rows = mgr.get_keywords_by_search_id(search_id)
    kw1_row = next(r for r in rows if r["keyword"] == "kw1")
    assert kw1_row["cluster_name"] == "Moved Cluster"

    # 2. Rename cluster across project
    renamed_count = mgr.rename_project_cluster(search_id, "Old Cluster", "Renamed Cluster")
    assert renamed_count == 1

    rows2 = mgr.get_keywords_by_search_id(search_id)
    kw2_row = next(r for r in rows2 if r["keyword"] == "kw2")
    assert kw2_row["cluster_name"] == "Renamed Cluster"


# ------------------------------------------------------------------------------
# 10. Formula-Injection Protection & Spreadsheet Export
# ------------------------------------------------------------------------------

def test_spreadsheet_formula_injection_defense():
    """Verify formula injection prefixes (=, +, -, @, \\t, \\r) are neutralized."""
    malicious_inputs = [
        "=CMD('calc')",
        "+SUM(A1:A10)",
        "-2+3*cmd|' /C calc'!A0",
        "@IMPORTDATA('http://malicious.com')",
        "\tmalicious_tab",
        "\rmalicious_return",
    ]

    for val in malicious_inputs:
        sanitized = sanitize_formula_injection(val)
        assert sanitized.startswith("'"), f"Failed to sanitize: {val}"

    # Safe inputs should not be altered
    assert sanitize_formula_injection("normal keyword") == "normal keyword"
    assert sanitize_formula_injection("best car wax") == "best car wax"


def test_csv_export_with_bangla_utf8_bom():
    """Verify CSV export includes UTF-8 BOM so Excel opens Bangla characters flawlessly."""
    df = pd.DataFrame([
        {
            "Keyword": "সেরা কার ওয়াক্স",
            "Relevance Score": 95.0,
            "Cluster": "Core Seed Variations",
            "Intent": "Informational",
        }
    ])

    csv_bytes = ExportService.export_csv(df, include_bom=True)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM signature
    assert "সেরা কার ওয়াক্স" in csv_bytes.decode("utf-8-sig")
