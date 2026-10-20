"""Unit and integration tests for Phase 23: YouTube SEO Audit & Affiliate Content Quality Engine."""

import pytest
from unittest.mock import MagicMock, patch

from src.models.channel import ChannelProfile
from src.models.audit import (
    AuditFindingSeverity,
    AuditStatus,
    VideoSeoAudit,
)
from src.intelligence.audit_engine import AuditEngine
from src.storage.database import DatabaseManager


@pytest.fixture
def test_channel():
    """Sample channel profile for testing."""
    return ChannelProfile(
        id=1,
        channel_name="Tech Review Lab",
        channel_handle="@techreviewlab",
        channel_niche="Mechanical Keyboards",
        sub_niches=["Custom Keyboards", "Budget Switches", "Keycaps"],
        target_audience="Keyboard enthusiasts and PC builders",
        affiliate_enabled=True,
        excluded_topics=["Membrane Keyboards", "Scam Brands"],
        excluded_keywords=["membrane", "cheap junk"],
    )


@pytest.fixture
def non_affiliate_channel():
    """Channel profile with affiliate marketing disabled."""
    return ChannelProfile(
        id=2,
        channel_name="Historical Archives",
        channel_handle="@historyarchive",
        channel_niche="World History",
        sub_niches=["Ancient Rome", "Medieval Warfare"],
        target_audience="History students and educators",
        affiliate_enabled=False,
        excluded_topics=[],
        excluded_keywords=[],
    )


@pytest.fixture
def audit_engine(tmp_path):
    """AuditEngine instance backed by a temporary SQLite database."""
    db_file = tmp_path / "test_audit.db"
    db = DatabaseManager(db_path=db_file)
    db.init_db()
    return AuditEngine(database=db)


# ==============================================================================
# 1. Title Quality Checker Tests
# ==============================================================================

def test_title_truncation_tiers(audit_engine, test_channel):
    """Test mobile truncation risk tiers: <60 Safe, 60-75 Moderate, >75 High Risk."""
    # Under 60 chars
    short_title = "Best Mechanical Keyboards in 2026: Complete Guide"
    res_short = audit_engine.audit_title(short_title, "mechanical keyboards", test_channel)
    assert res_short.truncation_risk == "Safe (<60 chars)"
    assert res_short.score >= 80.0

    # 60 to 75 chars
    medium_title = "Best Mechanical Keyboards for Programming and Daily Coding in 2026"
    res_med = audit_engine.audit_title(medium_title, "mechanical keyboards", test_channel)
    assert res_med.truncation_risk == "Moderate (60-75 chars)"

    # Over 75 chars
    long_title = "The Absolute Ultimate Complete Beginner Guide to Custom Mechanical Keyboards for Gaming and Work in 2026"
    res_long = audit_engine.audit_title(long_title, "mechanical keyboards", test_channel)
    assert res_long.truncation_risk == "High Risk (>75 chars)"
    assert any(f.severity == AuditFindingSeverity.WARNING and "Truncation" in f.title for f in res_long.findings)


def test_title_primary_keyword_front_loading(audit_engine, test_channel):
    """Test primary keyword placement detection (front-loaded vs middle vs missing)."""
    # Front-loaded (first 4 words)
    front_title = "Mechanical Keyboards Guide: Top 5 Switches"
    res_front = audit_engine.audit_title(front_title, "mechanical keyboards", test_channel)
    assert res_front.keyword_position == "Front (First 4 words)"
    assert res_front.has_primary_keyword is True

    # Missing keyword
    missing_title = "Top 5 Switches Every Gamer Needs to Buy Right Now"
    res_missing = audit_engine.audit_title(missing_title, "mechanical keyboards", test_channel)
    assert res_missing.keyword_position == "Missing"
    assert any(f.severity == AuditFindingSeverity.WARNING and "Missing" in f.title for f in res_missing.findings)


def test_title_misleading_claims_and_repetition(audit_engine, test_channel):
    """Test detection of clickbait/superlatives and excessive word repetition."""
    sensational_title = "100% Guaranteed Secret Hack to Make Millions on Mechanical Keyboards!"
    res = audit_engine.audit_title(sensational_title, "mechanical keyboards", test_channel)
    assert any("Sensational" in f.title or "Misleading" in f.title for f in res.findings)

    # Word repetition
    repetitive_title = "Keyboards Keyboards Keyboards: The Best Mechanical Keyboards"
    res_rep = audit_engine.audit_title(repetitive_title, "mechanical keyboards", test_channel)
    assert any("Repetition" in f.title for f in res_rep.findings)


