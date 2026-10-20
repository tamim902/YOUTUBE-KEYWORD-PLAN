"""Unit and integration tests for Phase 25: YouTube Content Strategy Autopilot for Four Channels."""

from datetime import datetime, timezone
import pytest
from pathlib import Path
import tempfile

from src.models.channel import ChannelProfile, get_default_four_channels
from src.models.strategy import (
    ChannelStrategySettings,
    ContentBriefDocument,
    ContentCluster,
    ContentPillar,
    PrioritizedTopic,
    ProductionEffort,
    ProductionWorkflowProject,
    StrategyCalendarItem,
    TopicUserStatus,
    WorkflowStage,
)
from src.storage.database import DatabaseManager
from src.intelligence.strategy_engine import ContentStrategyAutopilot, STAGE_SEQUENCE
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    EXTENDED_NAVIGATION_PAGES,
    PAGE_LABEL_CLEAN_MAP,
    EXTENDED_PAGE_SECTION_MAP,
    PAGE_STRATEGY,
    PHASE25_PAGES,
)


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_strategy.db"
        manager = DatabaseManager(db_path=db_path)
        manager.init_db()
        yield manager


@pytest.fixture
def sample_channels():
    """Return default four channel profiles."""
    return get_default_four_channels()


@pytest.fixture
def strategy_engine(temp_db):
    """Return strategy autopilot engine connected to temporary database."""
    return ContentStrategyAutopilot(db=temp_db)


# ==============================================================================
# 1. Navigation & Contract Integrity Tests
# ==============================================================================

def test_navigation_contract_remains_14_base_pages():
    """Ensure ALL_NAVIGATION_PAGES maintains exactly 14 base destinations for contract integrity."""
    assert len(ALL_NAVIGATION_PAGES) == 14, "ALL_NAVIGATION_PAGES must have exactly 14 items"


def test_phase25_page_registered_in_extended_navigation():
    """Verify PAGE_STRATEGY is properly registered in PHASE25_PAGES and EXTENDED_NAVIGATION_PAGES."""
    assert PAGE_STRATEGY in PHASE25_PAGES
    assert PAGE_STRATEGY in EXTENDED_NAVIGATION_PAGES
    assert PAGE_STRATEGY in PAGE_LABEL_CLEAN_MAP
    assert PAGE_LABEL_CLEAN_MAP[PAGE_STRATEGY] == "Content Strategy Autopilot"
    assert EXTENDED_PAGE_SECTION_MAP[PAGE_STRATEGY] == "DISCOVERY & INTELLIGENCE"


# ==============================================================================
# 2. Channel Isolation & Strategy Settings Tests
# ==============================================================================

def test_channel_strategy_settings_crud_and_isolation(temp_db):
    """Verify channel strategy settings save, retrieve, and isolate between channel 1 and channel 2."""
    settings_ch1 = ChannelStrategySettings(
        channel_id=1,
        videos_per_week=3,
        longform_pct=80,
        shorts_pct=20,
        weekly_production_hours_budget=15.0,
        preferred_publishing_days=["Monday", "Wednesday", "Friday"],
        strategic_priority="Topical dominance in tech reviews",
    )
    settings_ch2 = ChannelStrategySettings(
        channel_id=2,
        videos_per_week=1,
        longform_pct=50,
        shorts_pct=50,
        weekly_production_hours_budget=6.0,
        preferred_publishing_days=["Saturday"],
        strategic_priority="Coding tutorials in Bengali",
    )

    temp_db.save_channel_strategy_settings(settings_ch1)
    temp_db.save_channel_strategy_settings(settings_ch2)

    retrieved_1 = temp_db.get_channel_strategy_settings(1)
    retrieved_2 = temp_db.get_channel_strategy_settings(2)

    assert retrieved_1.videos_per_week == 3
    assert retrieved_1.weekly_production_hours_budget == 15.0
    assert "Monday" in retrieved_1.preferred_publishing_days
    assert retrieved_1.strategic_priority == "Topical dominance in tech reviews"

    assert retrieved_2.videos_per_week == 1
    assert retrieved_2.weekly_production_hours_budget == 6.0
    assert retrieved_2.preferred_publishing_days == ["Saturday"]
    assert retrieved_2.strategic_priority == "Coding tutorials in Bengali"


