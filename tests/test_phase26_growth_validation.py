"""Unit and integration tests for Phase 26: YouTube Growth Intelligence & Topic Validation Engine."""

from datetime import datetime, timezone
import pytest
from pathlib import Path
import tempfile

from src.models.channel import ChannelProfile, get_default_four_channels
from src.models.morning_report import GapFinderState
from src.models.validation import (
    TopicReadinessStatus,
    AngleType,
    TopicAngle,
    OwnChannelOverlapResult,
    CompetitorVideoRecord,
    ProductValidationRecord,
    TopicValidationReport,
)
from src.storage.database import DatabaseManager
from src.intelligence.validation_engine import TopicValidationEngine
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    EXTENDED_NAVIGATION_PAGES,
    PAGE_LABEL_CLEAN_MAP,
    EXTENDED_PAGE_SECTION_MAP,
    PAGE_VALIDATION,
    PHASE26_PAGES,
)


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_validation.db"
        manager = DatabaseManager(db_path=db_path)
        manager.init_db()
        yield manager


@pytest.fixture
def sample_channels():
    """Return default four channel profiles."""
    return get_default_four_channels()


@pytest.fixture
def validation_engine(temp_db):
    """Return validation engine connected to temporary database."""
    return TopicValidationEngine(db=temp_db)


# ==============================================================================
# 1. Navigation & Contract Integrity Tests
# ==============================================================================

def test_navigation_contract_remains_14_base_pages():
    """Ensure ALL_NAVIGATION_PAGES maintains exactly 14 base destinations for contract integrity."""
    assert len(ALL_NAVIGATION_PAGES) == 14, (
        f"Contract violation: ALL_NAVIGATION_PAGES must have exactly 14 base destinations, "
        f"found {len(ALL_NAVIGATION_PAGES)}"
    )


def test_phase26_page_registered_in_extended_navigation():
    """Verify PAGE_VALIDATION is properly registered in extended navigation structures."""
    assert PAGE_VALIDATION in PHASE26_PAGES
    assert PAGE_VALIDATION in EXTENDED_NAVIGATION_PAGES
    assert PAGE_VALIDATION not in ALL_NAVIGATION_PAGES  # Must not alter base contract


def test_phase26_clean_label_and_section_mapping():
    """Ensure clean label and section mappings exist for PAGE_VALIDATION."""
    assert PAGE_VALIDATION in PAGE_LABEL_CLEAN_MAP
    assert PAGE_LABEL_CLEAN_MAP[PAGE_VALIDATION] == "Topic Validation & Growth Intelligence"
    assert PAGE_VALIDATION in EXTENDED_PAGE_SECTION_MAP
    assert EXTENDED_PAGE_SECTION_MAP[PAGE_VALIDATION] == "DISCOVERY & INTELLIGENCE"


# ==============================================================================
# 2. Database Schema & Channel Isolation Tests
# ==============================================================================

def test_validation_report_database_crud(temp_db, sample_channels):
    """Test full CRUD operations on topic_validation_reports table."""
    channel = sample_channels[0]
    report = TopicValidationReport(
        id=None,
        channel_id=channel.id,
        topic="Affiliate Marketing for Beginners 2026",
        primary_keyword="affiliate marketing beginner guide",
        secondary_keywords=["passive income affiliate", "beginner affiliate step by step"],
        target_viewer="Beginner Creators",
        search_intent="Informational / Tutorial",
        readiness_status=TopicReadinessStatus.READY_FOR_REVIEW.value,
        composite_opportunity_score=84.5,
        confidence_tier="High Evidence",
        what_supports_idea=["Strong niche alignment", "Clear step-by-step search intent"],
        what_weakens_idea=["High volume of legacy competitor videos"],
        what_remains_unknown=["Conversion rates for proposed affiliate software"],
        further_research_needed=["Run 60-day query search", "Verify affiliate pricing"],
        is_saved=True,
    )

    # Save
    saved_id = temp_db.save_topic_validation_report(report)
    assert isinstance(saved_id, int)
    assert saved_id > 0

    # Get by ID
    retrieved = temp_db.get_topic_validation_report_by_id(saved_id)
    assert retrieved is not None
    assert retrieved.topic == report.topic
    assert retrieved.composite_opportunity_score == 84.5
    assert retrieved.readiness_status == TopicReadinessStatus.READY_FOR_REVIEW.value
    assert len(retrieved.what_supports_idea) == 2

    # Update
    retrieved.is_approved = True
    retrieved.is_saved = True
    temp_db.save_topic_validation_report(retrieved)

    re_check = temp_db.get_topic_validation_report_by_id(saved_id)
    assert re_check.is_approved is True
    assert re_check.is_saved is True

    # Delete
    deleted = temp_db.delete_topic_validation_report(saved_id)
    assert deleted is True
    assert temp_db.get_topic_validation_report_by_id(saved_id) is None


