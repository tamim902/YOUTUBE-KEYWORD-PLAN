"""Unit and integration tests for Phase 14: Product Opportunity Ranking & Affiliate Content Planner."""

import json
from pathlib import Path
import tempfile
import pytest

from src.models.product_planner import (
    AffiliateContentBrief,
    AffiliateProductData,
    ContentFormatRecommendation,
    ProductOpportunityShortlist,
    ShortlistStatus,
)
from src.intelligence.product_planner import (
    AffiliateBriefGenerator,
    ContentFormatRecommender,
    OpportunityScorerV14,
    ProductComparisonEngine,
)
from src.providers.affiliate import (
    BaseAffiliateProvider,
    CuratedCatalogAffiliateProvider,
    ManualAffiliateProvider,
    MockAffiliateProvider,
)
from src.storage.database import DatabaseManager
from src.storage.export import ExportService


class TestPhase14Models:
    """Test suite for Phase 14 domain models and serialization."""

    def test_shortlist_statuses(self):
        """Verify all 8 workflow statuses exist."""
        statuses = [s.value for s in ShortlistStatus]
        expected = [
            "Discovered",
            "Needs Research",
            "Verified",
            "Shortlisted",
            "Brief Created",
            "In Production",
            "Published",
            "Rejected",
        ]
        assert set(expected).issubset(set(statuses))
        assert len(statuses) == 8

    def test_content_format_recommendations(self):
        """Verify all 9 video content formats exist."""
        formats = [f.value for f in ContentFormatRecommendation]
        expected = [
            "Product Review",
            "Unboxing",
            "Product Comparison",
            "Alternatives",
            "Buying Guide",
            "Beginner Tutorial",
            "Common Mistakes",
            "Long-Term Review",
            "Problem-Solving Video",
        ]
        assert set(expected) == set(formats)

    def test_affiliate_product_data_serialization(self):
        """Test AffiliateProductData dictionary conversion."""
        data = AffiliateProductData(
            product_name="Sony WF-1000XM5",
            brand="Sony",
            model="WF-1000XM5",
            merchant="Amazon",
            price=299.99,
            currency="USD",
            affiliate_program="Amazon Associates",
            commission_info="1-3% Fixed Rate",
            availability="In Stock",
            is_verified_merchant=True,
        )
        d = data.to_dict()
        assert d["product_name"] == "Sony WF-1000XM5"
        assert d["price"] == 299.99
        assert d["is_verified_merchant"] is True

        reconstructed = AffiliateProductData.from_dict(d)
        assert reconstructed.product_name == data.product_name
        assert reconstructed.price == 299.99
        assert reconstructed.availability == "In Stock"

    def test_product_opportunity_shortlist_serialization(self):
        """Test ProductOpportunityShortlist model."""
        item = ProductOpportunityShortlist(
            product_name="Bose QC Ultra",
            brand="Bose",
            model="QC Ultra",
            niche="Noise Cancelling Earbuds",
            priority="High",
            status=ShortlistStatus.SHORTLISTED.value,
            opportunity_score=82.5,
            confidence_level="High Evidence",
            formula_version="v14.0",
            supporting_keywords=["bose qc ultra review", "bose qc ultra vs sony"],
        )
        d = item.to_dict()
        assert d["opportunity_score"] == 82.5
        assert d["formula_version"] == "v14.0"

        reconstructed = ProductOpportunityShortlist.from_dict(d)
        assert reconstructed.product_name == "Bose QC Ultra"
        assert reconstructed.priority == "High"
        assert reconstructed.supporting_keywords == ["bose qc ultra review", "bose qc ultra vs sony"]


