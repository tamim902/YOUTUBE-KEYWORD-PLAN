"""Domain models for YouTube SERP analysis, competitor video inspection, and quota tracking."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompetitorVideoItem:
    """Represents a ranking YouTube video in search results."""

    video_id: str
    title: str
    channel_id: str
    channel_title: str
    publish_date: str
    view_count: int = 0
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    duration: str = ""
    tags: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    video_url: str = ""
    channel_url: str = ""
    description: str = ""
    rank: int = 1
    relative_age: str = ""
    daily_views: float = 0.0
    provider: str = "YouTube Data API v3"
    search_query: str = ""

    def __post_init__(self) -> None:
        if not self.video_url and self.video_id:
            self.video_url = f"https://www.youtube.com/watch?v={self.video_id}"
        if not self.channel_url and self.channel_id:
            self.channel_url = f"https://www.youtube.com/channel/{self.channel_id}"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class KeywordValidationSummary:
    """Evidence-based keyword validation summary (Step 7)."""

    keyword: str
    total_videos: int = 0
    metadata_coverage: Dict[str, float] = field(default_factory=dict)
    unique_channels_count: int = 0
    view_count_distribution: Dict[str, Any] = field(default_factory=dict)
    age_distribution: Dict[str, int] = field(default_factory=dict)
    common_title_phrases: List[Tuple[str, int]] = field(default_factory=list)
    potential_content_angles: List[Dict[str, Any]] = field(default_factory=list)
    missing_data_limitations: List[str] = field(default_factory=list)
    research_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TitlePatternAnalysis:
    """Analysis of recurring title patterns and original angle generator (Step 8)."""

    format_distribution: Dict[str, int] = field(default_factory=dict)
    sample_size: int = 0
    detected_patterns: List[Dict[str, Any]] = field(default_factory=list)
    suggested_title_ideas: List[str] = field(default_factory=list)
    target_audience: str = "General Audience"
    preferred_format: str = "All Formats"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KeywordSerpAnalysis:
    """Comprehensive competitor and SERP analysis for a search keyword."""

    keyword: str
    language: str = "en"
    country: str = "US"
    videos: List[CompetitorVideoItem] = field(default_factory=list)
    total_videos_analyzed: int = 0
    average_views: float = 0.0
    median_views: float = 0.0
    min_views: int = 0
    max_views: int = 0
    newest_video_days: int = 0
    median_video_age_days: float = 0.0
    unique_channels_count: int = 0
    avg_daily_views: float = 0.0
    opportunity_score: float = 50.0  # 0 to 100
    opportunity_label: str = "Moderate Opportunity"
    top_tags: List[Tuple[str, int]] = field(default_factory=list)
    validation_summary: Optional[KeywordValidationSummary] = None
    title_analysis: Optional[TitlePatternAnalysis] = None
    is_cached: bool = False
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status_message: str = "Success"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["videos"] = [
            v.to_dict() if hasattr(v, "to_dict") else v for v in self.videos
        ]
        if self.validation_summary and hasattr(self.validation_summary, "to_dict"):
            data["validation_summary"] = self.validation_summary.to_dict()
        if self.title_analysis and hasattr(self.title_analysis, "to_dict"):
            data["title_analysis"] = self.title_analysis.to_dict()
        return data


@dataclass
class QuotaUsageLog:
    """Daily API quota tracking entry."""

    date: str
    units_used: int = 0
    daily_limit: int = 10000

    @property
    def units_remaining(self) -> int:
        return max(0, self.daily_limit - self.units_used)

    @property
    def percentage_used(self) -> float:
        if self.daily_limit <= 0:
            return 100.0
        return min(100.0, (self.units_used / self.daily_limit) * 100.0)