def test_channel_isolation_in_validation_reports(temp_db, sample_channels):
    """Ensure validation reports for channel 1 never bleed into channel 2, 3, or 4."""
    ch1 = sample_channels[0]  # id=1
    ch2 = sample_channels[1]  # id=2

    report1 = TopicValidationReport(
        id=None,
        channel_id=ch1.id,
        topic="AI Automation Workflows for Solopreneurs",
        primary_keyword="ai automation solopreneur",
    )
    report2 = TopicValidationReport(
        id=None,
        channel_id=ch2.id,
        topic="Best Productivity Apps for iPad",
        primary_keyword="best ipad productivity apps",
    )

    temp_db.save_topic_validation_report(report1)
    temp_db.save_topic_validation_report(report2)

    ch1_reports = temp_db.get_topic_validation_reports(channel_id=ch1.id)
    ch2_reports = temp_db.get_topic_validation_reports(channel_id=ch2.id)

    assert len(ch1_reports) == 1
    assert ch1_reports[0].topic == "AI Automation Workflows for Solopreneurs"
    assert len(ch2_reports) == 1
    assert ch2_reports[0].topic == "Best Productivity Apps for iPad"


def test_competitor_video_records_crud(temp_db):
    """Test competitor video record persistence and retrieval."""
    record = CompetitorVideoRecord(
        video_id="yt_test_12345",
        title="10 Mistakes Every AI Builder Makes",
        channel_title="Tech Builder Academy",
        published_at="2026-01-15",
        view_count=32000,
        views_per_day=711.1,
        matching_query="ai builder mistakes",
        relevance_reason="Exact intent match in title",
        relative_age_days=45,
    )

    vid = temp_db.save_competitor_video_record(record)
    assert vid == record.video_id

    records = temp_db.get_competitor_videos_by_query("ai builder mistakes")
    assert len(records) >= 1
    assert records[0].channel_title == "Tech Builder Academy"
    assert records[0].view_count == 32000


# ==============================================================================
# 3. Topic Validation Engine - 5-Point Epistemic Framework
# ==============================================================================

def test_topic_validation_report_generation_structure(validation_engine, sample_channels):
    """Verify validate_candidate_topic produces complete 5-point report structure."""
    channel = sample_channels[0]
    report = validation_engine.validate_candidate_topic(
        channel=channel,
        topic="Complete Notion Setup for Content Creators",
        keyword="notion setup content creators",
        secondary_keywords=["notion template youtube", "content calendar notion"],
        search_intent="Tutorial / Workflow",
        target_viewer="Content Creators and YouTubers",
    )

    assert isinstance(report, TopicValidationReport)
    assert report.channel_id == channel.id
    assert report.topic == "Complete Notion Setup for Content Creators"
    assert report.primary_keyword == "notion setup content creators"
    assert report.readiness_status in [
        TopicReadinessStatus.READY_FOR_REVIEW.value,
        TopicReadinessStatus.NEEDS_MORE_RESEARCH.value,
        TopicReadinessStatus.NOT_RECOMMENDED.value,
    ]


def test_topic_validation_evidence_five_points(validation_engine, sample_channels):
    """Verify all 5 required evidence sections are populated in the report."""
    channel = sample_channels[0]
    report = validation_engine.validate_candidate_topic(
        channel=channel,
        topic="How to Build Custom GPTs for Small Business",
        keyword="custom gpts for small business",
    )

    # 1. What supports the idea
    assert len(report.what_supports_idea) > 0
    # 2. What weakens the idea
    assert len(report.what_weakens_idea) > 0
    # 3. What remains unknown
    assert len(report.what_remains_unknown) > 0
    # 4. What further research is needed
    assert len(report.further_research_needed) > 0
    # 5. Readiness for human review
    assert report.readiness_status in [
        TopicReadinessStatus.READY_FOR_REVIEW.value,
        TopicReadinessStatus.NEEDS_MORE_RESEARCH.value,
        TopicReadinessStatus.NOT_RECOMMENDED.value,
    ]