class TestOpportunityScorerV14:
    """Test suite for OpportunityScorerV14 heuristic formula."""

    def setup_method(self):
        self.scorer = OpportunityScorerV14()

    def test_score_breakdown_structure(self):
        """Ensure all 6 transparent factors are reported in breakdown."""
        score, confidence, breakdown = self.scorer.calculate_score(
            is_identity_verified=True,
            has_niche_match=True,
            supporting_keywords_count=5,
            queries_executed_count=4,
            matching_videos_count=0,
            has_merchant_data=True,
            has_affiliate_info=True,
        )
        assert 0.0 <= score <= 100.0
        assert "identity_verification" in breakdown
        assert "niche_relevance" in breakdown
        assert "keyword_evidence" in breakdown
        assert "research_coverage" in breakdown
        assert "video_scarcity" in breakdown
        assert "evidence_completeness" in breakdown
        assert breakdown["formula_version"] == "v14.0"
        assert confidence == "High Evidence"

    def test_guardrail_cap_for_insufficient_queries(self):
        """Score must be capped at <= 40 with Low Evidence when queries < 2."""
        score, confidence, breakdown = self.scorer.calculate_score(
            is_identity_verified=True,
            has_niche_match=True,
            supporting_keywords_count=10,
            queries_executed_count=1,
            matching_videos_count=0,
            has_merchant_data=True,
            has_affiliate_info=True,
        )
        assert score <= 40.0
        assert confidence == "Low Evidence"
        assert any("Capped at 40" in g for g in breakdown.get("guardrails_applied", []))

    def test_guardrail_cap_for_unverified_identity(self):
        """Score must be capped at <= 50 when identity is unverified."""
        score, confidence, breakdown = self.scorer.calculate_score(
            is_identity_verified=False,
            has_niche_match=True,
            supporting_keywords_count=5,
            queries_executed_count=4,
            matching_videos_count=0,
            has_merchant_data=True,
            has_affiliate_info=True,
            brand_identified=True,
        )
        assert score <= 50.0
        assert any("Capped at 50" in g for g in breakdown.get("guardrails_applied", []))

    def test_scarcity_requires_research_coverage(self):
        """Scarcity alone cannot claim maximum points without at least 2 queries."""
        _, _, breakdown = self.scorer.calculate_score(
            is_identity_verified=True,
            has_niche_match=True,
            supporting_keywords_count=1,
            queries_executed_count=1,
            matching_videos_count=0,
        )
        assert breakdown["video_scarcity"] < 10.0
        assert "Insufficient query coverage" in breakdown["scarcity_reason"]


class TestContentFormatRecommender:
    """Test suite for rule-based format recommender."""

    def test_comparison_format_rule(self):
        """Keywords with 'vs' trigger Product Comparison."""
        fmt, alts = ContentFormatRecommender.recommend_formats(
            product_name="Earfun Air Pro 3",
            category="Earbuds",
            keywords=["earfun air pro 3 vs sony wf-c700n", "specs"],
        )
        assert fmt == ContentFormatRecommendation.PRODUCT_COMPARISON.value
        assert len(alts) > 0

    def test_beginner_tutorial_rule(self):
        """Keywords with 'how to' or 'setup' trigger Beginner Tutorial."""
        fmt, _ = ContentFormatRecommender.recommend_formats(
            product_name="DJI Mic 2",
            category="Microphones",
            keywords=["dji mic 2 how to connect to iphone", "setup guide"],
        )
        assert fmt == ContentFormatRecommendation.BEGINNER_TUTORIAL.value

    def test_problem_solving_rule(self):
        """Keywords with 'fix' or 'issue' trigger Problem-Solving Video."""
        fmt, _ = ContentFormatRecommender.recommend_formats(
            product_name="Pixel Buds Pro",
            keywords=["pixel buds pro bluetooth pairing issue fix"],
        )
        assert fmt == ContentFormatRecommendation.PROBLEM_SOLVING.value

    def test_default_review_rule(self):
        """General keywords default to Product Review."""
        fmt, _ = ContentFormatRecommender.recommend_formats(
            product_name="Sony WH-1000XM5",
            keywords=["sony wh-1000xm5 sound quality", "noise cancelling"],
        )
        assert fmt == ContentFormatRecommendation.PRODUCT_REVIEW.value


class TestAffiliateProviders:
    """Test suite for non-fabricating affiliate providers."""

    def test_manual_provider_non_fabrication(self):
        """Unverified fields default to 'Needs verification' or None."""
        record = ManualAffiliateProvider.create_record(
            product_name="Anker Soundcore Space One",
            brand="Anker",
            model="Space One",
        )
        assert record.product_name == "Anker Soundcore Space One"
        assert record.price is None
        assert record.merchant == "Needs verification"
        assert record.affiliate_program == "Needs verification"
        assert record.commission_info == "Needs verification"
        assert record.availability == "Unknown"
        assert record.is_verified_merchant is False

    def test_curated_catalog_provider(self):
        """Curated provider retrieves known items and returns None for unknown."""
        catalog = {
            "anker space one": {
                "product_name": "Anker Soundcore Space One",
                "brand": "Anker",
                "model": "Space One",
                "merchant": "Amazon",
                "price": 99.99,
                "currency": "USD",
                "affiliate_program": "Amazon Associates",
                "commission_info": "3%",
                "availability": "In Stock",
                "is_verified_merchant": True,
            }
        }
        provider = CuratedCatalogAffiliateProvider(catalog=catalog)
        found = provider.lookup_product("Anker Space One")
        assert found is not None
        assert found.price == 99.99
        assert found.is_verified_merchant is True

        missing = provider.lookup_product("Nonexistent Item 12345")
        assert missing is None

    def test_mock_affiliate_provider(self):
        """Mock provider returns deterministic fixtures."""
        provider = MockAffiliateProvider()
        res = provider.lookup_product("Sony WF-1000XM5")
        assert res is not None
        assert res.brand == "Sony"
        assert res.price == 299.99
        assert res.is_verified_merchant is True


