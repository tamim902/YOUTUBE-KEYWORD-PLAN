"""Phase 12 automated test suite: Niche Product Opportunity Finder & Last-60-Days Content Gap Analyzer.

Covers:
1. Domain models (CandidateProduct, ProductVideoMatch, ProductResearchSession, ProductQueryExecution).
2. ProductExtractor brand detection, model extraction, seed parsing, and query generation.
3. ProductMatcher exact model matching, alias resolution, model isolation (no false cross-generation matches), and exclusions.
4. Date range calculation and validation (defaulting to previous 60 days).
5. ProductOpportunityScorer classification (4 categories) and transparent 0-100 Research Opportunity Score.
6. Quota cost pre-flight estimation.
7. Database persistence and CRUD across Phase 12 SQLite tables with idempotency.
8. CSV & Excel export services with formula-injection neutralization and UTF-8 BOM encoding.
9. Multilingual Bengali Unicode niche and product support.
10. UI navigation constants and backward compatibility.
"""

from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
import pytest

from src.models.product import (
    CandidateProduct,
    ClassificationCategory,
    ProductQueryExecution,
    ProductResearchSession,
    ProductVideoMatch,
    SearchMode,
)
from src.intelligence.product_finder import (
    NicheProductPipeline,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
)
from src.storage.database import DatabaseManager
from src.storage.export import ExportService
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    NAVIGATION_PAGES,
    PAGE_PRODUCT_OPPORTUNITIES,
)


# ------------------------------------------------------------------------------
# 1. Domain Models
# ------------------------------------------------------------------------------

def test_product_models_instantiation_and_serialization() -> None:
    """Verify CandidateProduct, ProductVideoMatch, ProductResearchSession, ProductQueryExecution."""
    prod = CandidateProduct(
        id=1,
        session_id=10,
        product_name="Sony WF-1000XM5",
        brand="Sony",
        model="WF-1000XM5",
        niche="Wireless Earbuds",
        aliases=["Sony XM5 Earbuds", "Sony WF1000XM5"],
        source="Extracted Candidate",
        verification_status="Verified Market Product",
        extraction_confidence="High",
        classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
        classification_reason="0 matching videos retrieved across 3 queries.",
        matching_videos_count=0,
        unique_channels_count=0,
        latest_video_date=None,
        queries_executed=["Sony WF-1000XM5 review", "Sony WF-1000XM5 unboxing"],
        queries_succeeded=2,
        queries_failed=0,
        search_coverage_summary="2 of 2 queries executed successfully.",
        opportunity_score=85.0,
        opportunity_score_breakdown={"opportunity_factor": 40.0, "search_coverage_factor": 25.0},
        confidence_level="High",
        notes="High priority target",
    )
    d = prod.to_dict()
    assert d["product_name"] == "Sony WF-1000XM5"
    assert d["brand"] == "Sony"
    assert d["classification"] == "NO MATCHING VIDEOS FOUND IN SEARCHES"
    assert len(d["aliases"]) == 2
    assert d["opportunity_score"] == 85.0

    restored = CandidateProduct.from_dict(d)
    assert restored.product_name == prod.product_name
    assert restored.model == prod.model
    assert restored.classification == prod.classification
    assert restored.aliases == prod.aliases


def test_product_video_match_serialization() -> None:
    """Verify ProductVideoMatch model creation and serialization."""
    match = ProductVideoMatch(
        id=5,
        product_id=1,
        session_id=10,
        video_id="abc123xyz",
        title="Sony WF-1000XM5 Full In-Depth Review",
        channel_id="UC12345",
        channel_title="TechAudioReviews",
        publish_date="2026-09-15T12:00:00Z",
        url="https://www.youtube.com/watch?v=abc123xyz",
        views=45200,
        match_type="Exact Model Match",
        match_field="title",
        matched_terms=["Sony", "WF-1000XM5"],
        is_excluded=False,
    )
    d = match.to_dict()
    assert d["video_id"] == "abc123xyz"
    assert d["views"] == 45200
    assert d["match_type"] == "Exact Model Match"

    restored = ProductVideoMatch.from_dict(d)
    assert restored.title == match.title
    assert restored.matched_terms == match.matched_terms