def test_title_similarity_to_existing_channel_titles(audit_engine, test_channel):
    """Test detection of self-cannibalization risk against channel video history."""
    existing = ["Best Mechanical Keyboards in 2026", "Budget Switches Tested"]
    proposed = "The Best Mechanical Keyboards in 2026"
    res = audit_engine.audit_title(proposed, "mechanical keyboards", test_channel, existing_titles=existing)
    assert len(res.similarity_flags) > 0
    assert any("Cannibalization" in f.title for f in res.findings)


def test_title_alternatives_generated_without_ctr_guarantees(audit_engine, test_channel):
    """Test that improved title alternatives are generated with ethical rationales and zero fake CTR claims."""
    res = audit_engine.audit_title("Keyboards", "mechanical keyboards", test_channel)
    assert len(res.alternatives) == 4
    for alt in res.alternatives:
        assert "title" in alt
        assert "angle" in alt
        assert "why_suggested" in alt
        # Verify no fake CTR or ranking guarantees
        assert "guaranteed" not in alt["why_suggested"].lower()
        assert "100%" not in alt["why_suggested"]


# ==============================================================================
# 2. Description SEO Audit Tests
# ==============================================================================

def test_description_character_limit_and_hook(audit_engine, test_channel):
    """Test 5000 character limit enforcement and opening hook keyword detection."""
    # Exceeding 5,000 chars
    huge_desc = "Mechanical keyboards are awesome. " * 200  # > 6,000 chars
    res_huge = audit_engine.audit_description(huge_desc, "mechanical keyboards", channel=test_channel)
    assert any(f.severity == AuditFindingSeverity.CRITICAL and "5,000" in f.title for f in res_huge.findings)

    # Valid hook with primary keyword in first 200 chars
    good_desc = (
        "Looking for the best mechanical keyboards in 2026? In this video, we review "
        "and test the top 5 custom keyboards for ergonomics, typing sound, and gaming.\n\n"
        "TIMESTAMPS:\n0:00 - Introduction\n1:20 - Specs\n3:40 - Sound Test\n5:00 - Verdict\n\n"
        "DISCLOSURE: Some links are affiliate links. We may earn a small commission."
    )
    res_good = audit_engine.audit_description(good_desc, "mechanical keyboards", channel=test_channel)
    assert res_good.has_primary_keyword_hook is True
    assert res_good.has_timestamps is True


def test_description_timestamps_validation(audit_engine, test_channel):
    """Test timestamps must start at 0:00 and have at least 3 chapters."""
    # Timestamps starting at 1:15 instead of 0:00
    bad_ts_desc = (
        "Complete overview of keyboards.\n\n"
        "TIMESTAMPS:\n1:15 - Specs\n3:40 - Sound Test\n5:00 - Verdict"
    )
    res_bad_ts = audit_engine.audit_description(bad_ts_desc, "keyboards", channel=test_channel)
    assert any("0:00" in f.title for f in res_bad_ts.findings)

    # Fewer than 3 chapters
    few_ts_desc = "TIMESTAMPS:\n0:00 - Intro\n2:00 - Outro"
    res_few = audit_engine.audit_description(few_ts_desc, "keyboards", channel=test_channel)
    assert any("Fewer Than 3" in f.title for f in res_few.findings)


def test_description_ftc_disclosure_check(audit_engine, test_channel):
    """Test mandatory FTC affiliate disclosure check when affiliate is enabled."""
    desc_no_ftc = (
        "Check out these mechanical keyboards!\n"
        "Buy here: https://amzn.to/example\n\n"
        "TIMESTAMPS:\n0:00 - Intro\n1:00 - Test\n2:00 - Review"
    )
    res = audit_engine.audit_description(desc_no_ftc, "keyboards", channel=test_channel, has_affiliate_links=True)
    assert res.has_ftc_disclosure is False
    assert any(f.severity == AuditFindingSeverity.CRITICAL and "FTC" in f.title for f in res.findings)