def test_channel_pillars_isolation(temp_db, sample_channels):
    """Verify content pillars for channel 1 do not leak to channel 2."""
    ch1 = sample_channels[0]
    ch2 = sample_channels[1]

    p1 = ContentPillar(
        id=None,
        channel_id=ch1.id,
        pillar_name="Hardware Teardowns",
        description="Detailed review of creator tech",
        audience_problem="Overpriced gear",
        target_keywords=["hardware review", "creator gear"],
        candidate_topics=["Top 5 Mics", "Camera Rig Setup"],
        is_approved=True,
    )
    p2 = ContentPillar(
        id=None,
        channel_id=ch2.id,
        pillar_name="Python Backend Mastery",
        description="Django and FastAPI tutorials",
        audience_problem="Lack of practical projects",
        target_keywords=["fastapi tutorial", "django beginner"],
        candidate_topics=["FastAPI Full Course"],
        is_approved=False,
    )

    id1 = temp_db.save_content_pillar(p1)
    id2 = temp_db.save_content_pillar(p2)

    pillars_1 = temp_db.get_content_pillars(ch1.id)
    pillars_2 = temp_db.get_content_pillars(ch2.id)

    assert len(pillars_1) == 1
    assert pillars_1[0].pillar_name == "Hardware Teardowns"
    assert pillars_1[0].is_approved is True

    assert len(pillars_2) == 1
    assert pillars_2[0].pillar_name == "Python Backend Mastery"
    assert pillars_2[0].is_approved is False


# ==============================================================================
# 3. Pillar Suggestion & Approval Tests
# ==============================================================================

def test_build_suggested_pillars(strategy_engine, sample_channels):
    """Verify build_suggested_pillars creates 3-5 structured pillars anchored in niche."""
    ch = sample_channels[0] # TechGear Pulse
    pillars = strategy_engine.build_suggested_pillars(ch)

    assert len(pillars) >= 3
    for p in pillars:
        assert p.channel_id == ch.id
        assert len(p.pillar_name) > 0
        assert len(p.audience_problem) > 0
        assert len(p.target_keywords) > 0
        assert len(p.candidate_topics) > 0
        assert p.is_approved is False


def test_pillar_crud_and_approval(temp_db, strategy_engine, sample_channels):
    """Verify pillar approval and deletion."""
    ch = sample_channels[0]
    pillars = strategy_engine.build_suggested_pillars(ch)
    saved_id = temp_db.save_content_pillar(pillars[0])

    retrieved = temp_db.get_content_pillar_by_id(saved_id)
    assert retrieved is not None
    assert retrieved.is_approved is False

    # Approve
    retrieved.is_approved = True
    temp_db.save_content_pillar(retrieved)

    updated = temp_db.get_content_pillar_by_id(saved_id)
    assert updated.is_approved is True

    # Delete
    del_res = temp_db.delete_content_pillar(saved_id)
    assert del_res is True
    assert temp_db.get_content_pillar_by_id(saved_id) is None


# ==============================================================================
# 4. Content Cluster & Anti-Cannibalization Tests
# ==============================================================================

def test_plan_content_cluster_with_anti_cannibalization(strategy_engine, sample_channels):
    """Verify cluster generates interconnected videos with anti-cannibalization logic."""
    ch = sample_channels[0]
    pillar = ContentPillar(
        id=1,
        channel_id=ch.id,
        pillar_name="Budget Audio Setup",
        description="Audio gear for streamers and creators",
        audience_problem="Terrible room echo and muddy sound",
    )

    cluster = strategy_engine.plan_content_cluster(ch, pillar)

    assert cluster.channel_id == ch.id
    assert cluster.pillar_id == 1
    assert "Definitive Guide to Budget Audio Setup" in cluster.pillar_video_title
    assert len(cluster.supporting_video_titles) >= 2
    assert len(cluster.comparison_video_titles) >= 1
    assert len(cluster.review_video_titles) >= 1
    assert len(cluster.faq_video_titles) >= 2
    assert "Anti-Cannibalization Architecture" in cluster.anti_cannibalization_notes
    assert "informational" in cluster.anti_cannibalization_notes.lower()
    assert "commercial" in cluster.anti_cannibalization_notes.lower()


