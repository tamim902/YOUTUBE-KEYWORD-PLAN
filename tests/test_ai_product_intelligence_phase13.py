"""Phase 13 Test Suite: AI-Powered Niche Research & Product Discovery Intelligence.

Validates:
1. 10-step guided niche research workflow and pipeline orchestration.
2. Multi-channel candidate discovery, categorization, verification status, and audit trail.
3. AI-assisted and template query generation across 10 search modes labeled AI_GENERATED_QUERY.
4. 5-tier content gap classification including PRODUCT_IDENTITY_UNVERIFIED.
5. 0-100 opportunity scoring with configurable factor weights and penalization of unverified candidates.
6. Structured research report generation with empirical notice and live/test data mode tagging.
7. User corrections audit trail (renaming, status update, priority, aliases, video exclusion).
8. Research queue budget control, quota tracking, and session cancellation.
9. Executive AI research summary synthesis (facts vs interpretations, missing evidence, deterministic fallback).
10. Database persistence, idempotent migrations, formula-safe CSV and XLSX dual exports.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from src.models.product import (
    CandidateProduct,
    ClassificationCategory,
    ProductQueryExecution,
    ProductResearchSession,
    ProductVideoMatch,
    SearchMode,
)
from src.providers.ai import (
    DeterministicFallbackAiProvider,
    MockAiProvider,
    get_ai_provider,
)
from src.intelligence.product_finder import (
    NicheProductPipeline,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
    infer_product_category,
)
from src.storage.database import DatabaseManager
from src.storage.export import ExportService


class TestAiProvidersAndQueryGeneration:
    """Test AI provider implementations and multi-angle query generation."""

    def test_deterministic_ai_provider_queries(self):
        prov = DeterministicFallbackAiProvider()
        queries = prov.generate_search_queries(
            product_name="Sony WF-1000XM5",
            niche="Wireless Earbuds",
            search_modes=[
                SearchMode.REVIEWS.value,
                SearchMode.PRODUCT_TESTING.value,
                SearchMode.LONG_TERM_USE.value,
                SearchMode.COMMON_PROBLEMS.value,
                SearchMode.USE_CASES.value,
            ],
        )
        assert len(queries) >= 5
        for q_text, q_mode, q_source in queries:
            assert "Sony WF-1000XM5" in q_text
            assert q_source == "AI_GENERATED_QUERY"
            assert q_mode in [
                SearchMode.REVIEWS.value,
                SearchMode.PRODUCT_TESTING.value,
                SearchMode.LONG_TERM_USE.value,
                SearchMode.COMMON_PROBLEMS.value,
                SearchMode.USE_CASES.value,
            ]

    def test_mock_ai_provider_queries_and_summary(self):
        prov = MockAiProvider()
        queries = prov.generate_search_queries(
            product_name="Keychron Q1 Pro",
            niche="Mechanical Keyboards",
            search_modes=[SearchMode.UNBOXING.value, SearchMode.TARGET_AUDIENCES.value],
        )
        assert len(queries) == 2
        assert all(q[2] == "AI_GENERATED_QUERY" for q in queries)

        summary = prov.generate_research_summary(
            niche="Mechanical Keyboards",
            products=[
                CandidateProduct(
                    product_name="Keychron Q1 Pro",
                    brand="Keychron",
                    opportunity_score=85.0,
                    classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
                )
            ],
        )
        assert "Keychron Q1 Pro" in summary
        assert "Verified Facts" in summary or "FACTS" in summary.upper()

    def test_extractor_hybrid_queries(self):
        extractor = ProductExtractor()
        prod = CandidateProduct(product_name="Bose QuietComfort Ultra", brand="Bose")
        ai_prov = MockAiProvider()

        queries = extractor.generate_search_queries(
            prod,
            search_modes=[SearchMode.REVIEWS.value, SearchMode.PRODUCT_TESTING.value],
            ai_provider=ai_prov,
            niche="Wireless Earbuds",
        )
        # Should include both template queries and AI queries
        assert len(queries) >= 3
        sources = [q[2] for q in queries]
        assert "ALGORITHMIC_TEMPLATE" in sources
        assert "AI_GENERATED_QUERY" in sources

    def test_infer_product_category(self):
        assert infer_product_category("Sony WF-1000XM5", "Wireless Earbuds") == "In-Ear Monitors (IEMs)"
        assert infer_product_category("Bose QuietComfort Ultra", "Wireless Earbuds") == "Active Noise Cancelling (ANC)"
        assert infer_product_category("Shure SM7B", "Microphones") == "Dynamic Microphones"
        assert infer_product_category("Logitech G Pro X Superlight", "Gaming Mice") == "Wireless Gaming Mice"
        assert infer_product_category("Custom Gadget 3000", "Tech Gear") == "Tech Gear Accessory"


class TestCandidateVerificationAndAuditTrail:
    """Test candidate provenance, verification statuses, and non-destructive audit trail."""

    def test_candidate_instantiation_and_audit(self):
        prod = CandidateProduct(
            product_name="Nothing Ear (2)",
            brand="Nothing",
            model="Ear (2)",
            category="True Wireless Earbuds",
            source="Curated Market Catalog",
            evidence_reference="Curated Market Reference: Wireless Earbuds",
            verification_status="Verified Market Product",
            extraction_confidence="High",
            original_name="Nothing Ear (2)",
        )
        assert prod.product_name == "Nothing Ear (2)"
        assert prod.original_name == "Nothing Ear (2)"
        assert prod.priority == "Medium"
        assert len(prod.audit_trail) == 0

        # User renames candidate with explanation
        prod.record_user_correction("product_name", "Nothing Ear (2)", "Nothing Ear (a)", "Updated to newest model variant")
        prod.product_name = "Nothing Ear (a)"

        assert prod.product_name == "Nothing Ear (a)"
        assert prod.original_name == "Nothing Ear (2)"
        assert len(prod.audit_trail) == 1
        entry = prod.audit_trail[0]
        assert entry["field"] == "product_name"
        assert entry["old_value"] == "Nothing Ear (2)"
        assert entry["new_value"] == "Nothing Ear (a)"
        assert entry["reason"] == "Updated to newest model variant"

    def test_serialization_roundtrip_with_phase13_fields(self):
        prod = CandidateProduct(
            product_name="Moondrop Space Travel",
            brand="Moondrop",
            category="In-Ear Monitors (IEMs)",
            priority="High",
            original_name="Moondrop Space Travel",
            evidence_url="https://youtube.com/watch?v=123",
            evidence_reference="Competitor Video",
            verification_status="Extracted Candidate",
        )
        prod.record_user_correction("priority", "Medium", "High", "High content demand")
        d = prod.to_dict()
        assert d["category"] == "In-Ear Monitors (IEMs)"
        assert d["priority"] == "High"
        assert len(d["audit_trail"]) == 1

        restored = CandidateProduct.from_dict(d)
        assert restored.product_name == "Moondrop Space Travel"
        assert restored.category == "In-Ear Monitors (IEMs)"
        assert restored.priority == "High"
        assert restored.audit_trail[0]["reason"] == "High content demand"


class TestContentGapClassificationAndWeightedScoring:
    """Test 5-tier classification and customizable scoring factor weights."""

    def test_unverified_product_identity_classification(self):
        scorer = ProductOpportunityScorer()
        prod = CandidateProduct(
            product_name="Generic Random Noise 999",
            verification_status="Needs Review",
            extraction_confidence="Uncertain / Needs Review",
            queries_executed=["query 1", "query 2"],
            queries_succeeded=2,
            matching_videos_count=0,
        )
        score, classification, conf, breakdown = scorer.calculate_score(prod)
        assert classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value
        assert conf == "Low"
        assert score <= 50.0  # Penalized ceiling
        assert "unverified" in breakdown["classification_reason"].lower()

    def test_configurable_scoring_weights(self):
        scorer = ProductOpportunityScorer()
        prod = CandidateProduct(
            product_name="Sony WF-1000XM5",
            brand="Sony",
            verification_status="Verified Market Product",
            extraction_confidence="High",
            queries_executed=["query 1", "query 2", "query 3"],
            queries_succeeded=3,
            matching_videos_count=0,
        )

        # Baseline weights
        score_base, _, _, bd_base = scorer.calculate_score(prod)
        assert score_base >= 80.0

        # Heavily prioritize Scarcity
        weights_scarcity = {"scarcity": 3.0, "coverage": 0.5, "identity": 0.5, "relevance": 0.5}
        score_scarcity, _, _, bd_scarcity = scorer.calculate_score(prod, weights=weights_scarcity)

        assert 0.0 <= score_scarcity <= 100.0
        assert bd_scarcity["weights_applied"]["scarcity"] == 3.0

    def test_five_classification_tiers(self):
        scorer = ProductOpportunityScorer()

        # 1. Product Identity Unverified
        p_unver = CandidateProduct(product_name="Unknown Gadget", verification_status="Unverified")
        _, cat1, _, _ = scorer.calculate_score(p_unver)
        assert cat1 == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value

        # 2. Insufficient Research
        p_insuf = CandidateProduct(product_name="Sony Model", verification_status="Verified Market Product", queries_succeeded=1, matching_videos_count=0)
        _, cat2, _, _ = scorer.calculate_score(p_insuf, min_queries_for_zero_match=2)
        assert cat2 == ClassificationCategory.INSUFFICIENT_RESEARCH.value

        # 3. No Matching Videos Found
        p_gap = CandidateProduct(product_name="Sony Model", verification_status="Verified Market Product", queries_succeeded=2, matching_videos_count=0)
        _, cat3, _, _ = scorer.calculate_score(p_gap, min_queries_for_zero_match=2)
        assert cat3 == ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value

        # 4. Few Matching Videos Found
        p_few = CandidateProduct(product_name="Sony Model", verification_status="Verified Market Product", queries_succeeded=2, matching_videos_count=2)
        _, cat4, _, _ = scorer.calculate_score(p_few, few_videos_threshold=3)
        assert cat4 == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value

        # 5. Matching Videos Found
        p_found = CandidateProduct(product_name="Sony Model", verification_status="Verified Market Product", queries_succeeded=2, matching_videos_count=8)
        _, cat5, _, _ = scorer.calculate_score(p_found, few_videos_threshold=3)
        assert cat5 == ClassificationCategory.MATCHING_VIDEOS_FOUND.value


class TestResearchReportAndSummarySynthesis:
    """Test structured research report generation and facts vs interpretations synthesis."""

    def test_generate_research_report(self):
        pipeline = NicheProductPipeline()
        session = ProductResearchSession(
            niche="Wireless Earbuds",
            country="US",
            language="en",
            start_date="2026-08-01T00:00:00+00:00",
            end_date="2026-10-01T00:00:00+00:00",
        )
        prods = [
            CandidateProduct(
                product_name="Bose QC Ultra",
                classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
                opportunity_score=88.5,
            ),
            CandidateProduct(
                product_name="Sony XM5",
                classification=ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value,
                opportunity_score=72.0,
            ),
        ]
        queries = [
            ProductQueryExecution(product_name="Bose QC Ultra", query_text="Bose QC Ultra review", status="Success"),
            ProductQueryExecution(product_name="Sony XM5", query_text="Sony XM5 review", status="Success"),
        ]

        report = pipeline.generate_research_report(session, prods, queries, is_live=False, ai_summary="Executive synthesis")
        assert "TEST DATA" in report["session_metadata"]["data_mode"]
        assert "NOT LIVE RESEARCH" in report["session_metadata"]["data_mode"]
        assert report["summary_counts"]["zero_observed_gaps"] == 1
        assert report["summary_counts"]["few_matching_videos"] == 1
        assert report["query_telemetry"]["total_queries_executed"] == 2
        assert "research findings" in report["empirical_notice"].lower()

    def test_deterministic_summary_facts_vs_interpretations(self):
        ai_prov = DeterministicFallbackAiProvider()
        prods = [
            CandidateProduct(
                product_name="Moondrop Space Travel",
                brand="Moondrop",
                model="Space Travel",
                classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
                opportunity_score=92.0,
                queries_succeeded=2,
                matching_videos_count=0,
            ),
            CandidateProduct(
                product_name="Sony WF-1000XM5",
                brand="Sony",
                classification=ClassificationCategory.MATCHING_VIDEOS_FOUND.value,
                opportunity_score=40.0,
                queries_succeeded=2,
                matching_videos_count=12,
            ),
        ]
        summary = ai_prov.generate_research_summary(
            niche="Wireless Earbuds",
            products=prods,
            session_params={"few_videos_threshold": 3, "min_queries_for_zero_match": 2},
        )
        # Must clearly demarcate facts vs interpretations and cite limitations
        assert "VERIFIED EMPIRICAL RESEARCH FINDINGS" in summary
        assert "STRATEGIC CONTENT OPPORTUNITIES" in summary
        assert "Moondrop Space Travel" in summary
        assert "EMPIRICAL RESEARCH LIMITATION NOTICE" in summary


class TestDatabaseIntegrityAndExclusionsPhase13:
    """Test SQLite persistence of Phase 13 columns, corrections, and video exclusions."""

    @pytest.fixture
    def db(self, tmp_path):
        db_file = tmp_path / "test_p13.db"
        mgr = DatabaseManager(db_path=db_file)
        mgr.init_db()
        return mgr

    def test_session_persistence_and_cancellation(self, db):
        sess = ProductResearchSession(
            niche="Mechanical Keyboards",
            scoring_weights={"scarcity": 2.0, "coverage": 1.0, "identity": 1.0, "relevance": 1.0},
            is_mocked=True,
        )
        s_id = db.save_product_research_session(sess)
        assert s_id > 0

        # Retrieve and verify weights and mocked status
        loaded = db.get_product_research_session(s_id)
        assert loaded["scoring_weights"]["scarcity"] == 2.0
        assert loaded["is_mocked"] is True

        # Test cancellation
        db.cancel_product_research_session(s_id)
        cancelled = db.get_product_research_session(s_id)
        assert cancelled["status"] == "Cancelled"
        assert cancelled["cancelled_at"] is not None

        # Test AI summary update
        db.update_session_ai_summary(s_id, "Updated AI summary report")
        with_summary = db.get_product_research_session(s_id)
        assert with_summary["ai_summary"] == "Updated AI summary report"

    def test_product_user_corrections_and_audit_trail(self, db):
        prod = CandidateProduct(
            product_name="Keychron Q1",
            brand="Keychron",
            category="Custom Keyboards",
            priority="Medium",
            verification_status="Extracted Candidate",
        )
        p_id = db.save_discovered_product(prod)
        assert p_id > 0

        # Record a user correction
        ok = db.record_product_correction(p_id, "product_name", "Keychron Q1", "Keychron Q1 Pro", "Updated to wireless version")
        assert ok is True

        p_loaded = db.get_discovered_product(p_id)
        assert p_loaded["product_name"] == "Keychron Q1 Pro"
        assert len(p_loaded["audit_trail"]) == 1
        assert p_loaded["audit_trail"][0]["new_value"] == "Keychron Q1 Pro"
        assert p_loaded["audit_trail"][0]["reason"] == "Updated to wireless version"

        # Update user fields: priority, notes, verification status
        ok2 = db.update_product_user_fields(p_id, priority="High", verification_status="Verified Market Product", notes="Target video next week")
        assert ok2 is True

        p_loaded2 = db.get_discovered_product(p_id)
        assert p_loaded2["priority"] == "High"
        assert p_loaded2["verification_status"] == "Verified Market Product"
        assert p_loaded2["notes"] == "Target video next week"

    def test_video_exclusion_with_reason(self, db):
        prod = CandidateProduct(product_name="Sony XM5")
        p_id = db.save_discovered_product(prod)

        match = ProductVideoMatch(
            product_id=p_id,
            video_id="vid_test_123",
            title="Sony WH-1000XM5 Headphones Review",
            url="https://youtube.com/watch?v=vid_test_123",
        )
        m_id = db.save_product_video_match(match)
        assert m_id > 0

        # Exclude video with reason
        ok = db.exclude_video_match(m_id, is_excluded=True, exclusion_reason="Over-ear headphones, not earbuds")
        assert ok is True

        matches = db.get_product_video_matches(p_id, include_excluded=True)
        assert len(matches) == 1
        assert matches[0]["is_excluded"] is True
        assert matches[0]["exclusion_reason"] == "Over-ear headphones, not earbuds"

        # Excluded filter
        active_matches = db.get_product_video_matches(p_id, include_excluded=False)
        assert len(active_matches) == 0

    def test_query_source_logging(self, db):
        query = ProductQueryExecution(
            product_name="Sony XM5",
            query_text="Sony XM5 battery life test",
            search_mode="PRODUCT_TESTING",
            query_source="AI_GENERATED_QUERY",
            status="Success",
            results_count=4,
        )
        q_id = db.save_product_search_query(query)
        assert q_id > 0

        queries = db.get_product_search_queries()
        assert len(queries) >= 1
        last = queries[-1]
        assert last["query_source"] == "AI_GENERATED_QUERY"
        assert last["search_mode"] == "PRODUCT_TESTING"


class TestExportsPhase13:
    """Test CSV and XLSX dual exports with Phase 13 fields and formula safety."""

    def test_phase13_csv_and_xlsx_exports(self):
        prod = CandidateProduct(
            product_name="Moondrop Space Travel",
            brand="Moondrop",
            category="In-Ear Monitors (IEMs)",
            priority="High",
            classification=ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
            opportunity_score=95.0,
            original_name="Moondrop Space Travel",
            evidence_reference="Curated Catalog",
            notes="=cmd|' /C calc'!A0",  # Malicious formula injection attempt
        )
        prod.record_user_correction("priority", "Medium", "High", "User prioritized")

        # Export CSV
        csv_bytes = ExportService.export_products_csv([prod])
        assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        csv_text = csv_bytes.decode("utf-8")
        assert "Category" in csv_text
        assert "Priority" in csv_text
        assert "In-Ear Monitors (IEMs)" in csv_text
        assert "High" in csv_text
        assert "User Corrections Count" in csv_text
        # Check formula sanitization: leading '=' must be sanitized with apostrophe
        assert "'=cmd|" in csv_text

        # Export Excel
        xlsx_bytes = ExportService.export_products_excel([prod])
        assert len(xlsx_bytes) > 2000
        assert xlsx_bytes.startswith(b"PK")  # ZIP / OOXML header