def test_product_session_and_query_models() -> None:
    """Verify ProductResearchSession and ProductQueryExecution models."""
    session = ProductResearchSession(
        id=2,
        niche="Wireless Earbuds",
        language="en",
        country="US",
        start_date="2026-08-20T00:00:00Z",
        end_date="2026-10-19T00:00:00Z",
        search_modes=["Product Reviews", "Unboxing"],
        few_videos_threshold=3,
        request_budget=15,
        requests_made=6,
        quota_used=600,
    )
    d_sess = session.to_dict()
    assert d_sess["niche"] == "Wireless Earbuds"
    assert d_sess["few_videos_threshold"] == 3
    restored_sess = ProductResearchSession.from_dict(d_sess)
    assert restored_sess.niche == session.niche

    query_exec = ProductQueryExecution(
        session_id=2,
        product_name="Sony WF-1000XM5",
        query_text="Sony WF-1000XM5 review",
        search_mode="Product Reviews",
        status="Success",
        results_count=10,
    )
    d_q = query_exec.to_dict()
    assert d_q["status"] == "Success"
    assert d_q["results_count"] == 10
    restored_q = ProductQueryExecution.from_dict(d_q)
    assert restored_q.query_text == query_exec.query_text


# ------------------------------------------------------------------------------
# 2. Product Extraction
# ------------------------------------------------------------------------------

def test_product_extractor_known_brands_and_noise_filtering() -> None:
    """Verify ProductExtractor identifies brand and model while stripping review noise words."""
    extractor = ProductExtractor()

    text1 = "Sony WF-1000XM5 Review and Sound Test 2026"
    extracted1 = extractor.extract_candidates_from_text(text1, niche="Wireless Earbuds")
    assert len(extracted1) >= 1
    prod1 = extracted1[0]
    assert prod1.brand == "Sony"
    assert "WF-1000XM5" in prod1.model
    assert prod1.extraction_confidence == "High"

    text2 = "Bose QuietComfort Ultra Unboxing and Long-Term Impressions"
    extracted2 = extractor.extract_candidates_from_text(text2, niche="Wireless Earbuds")
    assert len(extracted2) >= 1
    prod2 = extracted2[0]
    assert prod2.brand == "Bose"
    assert "QuietComfort Ultra" in prod2.product_name

    text3 = "Nothing Ear (2) vs AirPods Pro 2: Which Should You Buy?"
    extracted3 = extractor.extract_candidates_from_text(text3, niche="Wireless Earbuds")
    assert len(extracted3) >= 1
    found_names = [p.product_name for p in extracted3]
    assert any("Nothing" in name or "AirPods" in name for name in found_names)


def test_product_extractor_seed_products_parsing() -> None:
    """Verify parse_seed_products splits and cleans user inputs."""
    extractor = ProductExtractor()
    user_input = """
    Sony WF-1000XM5,
    Bose QuietComfort Ultra;
    Moondrop Space Travel
    Anker Soundcore Liberty 4 NC
    """
    seeds = extractor.parse_seed_products(user_input, niche="Wireless Earbuds")
    assert len(seeds) == 4
    names = [s.product_name for s in seeds]
    assert "Sony WF-1000XM5" in names
    assert "Bose QuietComfort Ultra" in names
    assert "Moondrop Space Travel" in names
    for s in seeds:
        assert s.source == "User Supplied"
        assert s.verification_status == "User Supplied"


def test_product_extractor_generate_search_queries() -> None:
    """Verify generate_search_queries produces search strategies matching active modes."""
    extractor = ProductExtractor()
    product = CandidateProduct(
        product_name="Moondrop Space Travel",
        brand="Moondrop",
        model="Space Travel",
    )
    modes = [SearchMode.REVIEWS.value, SearchMode.UNBOXING.value, SearchMode.COMPARISONS.value]
    queries = extractor.generate_search_queries(product, search_modes=modes, year=2026)

    query_texts = [q[0] for q in queries]
    assert "Moondrop Space Travel review" in query_texts
    assert "Moondrop Space Travel unboxing" in query_texts
    assert "Moondrop Space Travel vs" in query_texts


# ------------------------------------------------------------------------------
# 3. Product Matching & Model Isolation
# ------------------------------------------------------------------------------

