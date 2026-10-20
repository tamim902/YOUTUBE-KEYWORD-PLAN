"""Domain models for Automated Niche Research Reports & Opportunity Monitoring (Phase 15)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ResearchScheduleFrequency(str, Enum):
    """Supported frequencies for recurring niche research monitoring."""

    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    MANUAL_QUEUE = "Manual Queue Only"


class MonitorRunStatus(str, Enum):
    """Lifecycle statuses for repeatable research runs."""

    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"
    PARTIAL = "Partial"


class AlertSeverity(str, Enum):
    """Severity levels for detected niche research change alerts."""

    INFO = "Info"
    WARNING = "Warning"
    HIGH_OPPORTUNITY = "High Opportunity"
    CRITICAL = "Critical"


@dataclass
class SavedResearchConfig:
    """Reusable niche research configuration template."""

    niche: str
    id: Optional[int] = None
    name: str = ""
    country: str = "US"
    language: str = "en"
    date_window_days: int = 60
    category_filters: List[str] = field(default_factory=list)
    query_templates: List[str] = field(default_factory=list)
    max_products_per_run: int = 25
    max_queries_per_run: int = 15
    request_budget: int = 15
    matching_mode: str = "Exact Model Match"
    min_research_coverage: int = 2
    opportunity_formula_version: str = "v14.0"
    enabled_discovery_methods: List[str] = field(
        default_factory=lambda: ["seed", "catalog", "autocomplete", "ai_angles"]
    )
    is_paused: bool = False
    notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedResearchConfig":
        valid_keys = {
            "id", "name", "niche", "country", "language", "date_window_days",
            "category_filters", "query_templates", "max_products_per_run",
            "max_queries_per_run", "request_budget", "matching_mode",
            "min_research_coverage", "opportunity_formula_version",
            "enabled_discovery_methods", "is_paused", "notes",
            "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProductSnapshotItem:
    """State of an observed product candidate within a specific research run snapshot."""

    product_name: str
    id: Optional[int] = None
    run_id: Optional[int] = None
    product_id: Optional[int] = None
    brand: str = ""
    model: str = ""
    niche: str = ""
    category: str = ""
    classification: str = "INSUFFICIENT RESEARCH"
    classification_reason: str = ""
    matching_videos_count: int = 0
    latest_video_date: Optional[str] = None
    unique_channels_count: int = 0
    observed_channels: List[str] = field(default_factory=list)
    opportunity_score: float = 50.0
    confidence_level: str = "Moderate Evidence"
    queries_executed_count: int = 0
    search_coverage_summary: str = ""
    verification_status: str = "Extracted Candidate"
    data_source: str = "Live YouTube Data API v3"
    snapshot_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductSnapshotItem":
        valid_keys = {
            "id", "run_id", "product_id", "product_name", "brand", "model",
            "niche", "category", "classification", "classification_reason",
            "matching_videos_count", "latest_video_date", "unique_channels_count",
            "observed_channels", "opportunity_score", "confidence_level",
            "queries_executed_count", "search_coverage_summary",
            "verification_status", "data_source", "snapshot_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ResearchMonitorRun:
    """Execution record of a repeatable niche research run."""

    config_id: Optional[int]
    niche: str
    id: Optional[int] = None
    run_number: int = 1
    trigger_type: str = "Manual"  # "Manual", "Scheduled", "Rerun"
    status: str = MonitorRunStatus.PENDING.value
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    queries_attempted: int = 0
    queries_succeeded: int = 0
    queries_failed: int = 0
    failed_query_list: List[Dict[str, str]] = field(default_factory=list)
    products_discovered: int = 0
    matching_videos_retrieved: int = 0
    live_requests_count: int = 0
    cached_requests_count: int = 0
    generated_items_count: int = 0
    provider_name: str = "YouTube Data API v3"
    error_message: Optional[str] = None
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchMonitorRun":
        valid_keys = {
            "id", "config_id", "niche", "run_number", "trigger_type", "status",
            "config_snapshot", "queries_attempted", "queries_succeeded",
            "queries_failed", "failed_query_list", "products_discovered",
            "matching_videos_retrieved", "live_requests_count",
            "cached_requests_count", "generated_items_count", "provider_name",
            "error_message", "started_at", "completed_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class MonitorAlert:
    """In-app alert generated when meaningful changes are detected between runs."""

    niche: str
    alert_type: str  # "New Verified Candidate", "Video Increase", "Score Shift", "Gap Category Change", "Budget Exhausted"
    title: str
    message: str
    evidence_data: Dict[str, Any]
    id: Optional[int] = None
    run_id: Optional[int] = None
    config_id: Optional[int] = None
    product_name: str = ""
    severity: str = AlertSeverity.INFO.value
    is_dismissed: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitorAlert":
        valid_keys = {
            "id", "run_id", "config_id", "niche", "product_name", "alert_type",
            "severity", "title", "message", "evidence_data", "is_dismissed",
            "created_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ResearchSchedule:
    """Recurring research schedule configuration."""

    config_id: int
    niche: str
    id: Optional[int] = None
    frequency: str = ResearchScheduleFrequency.WEEKLY.value
    local_time: str = "09:00"  # HH:MM local format
    timezone_name: str = "UTC"
    is_enabled: bool = True
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_window_key: str = ""  # Dedup key, e.g. "2026-W42" or "2026-10-19"
    missed_runs_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchSchedule":
        valid_keys = {
            "id", "config_id", "niche", "frequency", "local_time",
            "timezone_name", "is_enabled", "last_run_at", "next_run_at",
            "last_window_key", "missed_runs_count", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class SnapshotComparisonResult:
    """Differential analysis between two completed research run snapshots."""

    run_a_id: int
    run_b_id: int
    niche: str
    id: Optional[int] = None
    run_a_date: str = ""
    run_b_date: str = ""
    newly_discovered_products: List[Dict[str, Any]] = field(default_factory=list)
    dropped_products: List[Dict[str, Any]] = field(default_factory=list)
    video_count_changes: List[Dict[str, Any]] = field(default_factory=list)
    score_changes: List[Dict[str, Any]] = field(default_factory=list)
    coverage_changes: List[Dict[str, Any]] = field(default_factory=list)
    newly_observed_channels: List[Dict[str, Any]] = field(default_factory=list)
    comparison_matrix: List[Dict[str, Any]] = field(default_factory=list)
    summary_notes: str = ""
    empirical_caution: str = (
        "Empirical Caution: Discrepancies between snapshots reflect differences observed within "
        "the executed query sample and date range. Changes do not represent platform-wide additions or removals."
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotComparisonResult":
        valid_keys = {
            "id", "run_a_id", "run_b_id", "niche", "run_a_date", "run_b_date",
            "newly_discovered_products", "dropped_products", "video_count_changes",
            "score_changes", "coverage_changes", "newly_observed_channels",
            "comparison_matrix", "summary_notes", "empirical_caution", "created_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
