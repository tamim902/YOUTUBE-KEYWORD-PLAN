"""Domain models for Phase 25: YouTube Content Strategy Autopilot for Four Channels."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStage(str, Enum):
    """Sequential stages of the content production lifecycle."""
    IDEA = "Idea"
    RESEARCH = "Research"
    BRIEF = "Brief"
    SCRIPT = "Script"
    PRODUCTION = "Production"
    THUMBNAIL = "Thumbnail"
    SEO_REVIEW = "SEO Review"
    READY_TO_PUBLISH = "Ready to Publish"
    PUBLISHED = "Published"
    PERFORMANCE_REVIEW = "Performance Review"


class ProductionEffort(str, Enum):
    """Estimated effort level for video production."""
    LOW = "Low"          # 2-4 hours (screen recording / simple talking head)
    MEDIUM = "Medium"    # 5-8 hours (b-roll, live testing, graphics)
    HIGH = "High"        # 10+ hours (multi-product comparison, in-depth teardown)


class TopicUserStatus(str, Enum):
    """User review decision for a suggested topic."""
    SUGGESTED = "Suggested"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SAVED = "Saved for Later"
    IN_CALENDAR = "In Calendar"
    COVERED = "Already Covered"


@dataclass
class ContentPillar:
    """Strategic topic category representing a core content foundation for a channel."""
    id: Optional[int]
    channel_id: int
    pillar_name: str
    description: str
    audience_problem: str
    target_keywords: List[str] = field(default_factory=list)
    candidate_topics: List[str] = field(default_factory=list)
    existing_coverage_count: int = 0
    potential_affiliate_relevance: str = "Low"
    confidence_level: str = "Moderate Evidence"  # "High Evidence", "Moderate Evidence", "Low / Exploratory"
    is_approved: bool = False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ContentCluster:
    """Group of interconnected videos organized into a coherent series."""
    id: Optional[int]
    channel_id: int
    pillar_id: Optional[int]
    cluster_name: str
    pillar_video_title: str
    supporting_video_titles: List[str] = field(default_factory=list)
    comparison_video_titles: List[str] = field(default_factory=list)
    review_video_titles: List[str] = field(default_factory=list)
    faq_video_titles: List[str] = field(default_factory=list)
    cluster_rationale: str = ""
    anti_cannibalization_notes: str = ""
    created_at: str = ""


@dataclass
class PrioritizedTopic:
    """Transparently scored candidate video topic with full evidence provenance."""
    topic_id: str
    channel_id: int
    proposed_title: str
    target_keyword: str
    search_intent: str
    channel_relevance_score: float      # 0-100
    search_intent_score: float          # 0-100
    keyword_evidence_score: float       # 0-100
    recent_video_evidence_score: float  # 0-100
    research_coverage_score: float      # 0-100
    product_relevance_score: float      # 0-100
    composite_priority_score: float     # 0-100
    estimated_production_effort: ProductionEffort = ProductionEffort.MEDIUM
    selection_rationale: str = ""       # 1. Why it was selected
    supporting_sources: List[str] = field(default_factory=list) # 2. Supporting sources
    research_date: str = ""             # 3. Research date
    confidence_level: str = "Moderate"  # 4. Confidence
    missing_evidence: str = ""          # 5. Missing evidence
    suggested_next_step: str = ""       # 6. Suggested next step
    user_status: TopicUserStatus = TopicUserStatus.SUGGESTED


@dataclass
class StrategyCalendarItem:
    """A scheduled or planned video item on a channel's production calendar."""
    id: Optional[int]
    channel_id: int
    channel_name: str
    topic: str
    target_keyword: str
    search_intent: str
    suggested_format: str  # "Long-form", "Shorts"
    working_title: str
    production_status: str  # "Planned", "In Production", "Scheduled", "Published"
    planned_date: str
    evidence_summary: str = ""
    required_research: str = ""
    affiliate_disclosure_required: bool = False
    production_hours_estimate: float = 4.0
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ContentBriefDocument:
    """Comprehensive, actionable briefing document for a planned video."""
    id: Optional[int]
    channel_id: int
    topic: str
    target_viewer: str
    viewer_problem: str
    search_intent: str
    primary_keyword: str
    supporting_keywords: List[str] = field(default_factory=list)
    main_promise: str = ""
    title_options: List[Dict[str, str]] = field(default_factory=list)
    video_structure: List[Dict[str, str]] = field(default_factory=list)
    questions_to_answer: List[str] = field(default_factory=list)
    comparison_criteria: List[str] = field(default_factory=list)
    unverified_facts: List[str] = field(default_factory=list)
    suggested_research_sources: List[str] = field(default_factory=list)
    thumbnail_concept: str = ""
    description_draft: str = ""
    affiliate_disclosure_reminder: str = ""
    seo_prepublish_checklist: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ProductionWorkflowProject:
    """End-to-end production tracking project moving through sequential stages."""
    id: Optional[int]
    channel_id: int
    project_name: str
    primary_keyword: str
    current_stage: WorkflowStage = WorkflowStage.IDEA
    stage_history: List[Dict[str, str]] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    checklist_completed: Dict[str, bool] = field(default_factory=dict)
    brief_id: Optional[int] = None
    calendar_item_id: Optional[int] = None
    is_cancelled: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ChannelStrategySettings:
    """Strategic configuration parameters for an individual channel."""
    channel_id: int
    videos_per_week: int = 2
    longform_pct: int = 70
    shorts_pct: int = 30
    weekly_production_hours_budget: float = 12.0
    preferred_publishing_days: List[str] = field(default_factory=lambda: ["Tuesday", "Saturday"])
    preferred_duration_range: str = "8-15 minutes"
    strategic_priority: str = "Build initial topical authority with beginner guides"
    created_at: str = ""
    updated_at: str = ""