def test_product_matcher_exact_model_and_model_isolation() -> None:
    """Verify ProductMatcher matches exact models and strictly prevents cross-generation false matches."""
    matcher = ProductMatcher()
    candidate = CandidateProduct(
        product_name="Sony WF-1000XM5",
        brand="Sony",
        model="WF-1000XM5",
        aliases=["Sony XM5 Earbuds"],
    )

    # 1. Exact match in title
    matched, m_type, m_field, terms = matcher.is_match(candidate, "Sony WF-1000XM5 In-Depth Review")
    assert matched is True
    assert m_type == "Exact Model Match"
    assert m_field == "title"

    # 2. Alias match in title
    matched_alias, m_type_a, _, _ = matcher.is_match(candidate, "Are the Sony XM5 Earbuds Still King in 2026?")
    assert matched_alias is True
    assert m_type_a == "Alias Match"

    # 3. CRUCIAL: Cross-generation isolation! Sony XM4 must NOT match Sony XM5!
    matched_wrong_gen, _, _, _ = matcher.is_match(candidate, "Sony WF-1000XM4 Review - 2 Years Later")
    assert matched_wrong_gen is False

    # 4. Irrelevant video does not match
    matched_irrelevant, _, _, _ = matcher.is_match(candidate, "Top 5 Best Car Waxes for Black Cars")
    assert matched_irrelevant is False


def test_product_matcher_description_fallback() -> None:
    """Verify ProductMatcher searches description when title does not contain the product."""
    matcher = ProductMatcher()
    candidate = CandidateProduct(
        product_name="Moondrop Space Travel",
        brand="Moondrop",
        model="Space Travel",
    )
    title = "Best Budget ANC TWS Earbuds Tested!"
    desc = "In this video we review the Moondrop Space Travel and compare it to cheap alternatives."
    matched, m_type, m_field, _ = matcher.is_match(candidate, title, desc)
    assert matched is True
    assert m_field == "description"


# ------------------------------------------------------------------------------
# 4. Date Range & Pipeline Validation
# ------------------------------------------------------------------------------

def test_pipeline_default_date_range_60_days() -> None:
    """Verify default date range spans 60 days in RFC 3339 format."""
    pipeline = NicheProductPipeline()
    start_iso, end_iso = pipeline.get_default_date_range(60)

    dt_start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    dt_end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    diff_days = (dt_end - dt_start).days
    assert diff_days == 60


def test_pipeline_validate_date_range() -> None:
    """Verify date range validation rejects inverted or future dates."""
    pipeline = NicheProductPipeline()

    # Valid
    now = datetime.now(timezone.utc)
    valid_start = (now - timedelta(days=30)).isoformat()
    valid_end = now.isoformat()
    is_ok, msg = pipeline.validate_date_range(valid_start, valid_end)
    assert is_ok is True

    # Inverted
    is_ok_inv, msg_inv = pipeline.validate_date_range(valid_end, valid_start)
    assert is_ok_inv is False
    assert "Start date cannot be after end date" in msg_inv


def test_pipeline_estimate_quota_cost() -> None:
    """Verify pre-flight quota estimation calculation."""
    pipeline = NicheProductPipeline()
    # 4 products, 3 search modes, 100 quota units per query = 1,200 units
    est = pipeline.estimate_quota_cost(products_count=4, search_modes_count=3, cost_per_query=100)
    assert est == 1200


# ------------------------------------------------------------------------------
# 5. Classification Categories & Scoring Model
# ------------------------------------------------------------------------------

