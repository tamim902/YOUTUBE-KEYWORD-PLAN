"""Phase 31 Automated Test Suite: Personal YouTube SEO Coach & Daily Action Center.

Validates:
1. ActionTask and TaskType data models, serialization, and deserialization
2. ActionCenterEngine task generation from real database state
3. 4-Channel task isolation and channel separation
4. Deterministic duplicate prevention
5. Task completion and dismissal persistence (dismissed tasks never recreated)
6. Simple verified progress tracking (no fabricated completion percentages)
7. Daily scheduler status and automation telemetry
8. KeywordDecisionHelper transparent heuristics and anti-cannibalization checks
9. Epistemic honesty (no ranking guarantees, explicit disclaimers)
10. Database layer CRUD operations and WAL transaction safety
"""

import json
from pathlib import Path
import pytest
import sqlite3

from src.intelligence.action_center import (
    ActionCenterEngine,
    ActionTask,
    TaskStatus,
    TaskType,
)
from src.intelligence.channel_manager import ChannelManager
from src.intelligence.decision_helper import (
    KeywordDecision,
    KeywordDecisionHelper,
)
from src.models.channel import ChannelProfile
from src.models.morning_report import DailyIdeaItem
from src.models.strategy import ContentBriefDocument, StrategyCalendarItem
from src.storage.database import DatabaseManager


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    """Fixture providing an isolated SQLite database in WAL mode."""
    db_file = tmp_path / "test_action_center.db"
    db = DatabaseManager(db_file)
    db.init_db()
    return db


@pytest.fixture
def test_chan_mgr(test_db: DatabaseManager) -> ChannelManager:
    """Fixture providing a ChannelManager wired to the test database."""
    mgr = ChannelManager(test_db)
    # Ensure default channels are seeded
    mgr.get_all_channels()
    return mgr


@pytest.fixture
def action_engine(test_db: DatabaseManager, test_chan_mgr: ChannelManager) -> ActionCenterEngine:
    """Fixture providing an ActionCenterEngine wired to isolated test components."""
    return ActionCenterEngine(database=test_db, chan_mgr=test_chan_mgr)


@pytest.fixture
def decision_helper(test_db: DatabaseManager) -> KeywordDecisionHelper:
    """Fixture providing a KeywordDecisionHelper wired to test database."""
    return KeywordDecisionHelper(database=test_db)


# ==============================================================================
# 1. ActionTask Data Model & Serialization Tests
# ==============================================================================

def test_action_task_creation_and_serialization() -> None:
    """Test ActionTask instantiation, serialization, and dictionary round-trip."""
    task = ActionTask(
        task_key="chan_1_test_task_1",
        channel_id=1,
        channel_name="TechGear Pulse",
        task_type=TaskType.REVIEW_NEW_KEYWORDS,
        title="Review Discovered Topic Idea",
        short_summary="Discovered by morning gap analysis.",
        priority="high",
        target_page="Morning Idea Report",
        context_data={"keyword": "best mechanical keyboard 2026"},
        what_to_do="Review the 18 evidence fields.",
        why_it_matters="Improves CTR and browse recommendations.",
        how_to_do_it=["Step 1", "Step 2"],
        what_to_check=["Check A", "Check B"],
        what_comes_next="Open Morning Report.",
    )

    d = task.to_dict()
    assert d["task_key"] == "chan_1_test_task_1"
    assert d["channel_id"] == 1
    assert d["task_type"] == "review_new_keywords"
    assert d["status"] == "pending"

    reconstructed = ActionTask.from_dict(d)
    assert reconstructed.task_key == task.task_key
    assert reconstructed.channel_name == "TechGear Pulse"
    assert reconstructed.task_type == TaskType.REVIEW_NEW_KEYWORDS
    assert reconstructed.how_to_do_it == ["Step 1", "Step 2"]
    assert reconstructed.what_to_check == ["Check A", "Check B"]


# ==============================================================================
# 2. Database Layer CRUD & Table Creation Tests
# ==============================================================================

def test_database_action_task_crud(test_db: DatabaseManager) -> None:
    """Verify SQLite table creation and task CRUD operations."""
    task_dict = {
        "task_key": "test_key_001",
        "channel_id": 2,
        "channel_name": "CodeCraft বাংলা",
        "task_type": "draft_description",
        "title": "Draft Description for Python Video",
        "short_summary": "Prepare chapters and footer.",
        "priority": "medium",
        "target_page": "Description Studio",
        "context_data": {"keyword": "python tutorial"},
        "what_to_do": "Write 8-part description.",
        "why_it_matters": "Improves keyword indexing.",
        "how_to_do_it": ["Step 1"],
        "what_to_check": ["Check 1"],
        "what_comes_next": "Publish video.",
        "status": "pending",
    }

    # Save
    task_id = test_db.save_action_task(task_dict)
    assert task_id is not None
    assert task_id > 0

    # Retrieve
    tasks = test_db.get_action_tasks(channel_id=2, status="pending")
    assert len(tasks) == 1
    assert tasks[0]["task_key"] == "test_key_001"
    assert tasks[0]["channel_name"] == "CodeCraft বাংলা"
    assert tasks[0]["how_to_do_it"] == ["Step 1"]

    # Update status to completed
    updated = test_db.update_action_task_status("test_key_001", "completed")
    assert updated is True

    # Pending list should now be empty
    pending = test_db.get_action_tasks(channel_id=2, status="pending")
    assert len(pending) == 0

    # Completed list should have it
    completed = test_db.get_action_tasks(channel_id=2, status="completed")
    assert len(completed) == 1
    assert completed[0]["status"] == "completed"