class TestAffiliateBriefGenerator:
    """Test suite for Affiliate Content Brief synthesis."""

    def test_generate_brief_contents(self):
        """Ensure brief contains FTC disclosure, fact checks, structure, and title ideas."""
        shortlist_item = ProductOpportunityShortlist(
            id=10,
            product_name="Sennheiser Momentum 4",
            brand="Sennheiser",
            model="Momentum 4",
            niche="Wireless Headphones",
            intended_format=ContentFormatRecommendation.PRODUCT_REVIEW.value,
        )
        brief = AffiliateBriefGenerator.generate_brief(shortlist_item)

        assert brief.product_name == "Sennheiser Momentum 4"
        assert len(brief.title_ideas) >= 3
        assert len(brief.video_structure) >= 4
        assert len(brief.questions_to_investigate) >= 2
        assert len(brief.features_to_verify) >= 2
        assert "FTC Compliance Disclosure" in brief.affiliate_disclosure
        assert len(brief.fact_checking_checklist) >= 4


class TestProductComparisonEngine:
    """Test suite for side-by-side product comparison matrix."""

    def test_missing_metrics_handled_as_unavailable(self):
        """Missing prices and merchants must display 'Unavailable' or 'Needs verification', never 0."""
        p1 = ProductOpportunityShortlist(
            product_name="Product A",
            brand="Brand A",
            model="Model 1",
            opportunity_score=75.0,
            affiliate_data={"price": None, "merchant": ""},
        )
        p2 = ProductOpportunityShortlist(
            product_name="Product B",
            brand="Brand B",
            model="Model 2",
            opportunity_score=85.0,
            affiliate_data={"price": 149.99, "currency": "USD", "merchant": "Amazon"},
        )

        matrix = ProductComparisonEngine.build_comparison_matrix([p1, p2])
        rows = matrix["matrix_rows"]
        assert len(rows) == 2

        row_a = rows[0]
        assert row_a["Price"] == "Unavailable"
        assert row_a["Merchant"] == "Needs verification"

        row_b = rows[1]
        assert row_b["Price"] == "$149.99 USD"
        assert row_b["Merchant"] == "Amazon"
        assert "disclaimer" in matrix


class TestPhase14DatabaseStorage:
    """Test suite for Phase 14 database tables and CRUD operations."""

    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = tmp_path / "test_p14.db"
        mgr = DatabaseManager(db_path=db_file)
        mgr.init_db()
        return mgr

    def test_shortlist_crud(self, test_db):
        """Test insert, query, update status, and delete on product_opportunity_shortlist."""
        item = ProductOpportunityShortlist(
            product_name="Nothing Ear (2)",
            brand="Nothing",
            model="Ear (2)",
            niche="Wireless Earbuds",
            priority="High",
            status=ShortlistStatus.SHORTLISTED.value,
            opportunity_score=78.0,
            confidence_level="Moderate Evidence",
        )
        shortlist_id = test_db.save_shortlist_product(item)
        assert shortlist_id > 0

        # Query
        retrieved = test_db.get_shortlist_product(shortlist_id)
        assert retrieved is not None
        assert retrieved.product_name == "Nothing Ear (2)"
        assert retrieved.status == ShortlistStatus.SHORTLISTED.value

        # Update status
        updated = test_db.update_shortlist_status(
            shortlist_id,
            status=ShortlistStatus.IN_PRODUCTION.value,
            priority="High",
            notes="Ready for filming",
        )
        assert updated is True

        retrieved_updated = test_db.get_shortlist_product(shortlist_id)
        assert retrieved_updated.status == ShortlistStatus.IN_PRODUCTION.value
        assert retrieved_updated.notes == "Ready for filming"

        # List
        all_items = test_db.get_shortlist_products(status=ShortlistStatus.IN_PRODUCTION.value)
        assert len(all_items) == 1

        # Delete
        deleted = test_db.delete_shortlist_product(shortlist_id)
        assert deleted is True
        assert test_db.get_shortlist_product(shortlist_id) is None

    def test_affiliate_brief_crud(self, test_db):
        """Test save, retrieve, and delete on product_content_briefs_v14."""
        item = ProductOpportunityShortlist(
            product_name="JBL Tune 760NC",
            brand="JBL",
            model="Tune 760NC",
        )
        s_id = test_db.save_shortlist_product(item)

        brief = AffiliateContentBrief(
            shortlist_id=s_id,
            product_name="JBL Tune 760NC",
            primary_keyword="jbl tune 760nc review",
            brand="JBL",
            model="Tune 760NC",
            target_audience="Budget audio buyers",
        )
        b_id = test_db.save_affiliate_brief(brief)
        assert b_id > 0

        # Retrieve
        loaded_brief = test_db.get_affiliate_brief(s_id)
        assert loaded_brief is not None
        assert loaded_brief.primary_keyword == "jbl tune 760nc review"
        assert loaded_brief.target_audience == "Budget audio buyers"

        # Delete
        del_res = test_db.delete_affiliate_brief(b_id)
        assert del_res is True
        assert test_db.get_affiliate_brief(s_id) is None

    def test_affiliate_catalog_crud(self, test_db):
        """Test save and lookup on product_affiliate_catalog."""
        entry = AffiliateProductData(
            product_name="Sony WH-CH720N",
            brand="Sony",
            model="WH-CH720N",
            merchant="Best Buy",
            price=129.99,
            currency="USD",
            affiliate_program="Best Buy Affiliate",
            commission_info="0.5%",
            availability="In Stock",
            is_verified_merchant=True,
        )
        cat_id = test_db.save_affiliate_catalog_entry(entry)
        assert cat_id > 0

        found = test_db.get_affiliate_catalog_entry("Sony WH-CH720N")
        assert found is not None
        assert found.price == 129.99
        assert found.merchant == "Best Buy"

    def test_schema_version_preserved(self, test_db):
        """Verify schema version remains 3 for backwards compatibility."""
        assert test_db.migration_manager.get_current_schema_version() == 3


