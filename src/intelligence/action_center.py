"""Personal YouTube SEO Coach & Daily Action Center Engine (Phase 31).

Generates, prioritizes, and persists actionable next steps for each of the
four configured YouTube channels based strictly on verified SQLite application state.
Provides structured 5-section beginner-friendly SEO coaching guidance:
- WHAT TO DO
- WHY IT MATTERS
- HOW TO DO IT
- WHAT TO CHECK
- WHAT COMES NEXT
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional

from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager, db_manager

logger = logging.getLogger(__name__)


def _get_val(obj: Any, field_name: str, default: Any = "") -> Any:
    """Safely retrieve attribute from either a dataclass/object or dictionary."""
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


class TaskType(str, Enum):
    """Categorization of supported SEO coach action items."""
    REVIEW_NEW_KEYWORDS = "review_new_keywords"
    SELECT_VIDEO_TOPIC = "select_video_topic"
    RESEARCH_COMPETITORS = "research_competitors"
    DRAFT_DESCRIPTION = "draft_description"
    AUDIT_SEO = "audit_seo"
    CREATE_CONTENT_BRIEF = "create_content_brief"
    REVIEW_PRODUCT_OPPORTUNITY = "review_product_opportunity"
    REVIEW_PERFORMANCE = "review_performance"
    START_KEYWORD_RESEARCH = "start_keyword_research"


class TaskStatus(str, Enum):
    """Lifecycle status for persisted action center tasks."""
    PENDING = "pending"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


@dataclass
class ActionTask:
    """An actionable SEO task anchored in authentic application data."""
    task_key: str
    channel_id: int
    channel_name: str
    task_type: TaskType
    title: str
    short_summary: str
    priority: str = "normal"  # "high", "medium", "normal"
    target_page: str = "Dashboard"
    context_data: Dict[str, Any] = field(default_factory=dict)
    what_to_do: str = ""
    why_it_matters: str = ""
    how_to_do_it: List[str] = field(default_factory=list)
    what_to_check: List[str] = field(default_factory=list)
    what_comes_next: str = ""
    status: TaskStatus = TaskStatus.PENDING
    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to database-ready dictionary."""
        return {
            "task_key": self.task_key,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "task_type": self.task_type.value if isinstance(self.task_type, TaskType) else str(self.task_type),
            "title": self.title,
            "short_summary": self.short_summary,
            "priority": self.priority,
            "target_page": self.target_page,
            "context_data": self.context_data,
            "what_to_do": self.what_to_do,
            "why_it_matters": self.why_it_matters,
            "how_to_do_it": self.how_to_do_it,
            "what_to_check": self.what_to_check,
            "what_comes_next": self.what_comes_next,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionTask":
        """Reconstruct an ActionTask instance from a database row dictionary."""
        raw_type = data.get("task_type", TaskType.START_KEYWORD_RESEARCH.value)
        try:
            task_type = TaskType(raw_type)
        except ValueError:
            task_type = TaskType.START_KEYWORD_RESEARCH

        raw_status = data.get("status", TaskStatus.PENDING.value)
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.PENDING

        return cls(
            id=data.get("id"),
            task_key=data.get("task_key", ""),
            channel_id=int(data.get("channel_id", 1)),
            channel_name=data.get("channel_name", ""),
            task_type=task_type,
            title=data.get("title", ""),
            short_summary=data.get("short_summary", ""),
            priority=data.get("priority", "normal"),
            target_page=data.get("target_page", "Dashboard"),
            context_data=data.get("context_data", {}) if isinstance(data.get("context_data"), dict) else {},
            what_to_do=data.get("what_to_do", ""),
            why_it_matters=data.get("why_it_matters", ""),
            how_to_do_it=data.get("how_to_do_it", []) if isinstance(data.get("how_to_do_it"), list) else [],
            what_to_check=data.get("what_to_check", []) if isinstance(data.get("what_to_check"), list) else [],
            what_comes_next=data.get("what_comes_next", ""),
            status=status,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ActionCenterEngine:
    """Orchestrates daily action tasks, SEO coaching advice, and scheduler reporting."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        chan_mgr: Optional[ChannelManager] = None,
    ) -> None:
        self.db = database or db_manager
        self.chan_mgr = chan_mgr or channel_manager

    def sync_tasks_for_channel(self, channel_id: int) -> List[ActionTask]:
        """Scan real application state for a channel and persist new pending tasks.
        
        Strictly preserves existing task statuses: completed and dismissed tasks
        are never re-created or overwritten.
        """
        channel = self.chan_mgr.get_channel(channel_id)
        if not channel:
            return []

        c_name = channel.channel_name
        candidate_tasks: List[ActionTask] = []

        # ----------------------------------------------------------------------
        # 1. Unreviewed Daily Idea Opportunities (from SQLite daily_idea_items)
        # ----------------------------------------------------------------------
        daily_ideas = self.db.get_daily_ideas_by_channel(channel_id)
        unreviewed = [
            i for i in daily_ideas
            if not getattr(i, "is_saved", False) and not getattr(i, "is_rejected", False)
        ]
        if unreviewed:
            # Pick top opportunity
            top_idea = max(unreviewed, key=lambda x: getattr(x, "opportunity_estimate", 50.0))
            task_key = f"chan_{channel_id}_unreviewed_{top_idea.id or abs(hash(top_idea.proposed_topic))}"
            candidate_tasks.append(
                ActionTask(
                    task_key=task_key,
                    channel_id=channel_id,
                    channel_name=c_name,
                    task_type=TaskType.REVIEW_NEW_KEYWORDS,
                    title=f"Review Validated Topic Idea: '{top_idea.proposed_topic}'",
                    short_summary=f"Discovered by 60-day competitor gap analysis for {c_name} (Score: {getattr(top_idea, 'opportunity_estimate', 50):.1f}/100).",
                    priority="high",
                    target_page="🌅 Daily Morning Idea Report",
                    context_data={"idea_id": top_idea.id, "keyword": top_idea.main_keyword, "topic": top_idea.proposed_topic},
                    what_to_do=f"Review the 18 evidence fields for '{top_idea.proposed_topic}' on the Morning Report page, and decide whether to approve it for your content calendar.",
                    why_it_matters="Targeting phrases backed by authentic competitor gaps increases viewer click-through and helps your video stand out in YouTube browse recommendations.",
                    how_to_do_it=[
                        "1. Open the Morning Idea Report page.",
                        "2. Inspect the 60-day research window and matching competitor video count.",
                        "3. Review the 4 pre-calculated SEO title variations.",
                        "4. Click 'Save Idea' to queue it or 'Add to Calendar' to plan production.",
                    ],
                    what_to_check=[
                        "Proposed topic directly matches your channel audience",
                        "Primary keyword has verified search presence",
                        "You have a distinct angle or hands-on demonstration to offer",
                    ],
                    what_comes_next="Open Morning Idea Report to save or schedule this topic.",
                )
            )

        # ----------------------------------------------------------------------
        # 2. Planned Content Calendar Items Awaiting Content Brief
        # ----------------------------------------------------------------------
        cal_items = self.db.get_strategy_calendar_items(channel_id)
        brief_docs = self.db.get_content_brief_documents(channel_id)
        briefed_topics = {_get_val(b, "topic", "").lower().strip() for b in brief_docs}

        unbriefed_cal = [
            c for c in cal_items
            if _get_val(c, "topic", "").lower().strip() not in briefed_topics
            and _get_val(c, "production_status") != "Published"
        ]
        if unbriefed_cal:
            target_cal = unbriefed_cal[0]
            cal_topic = _get_val(target_cal, "topic", "")
            cal_id = _get_val(target_cal, "id", abs(hash(cal_topic)))
            task_key = f"chan_{channel_id}_brief_cal_{cal_id}"
            candidate_tasks.append(
                ActionTask(
                    task_key=task_key,
                    channel_id=channel_id,
                    channel_name=c_name,
                    task_type=TaskType.CREATE_CONTENT_BRIEF,
                    title=f"Complete Content Brief for Planned Video: '{cal_topic}'",
                    short_summary=f"Planned for {_get_val(target_cal, 'planned_date', 'upcoming schedule')} but missing an audience problem brief.",
                    priority="medium",
                    target_page="🧭 Content Strategy Autopilot",
                    context_data={"calendar_id": cal_id, "topic": cal_topic, "keyword": _get_val(target_cal, "target_keyword", "")},
                    what_to_do=f"Create a structured video brief for '{cal_topic}' to outline the audience problem, core promise, and chapter outline before recording.",
                    why_it_matters="A structured brief prevents script wandering, improves viewer retention across the first 60 seconds, and ensures your key takeaways are clear.",
                    how_to_do_it=[
                        "1. Open Content Strategy Autopilot.",
                        "2. Select the planned calendar topic from the project drawer.",
                        "3. Define the viewer problem, main promise, and 4-part video outline.",
                        "4. Save the brief to link it directly to your production workflow.",
                    ],
                    what_to_check=[
                        "First 30 seconds explicitly addresses viewer question or pain point",
                        "Outline includes at least 3 concrete steps or demonstration points",
                        "Clear call-to-action planned before final screen",
                    ],
                    what_comes_next="Open Content Strategy Autopilot to generate content brief.",
                )
            )

        # ----------------------------------------------------------------------
        # 3. Videos in Calendar or Briefs Missing 8-Part Descriptions
        # ----------------------------------------------------------------------
        descriptions = self.db.get_video_descriptions(channel_id)
        described_topics = {_get_val(d, "topic", "").lower().strip() for d in descriptions}

        items_needing_desc = [
            c for c in cal_items
            if _get_val(c, "topic", "").lower().strip() not in described_topics
            and _get_val(c, "production_status") in ("In Production", "Ready for Recording", "Planned")
        ]
        if items_needing_desc:
            desc_target = items_needing_desc[0]
            d_topic = _get_val(desc_target, "topic", "")
            d_kw = _get_val(desc_target, "target_keyword") or d_topic
            d_id = _get_val(desc_target, "id", abs(hash(d_topic)))
            task_key = f"chan_{channel_id}_desc_{d_id}"
            candidate_tasks.append(
                ActionTask(
                    task_key=task_key,
                    channel_id=channel_id,
                    channel_name=c_name,
                    task_type=TaskType.DRAFT_DESCRIPTION,
                    title=f"Draft 8-Part Description & Timestamps: '{d_topic}'",
                    short_summary=f"Prepare SEO-friendly description text, chapters, and affiliate disclosure before publishing.",
                    priority="normal",
                    target_page="📝 Video Description Studio",
                    context_data={"topic": d_topic, "keyword": d_kw},
                    what_to_do=f"Generate an 8-part YouTube description draft for '{d_topic}' with chapter markers, summary hook, and channel footer links.",
                    why_it_matters="YouTube search indexes the first 3 lines of your description; structured timestamps also enable Google Search video key moments.",
                    how_to_do_it=[
                        "1. Open Video Description Studio.",
                        "2. Enter the primary keyword and select your channel profile.",
                        "3. Review generated chapters, value summary, and FTC affiliate disclaimer.",
                        "4. Save the description or copy to clipboard.",
                    ],
                    what_to_check=[
                        "Target keyword appears in the opening 100 characters",
                        "Timestamps start at 00:00 and are chronologically ordered",
                        "Affiliate links include explicit FTC disclosure notice",
                    ],
                    what_comes_next="Open Video Description Studio to assemble description.",
                )
            )

        # ----------------------------------------------------------------------
        # 4. SEO Audits Requiring Attention (Score < 80)
        # ----------------------------------------------------------------------
        audits = self.db.get_seo_audits_by_channel(channel_id)
        incomplete_audits = []
        for a in audits:
            try:
                scores = json.loads(a.get("scores_json") or "{}")
                if scores.get("overall_score", 100) < 80:
                    incomplete_audits.append((a, scores.get("overall_score", 0)))
            except Exception:
                pass

        if incomplete_audits:
            target_audit, sc = min(incomplete_audits, key=lambda x: x[1])
            t_title = target_audit.get("proposed_title", "Video Draft")
            task_key = f"chan_{channel_id}_audit_{target_audit.get('id', abs(hash(t_title)))}"
            candidate_tasks.append(
                ActionTask(
                    task_key=task_key,
                    channel_id=channel_id,
                    channel_name=c_name,
                    task_type=TaskType.AUDIT_SEO,
                    title=f"Fix SEO Audit Issues for '{t_title}' ({sc}/100)",
                    short_summary=f"Deterministic pre-publish audit flagged title length, keyword placement, or description density issues.",
                    priority="high",
                    target_page="🔍 Video SEO & Content Audit Studio",
                    context_data={"audit_id": target_audit.get("id"), "title": t_title, "keyword": target_audit.get("primary_keyword", "")},
                    what_to_do=f"Review the audit checklist findings for '{t_title}' and apply recommendations to raise your score above 80.",
                    why_it_matters="Fixing mobile title truncation (50-70 characters) and primary keyword placement before publishing improves YouTube search click-through rate.",
                    how_to_do_it=[
                        "1. Open Video SEO & Content Audit Studio.",
                        "2. Review highlighted checklist findings and actionable advice.",
                        "3. Adjust the title length and description opening text.",
                        "4. Re-calculate score to confirm resolution.",
                    ],
                    what_to_check=[
                        "Title length is within 50-70 characters (avoids mobile truncation)",
                        "Primary keyword placed near the beginning of the title",
                        "Description includes at least 150 words of authentic context",
                    ],
                    what_comes_next="Open Video SEO Audit Studio to update draft.",
                )
            )

        # ----------------------------------------------------------------------
        # 5. Saved Search Queries Awaiting Competitor SERP Inspection
        # ----------------------------------------------------------------------
        recent_searches = self.db.get_recent_searches(limit=5)
        if recent_searches:
            # Check if any search seed has not been checked in SERP
            for s in recent_searches:
                seed = s.get("seed_keyword", "")
                s_lang = s.get("language", channel.target_language or "en")
                s_country = s.get("country", channel.target_country or "US")
                if seed and not self.db.get_cached_serp(seed, s_lang, s_country):
                    task_key = f"chan_{channel_id}_serp_{s.get('id', abs(hash(seed)))}"
                    candidate_tasks.append(
                        ActionTask(
                            task_key=task_key,
                            channel_id=channel_id,
                            channel_name=c_name,
                            task_type=TaskType.RESEARCH_COMPETITORS,
                            title=f"Inspect Competitor Videos for '{seed}'",
                            short_summary=f"Top ranking videos for '{seed}' have not been analyzed for thumbnail patterns and content gaps.",
                            priority="normal",
                            target_page="📺 YouTube Video Research",
                            context_data={"search_id": s.get("id"), "keyword": seed},
                            what_to_do=f"Run a competitor SERP check for '{seed}' to evaluate existing top-ranking video titles, view counts, and publish dates.",
                            why_it_matters="Analyzing existing competitor videos helps you spot visual patterns, outdated recommendations, and unanswered questions you can address.",
                            how_to_do_it=[
                                "1. Open YouTube Video Research.",
                                "2. Inspect the top video cards, channel sizes, and upload dates.",
                                "3. Look for gaps (e.g. videos older than 12 months, missing newer product models).",
                                "4. Choose a differentiated title angle before drafting your outline.",
                            ],
                            what_to_check=[
                                "Check if the top 3 videos are over a year old",
                                "Look for common keywords in competitor titles",
                                "Identify at least one topic nuance the competitors skipped",
                            ],
                            what_comes_next="Open YouTube Video Research to inspect competitors.",
                        )
                    )
                    break

        # ----------------------------------------------------------------------
        # 6. Fallback / Bootstrap Task if Channel Has Zero Active Items
        # ----------------------------------------------------------------------
        if not candidate_tasks:
            task_key = f"chan_{channel_id}_start_research"
            candidate_tasks.append(
                ActionTask(
                    task_key=task_key,
                    channel_id=channel_id,
                    channel_name=c_name,
                    task_type=TaskType.START_KEYWORD_RESEARCH,
                    title=f"Find New Keyword Opportunities for {c_name}",
                    short_summary=f"Start fresh keyword discovery in the '{channel.channel_niche}' niche to seed your next video project.",
                    priority="normal",
                    target_page="🔍 New Keyword Research",
                    context_data={"channel_id": channel_id, "niche": channel.channel_niche},
                    what_to_do=f"Enter a seed topic related to '{channel.channel_niche}' to discover authentic viewer search queries typed into YouTube.",
                    why_it_matters="Discovering verified viewer queries directly from YouTube autocomplete ensures you invest production time in topics people are already looking for.",
                    how_to_do_it=[
                        "1. Open New Keyword Research (Simple Guided Wizard or Quick Search).",
                        "2. Enter a broad seed phrase or viewer problem.",
                        "3. Review plain-English relevance scores and select your best-fit phrase.",
                        "4. Save the research to unlock competitor analysis and description tools.",
                    ],
                    what_to_check=[
                        "Query is at least 3 words (long-tail specificity)",
                        "Search intent aligns with your channel's format",
                        "Topic does not duplicate an existing video on your channel",
                    ],
                    what_comes_next="Open New Keyword Research to discover keywords.",
                )
            )

        # ----------------------------------------------------------------------
        # 7. Persist Candidates to SQLite (Preserving Completed / Dismissed)
        # ----------------------------------------------------------------------
        for task in candidate_tasks:
            self.db.save_action_task(task.to_dict())

        # Retrieve and return currently pending tasks for this channel
        rows = self.db.get_action_tasks(channel_id=channel_id, status=TaskStatus.PENDING.value)
        return [ActionTask.from_dict(r) for r in rows]

    def mark_task_completed(self, task_key: str) -> bool:
        """Mark an action task as completed in SQLite."""
        return self.db.update_action_task_status(task_key, TaskStatus.COMPLETED.value)

    def dismiss_task(self, task_key: str) -> bool:
        """Dismiss an action task so it never re-appears in pending queues."""
        return self.db.update_action_task_status(task_key, TaskStatus.DISMISSED.value)

    def get_progress_summary(self, channel_id: int) -> Dict[str, Any]:
        """Retrieve real verified project state counts for a channel."""
        return self.db.get_channel_progress_counts(channel_id)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Inspect daily morning report runs and return authentic scheduler telemetry."""
        reports = self.db.get_daily_morning_reports(limit=5)
        last_run = reports[0] if reports else None

        last_run_display = "No runs recorded yet"
        last_status = "Pending First Run"
        ideas_generated = 0
        if last_run:
            completed_str = last_run.get("completed_at") or last_run.get("started_at")
            if completed_str:
                try:
                    dt = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                    last_run_display = dt.strftime("%B %d, %Y at %I:%M %p UTC")
                except Exception:
                    last_run_display = completed_str
            last_status = last_run.get("status", "Completed")
            ideas_generated = last_run.get("total_ideas_generated", 0)

        # Count total unreviewed ideas across all channels
        unreviewed_total = 0
        for cid in [1, 2, 3, 4]:
            ideas = self.db.get_daily_ideas_by_channel(cid)
            unreviewed_total += sum(
                1 for i in ideas
                if not getattr(i, "is_saved", False) and not getattr(i, "is_rejected", False)
            )

        failed_count = sum(1 for r in reports if r.get("status") not in ("Completed", "completed"))

        return {
            "last_run_display": last_run_display,
            "last_status": last_status,
            "ideas_generated_last_run": ideas_generated,
            "next_scheduled_run": "Daily at 07:00 AM (Asia/Dhaka)",
            "timezone": "Asia/Dhaka",
            "is_scheduled": True,
            "unreviewed_ideas_total": unreviewed_total,
            "failed_reports_count": failed_count,
            "local_runner_notice": (
                "Local Schedule Requirement: Keyword Studio and your computer must remain running "
                "with the Streamlit process active for local scheduled background jobs to execute."
            ),
        }


# Default singleton instance
action_center_engine = ActionCenterEngine()
