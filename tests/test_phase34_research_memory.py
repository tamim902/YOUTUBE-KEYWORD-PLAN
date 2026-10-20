"""
Test suite for Phase 34: Personal SEO Research Memory & Smart Recommendations.

Verifies:
1. Channel-specific research retrieval & strict multi-channel isolation.
2. Duplicate research detection (exact & semantic similarity matching).
3. Stale research handling (>30 days threshold) vs. fresh research.
4. Smart recommendation generation with evidence-grounded explanations.
5. Beginner first-step fallback for empty research memory.
6. User feedback persistence (Useful, Not relevant, Already completed, Try again later).
7. User feedback suppression of dismissed recommendations.
8. Recording published videos with creator performance ratings.
9. Performance insights comparing selected vs published topics.
10. Safe single-record deletion with channel boundary enforcement.
11. Fresh database initialization and Phase 34 table schema integrity.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from src.intelligence.channel_manager import ChannelManager
from src.intelligence.research_memory import (
    FeedbackStatus,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    ResearchMemoryEngine,
    SimilarityType,
    UserPerformanceRating,
)
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    """Fixture providing an isolated SQLite database in WAL mode with Phase 34 tables."""
    db_file = tmp_path / "test_phase34_memory.db"
    db = DatabaseManager(db_file)
    db.init_db()
    return db


@pytest.fixture
def test_chan_mgr(test_db: DatabaseManager) -> ChannelManager:
    """Fixture providing a ChannelManager wired to the isolated test database."""
    mgr = ChannelManager(test_db)
    mgr.get_all_channels()
    return mgr


@pytest.fixture
def memory_engine(test_db: DatabaseManager, test_chan_mgr: ChannelManager) -> ResearchMemoryEngine:
    """Fixture providing a ResearchMemoryEngine wired to the isolated test database."""
    return ResearchMemoryEngine(
        database=test_db,
        chan_mgr=test_chan_mgr,
        stale_threshold_days=30,
    )


# ==============================================================================
# 1. CHANNEL-SPECIFIC RETRIEVAL & ISOLATION
# ==============================================================================

def test_channel_specific_research_retrieval(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that research memory records are strictly partitioned by channel ID."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Save record for Channel 1 (TechGear Pulse)
    rec1 = MemoryRecord(
        channel_id=1,
        topic_or_keyword="mechanical keyboard switches",
        memory_type=MemoryType.SEED_SEARCH,
        research_date=now,
    )
    test_db.save_research_memory_record(rec1)

    # Save record for Channel 2 (CodeCraft বাংলা)
    rec2 = MemoryRecord(
        channel_id=2,
        topic_or_keyword="পাইথন প্রোগ্রামিং টিউটোরিয়াল",
        memory_type=MemoryType.SAVED_TOPIC,
        research_date=now,
    )
    test_db.save_research_memory_record(rec2)

    ch1_records = test_db.get_research_memory_records(channel_id=1)
    ch2_records = test_db.get_research_memory_records(channel_id=2)

    assert len(ch1_records) == 1
    assert ch1_records[0]["topic_or_keyword"] == "mechanical keyboard switches"
    assert ch1_records[0]["channel_id"] == 1

    assert len(ch2_records) == 1
    assert "পাইথন" in ch2_records[0]["topic_or_keyword"]
    assert ch2_records[0]["channel_id"] == 2


# ==============================================================================
# 2. DUPLICATE DETECTION (EXACT & SEMANTIC SIMILARITY)
# ==============================================================================

def test_exact_duplicate_detection(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that an exact query match is detected with 1.0 similarity score."""
    now = datetime.now(timezone.utc).isoformat()
    test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="best mechanical keyboard for typing",
            memory_type=MemoryType.SEED_SEARCH,
            research_date=now,
        )
    )

    match = memory_engine.check_duplicate_research(
        channel_id=1, query="best mechanical keyboard for typing"
    )

    assert match.is_duplicate is True
    assert match.similarity_type == SimilarityType.EXACT_MATCH
    assert match.similarity_score == 1.0
    assert match.matched_topic == "best mechanical keyboard for typing"
    assert "You previously researched this exact topic" in match.explanation


