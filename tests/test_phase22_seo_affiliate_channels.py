"""Comprehensive automated test suite for Phase 22:
- Advanced YouTube SEO + Affiliate Marketing + Four-Channel Daily Opportunity Engine.

Tests:
1. Channel Profile Workspace (initialization, URL validation, exclusions, persistence)
2. SEO Intent Classification & Zero Fake Metrics Guarantee
3. Transparent Multi-Dimensional Opportunity Scoring & Disclaimer
4. 6-Angle SEO Title Generator & Truncation Checks
5. 8-Part Description Studio & FTC Affiliate Disclosure Enforcement
6. Rolling 60-Day Gap Finder (All 4 Distinct States)
7. Four-Channel Independent Daily Morning Opportunity Engine (All 18 Fields)
8. Notification Delivery Service (Graceful Fallback & Webhook)
9. Data Persistence & Formula Injection Protection
"""

import json
from datetime import datetime, timezone
import pytest

from src.intelligence.channel_manager import ChannelManager
from src.intelligence.description_studio import DescriptionStudio
from src.intelligence.gap_finder import GapFinder
from src.intelligence.notification import NotificationService
from src.intelligence.seo_engine import SeoEngine
from src.intelligence.daily_engine import DailyOpportunityEngine
from src.models.channel import ChannelProfile, get_default_four_channels
from src.models.morning_report import DailyIdeaItem, DailyMorningReport, GapFinderState, IdeaReviewStatus
from src.models.seo import (
    AffiliatePotentialTier,
    KeywordIntentType,
    ResearchConfidenceTier,
    SeoOpportunityTier,
    SeoRelevanceTier,
    VideoDescription,
)
from src.storage.database import DatabaseManager
from src.storage.export import sanitize_formula_injection


@pytest.fixture
def temp_db(tmp_path):
    """Provide an isolated SQLite database instance."""
    db_file = tmp_path / "test_phase22.db"
    manager = DatabaseManager(db_path=db_file)
    manager.init_db()
    return manager


# ==============================================================================
# 1. Four-Channel Workspace & Profile Portfolio Tests
# ==============================================================================

def test_default_four_channels_initialization(temp_db):
    """Verify that 4 distinct default channel profiles are seeded into the database."""
    chan_mgr = ChannelManager(database=temp_db)
    channels = chan_mgr.get_all_channels()

    assert len(channels) == 4
    ids = [c.id for c in channels]
    assert ids == [1, 2, 3, 4]

    # Verify distinct niches
    niches = {c.channel_niche for c in channels}
    assert len(niches) >= 3

    # Verify channel 1
    ch1 = chan_mgr.get_channel(1)
    assert ch1 is not None
    assert ch1.channel_name == "TechGear Pulse"
    assert ch1.target_country == "US"
    assert ch1.target_language == "en"
    assert ch1.affiliate_enabled is True
    assert len(ch1.sub_niches) > 0


def test_channel_profile_validation_and_url_checks():
    """Verify channel URL regex validation and profile metadata constraints."""
    profile = ChannelProfile(
        id=1,
        channel_name="Valid Channel",
        channel_url="https://youtube.com/@ValidHandle",
        channel_niche="Tech",
        target_country="US",
        target_language="en",
    )
    is_valid, msg = profile.validate_channel_url()
    assert is_valid is True
    assert "Valid" in msg

    # Invalid URL scheme
    bad_profile = ChannelProfile(
        id=1,
        channel_name="Bad Channel",
        channel_url="https://notyoutube.com/channel/123",
        channel_niche="Tech",
    )
    is_valid, msg = bad_profile.validate_channel_url()
    assert is_valid is False