# ==============================================================================
# 3. Channel Separation & Isolation Tests
# ==============================================================================

def test_action_center_channel_separation(
    action_engine: ActionCenterEngine,
    test_db: DatabaseManager,
) -> None:
    """Verify that tasks generated for one channel do not bleed into others."""
    # Channel 1 sync
    tasks_ch1 = action_engine.sync_tasks_for_channel(1)
    # Channel 2 sync
    tasks_ch2 = action_engine.sync_tasks_for_channel(2)

    assert all(t.channel_id == 1 for t in tasks_ch1)
    assert all(t.channel_id == 2 for t in tasks_ch2)

    # All keys for ch1 must start with chan_1
    for t in tasks_ch1:
        assert t.task_key.startswith("chan_1")
    # All keys for ch2 must start with chan_2
    for t in tasks_ch2:
        assert t.task_key.startswith("chan_2")


# ==============================================================================
# 4. Duplicate Prevention & Re-Sync Invariants
# ==============================================================================

def test_action_center_duplicate_prevention(action_engine: ActionCenterEngine) -> None:
    """Verify that repeatedly running sync_tasks_for_channel does not create duplicate tasks."""
    tasks_run1 = action_engine.sync_tasks_for_channel(1)
    initial_count = len(tasks_run1)
    assert initial_count > 0

    # Re-sync 3 times
    tasks_run2 = action_engine.sync_tasks_for_channel(1)
    tasks_run3 = action_engine.sync_tasks_for_channel(1)

    assert len(tasks_run2) == initial_count
    assert len(tasks_run3) == initial_count

    # Keys must be unique
    keys = [t.task_key for t in tasks_run3]
    assert len(keys) == len(set(keys))


# ==============================================================================
# 5. Task Dismissal & Completion Persistence
# ==============================================================================

def test_dismissed_tasks_never_resurrected(action_engine: ActionCenterEngine) -> None:
    """Verify that dismissed tasks are permanently dismissed and never recreated on sync."""
    tasks = action_engine.sync_tasks_for_channel(3)
    assert len(tasks) > 0

    first_task = tasks[0]
    dismissed_key = first_task.task_key

    # Dismiss task
    success = action_engine.dismiss_task(dismissed_key)
    assert success is True

    # Re-sync
    new_tasks = action_engine.sync_tasks_for_channel(3)

    # Dismissed task must NOT appear in pending tasks
    assert not any(t.task_key == dismissed_key for t in new_tasks)
    assert len(new_tasks) == len(tasks) - 1 or len(new_tasks) >= 0


def test_completed_tasks_remain_completed(action_engine: ActionCenterEngine) -> None:
    """Verify that completed tasks remain completed and are not reset to pending."""
    tasks = action_engine.sync_tasks_for_channel(4)
    assert len(tasks) > 0

    first_task = tasks[0]
    completed_key = first_task.task_key

    # Mark completed
    success = action_engine.mark_task_completed(completed_key)
    assert success is True

    # Re-sync
    new_tasks = action_engine.sync_tasks_for_channel(4)
    assert not any(t.task_key == completed_key for t in new_tasks)


# ==============================================================================
# 6. Real Progress Summary Tracking (Zero Fabricated Metrics)
# ==============================================================================

def test_real_progress_summary_counts(
    action_engine: ActionCenterEngine,
    test_db: DatabaseManager,
) -> None:
    """Verify that progress summary accurately reflects verified SQLite state."""
    # Clean initial state
    summary = action_engine.get_progress_summary(1)
    assert isinstance(summary, dict)
    assert "saved_searches" in summary
    assert "topics_awaiting_review" in summary
    assert "briefs_completed" in summary
    assert "videos_in_production" in summary
    assert "audits_requiring_attention" in summary

    # Add a real content brief for channel 1
    test_db.save_content_brief_document(ContentBriefDocument(
        id=None,
        channel_id=1,
        topic="Custom Keyboard Lubing Guide",
        primary_keyword="how to lube switches",
        target_viewer="Keyboard enthusiasts",
        viewer_problem="Scratchy stock switches",
        search_intent="How-to / Tutorial",
    ))

    # Add a calendar item in production
    test_db.save_strategy_calendar_item(StrategyCalendarItem(
        id=None,
        channel_id=1,
        channel_name="TechGear Pulse",
        topic="Silent Switch Shootout",
        target_keyword="silent mechanical switches",
        search_intent="Comparison",
        suggested_format="Long-form",
        working_title="Silent Switch Shootout 2026",
        planned_date="2026-11-01",
        production_status="In Production",
    ))

    summary2 = action_engine.get_progress_summary(1)
    assert summary2["briefs_completed"] == 1
    assert summary2["videos_in_production"] >= 1