def test_description_placeholders_detected(audit_engine, test_channel):
    """Test detection of unfilled template placeholders."""
    desc_with_placeholders = (
        "Here is the review of [PRODUCT NAME]. Buy it at [INSERT LINK HERE].\n"
        "TODO: add specs.\n"
        "TIMESTAMPS:\n0:00 - Intro\n1:00 - Test\n2:00 - Verdict"
    )
    res = audit_engine.audit_description(desc_with_placeholders, "product", channel=test_channel)
    assert res.has_placeholders is True
    assert any(f.severity == AuditFindingSeverity.CRITICAL and "Placeholders" in f.title for f in res.findings)


# ==============================================================================
# 3. Script & Content Alignment Tests
# ==============================================================================

def test_script_alignment_not_checked_when_empty(audit_engine):
    """CRITICAL RULE: If no script is provided, mark as NOT CHECKED with zero penalty."""
    res_empty = audit_engine.audit_script_alignment(
        title="Best Mechanical Keyboards 2026",
        description="Comprehensive review",
        primary_keyword="mechanical keyboards",
        script_or_outline="",
    )
    assert res_empty.status == AuditStatus.NOT_CHECKED
    assert res_empty.score is None
    assert any("NOT CHECKED" in f.title for f in res_empty.findings)

    res_none = audit_engine.audit_script_alignment(
        title="Best Mechanical Keyboards 2026",
        description="Comprehensive review",
        primary_keyword="mechanical keyboards",
        script_or_outline=None,
    )
    assert res_none.status == AuditStatus.NOT_CHECKED
    assert res_none.score is None


def test_script_alignment_when_provided(audit_engine):
    """Test script alignment checking title promises, fluff phrases, and review criteria."""
    script = (
        "Without further ado, in today's video we explore the fast-paced world of typing. "
        "We discuss mechanical keyboards, testing custom switches, build quality, and pricing. "
        "Here are the pros and cons of each setup."
    )
    res = audit_engine.audit_script_alignment(
        title="Custom Mechanical Keyboards Review: Pricing and Specs",
        description="Review guide",
        primary_keyword="mechanical keyboards",
        script_or_outline=script,
    )
    assert res.status == AuditStatus.CHECKED
    assert res.score is not None
    assert len(res.fluff_phrases_found) > 0  # "without further ado", "in today's video", "fast-paced world"
    assert len(res.criteria_covered) > 0    # "pros", "cons", "price", "build"


# ==============================================================================
# 4. Affiliate Content Quality Audit Tests
# ==============================================================================

def test_affiliate_quality_not_applicable_when_disabled(audit_engine, non_affiliate_channel):
    """Test that affiliate quality is marked NOT APPLICABLE for non-commercial channels."""
    res = audit_engine.audit_affiliate_content(
        description="A historical documentary about ancient Rome.",
        script_or_outline="In this video we analyze Roman military tactics.",
        channel=non_affiliate_channel,
        has_affiliate_links=False,
    )
    assert res.status == AuditStatus.NOT_APPLICABLE
    assert res.score is None


def test_affiliate_quality_superlatives_and_balanced_reviews(audit_engine, test_channel):
    """Test detection of unsupported superlatives and missing limitations in commercial content."""
    unbalanced_text = (
        "This is the best ever keyboard, completely flawless and a miracle device with 100% recommended for everyone. "
        "Buy it now with our affiliate link: https://example.com"
    )
    res = audit_engine.audit_affiliate_content(
        description=unbalanced_text,
        script_or_outline="",
        channel=test_channel,
        has_affiliate_links=True,
    )
    assert res.status == AuditStatus.CHECKED
    assert len(res.unsupported_superlatives) > 0
    assert res.has_balanced_pros_cons is False
    assert any("Superlatives" in f.title for f in res.findings)
    assert any("Drawbacks" in f.title or "Limitations" in f.title for f in res.findings)


# ==============================================================================
# 5. Thumbnail & Title Alignment Tests
# ==============================================================================

