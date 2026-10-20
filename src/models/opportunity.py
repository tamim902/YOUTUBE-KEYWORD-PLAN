"""Domain models for YouTube Content Opportunities, Briefs, Calendar, and Cannibalization Analysis (Phase 11)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ContentOpportunityItem:
    """Represents an identified YouTube content opportunity topic."""

    topic: str
    primary_keyword: str
    id: Optional[int] = None
    project_id: Optional[int] = None
    supporting_keywords: List[str] = field(default_factory=list)
    target_audience: str = "General Audience"
    search_intent: str = "Informational"
    content_format: str = "Step-by-step Guide"
    opportunity_score: float = 50.0  # 0 to 100 heuristic
    confidence_level: str = "Moderate Evidence"  # "High Evidence", "Moderate Evidence", "Low / Lexical Only"
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    gap_rationale: str = ""
    notes: str = ""
    status: str = "Idea"  # Idea, Researching, Brief Ready, Scripting, Production, Editing, Scheduled, Published, Archived
    priority: str = "Medium"  # Low, Medium, High
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentOpportunityItem":
        valid_keys = {
            "topic", "primary_keyword", "id", "project_id", "supporting_keywords",
            "target_audience", "search_intent", "content_format", "opportunity_score",
            "confidence_level", "score_breakdown", "evidence", "gap_rationale",
            "notes", "status", "priority", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ContentBrief:
    """Editable content brief for planning and scripting a YouTube video (Step 7)."""

    working_title: str
    primary_keyword: str
    id: Optional[int] = None
    opportunity_id: Optional[int] = None
    supporting_keywords: List[str] = field(default_factory=list)
    target_audience: str = "General Audience"
    search_intent: str = "Informational"
    viewer_problem: str = ""
    unique_angle: str = ""
    proposed_intro: str = ""
    main_sections: List[str] = field(default_factory=list)
    examples_to_research: List[str] = field(default_factory=list)
    visual_elements: List[str] = field(default_factory=list)
    faqs: List[str] = field(default_factory=list)
    conclusion_cta: str = ""
    fact_checking_checklist: List[str] = field(default_factory=list)
    source_references: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentBrief":
        valid_keys = {
            "working_title", "primary_keyword", "id", "opportunity_id",
            "supporting_keywords", "target_audience", "search_intent",
            "viewer_problem", "unique_angle", "proposed_intro", "main_sections",
            "examples_to_research", "visual_elements", "faqs", "conclusion_cta",
            "fact_checking_checklist", "source_references", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class CalendarEntry:
    """Represents a scheduled video topic in the YouTube content calendar (Step 8)."""

    title: str
    primary_keyword: str
    planned_date: str  # YYYY-MM-DD
    id: Optional[int] = None
    opportunity_id: Optional[int] = None
    status: str = "Idea"  # Idea, Researching, Brief Ready, Scripting, Production, Editing, Scheduled, Published, Archived
    priority: str = "Medium"  # Low, Medium, High
    notes: str = ""
    session_id: Optional[int] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEntry":
        valid_keys = {
            "title", "primary_keyword", "planned_date", "id", "opportunity_id",
            "status", "priority", "notes", "session_id", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class TopicOverlapResult:
    """Represents potential content overlap / keyword cannibalization between two topics (Step 9)."""

    topic_a: str
    topic_b: str
    similarity_score: float  # 0.0 to 1.0 Jaccard or token similarity
    overlap_type: str  # "Shared Primary Keyword", "High Token Overlap", "Shared Supporting Keywords", "Identical Intent"
    shared_keywords: List[str] = field(default_factory=list)
    warning_message: str = ""
    resolution: str = "Unresolved"  # "Unresolved", "Keep Both", "Edited", "Intentionally Related"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicOverlapResult":
        valid_keys = {
            "topic_a", "topic_b", "similarity_score", "overlap_type",
            "shared_keywords", "warning_message", "resolution",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class TitleQualityCheck:
    """Quality evaluation and checklist feedback for a proposed YouTube title (Step 6)."""

    title: str
    score: float = 80.0
    passes_relevance: bool = True
    passes_clarity: bool = True
    passes_specificity: bool = True
    passes_audience_fit: bool = True
    has_unsupported_claims: bool = False
    has_excessive_repetition: bool = False
    has_misleading_wording: bool = False
    feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TitleQualityCheck":
        valid_keys = {
            "title", "score", "passes_relevance", "passes_clarity",
            "passes_specificity", "passes_audience_fit", "has_unsupported_claims",
            "has_excessive_repetition", "has_misleading_wording", "feedback",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