def test_topic_validation_factor_scores_breakdown(validation_engine, sample_channels):
    """Ensure multi-factor breakdown contains all distinct transparent dimensions."""
    channel = sample_channels[0]
    report = validation_engine.validate_candidate_topic(
        channel=channel,
        topic="Descript vs Premiere Pro 2026 Comparison",
        keyword="descript vs premiere pro",
    )

    assert 0.0 <= report.niche_match_score <= 100.0
    assert 0.0 <= report.intent_clarity_score <= 100.0
    assert 0.0 <= report.keyword_evidence_score <= 100.0
    assert 0.0 <= report.recent_video_evidence_score <= 100.0
    assert 0.0 <= report.own_channel_overlap_score <= 100.0
    assert 0.0 <= report.product_relevance_score <= 100.0
    assert 0.0 <= report.composite_opportunity_score <= 100.0


def test_topic_validation_no_fabricated_metrics(validation_engine, sample_channels):
    """Verify epistemic honesty: warnings are present regarding missing private metrics."""
    channel = sample_channels[0]
    report = validation_engine.validate_candidate_topic(
        channel=channel,
        topic="Best Wireless Microphone for YouTube",
        keyword="best wireless microphone youtube",
        product_name="Rode Wireless Pro",
    )

    # what_remains_unknown must explicitly disclose no private metrics
    assert len(report.what_remains_unknown) > 0
    unknown_text = " ".join(report.what_remains_unknown).lower()
    assert "retention" in unknown_text or "impressions" in unknown_text or "ctr" in unknown_text


# ==============================================================================
# 4. Own-Channel Content Gap & Anti-Cannibalization Detection
# ==============================================================================

def test_detect_own_channel_overlap_exact_match(validation_engine, sample_channels):
    """Verify exact match detection against existing uploads or planned topics."""
    channel = sample_channels[0]
    # Inject existing topic
    channel.existing_video_topics = ["Notion Content Calendar Full Tutorial", "Descript Workflow Guide"]

    result = validation_engine.detect_own_channel_overlap(
        channel=channel,
        candidate_topic="Notion Content Calendar Full Tutorial",
    )

    assert result.is_exact_duplicate is True
    assert result.has_similar_title is True
    assert result.overlap_score == 0.0
    assert "Notion Content Calendar Full Tutorial" in result.overlapping_titles


def test_detect_own_channel_overlap_fuzzy_or_partial(validation_engine, sample_channels):
    """Verify partial overlap detection flags similarity without claiming exact duplicate."""
    channel = sample_channels[0]
    channel.existing_video_topics = ["Top 5 AI Video Editors 2026"]

    result = validation_engine.detect_own_channel_overlap(
        channel=channel,
        candidate_topic="Top 5 AI Video Editors for Beginners",
    )

    assert result.is_exact_duplicate is False
    assert result.has_similar_title is True
    assert result.overlap_score < 100.0
    assert len(result.suggested_action) > 0


def test_detect_own_channel_overlap_completely_new(validation_engine, sample_channels):
    """Verify completely distinct topic passes overlap check cleanly."""
    channel = sample_channels[0]
    channel.existing_video_topics = ["Notion Setup", "Descript Tutorial", "ChatGPT Prompts"]

    result = validation_engine.detect_own_channel_overlap(
        channel=channel,
        candidate_topic="Quantum Computing Fundamentals for Software Engineers",
    )

    assert result.is_exact_duplicate is False
    assert result.has_similar_title is False
    assert result.overlap_score == 100.0


# ==============================================================================
# 5. Competitor Video Analysis & Velocity
# ==============================================================================

def test_competitor_video_analysis_velocity_calculation(validation_engine):
    """Ensure views_per_day velocity is correctly calculated without fabricating retention."""
    videos = validation_engine.analyze_competitor_videos(query="ai productivity workflows", limit=5)

    assert len(videos) > 0
    for v in videos:
        assert isinstance(v, CompetitorVideoRecord)
        assert v.matching_query == "ai productivity workflows"
        assert v.views_per_day is not None
        assert v.views_per_day >= 0.0
        if v.view_count is not None and v.relative_age_days > 0:
            expected_velocity = round(v.view_count / max(1, v.relative_age_days), 1)
            assert abs(v.views_per_day - expected_velocity) <= 0.2