def test_channel_exclusions_filtering():
    """Verify that excluded topics, brands, products, and negative keywords are strictly filtered."""
    profile = ChannelProfile(
        id=1,
        channel_name="Filter Test",
        excluded_topics=["Cheap Membrane"],
        excluded_brands=["GenericBrand"],
        excluded_products=["Toy Keyboard"],
        excluded_keywords=["cracked", "free hack"],
    )

    # Negative hits
    assert profile.is_topic_excluded("Best Cheap Membrane Keyboards") is True
    assert profile.is_topic_excluded("GenericBrand Switch Review") is True
    assert profile.is_topic_excluded("Toy Keyboard for toddlers") is True
    assert profile.is_topic_excluded("Download cracked firmware free hack") is True

    # Positive clean items
    assert profile.is_topic_excluded("High-end Custom Mechanical Keyboard") is False
    assert profile.is_topic_excluded("Gateron Oil King Sound Test") is False


# ==============================================================================
# 2. Advanced YouTube SEO Intelligence Tests
# ==============================================================================

def test_seo_intent_classification():
    """Verify search intent classification across 10+ distinct SEO buckets."""
    engine = SeoEngine()

    assert engine.classify_keyword_intent("how to lube mechanical switches") == KeywordIntentType.HOW_TO
    assert engine.classify_keyword_intent("keyboard chattering fix not working") == KeywordIntentType.PROBLEM_SOLVING
    assert engine.classify_keyword_intent("wooting 80he vs apex pro") == KeywordIntentType.COMPARISON
    assert engine.classify_keyword_intent("best budget espresso grinder 2026") == KeywordIntentType.REVIEW_BUYER
    assert engine.classify_keyword_intent("why do my switches sound scratchy") == KeywordIntentType.QUESTION
    assert engine.classify_keyword_intent("top 5 keycaps for thock") == KeywordIntentType.LISTICLE
    assert engine.classify_keyword_intent("gateron milky yellow pro switch") == KeywordIntentType.PRODUCT_SPECIFIC


def test_seo_opportunity_scoring_zero_fake_metrics():
    """Verify transparent multi-dimensional scoring and zero fake search volume guarantee."""
    engine = SeoEngine()
    channel = ChannelProfile(
        id=1,
        channel_niche="Mechanical Keyboards",
        sub_niches=["Switches", "Sound Test"],
        affiliate_enabled=True,
    )

    score = engine.calculate_opportunity_score(
        keyword="how to lube mechanical switches step by step",
        channel=channel,
        recent_video_count=2,  # low competition gap
        is_exact_match_available=True,
        has_affiliate_opportunity=True,
    )

    # Zero fake metrics checks
    assert score.is_search_volume_available is False
    assert score.volume_display_text == "Search volume unavailable"
    assert "Does not guarantee" in score.guaranteed_ranking_disclaimer

    # Scores breakdown
    assert 0.0 <= score.overall_score <= 100.0
    assert score.seo_relevance_label in [t.value for t in SeoRelevanceTier]
    assert score.opportunity_label in [t.value for t in SeoOpportunityTier]
    assert score.affiliate_potential_label in [t.value for t in AffiliatePotentialTier]
    assert score.confidence_level in [t.value for t in ResearchConfidenceTier]
    assert "gap_opportunity_score" in score.signals_breakdown


# ==============================================================================
# 3. SEO Title Generator Tests
# ==============================================================================

def test_seo_title_generator_angles_and_truncation():
    """Verify 6 distinct title angles and length truncation checks."""
    engine = SeoEngine()
    titles = engine.generate_seo_titles(
        topic="Hall Effect Keyboards",
        primary_keyword="best hall effect keyboard",
    )

    assert len(titles) == 6
    angles = {t.angle_category for t in titles}
    assert "Search-Focused" in angles
    assert "Question-Based" in angles
    assert "Problem-Solving" in angles
    assert "Comparison (VS)" in angles
    assert "Review & Buyer-Intent" in angles
    assert "Curiosity & Value" in angles

    for t in titles:
        assert len(t.title) > 0
        assert t.character_count == len(t.title)
        assert t.truncation_risk in [
            "Optimal (Mobile & Desktop <60 chars)",
            "Desktop Safe (<75 chars, may truncate on some mobile)",
            "High Truncation Risk (>75 chars, title will truncate on mobile)",
        ]