# ==============================================================================
# 5. Evidence-Based Topic Prioritization Tests (Zero Fake Volume / CTR)
# ==============================================================================

def test_prioritize_candidate_topics_provenance_and_scoring(strategy_engine, sample_channels):
    """Verify transparent scoring across 6 factors and 6-point provenance without fake metrics."""
    ch = sample_channels[0]
    topics = strategy_engine.prioritize_candidate_topics(ch)

    assert len(topics) >= 5
    for t in topics:
        assert t.channel_id == ch.id
        assert 0.0 <= t.channel_relevance_score <= 100.0
        assert 0.0 <= t.search_intent_score <= 100.0
        assert 0.0 <= t.keyword_evidence_score <= 100.0
        assert 0.0 <= t.recent_video_evidence_score <= 100.0
        assert 0.0 <= t.research_coverage_score <= 100.0
        assert 0.0 <= t.product_relevance_score <= 100.0
        assert 0.0 <= t.composite_priority_score <= 100.0

        # Verify 6-Point Provenance Framework fields are present
        assert len(t.selection_rationale) > 0, "1. Why selected must be populated"
        assert len(t.supporting_sources) > 0, "2. Supporting sources must be populated"
        assert len(t.research_date) == 10, "3. Research date must be YYYY-MM-DD"
        assert t.confidence_level in ["High Evidence", "Moderate Evidence", "Exploratory"], "4. Confidence level valid"
        assert len(t.missing_evidence) > 0, "5. Missing evidence disclosure must be populated"
        assert len(t.suggested_next_step) > 0, "6. Suggested next step must be populated"

        # Verify no fabricated claims
        assert "exact monthly volume: " not in t.selection_rationale.lower()
        assert "predicted ctr:" not in t.selection_rationale.lower()


def test_topic_user_status_transitions(temp_db, strategy_engine, sample_channels):
    """Verify topic status transitions (Suggested -> Approved -> In Calendar -> Covered -> Rejected)."""
    ch = sample_channels[0]
    topics = strategy_engine.prioritize_candidate_topics(ch)
    t = topics[0]
    temp_db.save_prioritized_topic(t)

    # Initial status
    loaded = temp_db.get_prioritized_topic_by_id(t.topic_id)
    assert loaded.user_status == TopicUserStatus.SUGGESTED

    # Update to Approved
    temp_db.update_topic_user_status(t.topic_id, TopicUserStatus.APPROVED)
    loaded = temp_db.get_prioritized_topic_by_id(t.topic_id)
    assert loaded.user_status == TopicUserStatus.APPROVED

    # Update to In Calendar
    temp_db.update_topic_user_status(t.topic_id, TopicUserStatus.IN_CALENDAR)
    loaded = temp_db.get_prioritized_topic_by_id(t.topic_id)
    assert loaded.user_status == TopicUserStatus.IN_CALENDAR


# ==============================================================================
# 6. Capacity-Aware Calendar Scheduler Tests
# ==============================================================================

def test_generate_calendar_schedule_respects_capacity(strategy_engine, sample_channels):
    """Verify schedule distributes topics respecting videos per week and production hours budget."""
    ch = sample_channels[0]
    settings = ChannelStrategySettings(
        channel_id=ch.id,
        videos_per_week=2,
        longform_pct=50,
        shorts_pct=50,
        weekly_production_hours_budget=10.0,
        preferred_publishing_days=["Tuesday", "Friday"],
    )
    candidate_topics = strategy_engine.prioritize_candidate_topics(ch)

    schedule = strategy_engine.generate_calendar_schedule(ch, settings, candidate_topics, weeks=4)

    # 2 vids/week * 4 weeks = 8 target videos
    assert len(schedule) == 8
    for item in schedule:
        assert item.channel_id == ch.id
        assert item.production_status == "Planned"  # Never auto-publishes!
        assert item.suggested_format in ["Long-form", "Shorts"]
        assert item.production_hours_estimate > 0

    # Verify both Long-form and Shorts appear
    formats = {item.suggested_format for item in schedule}
    assert "Long-form" in formats
    assert "Shorts" in formats


# ==============================================================================
# 7. Content Brief Studio Tests (14 Sections)
# ==============================================================================