class TestPhase14Exports:
    """Test suite for Phase 14 CSV and Excel export formats."""

    def test_shortlist_csv_export(self):
        """CSV export must include UTF-8 BOM and formula sanitization."""
        p = ProductOpportunityShortlist(
            product_name="=HYPERLINK('http://malicious.com')",
            brand="+BrandMalicious",
            model="Model-Safe",
            niche="Tech",
            priority="High",
            opportunity_score=70.0,
            affiliate_data={"price": 99.0, "currency": "USD", "merchant": "Amazon"},
        )
        csv_bytes = ExportService.export_shortlist_csv([p])
        assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        text = csv_bytes.decode("utf-8-sig")
        # Formula prefixes must be escaped with a leading single quote
        assert "'=HYPERLINK" in text
        assert "'+BrandMalicious" in text

    def test_shortlist_excel_export(self):
        """Excel export must generate valid XLSX bytes."""
        p = ProductOpportunityShortlist(
            product_name="JBL Live 660NC",
            brand="JBL",
            model="Live 660NC",
            opportunity_score=65.0,
        )
        xlsx_bytes = ExportService.export_shortlist_excel([p])
        assert len(xlsx_bytes) > 0
        assert xlsx_bytes.startswith(b"PK")  # ZIP container header for XLSX

    def test_affiliate_brief_exports(self):
        """Export brief to CSV and XLSX."""
        brief = AffiliateContentBrief(
            product_name="Bose QuietComfort 45",
            primary_keyword="bose qc45 review",
            brand="Bose",
            title_ideas=["Bose QC45 Review 2026"],
        )
        csv_bytes = ExportService.export_affiliate_brief_csv(brief)
        assert csv_bytes.startswith(b"\xef\xbb\xbf")
        text = csv_bytes.decode("utf-8-sig")
        assert "Bose QuietComfort 45" in text
        assert "FTC Affiliate Disclosure Reminder" in text

        xlsx_bytes = ExportService.export_affiliate_brief_excel(brief)
        assert len(xlsx_bytes) > 0
        assert xlsx_bytes.startswith(b"PK")

    def test_comparison_matrix_exports(self):
        """Export comparison matrix to CSV and XLSX."""
        matrix_rows = [
            {"Product Name": "Item 1", "Price": "Unavailable", "Merchant": "Needs verification"},
            {"Product Name": "Item 2", "Price": "$99.99 USD", "Merchant": "Amazon"},
        ]
        csv_bytes = ExportService.export_comparison_matrix_csv(matrix_rows)
        assert csv_bytes.startswith(b"\xef\xbb\xbf")
        assert "Unavailable" in csv_bytes.decode("utf-8-sig")

        xlsx_bytes = ExportService.export_comparison_matrix_excel(matrix_rows)
        assert len(xlsx_bytes) > 0
        assert xlsx_bytes.startswith(b"PK")