# ==============================================================================
# 4. Description Studio & FTC Affiliate Compliance Tests
# ==============================================================================

def test_description_studio_assembly_and_ftc_compliance():
    """Verify 8-part description generation, character limits, and FTC disclosure enforcement."""
    studio = DescriptionStudio()
    channel = ChannelProfile(
        id=1,
        channel_name="TechGear Pulse",
        channel_niche="Mechanical Keyboards",
        affiliate_enabled=True,
        channel_footer="TechGear Pulse • Independent Reviews",
    )

    desc = studio.build_description(
        topic="Wooting 80HE Review",
        primary_keyword="wooting 80he review",
        channel=channel,
        affiliate_links=[{"label": "Wooting 80HE", "url": "https://amzn.to/example", "merchant": "Amazon"}],
        include_ftc_disclosure=True,
    )

    assert desc.character_count <= 5000
    assert desc.has_affiliate_links is True
    assert desc.has_affiliate_disclosure is True
    assert desc.is_ftc_compliant is True
    assert "DISCLOSURE" in desc.full_text

    # Audit check
    is_compliant, errors, warnings = studio.audit_description(desc)
    assert is_compliant is True
    assert len(errors) == 0


def test_description_studio_ftc_violation_flagged():
    """Verify that omission of FTC disclosure when affiliate links are present fails compliance."""
    studio = DescriptionStudio()
    channel = ChannelProfile(id=1, channel_name="Test", affiliate_enabled=False)

    # Manually build description with affiliate links but no disclosure
    desc = VideoDescription(
        channel_id=1,
        channel_name="Test",
        topic="Affiliate Test",
        primary_keyword="test",
        affiliate_links=[{"label": "Product", "url": "https://example.com/aff"}],
        affiliate_disclosure="",
        has_affiliate_links=True,
        has_affiliate_disclosure=False,
    )
    desc.assemble_full_text()

    is_compliant, errors, warnings = studio.audit_description(desc)
    assert is_compliant is False
    assert any("FTC Affiliate Disclosure is REQUIRED" in e for e in errors)


# ==============================================================================
# 5. Rolling 60-Day Content Gap Finder Tests
# ==============================================================================

def test_gap_finder_four_distinct_states():
    """Verify rolling 60-day gap finder correctly returns all 4 required states."""
    gf = GapFinder(window_days=60)
    start_dt, end_dt, window_str = gf.get_rolling_window()
    assert (end_dt - start_dt).days == 60
    assert "60 days" in window_str

    # State 1: Matching Recent Videos Found (>= 4 videos)
    s1, _ = gf.evaluate_gap_state(matching_videos_count=5, queries_executed=3)
    assert s1 == GapFinderState.MATCHING_RECENT_VIDEOS_FOUND

    # State 2: Few Matching Recent Videos Found (1 to 3 videos, Sweet spot)
    s2, _ = gf.evaluate_gap_state(matching_videos_count=2, queries_executed=2)
    assert s2 == GapFinderState.FEW_MATCHING_RECENT_VIDEOS_FOUND

    # State 3: No Matching Videos Found in Executed Searches (0 videos across >=2 queries)
    s3, _ = gf.evaluate_gap_state(matching_videos_count=0, queries_executed=2)
    assert s3 == GapFinderState.NO_MATCHING_VIDEOS_FOUND

    # State 4: Insufficient Research (<2 queries or API error)
    s4a, _ = gf.evaluate_gap_state(matching_videos_count=0, queries_executed=1)
    assert s4a == GapFinderState.INSUFFICIENT_RESEARCH

    s4b, _ = gf.evaluate_gap_state(matching_videos_count=0, queries_executed=2, has_api_error=True)
    assert s4b == GapFinderState.INSUFFICIENT_RESEARCH