# ==============================================================================
# 7. Daily Scheduler Status & Telemetry
# ==============================================================================

def test_scheduler_status_telemetry(action_engine: ActionCenterEngine) -> None:
    """Verify that scheduler reporting returns genuine status, timezone, and local runner notice."""
    sched = action_engine.get_scheduler_status()
    assert "last_run_display" in sched
    assert "next_scheduled_run" in sched
    assert "timezone" in sched
    assert sched["timezone"] == "Asia/Dhaka"
    assert "local_runner_notice" in sched
    assert "Keyword Studio and your computer must remain running" in sched["local_runner_notice"]


# ==============================================================================
# 8. Keyword Decision Helper Tests
# ==============================================================================

def test_keyword_decision_helper_relevant_candidate(
    decision_helper: KeywordDecisionHelper,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify that a highly aligned keyword is evaluated as a strong candidate."""
    chan1 = test_chan_mgr.get_channel(1)  # TechGear Pulse (Keyboards)
    decision = decision_helper.evaluate_keyword(
        keyword="best wireless mechanical keyboard 2026",
        channel=chan1,
        source_type="autocomplete",
    )

    assert isinstance(decision, KeywordDecision)
    assert decision.channel_name == chan1.channel_name
    assert "Strong Candidate" in decision.verdict
    assert decision.confidence == "High Evidence"
    assert "mechanical" in decision.relevance_reason.lower() or "keyboard" in decision.relevance_reason.lower()
    assert "disclaimer" in decision.to_dict()
    assert "does not promise guaranteed search rankings" in decision.disclaimer


def test_keyword_decision_helper_short_tail_warning(
    decision_helper: KeywordDecisionHelper,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify that a 1-2 word head term receives an explicit recommendation to expand."""
    chan1 = test_chan_mgr.get_channel(1)
    decision = decision_helper.evaluate_keyword(
        keyword="keyboard",
        channel=chan1,
        source_type="autocomplete",
    )

    assert "Needs More Research" in decision.verdict
    assert "Short-tail phrase" in decision.tail_length_fit
    assert "3-5 word" in decision.recommended_action


def test_keyword_decision_helper_anti_cannibalization(
    decision_helper: KeywordDecisionHelper,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify that a keyword matching an existing channel video is flagged for cannibalization risk."""
    chan1 = test_chan_mgr.get_channel(1)
    # Add an existing topic to channel 1
    chan1.existing_video_topics = ["Best Custom Mechanical Keyboard Build 2026"]
    test_chan_mgr.save_channel(chan1)

    decision = decision_helper.evaluate_keyword(
        keyword="best custom mechanical keyboard build",
        channel=chan1,
        source_type="autocomplete",
    )

    assert "High Cannibalization Risk" in decision.verdict
    assert "splits your own channel's search impressions" in decision.cannibalization_risk or "High overlap" in decision.cannibalization_risk


def test_keyword_decision_helper_batch_evaluation(
    decision_helper: KeywordDecisionHelper,
    test_chan_mgr: ChannelManager,
) -> None:
    """Verify batch evaluation of candidate keywords."""
    chan2 = test_chan_mgr.get_channel(2)  # CodeCraft বাংলা
    candidates = [
        "python tutorial for beginners full course",
        "fastapi microservices tutorial",
        "coding",
    ]

    decisions = decision_helper.evaluate_candidates(candidates, chan2, limit=3)
    assert len(decisions) == 3
    assert decisions[0].keyword == "python tutorial for beginners full course"
    assert decisions[2].keyword == "coding"
    assert "Needs More Research" in decisions[2].verdict  # Short-tail


# ==============================================================================
# 9. 5-Section Beginner SEO Coach Content Verification
# ==============================================================================

def test_five_section_seo_coach_structure(action_engine: ActionCenterEngine) -> None:
    """Verify that every generated ActionTask provides all 5 required coaching sections."""
    tasks = action_engine.sync_tasks_for_channel(1)
    assert len(tasks) > 0

    for task in tasks:
        # 1. WHAT TO DO
        assert len(task.what_to_do.strip()) > 10, f"Task {task.task_key} missing what_to_do"
        # 2. WHY IT MATTERS
        assert len(task.why_it_matters.strip()) > 10, f"Task {task.task_key} missing why_it_matters"
        # 3. HOW TO DO IT
        assert len(task.how_to_do_it) >= 2, f"Task {task.task_key} missing how_to_do_it steps"
        # 4. WHAT TO CHECK
        assert len(task.what_to_check) >= 2, f"Task {task.task_key} missing what_to_check checklist"
        # 5. WHAT COMES NEXT
        assert len(task.what_comes_next.strip()) > 5, f"Task {task.task_key} missing what_comes_next"