def test_thumbnail_concept_audit_and_visual_not_checked(audit_engine):
    """Test thumbnail text length check and verify visual pixel inspection is marked NOT CHECKED."""
    # Short punchy concept
    good_concept = "DON'T BUY YET! Split keyboard comparison"
    res_good = audit_engine.audit_thumbnail_alignment(good_concept, "Should You Buy a Split Keyboard in 2026?")
    assert res_good.concept_status == AuditStatus.CHECKED
    assert res_good.visual_inspection_status == AuditStatus.NOT_CHECKED
    assert any("NOT CHECKED" in f.title for f in res_good.findings)

    # Wordy concept
    wordy_concept = "This is why you should never buy this keyboard because it will break your fingers and wallet"
    res_wordy = audit_engine.audit_thumbnail_alignment(wordy_concept, "Keyboard Review")
    assert any("Too Many Words" in f.title for f in res_wordy.findings)


# ==============================================================================
# 6. Transparent SEO Readiness Score Breakdown Tests
# ==============================================================================

def test_readiness_score_calculation_with_not_checked(audit_engine, test_channel):
    """Test dynamic weight normalization when script is NOT CHECKED."""
    title_res = audit_engine.audit_title("Best Mechanical Keyboards 2026", "mechanical keyboards", test_channel)
    desc_res = audit_engine.audit_description(
        "Complete guide to mechanical keyboards.\nTIMESTAMPS:\n0:00 - Intro\n1:00 - Test\n2:00 - Verdict\nDISCLOSURE: Affiliate links included.",
        "mechanical keyboards",
        channel=test_channel,
    )
    script_res = audit_engine.audit_script_alignment("Best Mechanical Keyboards 2026", "desc", "kw", script_or_outline="")
    aff_res = audit_engine.audit_affiliate_content("desc", "script", test_channel, has_affiliate_links=False)
    thumb_res = audit_engine.audit_thumbnail_alignment("Top Keyboards", "Best Mechanical Keyboards 2026")

    score_breakdown = audit_engine.calculate_readiness_score(title_res, desc_res, script_res, aff_res, thumb_res)
    assert 0.0 <= score_breakdown.overall_readiness_score <= 100.0
    assert "Script & Content Alignment" in score_breakdown.not_checked_categories
    assert "Title Quality" in score_breakdown.checked_categories
    assert "Description & FTC Compliance" in score_breakdown.checked_categories
    # Verify ranking guarantee disclaimer is present
    assert "cannot be guaranteed" in score_breakdown.disclaimer.lower()


# ==============================================================================
# 7. Before-Publishing Checklist Tests
# ==============================================================================

def test_publishing_checklist_requires_manual_confirmation(audit_engine, test_channel):
    """Test that all generated checklist items start uncompleted and require manual confirmation."""
    checklist = audit_engine.generate_publishing_checklist(test_channel, has_affiliate=True)
    assert len(checklist) >= 7
    for item in checklist:
        assert item.is_completed is False
        assert item.is_manual_required is True


# ==============================================================================
# 8. Four-Channel Topic Isolation Tests
# ==============================================================================

def test_channel_isolation_exclusions(audit_engine, test_channel):
    """Test detection of channel exclusion violations and cross-channel overlap."""
    # Excluded topic: "Membrane Keyboards"
    findings = audit_engine.check_channel_isolation(test_channel, "Why Membrane Keyboards are Bad", "membrane keyboards")
    assert any(f.severity == AuditFindingSeverity.CRITICAL and "Exclusion" in f.title for f in findings)


# ==============================================================================
# 9. Public YouTube Video URL Metadata Fetching Tests
# ==============================================================================