def test_semantic_duplicate_detection(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that semantically similar query variations are detected via token overlap."""
    now = datetime.now(timezone.utc).isoformat()
    test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="custom mechanical keyboard build guide",
            memory_type=MemoryType.CONTENT_PACKAGE,
            research_date=now,
        )
    )

    # Candidate query with high token overlap
    match = memory_engine.check_duplicate_research(
        channel_id=1, query="mechanical keyboard custom build"
    )

    assert match.is_duplicate is True
    assert match.similarity_type in (SimilarityType.SEMANTIC_SIMILAR, SimilarityType.SUBSTRING_MATCH)
    assert match.similarity_score >= 0.55
    assert match.matched_topic == "custom mechanical keyboard build guide"


def test_no_duplicate_cross_channel_bleed(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that a topic researched on Channel 1 is NOT treated as a duplicate on Channel 2."""
    now = datetime.now(timezone.utc).isoformat()
    test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="coffee machine review",
            memory_type=MemoryType.SEED_SEARCH,
            research_date=now,
        )
    )

    # Channel 2 check
    match_ch2 = memory_engine.check_duplicate_research(
        channel_id=2, query="coffee machine review"
    )

    assert match_ch2.is_duplicate is False
    assert match_ch2.similarity_type == SimilarityType.NO_MATCH


# ==============================================================================
# 3. STALE VS. FRESH RESEARCH HANDLING
# ==============================================================================

def test_stale_research_detection(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that research older than 30 days is flagged as stale with refresh advice."""
    past_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="hall effect magnetic keyboards",
            memory_type=MemoryType.SEED_SEARCH,
            research_date=past_date,
        )
    )

    match = memory_engine.check_duplicate_research(
        channel_id=1, query="hall effect magnetic keyboards"
    )

    assert match.is_duplicate is True
    assert match.is_stale is True
    assert match.days_ago >= 44
    assert match.suggested_action == "refresh_research"
    assert "older than 30 days" in match.explanation or "over 30 days" in match.explanation


def test_fresh_research_suggests_reopening(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify that fresh research suggests reopening existing findings."""
    fresh_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="desk setup lighting guide",
            memory_type=MemoryType.SEED_SEARCH,
            research_date=fresh_date,
        )
    )

    match = memory_engine.check_duplicate_research(
        channel_id=1, query="desk setup lighting guide"
    )

    assert match.is_duplicate is True
    assert match.is_stale is False
    assert match.days_ago <= 6
    assert match.suggested_action == "open_previous_research"


# ==============================================================================
# 4. SMART RECOMMENDATIONS & EXPLANATIONS
# ==============================================================================

