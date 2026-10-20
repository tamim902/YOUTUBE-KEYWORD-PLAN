"""Domain models for Niche Product Discovery & AI-Powered Content Gap Intelligence (Phase 12 & Phase 13)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ClassificationCategory(str, Enum):
    """Product research classification categories based on observed video evidence."""

    MATCHING_VIDEOS_FOUND = "MATCHING VIDEOS FOUND"
    FEW_MATCHING_VIDEOS_FOUND = "FEW MATCHING VIDEOS FOUND"
    NO_MATCHING_VIDEOS_FOUND = "NO MATCHING VIDEOS FOUND IN SEARCHES"
    NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES = "NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES"
    INSUFFICIENT_RESEARCH = "INSUFFICIENT RESEARCH"
    PRODUCT_IDENTITY_UNVERIFIED = "PRODUCT IDENTITY UNVERIFIED"


class SearchMode(str, Enum):
    """Configurable query strategy search modes for investigating products."""

    REVIEWS = "Product Reviews"
    UNBOXING = "Unboxing"
    COMPARISONS = "Comparisons"
    BUYING_GUIDES = "Buying Guides"
    ALTERNATIVES = "Alternatives"
    GENERAL = "General Product Videos"
    # Phase 13 Extended AI & Deep Search Modes
    PRODUCT_TESTING = "Product Testing"
    LONG_TERM_USE = "Long-Term Use"
    COMMON_PROBLEMS = "Common Problems"
    TARGET_AUDIENCES = "Target Audiences"
    USE_CASES = "Different Use Cases"


@dataclass
class CandidateProduct:
    """Represents a discovered or user-supplied product candidate within a niche."""

    product_name: str
    id: Optional[int] = None
    session_id: Optional[int] = None
    brand: str = ""
    model: str = ""
    niche: str = ""
    category: str = ""
    aliases: List[str] = field(default_factory=list)
    source: str = "Extracted Candidate"  # "Curated Market Catalog", "Extracted Candidate", "Existing Keywords", "Video Titles", "User Supplied", "Autocomplete Discovery"
    evidence_url: str = ""
    evidence_reference: str = ""
    verification_status: str = "Extracted Candidate"  # "Verified Market Product", "Extracted Candidate", "User Supplied", "Needs Review", "Unverified", "Rejected"
    extraction_confidence: str = "High"  # "High", "Moderate", "Uncertain / Needs Review"
    classification: str = ClassificationCategory.INSUFFICIENT_RESEARCH.value
    classification_reason: str = ""
    matching_videos_count: int = 0
    unique_channels_count: int = 0
    latest_video_date: Optional[str] = None
    queries_executed: List[str] = field(default_factory=list)
    queries_succeeded: int = 0
    queries_failed: int = 0
    search_coverage_summary: str = ""
    opportunity_score: float = 50.0  # 0 to 100 Research Opportunity Score
    opportunity_score_breakdown: Dict[str, Any] = field(default_factory=dict)
    confidence_level: str = "Low"  # "High", "Moderate", "Low"
    data_source: str = "Live YouTube Data API v3"  # "Live YouTube Data API v3" or "Offline Simulation / Heuristics"
    notes: str = ""
    original_name: str = ""
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    priority: str = "Medium"  # "High", "Medium", "Low"
    first_seen_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def record_user_correction(
        self, field_name: str, old_val: Any, new_val: Any, reason: str = ""
    ) -> None:
        """Record an audit trail entry for user review changes without destroying provenance."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "field": field_name,
            "old_value": old_val,
            "new_value": new_val,
            "reason": reason,
        }
        self.audit_trail.append(entry)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CandidateProduct":
        valid_keys = {
            "id", "session_id", "product_name", "brand", "model", "niche", "category",
            "aliases", "source", "evidence_url", "evidence_reference", "verification_status",
            "extraction_confidence", "classification", "classification_reason",
            "matching_videos_count", "unique_channels_count", "latest_video_date",
            "queries_executed", "queries_succeeded", "queries_failed",
            "search_coverage_summary", "opportunity_score", "opportunity_score_breakdown",
            "confidence_level", "data_source", "notes", "original_name", "audit_trail",
            "priority", "first_seen_at", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProductVideoMatch:
    """Represents a video retrieved within the selected date range matched to a product."""

    video_id: str
    title: str
    id: Optional[int] = None
    product_id: Optional[int] = None
    session_id: Optional[int] = None
    channel_id: str = ""
    channel_title: str = ""
    publish_date: str = ""
    url: str = ""
    views: int = 0
    match_type: str = "Exact Model Match"  # "Exact Model Match", "Alias Match", "Token / Partial Match"
    match_field: str = "title"  # "title", "description"
    matched_terms: List[str] = field(default_factory=list)
    is_excluded: bool = False  # User can manually exclude irrelevant videos
    exclusion_reason: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductVideoMatch":
        valid_keys = {
            "id", "product_id", "session_id", "video_id", "title",
            "channel_id", "channel_title", "publish_date", "url",
            "views", "match_type", "match_field", "matched_terms",
            "is_excluded", "exclusion_reason", "created_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProductResearchSession:
    """Represents a research run investigating products in a niche over a date range."""

    niche: str
    id: Optional[int] = None
    language: str = "en"
    country: str = "US"
    start_date: str = ""
    end_date: str = ""
    category_filters: List[str] = field(default_factory=list)
    search_modes: List[str] = field(default_factory=list)
    few_videos_threshold: int = 3
    min_queries_for_zero_match: int = 2
    max_queries: int = 15
    max_videos_per_query: int = 20
    request_budget: int = 10
    requests_made: int = 0
    quota_used: int = 0
    status: str = "Completed"  # "Running", "Completed", "Stopped", "Cancelled", "Error"
    error_message: Optional[str] = None
    scoring_weights: Dict[str, float] = field(default_factory=dict)
    ai_summary: str = ""
    is_mocked: bool = False
    cancelled_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductResearchSession":
        valid_keys = {
            "id", "niche", "language", "country", "start_date", "end_date",
            "category_filters", "search_modes", "few_videos_threshold",
            "min_queries_for_zero_match", "max_queries", "max_videos_per_query",
            "request_budget", "requests_made", "quota_used", "status",
            "error_message", "scoring_weights", "ai_summary", "is_mocked",
            "cancelled_at", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProductQueryExecution:
    """Log entry for an executed YouTube search query for a candidate product."""

    product_name: str
    query_text: str
    search_mode: str = "General"
    id: Optional[int] = None
    session_id: Optional[int] = None
    product_id: Optional[int] = None
    query_source: str = "ALGORITHMIC_TEMPLATE"  # "ALGORITHMIC_TEMPLATE", "AI_GENERATED_QUERY", "USER_CUSTOM"
    status: str = "Success"  # "Success", "Zero Results", "Error", "Skipped - Budget Limit"
    results_count: int = 0
    error_message: Optional[str] = None
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductQueryExecution":
        valid_keys = {
            "id", "session_id", "product_id", "product_name", "query_text",
            "search_mode", "query_source", "status", "results_count",
            "error_message", "executed_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