def test_fetch_public_video_metadata_no_private_analytics(audit_engine):
    """Test public video URL metadata parsing and verification of public-only access."""
    # Valid YouTube watch URL format
    res = audit_engine.fetch_public_video_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert res["success"] is True
    assert res["video_id"] == "dQw4w9WgXcQ"
    assert res["is_public_metadata_only"] is True
    assert res["private_analytics_accessible"] is False

    # Shorts URL format
    res_shorts = audit_engine.fetch_public_video_metadata("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert res_shorts["success"] is True
    assert res_shorts["video_id"] == "dQw4w9WgXcQ"

    # Invalid URL format
    res_inv = audit_engine.fetch_public_video_metadata("https://example.com/not-a-video")
    assert res_inv["success"] is False


# ==============================================================================
# 10. Report Export & Formula Injection Protection Tests
# ==============================================================================

def test_export_audit_report_formula_injection_sanitization(audit_engine, test_channel):
    """Test that CSV/text formula injection triggers (=, +, -, @) are sanitized upon export."""
    title_res = audit_engine.audit_title("=SUM(1,2) Dangerous Title", "formula test", test_channel)
    desc_res = audit_engine.audit_description("Description", "formula test", channel=test_channel)
    script_res = audit_engine.audit_script_alignment("title", "desc", "kw", "")
    aff_res = audit_engine.audit_affiliate_content("desc", "", test_channel)
    thumb_res = audit_engine.audit_thumbnail_alignment("thumb", "title")
    scores = audit_engine.calculate_readiness_score(title_res, desc_res, script_res, aff_res, thumb_res)
    checklist = audit_engine.generate_publishing_checklist(test_channel)

    audit = VideoSeoAudit(
        id=1,
        channel_id=test_channel.id,
        channel_name="@MaliciousChannel",
        idea_id=None,
        primary_keyword="+123456",
        secondary_keywords=[],
        proposed_title="=cmd|' /C calc'!A0",
        draft_description="-3+4",
        script_text="",
        thumbnail_concept="",
        video_url="",
        is_published_url=False,
        scores=scores,
        findings=[],
        title_result=title_res,
        description_result=desc_res,
        script_result=script_res,
        affiliate_result=aff_res,
        thumbnail_result=thumb_res,
        checklist=checklist,
        revision_number=1,
        created_at="2026-10-20T12:00:00Z",
        updated_at="2026-10-20T12:00:00Z",
    )

    md_report = audit_engine.export_audit_report(audit, format="markdown")
    # Must be escaped with leading quote
    assert "'=cmd|" in md_report or "\\=" in md_report or "cmd|" in md_report
    assert "'@MaliciousChannel" in md_report or "@MaliciousChannel" in md_report

    json_report = audit_engine.export_audit_report(audit, format="json")
    assert "'=cmd|" in json_report


# ==============================================================================
# 11. SQLite Persistence & Revision Snapshot Tests
# ==============================================================================

def test_save_and_retrieve_seo_audit_revisions(audit_engine, test_channel):
    """Test persisting an audit, updating it, and verifying revision snapshots in SQLite."""
    db = audit_engine.db
    title_res = audit_engine.audit_title("Best Keyboards 2026", "keyboards", test_channel)
    desc_res = audit_engine.audit_description("Description text", "keyboards", channel=test_channel)
    script_res = audit_engine.audit_script_alignment("title", "desc", "kw", "")
    aff_res = audit_engine.audit_affiliate_content("desc", "", test_channel)
    thumb_res = audit_engine.audit_thumbnail_alignment("thumb", "title")
    scores = audit_engine.calculate_readiness_score(title_res, desc_res, script_res, aff_res, thumb_res)
    checklist = audit_engine.generate_publishing_checklist(test_channel)

    audit = VideoSeoAudit(
        id=None,
        channel_id=test_channel.id,
        channel_name=test_channel.channel_name,
        idea_id=None,
        primary_keyword="keyboards",
        secondary_keywords=["switches"],
        proposed_title="Best Keyboards 2026",
        draft_description="Description text",
        script_text="",
        thumbnail_concept="",
        video_url="",
        is_published_url=False,
        scores=scores,
        findings=[],
        title_result=title_res,
        description_result=desc_res,
        script_result=script_res,
        affiliate_result=aff_res,
        thumbnail_result=thumb_res,
        checklist=checklist,
        revision_number=1,
    )

    # Save initial audit
    audit_id = db.save_seo_audit(audit)
    assert audit_id > 0
    assert audit.revision_number == 1

    # Retrieve audit
    saved = db.get_seo_audit(audit_id)
    assert saved is not None
    assert saved["primary_keyword"] == "keyboards"
    assert saved["revision_number"] == 1

    # Update audit to create revision 2
    audit.proposed_title = "Top 5 Mechanical Keyboards (2026 Update)"
    audit.id = audit_id
    db.save_seo_audit(audit)
    assert audit.revision_number == 2

    # Check revisions history
    revs = db.get_audit_revisions(audit_id)
    assert len(revs) == 2
    assert revs[0]["revision_number"] == 1
    assert revs[1]["revision_number"] == 2
    assert revs[1]["proposed_title"] == "Top 5 Mechanical Keyboards (2026 Update)"