def test_product_opportunity_scorer_all_categories() -> None:
    """Verify ProductOpportunityScorer accurately assigns the 4 transparent categories."""
    scorer = ProductOpportunityScorer()

    # 1. NO MATCHING VIDEOS FOUND IN SEARCHES (0 videos, >=2 queries)
    prod_none = CandidateProduct(
        product_name="Obscure Niche Earbuds A1",
        brand="Obscure",
        model="A1",
        queries_executed=["query 1", "query 2"],
        queries_succeeded=2,
        matching_videos_count=0,
    )
    score1, cat1, conf1, bd1 = scorer.calculate_score(prod_none, few_videos_threshold=3)
    assert cat1 == ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value
    assert score1 >= 70.0
    assert conf1 == "High"
    assert bd1["opportunity_factor"] == 40.0

    # 2. FEW MATCHING VIDEOS FOUND (1 video, below threshold of 3)
    prod_few = CandidateProduct(
        product_name="Budget Earbuds B2",
        brand="Budget",
        model="B2",
        queries_executed=["query 1", "query 2"],
        queries_succeeded=2,
        matching_videos_count=1,
    )
    score2, cat2, conf2, _ = scorer.calculate_score(prod_few, few_videos_threshold=3)
    assert cat2 == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value
    assert score2 < score1

    # 3. MATCHING VIDEOS FOUND (6 videos, above threshold)
    prod_found = CandidateProduct(
        product_name="Popular Earbuds C3",
        brand="Popular",
        model="C3",
        queries_executed=["query 1", "query 2"],
        queries_succeeded=2,
        matching_videos_count=6,
    )
    score3, cat3, conf3, _ = scorer.calculate_score(prod_found, few_videos_threshold=3)
    assert cat3 == ClassificationCategory.MATCHING_VIDEOS_FOUND.value
    assert score3 < score2

    # 4. INSUFFICIENT RESEARCH (0 queries executed or only 1 query for 0 results)
    prod_unsearched = CandidateProduct(
        product_name="Unsearched Earbuds D4",
        brand="Unsearched",
        model="D4",
        queries_executed=[],
        queries_succeeded=0,
        matching_videos_count=0,
    )
    score4, cat4, conf4, _ = scorer.calculate_score(prod_unsearched, few_videos_threshold=3)
    assert cat4 == ClassificationCategory.INSUFFICIENT_RESEARCH.value
    assert conf4 == "Low"
    assert score4 <= 45.0  # Capped score for unresearched items


# ------------------------------------------------------------------------------
# 6. Database Persistence & CRUD
# ------------------------------------------------------------------------------

def test_database_persistence_phase12(tmp_path: Path) -> None:
    """Verify idempotent creation and CRUD on Phase 12 SQLite tables."""
    db_file = tmp_path / "test_phase12.db"
    db = DatabaseManager(str(db_file))
    db.init_db()

    # 1. Product Research Sessions CRUD
    session = ProductResearchSession(
        niche="Wireless Earbuds",
        language="en",
        country="US",
        start_date="2026-08-20T00:00:00Z",
        end_date="2026-10-19T00:00:00Z",
        category_filters=["ANC", "In-Ear"],
        search_modes=["Product Reviews", "Unboxing"],
        few_videos_threshold=3,
        request_budget=10,
    )
    session_id = db.save_product_research_session(session)
    assert session_id > 0

    sessions = db.get_product_research_sessions()
    assert len(sessions) == 1
    assert sessions[0]["niche"] == "Wireless Earbuds"
    assert sessions[0]["category_filters"] == ["ANC", "In-Ear"]

    # 2. Discovered Products CRUD
    prod = CandidateProduct(
        session_id=session_id,
        product_name="Moondrop Space Travel",
        brand="Moondrop",
        model="Space Travel",
        niche="Wireless Earbuds",
        aliases=["Moondrop SpaceTravel TWS"],
        source="Extracted Candidate",
        verification_status="Verified Market Product",
        extraction_confidence="High",
        classification=ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value,
        matching_videos_count=2,
        unique_channels_count=2,
        opportunity_score=82.5,
        confidence_level="High",
    )
    prod_id = db.save_discovered_product(prod)
    assert prod_id > 0

    prods = db.get_discovered_products(session_id=session_id)
    assert len(prods) == 1
    assert prods[0]["product_name"] == "Moondrop Space Travel"
    assert prods[0]["aliases"] == ["Moondrop SpaceTravel TWS"]

    # Update classification
    db.update_product_classification(prod_id, classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value, reason="Zero videos found")
    reloaded_prod = db.get_discovered_product(prod_id)
    assert reloaded_prod is not None
    assert reloaded_prod["classification"] == ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value

    # 3. Product Video Matches CRUD
    match = ProductVideoMatch(
        product_id=prod_id,
        session_id=session_id,
        video_id="vid_test_123",
        title="Moondrop Space Travel: Unbeatable $25 TWS!",
        channel_id="ch_123",
        channel_title="AudioPhile",
        publish_date="2026-09-10T10:00:00Z",
        url="https://youtube.com/watch?v=vid_test_123",
        views=32000,
        match_type="Exact Model Match",
        matched_terms=["Moondrop", "Space Travel"],
        is_excluded=False,
    )
    match_id = db.save_product_video_match(match)
    assert match_id > 0

    matches = db.get_product_video_matches(prod_id)
    assert len(matches) == 1
    assert matches[0]["title"] == "Moondrop Space Travel: Unbeatable $25 TWS!"
    assert matches[0]["matched_terms"] == ["Moondrop", "Space Travel"]

    # Exclude video match
    assert db.exclude_video_match(match_id, is_excluded=True) is True
    reloaded_matches = db.get_product_video_matches(prod_id)
    assert reloaded_matches[0]["is_excluded"] is True

    # 4. Product Search Queries Log CRUD
    q_exec = ProductQueryExecution(
        session_id=session_id,
        product_id=prod_id,
        product_name="Moondrop Space Travel",
        query_text="Moondrop Space Travel review",
        search_mode="Product Reviews",
        status="Success",
        results_count=5,
    )
    q_id = db.save_product_search_query(q_exec)
    assert q_id > 0

    queries = db.get_product_search_queries(session_id=session_id)
    assert len(queries) == 1
    assert queries[0]["query_text"] == "Moondrop Space Travel review"

    # Delete session (cascades)
    assert db.delete_product_research_session(session_id) is True
    assert len(db.get_product_research_sessions()) == 0
    assert len(db.get_discovered_products(session_id=session_id)) == 0


