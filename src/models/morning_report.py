"""Domain models for Four-Channel Daily Morning Idea Reports and Automation (Phase 22 Parts 8, 9)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IdeaReviewStatus(str, Enum):
    READY_FOR_REVIEW = "Ready for further review"
    NEEDS_MORE_RESEARCH = "Needs more research"
    AFFILIATE_UNVERIFIED = "Affiliate details unverified"
    LOW_CONFIDENCE = "Low-confidence opportunity"
    ALREADY_PLANNED = "Already planned or duplicate topic"


class GapFinderState(str, Enum):
    """The 4 required states for the 60-day gap finder (Phase 22 Part 7)."""

    MATCHING_RECENT_VIDEOS_FOUND = "MATCHING RECENT VIDEOS FOUND"
    FEW_MATCHING_RECENT_VIDEOS_FOUND = "FEW MATCHING RECENT VIDEOS FOUND"
    NO_MATCHING_VIDEOS_FOUND = "NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES"
    INSUFFICIENT_RESEARCH = "INSUFFICIENT RESEARCH"


@dataclass
class DailyIdeaItem:
    """Represents a prioritized daily research idea with all 18 required evidence fields."""

    channel_id: int
    channel_name: str
    proposed_topic: str
    main_keyword: str
    supporting_keywords: List[str] = field(default_factory=list)
    search_intent: str = "Informational"
    target_viewer: str = "General Audience"
    why_topic_worth_researching: str = ""
    recent_relevant_videos_found: int = 0
    exact_research_window: str = ""  # Start ISO to End ISO
    source_and_coverage_summary: str = ""
    potential_product_match: Optional[str] = None
    affiliate_availability_status: str = "Unverified"
    opportunity_estimate: float = 50.0  # 0 to 100
    confidence_level: str = "Moderate Confidence"
    suggested_video_format: str = "Long-form In-depth"
    seo_focused_title_options: List[str] = field(default_factory=list)
    suggested_thumbnail_concept: str = ""
    description_draft: str = ""
    next_recommended_action: str = ""
    review_label: str = IdeaReviewStatus.READY_FOR_REVIEW.value
    gap_state: str = GapFinderState.FEW_MATCHING_RECENT_VIDEOS_FOUND.value
    sample_video_ids: List[str] = field(default_factory=list)
    sample_video_titles: List[str] = field(default_factory=list)
    is_saved: bool = False
    is_rejected: bool = False
    is_marked_covered: bool = False
    is_added_to_calendar: bool = False
    id: Optional[int] = None
    report_id: Optional[int] = None
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailyIdeaItem":
        valid_keys = {
            "channel_id", "channel_name", "proposed_topic", "main_keyword",
            "supporting_keywords", "search_intent", "target_viewer",
            "why_topic_worth_researching", "recent_relevant_videos_found",
            "exact_research_window", "source_and_coverage_summary",
            "potential_product_match", "affiliate_availability_status",
            "opportunity_estimate", "confidence_level", "suggested_video_format",
            "seo_focused_title_options", "suggested_thumbnail_concept",
            "description_draft", "next_recommended_action", "review_label",
            "gap_state", "sample_video_ids", "sample_video_titles", "is_saved",
            "is_rejected", "is_marked_covered", "is_added_to_calendar", "id",
            "report_id", "created_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class DailyMorningReport:
    """Consolidated morning report for all four channels."""

    id: Optional[int] = None
    run_date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    timezone_name: str = "Asia/Dhaka"
    scheduled_time: str = "07:00"
    status: str = "Completed"  # "Completed", "Partial", "Running", "Failed"
    total_channels_processed: int = 4
    total_ideas_generated: int = 0
    total_queries_executed: int = 0
    api_quota_units_used: int = 0
    ideas: List[DailyIdeaItem] = field(default_factory=list)
    ideas_by_channel: Dict[int, List[DailyIdeaItem]] = field(default_factory=dict)
    summary_notes: str = ""
    error_message: Optional[str] = None
    started_at: str = field(default_factory=_now_iso)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Serialize nested idea dict
        d["ideas_by_channel"] = {
            cid: [i.to_dict() if hasattr(i, "to_dict") else i for i in items]
            for cid, items in self.ideas_by_channel.items()
        }
        return d
