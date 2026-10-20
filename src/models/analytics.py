"""Domain models for Phase 24: YouTube Analytics & Four-Channel Growth Intelligence."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalyticsAuthStatus(str, Enum):
    """Authorization status for YouTube Analytics API."""
    NOT_CONNECTED = "NOT_CONNECTED"
    AUTHORIZED = "AUTHORIZED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


@dataclass
class ChannelOAuthCredentials:
    """OAuth 2.0 credentials for channel-owner YouTube Analytics."""
    channel_id: int
    channel_name: str
    client_id: str = ""
    client_secret: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
    ])
    auth_status: AnalyticsAuthStatus = AnalyticsAuthStatus.NOT_CONNECTED
    connected_at: Optional[str] = None
    last_refreshed_at: Optional[str] = None
    error_message: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if credentials are functionally authorized."""
        return self.auth_status == AnalyticsAuthStatus.AUTHORIZED and bool(self.access_token)

    def mask_secret(self) -> str:
        """Return masked client secret for secure UI display."""
        if not self.client_secret:
            return ""
        if len(self.client_secret) <= 6:
            return "******"
        return f"{self.client_secret[:3]}...{self.client_secret[-3:]}"

    def __repr__(self) -> str:
        """Never expose access tokens, refresh tokens, or secrets in representations."""
        return (
            f"ChannelOAuthCredentials(channel_id={self.channel_id}, "
            f"channel_name='{self.channel_name}', auth_status='{self.auth_status.value}', "
            f"has_access_token={bool(self.access_token)}, has_refresh_token={bool(self.refresh_token)})"
        )


@dataclass
class MetricComparison:
    """Rigorous comparison between a current period and a baseline comparison period."""
    metric_name: str
    current_value: Optional[float]
    comparison_value: Optional[float]
    absolute_change: Optional[float]
    percentage_change: Optional[float]  # None if comparison_value is 0 or unavailable
    change_direction: str  # "increased", "decreased", "unchanged", "unavailable"
    display_current: str
    display_comparison: str
    display_change: str
    is_available: bool = True
    unavailable_reason: Optional[str] = None


@dataclass
class ChannelAnalyticsOverview:
    """Aggregated channel analytics for a specified observation window with prior period comparisons."""
    channel_id: int
    channel_name: str
    date_range_start: str
    date_range_end: str
    comparison_start: str
    comparison_end: str
    views: MetricComparison
    watch_time_hours: MetricComparison
    avg_view_duration_seconds: MetricComparison
    subscribers_net: MetricComparison
    subscribers_gained: MetricComparison
    subscribers_lost: MetricComparison
    impressions: MetricComparison
    impressions_ctr: MetricComparison
    estimated_revenue: MetricComparison
    retrieved_at: str
    data_source: str = "YouTube Analytics API"
    is_authorized_analytics: bool = True
    missing_data_notes: List[str] = field(default_factory=list)


@dataclass
class VideoAnalyticsItem:
    """Performance metrics for an individual video, distinguishing public vs authorized data."""
    video_id: str
    channel_id: int
    title: str
    published_at: str
    video_format: str = "Long-form"  # "Long-form", "Shorts", "Unknown"
    views: int = 0
    watch_time_minutes: Optional[float] = None
    avg_view_duration_seconds: Optional[float] = None
    impressions: Optional[int] = None
    impressions_ctr: Optional[float] = None
    subscribers_gained: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    matched_keyword: Optional[str] = None
    matched_topic: Optional[str] = None
    is_authorized_data: bool = False
    observation_window_days: int = 0


@dataclass
class GrowthRecommendation:
    """5-point evidence-based growth recommendation."""
    recommendation_id: str
    channel_id: int
    title: str
    category: str  # "Topic Opportunity", "Content Optimization", "Cluster Expansion", "Underperforming Review", "Starter Strategy"
    observed_fact: str               # 1. What was observed
    supporting_evidence: str         # 2. Which data supports the recommendation
    uncertainty_and_confounders: str # 3. What remains uncertain
    suggested_action: str            # 4. Suggested action
    success_measurement: str         # 5. How success could be measured
    priority: str = "Medium"         # "High", "Medium", "Exploratory"
    requires_authorized_analytics: bool = False


@dataclass
class PublishingExperiment:
    """Manual publishing experiment record with before-and-after evaluation."""
    id: Optional[int]
    channel_id: int
    experiment_name: str
    video_id: str
    video_title: str
    experiment_type: str  # "Title Revision", "Thumbnail Revision", "Description Update", "Publication Time", "Video Format", "Content Structure"
    hypothesis: str
    status: str = "Running"  # "Running", "Completed", "Cancelled"
    started_at: str = ""
    completed_at: Optional[str] = None
    pre_metrics: Dict[str, Any] = field(default_factory=dict)
    post_metrics: Dict[str, Any] = field(default_factory=dict)
    outcome_conclusion: str = ""
    is_conclusive: bool = False
    confounding_factors: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
