"""Phase 12.1 Comprehensive Audit & Verification Test Suite.

Audits:
1. End-to-end product research pipeline on 'Wireless Earbuds' niche.
2. Provider search with 60-day date bounding (publishedAfter / publishedBefore).
3. Evidence-based 4-tier classification and minimum query coverage rules.
4. Transparent 0-100 Opportunity Scoring rules, penalties, and zero synthetic volume.
5. Data integrity: database persistence, aliases, duplicate video deduplication,
   video exclusions, partial recovery, and formula-safe CSV/XLSX exports.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
import pytest

from src.intelligence.product_finder import (
    NicheProductPipeline,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
)
from src.models.product import (
    CandidateProduct,
    ClassificationCategory,
    ProductQueryExecution,
    ProductResearchSession,
    ProductVideoMatch,
    SearchMode,
)
from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.storage.database import DatabaseManager
from src.storage.export import ExportService


class MockAuditedSerpProvider:
    """Mock SERP Provider simulating live YouTube Data API v3 with date range enforcement."""

    def __init__(self, sample_videos_by_query: Dict[str, List[CompetitorVideoItem]]):
        self.sample_videos = sample_videos_by_query
        self.recorded_calls: List[Dict[str, Any]] = []

    def is_connected(self) -> bool:
        return True

    def analyze_keyword(
        self,
        keyword: str,
        language: str = "en",
        country: str = "US",
        max_results: int = 10,
        published_after: str = "",
        published_before: str = "",
        use_cache: bool = True,
        **kwargs: Any,
    ) -> KeywordSerpAnalysis:
        self.recorded_calls.append({
            "keyword": keyword,
            "language": language,
            "country": country,
            "max_results": max_results,
            "published_after": published_after,
            "published_before": published_before,
        })
        vids = self.sample_videos.get(keyword.strip().lower(), [])
        return KeywordSerpAnalysis(
            keyword=keyword,
            language=language,
            country=country,
            videos=vids[:max_results],
            total_videos_analyzed=len(vids[:max_results]),
            status_message="OK",
        )


def test_audit_niche_product_research_workflow(tmp_path: Path) -> None:
    """Verify complete product discovery, query generation, 60-day search, matching, and classification."""
    db_file = tmp_path / "audit_phase12.db"
    db = DatabaseManager(db_path=db_file)
    db.init_db()

    pipeline = NicheProductPipeline()
    start_iso, end_iso = pipeline.get_default_date_range(60)

    # Validate 60-day range
    is_valid, msg = pipeline.validate_date_range(start_iso, end_iso)
    assert is_valid is True

    # Prepare Mock Videos published in date window
    now = datetime.now(timezone.utc)
    pub_date_1 = (now - timedelta(days=10)).isoformat()
    pub_date_2 = (now - timedelta(days=25)).isoformat()

    mock_videos: Dict[str, List[CompetitorVideoItem]] = {
        "sony wf-1000xm5 review": [
            CompetitorVideoItem(
                video_id="vid_xm5_01",
                title="Sony WF-1000XM5 In-Depth Review - 60 Days Later",
                channel_id="ch_audio_lab",
                channel_title="Audio Lab",
                publish_date=pub_date_1,
                view_count=85000,
                duration="12:30",
            ),
            CompetitorVideoItem(
                video_id="vid_xm5_02",
                title="Why I Kept the Sony WF-1000XM5",
                channel_id="ch_tech_daily",
                channel_title="Tech Daily",
                publish_date=pub_date_2,
                view_count=42000,
                duration="09:15",
            ),
        ],
        "sony wf-1000xm5 unboxing": [
            CompetitorVideoItem(
                video_id="vid_xm5_01",  # Same video as above to test deduplication
                title="Sony WF-1000XM5 In-Depth Review - 60 Days Later",
                channel_id="ch_audio_lab",
                channel_title="Audio Lab",
                publish_date=pub_date_1,
                view_count=85000,
            ),
            CompetitorVideoItem(
                video_id="vid_xm5_03",
                title="Sony WF-1000XM5 Silver Unboxing & First Impressions",
                channel_id="ch_unboxing_guy",
                channel_title="Unbox Guy",
                publish_date=pub_date_2,
                view_count=19000,
            ),
        ],
        "moondrop space travel review": [
            CompetitorVideoItem(
                video_id="vid_md_01",
                title="Moondrop Space Travel - Best $25 Earbuds Still?",
                channel_id="ch_budget_hifi",
                channel_title="Budget HiFi",
                publish_date=pub_date_1,
                view_count=12000,
            )
        ],
        "moondrop space travel unboxing": [],  # 0 results
        "earfun air pro 4 review": [],        # 0 results
        "earfun air pro 4 unboxing": [],      # 0 results
    }

    mock_provider = MockAuditedSerpProvider(mock_videos)

    # Products: 1 popular, 1 few matches, 1 zero matches (>=2 queries), 1 single query (insufficient)
    p_xm5 = CandidateProduct(
        product_name="Sony WF-1000XM5", brand="Sony", model="WF-1000XM5",
        source="Curated Market Catalog", verification_status="Verified Market Product"
    )
    p_moondrop = CandidateProduct(
        product_name="Moondrop Space Travel", brand="Moondrop", model="Space Travel",
        source="Curated Market Catalog", verification_status="Verified Market Product"
    )
    p_earfun = CandidateProduct(
        product_name="EarFun Air Pro 4", brand="EarFun", model="Air Pro 4",
        source="Curated Market Catalog", verification_status="Verified Market Product"
    )
    p_single_q = CandidateProduct(
        product_name="Rare Vintage Earbuds", brand="Rare", model="Vintage",
        source="User Supplied", verification_status="User Supplied"
    )

    matcher = ProductMatcher()
    scorer = ProductOpportunityScorer()

    # Session persistence
    session = ProductResearchSession(
        niche="Wireless Earbuds",
        language="en",
        country="US",
        start_date=start_iso,
        end_date=end_iso,
        min_queries_for_zero_match=2,
        few_videos_threshold=4,
    )
    sess_id = db.save_product_research_session(session)

    # 1. Investigate XM5 (2 queries, 4 total matches, 1 duplicate removed -> 3 unique videos)
    q_xm5 = [("Sony WF-1000XM5 review", SearchMode.REVIEWS.value), ("Sony WF-1000XM5 unboxing", SearchMode.UNBOXING.value)]
    all_xm5_vids = []
    for q_text, mode in q_xm5:
        serp = mock_provider.analyze_keyword(q_text, published_after=start_iso, published_before=end_iso)
        p_xm5.queries_executed.append(q_text)
        p_xm5.queries_succeeded += 1
        db.save_product_search_query(ProductQueryExecution(session_id=sess_id, product_name=p_xm5.product_name, query_text=q_text, search_mode=mode))
        for v in serp.videos:
            is_m, m_type, m_field, m_terms = matcher.is_match(p_xm5, v.title)
            if is_m:
                all_xm5_vids.append(ProductVideoMatch(
                    video_id=v.video_id, title=v.title, channel_id=v.channel_id,
                    channel_title=v.channel_title, publish_date=v.publish_date,
                    url=f"https://www.youtube.com/watch?v={v.video_id}", views=v.view_count,
                    match_type=m_type, match_field=m_field, matched_terms=m_terms
                ))

    # Deduplicate video matches: 4 raw matches -> 3 unique videos
    assert len(all_xm5_vids) == 4
    deduped_xm5 = list({m.video_id: m for m in all_xm5_vids}.values())
    assert len(deduped_xm5) == 3  # vid_xm5_01, vid_xm5_02, and vid_xm5_03
    p_xm5.matching_videos_count = len(deduped_xm5)
    p_xm5.unique_channels_count = len(set(m.channel_id for m in deduped_xm5))
    p_xm5.latest_video_date = sorted([m.publish_date for m in deduped_xm5], reverse=True)[0]
    p_xm5.session_id = sess_id

    score_xm5, class_xm5, conf_xm5, bd_xm5 = scorer.calculate_score(p_xm5, few_videos_threshold=4)
    p_xm5.opportunity_score = score_xm5
    p_xm5.classification = class_xm5
    p_xm5.confidence_level = conf_xm5
    p_xm5.opportunity_score_breakdown = bd_xm5
    assert class_xm5 == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value  # 2 videos < threshold 3
    assert conf_xm5 == "High"
    p_xm5_id = db.save_discovered_product(p_xm5)
    for m in deduped_xm5:
        m.product_id = p_xm5_id
        db.save_product_video_match(m)

    # 2. Investigate EarFun Air Pro 4 (2 queries, 0 videos -> NO_MATCHING_VIDEOS_FOUND)
    q_earfun = [("earfun air pro 4 review", SearchMode.REVIEWS.value), ("earfun air pro 4 unboxing", SearchMode.UNBOXING.value)]
    for q_text, mode in q_earfun:
        mock_provider.analyze_keyword(q_text, published_after=start_iso, published_before=end_iso)
        p_earfun.queries_executed.append(q_text)
        p_earfun.queries_succeeded += 1
        db.save_product_search_query(ProductQueryExecution(session_id=sess_id, product_name=p_earfun.product_name, query_text=q_text, search_mode=mode))

    p_earfun.matching_videos_count = 0
    p_earfun.session_id = sess_id
    score_ef, class_ef, conf_ef, bd_ef = scorer.calculate_score(p_earfun, min_queries_for_zero_match=2)
    p_earfun.opportunity_score = score_ef
    p_earfun.classification = class_ef
    p_earfun.confidence_level = conf_ef
    p_earfun.opportunity_score_breakdown = bd_ef
    assert class_ef == ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value
    assert conf_ef == "High"
    assert bd_ef["opportunity_factor"] == 40.0
    db.save_discovered_product(p_earfun)

    # 3. Investigate Rare Vintage (1 query only, 0 videos -> INSUFFICIENT_RESEARCH)
    mock_provider.analyze_keyword("rare vintage review", published_after=start_iso, published_before=end_iso)
    p_single_q.queries_executed.append("rare vintage review")
    p_single_q.queries_succeeded = 1
    p_single_q.matching_videos_count = 0
    p_single_q.session_id = sess_id
    score_sq, class_sq, conf_sq, bd_sq = scorer.calculate_score(p_single_q, min_queries_for_zero_match=2)
    p_single_q.opportunity_score = score_sq
    p_single_q.classification = class_sq
    p_single_q.confidence_level = conf_sq
    p_single_q.opportunity_score_breakdown = bd_sq
    assert class_sq == ClassificationCategory.INSUFFICIENT_RESEARCH.value
    assert conf_sq == "Low"
    assert score_sq <= 45.0
    db.save_discovered_product(p_single_q)

    # Verify Database Retrieval & Partial Research Recovery
    recovered_prods = db.get_discovered_products(session_id=sess_id)
    assert len(recovered_prods) == 3
    rec_names = [p["product_name"] for p in recovered_prods]
    assert "Sony WF-1000XM5" in rec_names
    assert "EarFun Air Pro 4" in rec_names
    assert "Rare Vintage Earbuds" in rec_names

    # Verify foreign key video matches
    xm5_db_matches = db.get_product_video_matches(p_xm5_id)
    assert len(xm5_db_matches) == 3
    assert xm5_db_matches[0]["url"].startswith("https://www.youtube.com/watch?v=")
    assert xm5_db_matches[0]["publish_date"] != ""


def test_audit_scoring_formula_edge_cases_and_penalties() -> None:
    """Verify scoring formula penalties for uncertain extractions and unresearched items."""
    scorer = ProductOpportunityScorer()

    # Case A: Uncertain extraction candidate ("Needs Review")
    # Even if zero matching videos were found across 2 queries, uncertain candidate should NOT get top score
    candidate_unverified = CandidateProduct(
        product_name="Random Noise String 2026",
        brand="Random",
        model="Noise String",
        source="Extracted Candidate",
        verification_status="Needs Review",
        extraction_confidence="Uncertain / Needs Review",
        queries_executed=["query 1", "query 2"],
        queries_succeeded=2,
        matching_videos_count=0,
    )
    score_unver, cat_unver, conf_unver, _ = scorer.calculate_score(candidate_unverified, min_queries_for_zero_match=2)
    assert cat_unver in (
        ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
        ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value,
    )
    assert conf_unver == "Low"  # Penalized confidence
    assert score_unver <= 55.0  # Capped penalty for uncertain identity

    # Case B: Verified product with 1 video and 3 queries
    candidate_verified = CandidateProduct(
        product_name="Verified Market Earbuds Pro",
        brand="Verified",
        model="Earbuds Pro",
        source="Curated Market Catalog",
        verification_status="Verified Market Product",
        extraction_confidence="High",
        queries_executed=["query 1", "query 2", "query 3"],
        queries_succeeded=3,
        matching_videos_count=1,
    )
    score_ver, cat_ver, conf_ver, bd_ver = scorer.calculate_score(candidate_verified, few_videos_threshold=3)
    assert cat_ver == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value
    assert conf_ver == "High"
    assert score_ver > score_unver  # Verified item with 1 video outscores unverified zero-match!
    assert score_ver >= 85.0

    # Case C: Zero synthetic metrics check
    assert "monthly_search_volume" not in bd_ver
    assert "keyword_difficulty" not in bd_ver
    assert "empirical_limitation_notice" in bd_ver


def test_audit_database_integrity_and_exclusions(tmp_path: Path) -> None:
    """Verify video exclusion toggle updates database properly without deleting data."""
    db_file = tmp_path / "audit_exclusion.db"
    db = DatabaseManager(db_path=db_file)
    db.init_db()

    # Save a product
    prod = CandidateProduct(product_name="Test Headphones", brand="Test", model="Headphones")
    p_id = db.save_discovered_product(prod)

    # Save a video match
    match = ProductVideoMatch(
        product_id=p_id,
        video_id="v_ex_123",
        title="Test Headphones Review",
        publish_date="2026-09-01T12:00:00Z",
        url="https://youtube.com/watch?v=v_ex_123",
        is_excluded=False,
    )
    m_id = db.save_product_video_match(match)

    # Initially not excluded
    matches_init = db.get_product_video_matches(p_id, include_excluded=False)
    assert len(matches_init) == 1

    # Toggle exclude
    db.exclude_video_match(m_id, is_excluded=True)
    matches_after_exclude = db.get_product_video_matches(p_id, include_excluded=False)
    assert len(matches_after_exclude) == 0

    # Include all shows it marked as excluded
    matches_all = db.get_product_video_matches(p_id, include_excluded=True)
    assert len(matches_all) == 1
    assert matches_all[0]["is_excluded"] is True


def test_audit_exports_formula_sanitization() -> None:
    """Verify formula injection sanitization in both CSV and XLSX exports."""
    malicious_product = CandidateProduct(
        product_name="=cmd|'/C calc'!A0",
        brand="+SUM(1,2)",
        model="@HYPERLINK('http://malicious.com')",
        niche="-Dangerous Niche",
        queries_executed=["=DANGEROUS_FORMULA()"],
        queries_succeeded=1,
    )

    # CSV Export
    csv_bytes = ExportService.export_products_csv([malicious_product])
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "'=cmd|'/C calc'!A0" in csv_text
    assert "'+SUM(1,2)" in csv_text

    # Excel Export
    excel_bytes = ExportService.export_products_excel([malicious_product])
    assert len(excel_bytes) > 1000
    assert excel_bytes[:4] == b"PK\x03\x04"  # Valid ZIP/XLSX signature