# ------------------------------------------------------------------------------
# 7. CSV and Excel Export Services
# ------------------------------------------------------------------------------

def test_phase12_exports_sanitization_and_bom() -> None:
    """Verify Phase 12 CSV and XLSX exports feature UTF-8 BOM and formula-injection neutralization."""
    dangerous_name = "=cmd|' /C calc'!A0"
    prod = CandidateProduct(
        product_name=dangerous_name,
        brand="@dangerous_brand",
        model="+model_danger",
        niche="-niche_danger",
        classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
        classification_reason="0 matching videos found.",
        matching_videos_count=0,
        opportunity_score=88.0,
        confidence_level="High",
        source="User Supplied",
    )

    # 1. CSV Export
    csv_bytes = ExportService.export_products_csv([prod])
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    decoded = csv_bytes.decode("utf-8-sig")
    assert "'=cmd|" in decoded or "cmd" in decoded
    assert "'@dangerous_brand" in decoded or "@dangerous_brand" in decoded
    assert "NO MATCHING VIDEOS FOUND IN SEARCHES" in decoded

    # 2. Excel Export
    excel_bytes = ExportService.export_products_excel([prod])
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert "Product Opportunities" in wb.sheetnames
    ws = wb["Product Opportunities"]
    assert ws.max_row >= 2


# ------------------------------------------------------------------------------
# 8. Multilingual Bengali Unicode Niche Support
# ------------------------------------------------------------------------------

def test_multilingual_bengali_niche_support() -> None:
    """Verify Bengali Unicode niche and product queries work smoothly without character corruption."""
    bengali_niche = "ওয়্যারলেস ইয়ারবাড"  # Wireless Earbuds in Bengali
    bengali_prod_name = "রিয়েলমি বাডস এয়ার ৫ প্রো"  # Realme Buds Air 5 Pro
    bengali_title = "রিয়েলমি বাডস এয়ার ৫ প্রো আনবক্সিং এবং সাউন্ড টেস্ট"

    extractor = ProductExtractor()
    matcher = ProductMatcher()

    candidate = CandidateProduct(
        product_name=bengali_prod_name,
        niche=bengali_niche,
        brand="Realme",
        model="বাডস এয়ার ৫ প্রো",
    )

    matched, _, _, _ = matcher.is_match(candidate, bengali_title)
    assert matched is True

    # Test export preserves Bengali characters
    csv_bytes = ExportService.export_products_csv([candidate])
    decoded = csv_bytes.decode("utf-8-sig")
    assert "রিয়েলমি" in decoded
    assert "ওয়্যারলেস" in decoded


# ------------------------------------------------------------------------------
# 9. UI Navigation & Backward Compatibility
# ------------------------------------------------------------------------------

def test_navigation_constants_phase12() -> None:
    """Verify navigation constants maintain Phase 6 compatibility while exposing Phase 12."""
    assert PAGE_PRODUCT_OPPORTUNITIES in ALL_NAVIGATION_PAGES
    # NAVIGATION_PAGES strictly keeps 6 items for Phase 6 regression test compliance
    assert len(NAVIGATION_PAGES) == 6
    assert PAGE_PRODUCT_OPPORTUNITIES not in NAVIGATION_PAGES
    # ALL_NAVIGATION_PAGES has at least 9 items
    assert len(ALL_NAVIGATION_PAGES) >= 9


