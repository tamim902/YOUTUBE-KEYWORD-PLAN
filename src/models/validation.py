"""Domain models for Phase 26: YouTube Growth Intelligence & Topic Validation Engine."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TopicReadinessStatus(str, Enum):
    """Overall readiness recommendation for a candidate topic."""
    READY_FOR_REVIEW = "Ready for Human Review"
    NEEDS_MORE_RESEARCH = "Needs More Research"
    NOT_RECOMMENDED = "Not Recommended"


class AngleType(str, Enum):
    """Strategic angle archetypes for approved topics."""
    BEGINNER_GUIDE = "Beginner Guide"
    DETAILED_TUTORIAL = "Detailed Tutorial"
    COMPARISON = "Comparison / Versus"
    REVIEW = "Review / Evaluation"
    ALTERNATIVES = "Alternatives"
    COMMON_MISTAKES = "Common Mistakes"
    PROBLEM_SOLVING = "Problem-Solving Demonstration"
    UPDATED_GUIDE = "Updated Guide (Current Year)"
    FAQ = "FAQ & Troubleshooting"
    BUDGET_GUIDE = "Budget-Specific Guide"


@dataclass
class TopicAngle:
    """Distinct, non-repetitive angle for video execution."""
    angle_type: str
    angle_title: str
    intended_viewer: str
    main_question_answered: str
    primary_keyword: str
    supporting_evidence: str
    required_research: str
    potential_overlap_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicAngle":
        return cls(**data)


@dataclass
class OwnChannelOverlapResult:
    """Detection result comparing candidate idea against existing channel content."""
    topic: str
    is_exact_duplicate: bool = False
    has_similar_title: bool = False
    overlapping_titles: List[str] = field(default_factory=list)
    overlapping_reasons: List[str] = field(default_factory=list)
    intent_overlap_warning: str = ""
    recommendation_override_allowed: bool = True
    suggested_action: str = "Proceed with unique angle"
    overlap_score: float = 100.0  # 100 = completely unique / zero cannibalization, 0 = exact duplicate

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompetitorVideoRecord:
    """Public metadata record of a competitor video found in executed searches."""
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: Optional[int] = None
    duration: str = ""
    video_url: str = ""
    matching_query: str = ""
    relevance_reason: str = ""
    relative_age_days: int = 0
    views_per_day: Optional[float] = None
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductValidationRecord:
    """Validation audit for product and affiliate content."""
    product_id: str
    product_name: str
    category: str
    brand: str = ""
    verified_specs: Dict[str, Any] = field(default_factory=dict)
    price_estimate: str = "Unverified"
    price_source: str = "Manufacturer Catalog / Verified Retailer"
    availability_status: str = "Available"
    affiliate_program: str = "Amazon Associates"
    source_links: List[str] = field(default_factory=list)
    unverified_facts: List[str] = field(default_factory=list)
    already_covered_on_channel: bool = False
    last_checked_iso: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TopicValidationReport:
    """Comprehensive, evidence-based validation audit report for a candidate topic."""
    id: Optional[int]
    channel_id: int
    topic: str
    primary_keyword: str
    secondary_keywords: List[str] = field(default_factory=list)
    search_intent: str = "Informational / How-To"
    target_viewer: str = "General Audience"
    niche_match_score: float = 0.0          # 0-100
    intent_clarity_score: float = 0.0       # 0-100
    keyword_evidence_score: float = 0.0     # 0-100
    recent_video_evidence_score: float = 0.0 # 0-100
    own_channel_overlap_score: float = 100.0# 0-100 (100 = completely unique)
    product_relevance_score: float = 0.0    # 0-100
    composite_opportunity_score: float = 0.0# 0-100
    confidence_tier: str = "Moderate Evidence"
    readiness_status: str = TopicReadinessStatus.READY_FOR_REVIEW.value
    what_supports_idea: List[str] = field(default_factory=list)
    what_weakens_idea: List[str] = field(default_factory=list)
    what_remains_unknown: List[str] = field(default_factory=list)
    further_research_needed: List[str] = field(default_factory=list)
    gap_state: str = "FEW MATCHING RECENT VIDEOS FOUND"
    queries_executed: List[str] = field(default_factory=list)
    recent_videos_count: int = 0
    competitor_videos: List[Dict[str, Any]] = field(default_factory=list)
    suggested_angles: List[Dict[str, Any]] = field(default_factory=list)
    product_validation: Optional[Dict[str, Any]] = None
    is_approved: bool = False
    is_rejected: bool = False
    is_saved: bool = False
    is_added_to_calendar: bool = False
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicValidationReport":
        return cls(**data)