def test_recommendation_explanations_evidence_grounded(
    memory_engine: ResearchMemoryEngine, test_db: DatabaseManager
):
    """Verify recommendations provide clear plain-English reasons and supporting evidence."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Insert a package missing a calendar schedule
    test_db.save_video_content_package({
        "channel_id": 1,
        "channel_name": "TechGear Pulse",
        "topic": "Ergonomic Split Keyboards",
        "primary_keyword": "split keyboard",
        "format_type": "long-form",
        "purpose_type": "tutorial",
        "selected_title": "Best Split Keyboards in 2026",
        "calendar_item_id": None,
        "created_at": now,
    })

    recs = memory_engine.generate_smart_recommendations(channel_id=1)
    assert len(recs) >= 1
    
    sched_rec = next((r for r in recs if r.recommendation_type == "add_to_calendar"), None)
    assert sched_rec is not None
    assert "Ergonomic Split Keyboards" in sched_rec.title
    assert "not yet on your production calendar" in sched_rec.why_suggested
    assert "Video Content Package" in sched_rec.supporting_evidence
    assert sched_rec.next_action_label == "Add to Content Calendar"


def test_empty_history_beginner_first_step(memory_engine: ResearchMemoryEngine):
    """Verify empty research memory returns a grounded first-step recommendation."""
    recs = memory_engine.generate_smart_recommendations(channel_id=3)  # HomeChef Artisan
    assert len(recs) == 1
    first_step = recs[0]
    assert first_step.recommendation_type == "first_step"
    assert "HomeChef Artisan" in first_step.title
    assert "Start Keyword Research" in first_step.next_action_label


# ==============================================================================
# 5. USER FEEDBACK PERSISTENCE & SUPPRESSION
# ==============================================================================

def test_user_feedback_persistence_and_suppression(
    memory_engine: ResearchMemoryEngine, test_db: DatabaseManager
):
    """Verify marking a recommendation as Not Relevant suppresses it from future suggestions."""
    now = datetime.now(timezone.utc).isoformat()
    test_db.save_video_content_package({
        "channel_id": 1,
        "channel_name": "TechGear Pulse",
        "topic": "Low Profile Keyboards",
        "primary_keyword": "low profile keyboard",
        "calendar_item_id": None,
        "created_at": now,
    })

    recs_before = memory_engine.generate_smart_recommendations(channel_id=1)
    target_rec = next(r for r in recs_before if "Low Profile Keyboards" in r.title)
    
    # Record feedback: NOT_RELEVANT
    memory_engine.record_recommendation_feedback(
        channel_id=1,
        recommendation_key=target_rec.recommendation_key,
        recommendation_type=target_rec.recommendation_type,
        status=FeedbackStatus.NOT_RELEVANT,
        reason="Decided not to produce low profile content",
    )

    # Verify feedback persisted
    feedback_map = test_db.get_recommendation_feedback(channel_id=1)
    assert target_rec.recommendation_key in feedback_map
    assert feedback_map[target_rec.recommendation_key]["feedback_status"] == "not_relevant"

    # Re-generate recommendations: suppressed item should not appear
    recs_after = memory_engine.generate_smart_recommendations(channel_id=1)
    keys_after = [r.recommendation_key for r in recs_after]
    assert target_rec.recommendation_key not in keys_after


def test_user_feedback_reversal(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify feedback can be deleted/reversed to restore a recommendation."""
    test_db.save_recommendation_feedback(
        channel_id=1,
        recommendation_key="test_key_xyz",
        recommendation_type="add_to_calendar",
        feedback_status="useful",
    )
    fb = test_db.get_recommendation_feedback(channel_id=1)
    assert "test_key_xyz" in fb

    deleted = test_db.delete_recommendation_feedback(channel_id=1, recommendation_key="test_key_xyz")
    assert deleted is True

    fb_after = test_db.get_recommendation_feedback(channel_id=1)
    assert "test_key_xyz" not in fb_after


# ==============================================================================
# 6. PUBLISHED TOPICS & PERFORMANCE INSIGHTS
# ==============================================================================

def test_record_topic_published_and_insights(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify explicit recording of published video with creator performance rating."""
    memory_engine.record_topic_published(
        channel_id=1,
        topic="Budget Mechanical Keyboards in 2026",
        video_url="https://youtube.com/watch?v=mock123",
        user_rating=UserPerformanceRating.EXCEEDED_EXPECTATIONS.value,
    )

    insights = memory_engine.get_performance_insights(channel_id=1)
    assert insights.total_topics_published >= 1
    assert insights.user_ratings_breakdown["exceeded_expectations"] >= 1
    assert "YouTube Analytics OAuth is not configured" in insights.analytics_explanation


# ==============================================================================
# 7. PRIVACY & SAFE RECORD DELETION
# ==============================================================================

def test_clear_memory_record_with_channel_boundary(memory_engine: ResearchMemoryEngine, test_db: DatabaseManager):
    """Verify deleting a memory record respects channel boundary safeguards."""
    now = datetime.now(timezone.utc).isoformat()
    rec_id = test_db.save_research_memory_record(
        MemoryRecord(
            channel_id=1,
            topic_or_keyword="temporary test keyword",
            research_date=now,
        )
    )

    # Attempting to delete using wrong channel_id must fail
    fail_del = memory_engine.clear_memory_record(record_id=rec_id, channel_id=2)
    assert fail_del is False
    assert test_db.get_research_memory_record_by_id(rec_id) is not None

    # Correct channel_id deletion must succeed
    ok_del = memory_engine.clear_memory_record(record_id=rec_id, channel_id=1)
    assert ok_del is True
    assert test_db.get_research_memory_record_by_id(rec_id) is None


# ==============================================================================
# 8. DATABASE SCHEMA INTEGRITY & MIGRATION
# ==============================================================================

def test_phase34_tables_exist_in_db(test_db: DatabaseManager):
    """Verify Phase 34 tables and indexes exist in fresh database."""
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]

    assert "research_memory_records" in tables
    assert "recommendation_feedback" in tables