# ==============================================================================
# 6. Four-Channel Independent Daily Opportunity Engine Tests
# ==============================================================================

def test_daily_morning_report_execution_all_18_fields(temp_db):
    """Verify daily morning report execution generates ideas for all 4 channels with 18 fields."""
    chan_mgr = ChannelManager(database=temp_db)
    engine = DailyOpportunityEngine(chan_mgr=chan_mgr, database=temp_db)

    report = engine.run_daily_morning_report(
        timezone_name="Asia/Dhaka",
        scheduled_time="07:00",
        ideas_per_channel=4,
    )

    assert report is not None
    assert report.total_channels_processed == 4
    assert len(report.ideas) == 16
    assert report.status == "Completed"

    # Verify channel distribution
    channel_ids = {i.channel_id for i in report.ideas}
    assert channel_ids == {1, 2, 3, 4}

    # Verify all 18 evidence fields on every idea
    for item in report.ideas:
        assert item.channel_id in [1, 2, 3, 4]
        assert bool(item.channel_name)
        assert bool(item.proposed_topic)
        assert bool(item.main_keyword)
        assert len(item.supporting_keywords) >= 2
        assert bool(item.search_intent)
        assert bool(item.target_viewer)
        assert bool(item.why_topic_worth_researching)
        assert item.recent_relevant_videos_found >= 0
        assert "60 days" in item.exact_research_window
        assert bool(item.source_and_coverage_summary)
        assert item.opportunity_estimate >= 0.0
        assert bool(item.confidence_level)
        assert bool(item.suggested_video_format)
        assert len(item.seo_focused_title_options) >= 3
        assert bool(item.suggested_thumbnail_concept)
        assert bool(item.description_draft)
        assert bool(item.next_recommended_action)
        assert item.gap_state in [s.value for s in GapFinderState]


def test_channel_isolation_on_error(temp_db, monkeypatch):
    """Verify that a failure in one channel does not interrupt or fail the other 3 channels."""
    chan_mgr = ChannelManager(database=temp_db)
    engine = DailyOpportunityEngine(chan_mgr=chan_mgr, database=temp_db)

    original_gen = engine._generate_ideas_for_channel

    def mock_gen_with_failure(channel, count=4, existing_topics=None):
        if channel.id == 2:
            raise RuntimeError("Simulated API failure on channel 2")
        return original_gen(channel, count=count, existing_topics=existing_topics)

    monkeypatch.setattr(engine, "_generate_ideas_for_channel", mock_gen_with_failure)

    report = engine.run_daily_morning_report()
    # Channels 1, 3, 4 must succeed!
    assert report.total_channels_processed == 3
    assert len(report.ideas) == 12
    assert {i.channel_id for i in report.ideas} == {1, 3, 4}
    assert report.status == "Partially Completed"


# ==============================================================================
# 7. Notification Delivery Service Tests
# ==============================================================================

def test_notification_service_safe_fallback_when_unconfigured():
    """Verify that notification service skips gracefully without errors when unconfigured."""
    service = NotificationService()
    report = DailyMorningReport(
        run_date="2026-10-20",
        timezone_name="Asia/Dhaka",
        ideas=[],
    )

    success, message = service.dispatch_report(report, smtp_config=None, webhook_url=None)
    assert success is True
    assert "skipped" in message.lower()


# ==============================================================================
# 8. Data Safety & Formula Injection Protection Tests
# ==============================================================================

def test_formula_injection_sanitization_on_export():
    """Verify that CSV export data sanitizes leading formula triggers (=, +, -, @)."""
    assert sanitize_formula_injection("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert sanitize_formula_injection("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert sanitize_formula_injection("-10% Discount") == "'-10% Discount"
    assert sanitize_formula_injection("@channel_name") == "'@channel_name"
    assert sanitize_formula_injection("Normal Text") == "Normal Text"