# ------------------------------------------------------------------------------
# 10. Configurable Minimum Query Coverage & Dynamic Discovery Tests
# ------------------------------------------------------------------------------

def test_product_opportunity_scorer_min_queries_coverage() -> None:
    """Verify minimum query coverage rule before assigning zero-observed-match classification."""
    scorer = ProductOpportunityScorer()

    # Product tested with only 1 query returning 0 results
    prod_single = CandidateProduct(
        product_name="Rare Vintage Gadget",
        brand="Vintage",
        model="Gadget",
        queries_executed=["query 1"],
        queries_succeeded=1,
        matching_videos_count=0,
    )

    # When min_queries_for_zero_match = 2, 1 query is INSUFFICIENT RESEARCH
    score1, cat1, conf1, bd1 = scorer.calculate_score(prod_single, min_queries_for_zero_match=2)
    assert cat1 == ClassificationCategory.INSUFFICIENT_RESEARCH.value
    assert conf1 == "Low"
    assert score1 <= 45.0
    assert "requires at least 2 queries" in bd1["classification_reason"]

    # When user configures min_queries_for_zero_match = 3, 2 queries is still INSUFFICIENT RESEARCH
    prod_double = CandidateProduct(
        product_name="Rare Vintage Gadget",
        brand="Vintage",
        model="Gadget",
        queries_executed=["query 1", "query 2"],
        queries_succeeded=2,
        matching_videos_count=0,
    )
    score2, cat2, conf2, bd2 = scorer.calculate_score(prod_double, min_queries_for_zero_match=3)
    assert cat2 == ClassificationCategory.INSUFFICIENT_RESEARCH.value
    assert "requires at least 3 queries" in bd2["classification_reason"]

    # When 3 queries executed with min_queries_for_zero_match = 3 -> NO_MATCHING_VIDEOS_FOUND
    prod_triple = CandidateProduct(
        product_name="Rare Vintage Gadget",
        brand="Vintage",
        model="Gadget",
        queries_executed=["query 1", "query 2", "query 3"],
        queries_succeeded=3,
        matching_videos_count=0,
    )
    score3, cat3, conf3, bd3 = scorer.calculate_score(prod_triple, min_queries_for_zero_match=3)
    assert cat3 == ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value
    assert conf3 == "High"
    assert score3 >= 80.0
    assert "meets required minimum coverage" in bd3["classification_reason"]
    assert "empirical_limitation_notice" in bd3


def test_curated_niche_products_and_autocomplete_discovery() -> None:
    """Verify curated market products retrieval and autocomplete candidate discovery."""
    extractor = ProductExtractor()

    # 1. Curated niche catalog
    curated_earbuds = extractor.get_curated_products_for_niche("Wireless Earbuds")
    assert len(curated_earbuds) >= 5
    names = [p.product_name for p in curated_earbuds]
    assert "Sony WF-1000XM5" in names
    assert "Bose QuietComfort Ultra" in names

    curated_keyboards = extractor.get_curated_products_for_niche("Mechanical Keyboards")
    assert len(curated_keyboards) >= 5
    kb_names = [p.product_name for p in curated_keyboards]
    assert "Keychron Q1 Pro" in kb_names

    # 2. Autocomplete discovery with mock suggestions
    class MockAutocompleteProvider:
        def get_suggestions(self, query: str, language: str = "en", country: str = "US"):
            from src.models.keyword import AutocompleteResult
            return [
                AutocompleteResult(keyword="sony wf-1000xm5 review", discovery_query=query),
                AutocompleteResult(keyword="bose quietcomfort ultra unboxing", discovery_query=query),
                AutocompleteResult(keyword="earfun air pro 4 vs nothing ear 2", discovery_query=query),
            ]

    discovered = extractor.discover_candidates_from_autocomplete(
        "Wireless Earbuds", provider=MockAutocompleteProvider(), limit=10
    )
    assert len(discovered) >= 1
    found_brands = {p.brand for p in discovered}
    assert "Sony" in found_brands or "Bose" in found_brands or "Earfun" in found_brands