def test_competitor_video_epistemic_modesty_disclosures(validation_engine):
    """Ensure competitor analysis does not infer private impressions or retention."""
    videos = validation_engine.analyze_competitor_videos(query="video editing tutorial", limit=3)

    for v in videos:
        # None of the records should contain private retention or CTR claims
        assert not hasattr(v, "private_ctr")
        assert not hasattr(v, "audience_retention_rate")


# ==============================================================================
# 6. Affiliate Product Validation
# ==============================================================================

def test_affiliate_product_validation_when_enabled(validation_engine, sample_channels):
    """Verify affiliate product validation checks official specs, availability, and disclosure."""
    channel = sample_channels[0]
    channel.affiliate_enabled = True

    prod = validation_engine.validate_affiliate_product(
        channel=channel,
        product_name="Epidemic Sound",
    )

    assert isinstance(prod, ProductValidationRecord)
    assert prod.product_name == "Epidemic Sound"
    assert prod.price_source is not None
    assert prod.availability_status == "Available"
    assert len(prod.unverified_facts) > 0  # Requires manual creator verification


def test_affiliate_product_validation_when_disabled(validation_engine, sample_channels):
    """Verify product validation still succeeds with manual verification notes."""
    channel = sample_channels[1]
    channel.affiliate_enabled = False

    prod = validation_engine.validate_affiliate_product(
        channel=channel,
        product_name="Sony A7 IV",
    )

    assert isinstance(prod, ProductValidationRecord)
    assert prod.product_name == "Sony A7 IV"
    assert len(prod.unverified_facts) >= 2


# ==============================================================================
# 7. Multi-Angle Generator Archetypes
# ==============================================================================

def test_generate_topic_angles_diverse_archetypes(validation_engine, sample_channels):
    """Ensure generator produces multiple distinct archetypes without repetitive variations."""
    channel = sample_channels[0]
    angles = validation_engine.generate_topic_angles(
        channel=channel,
        topic="Building an Automated YouTube Pipeline",
        keyword="automated youtube pipeline",
    )

    assert len(angles) >= 6
    # Ensure distinct angle types
    angle_types = {a.angle_type for a in angles}
    assert len(angle_types) >= 6
    assert AngleType.BEGINNER_GUIDE.value in angle_types
    assert AngleType.DETAILED_TUTORIAL.value in angle_types
    assert AngleType.COMMON_MISTAKES.value in angle_types


def test_topic_angles_contain_required_explanations(validation_engine, sample_channels):
    """Ensure each generated angle provides full explanation dimensions."""
    channel = sample_channels[0]
    angles = validation_engine.generate_topic_angles(
        channel=channel,
        topic="Midjourney v6 vs DALL-E 3",
        keyword="midjourney vs dalle 3",
    )

    for angle in angles:
        assert isinstance(angle, TopicAngle)
        assert len(angle.intended_viewer) > 0
        assert len(angle.main_question_answered) > 0
        assert len(angle.primary_keyword) > 0
        assert len(angle.supporting_evidence) > 0
        assert len(angle.required_research) > 0


# ==============================================================================
# 8. Channel Status Transitions
# ==============================================================================

def test_validation_report_status_transitions(temp_db, validation_engine, sample_channels):
    """Test full cycle: validate -> save -> approve -> reject."""
    channel = sample_channels[0]
    report = validation_engine.validate_candidate_topic(
        channel=channel,
        topic="CapCut Desktop Mastery Course",
        keyword="capcut desktop tutorial",
    )

    # Initial save
    saved_id = temp_db.save_topic_validation_report(report)
    assert saved_id > 0
    fetched = temp_db.get_topic_validation_report_by_id(saved_id)
    assert fetched.is_approved is False
    assert fetched.is_rejected is False

    # User marks approved
    fetched.is_approved = True
    temp_db.save_topic_validation_report(fetched)
    fetched_approved = temp_db.get_topic_validation_report_by_id(saved_id)
    assert fetched_approved.is_approved is True

    # User marks rejected
    fetched_approved.is_approved = False
    fetched_approved.is_rejected = True
    temp_db.save_topic_validation_report(fetched_approved)
    fetched_rejected = temp_db.get_topic_validation_report_by_id(saved_id)
    assert fetched_rejected.is_approved is False
    assert fetched_rejected.is_rejected is True