def test_generate_content_brief_has_14_sections(strategy_engine, sample_channels):
    """Verify content brief document has all 14 required sections including unverified facts."""
    ch = sample_channels[0]
    brief = strategy_engine.generate_content_brief(
        channel=ch,
        topic="Best Budget Audio Interface for YouTube Creators",
        keyword="best budget audio interface",
    )

    assert brief.channel_id == ch.id
    assert brief.primary_keyword == "best budget audio interface"
    assert len(brief.target_viewer) > 0
    assert len(brief.viewer_problem) > 0
    assert len(brief.search_intent) > 0
    assert len(brief.main_promise) > 0
    assert len(brief.title_options) == 3
    assert len(brief.video_structure) == 6
    assert len(brief.questions_to_answer) >= 3
    assert len(brief.comparison_criteria) >= 3
    assert len(brief.unverified_facts) >= 2, "Must contain explicit unverified facts placeholders"
    assert len(brief.suggested_research_sources) >= 2
    assert len(brief.thumbnail_concept) > 0
    assert len(brief.description_draft) > 0
    assert "FTC Compliance Notice" in brief.affiliate_disclosure_reminder
    assert len(brief.seo_prepublish_checklist) >= 5


# ==============================================================================
# 8. Production Workflow Sequential Stage Progression Tests
# ==============================================================================

def test_production_workflow_sequential_progression(strategy_engine):
    """Verify workflow project progresses sequentially and enforces blockers."""
    now_iso = datetime.now(timezone.utc).isoformat()
    project = ProductionWorkflowProject(
        id=1,
        channel_id=1,
        project_name="Top 5 Microphones Video",
        primary_keyword="top 5 microphones",
        current_stage=WorkflowStage.IDEA,
        stage_history=[{"from_stage": "None", "to_stage": "Idea", "transitioned_at": now_iso, "user_notes": "Init"}],
    )

    # 1. Advance Idea -> Research
    project = strategy_engine.advance_workflow_stage(project, WorkflowStage.RESEARCH, "Keyword research done")
    assert project.current_stage == WorkflowStage.RESEARCH
    assert len(project.stage_history) == 2

    # 2. Advance Research -> Brief
    project = strategy_engine.advance_workflow_stage(project, WorkflowStage.BRIEF, "Brief drafted")
    assert project.current_stage == WorkflowStage.BRIEF

    # 3. Test Blocker Enforcement: adding blocker prevents moving to PRODUCTION
    project.current_stage = WorkflowStage.SCRIPT
    project.blockers.append("Waiting on audio interface delivery")
    with pytest.raises(ValueError, match="unresolved blockers present"):
        strategy_engine.advance_workflow_stage(project, WorkflowStage.PRODUCTION, "Trying to start shooting")

    # 4. Clear blocker and advance
    project.blockers = []
    project = strategy_engine.advance_workflow_stage(project, WorkflowStage.PRODUCTION, "Gear arrived, shooting now")
    assert project.current_stage == WorkflowStage.PRODUCTION


def test_production_workflow_cannot_advance_cancelled(strategy_engine):
    """Verify cancelled workflow projects cannot be advanced."""
    project = ProductionWorkflowProject(
        id=2,
        channel_id=1,
        project_name="Cancelled Project",
        primary_keyword="test",
        current_stage=WorkflowStage.SCRIPT,
        is_cancelled=True,
    )
    with pytest.raises(ValueError, match="Cannot advance a cancelled project"):
        strategy_engine.advance_workflow_stage(project, WorkflowStage.PRODUCTION)


# ==============================================================================
# 9. Weekly Strategic Intelligence Tests
# ==============================================================================

def test_generate_weekly_strategy_intelligence(temp_db, strategy_engine, sample_channels):
    """Verify weekly strategic intelligence summarizes capacity, pillars, and recommendations."""
    ch = sample_channels[0]
    intel = strategy_engine.generate_weekly_strategy_intelligence(ch)

    assert intel["channel_id"] == ch.id
    assert intel["channel_name"] == ch.channel_name
    assert intel["capacity_status"] in ["Balanced", "Over Capacity", "Under Capacity"]
    assert "weekly_hours_budget" in intel
    assert "recommended_actions" in intel
    assert isinstance(intel["recommended_actions"], list)
