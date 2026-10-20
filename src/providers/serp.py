import os
import re
import statistics
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.models.serp import (
    CompetitorVideoItem,
    KeywordSerpAnalysis,
    KeywordValidationSummary,
    TitlePatternAnalysis,
)


@dataclass
class SerpMetrics:
    """Metrics container for a keyword.

    If is_available is False, status_message explains that no verified provider is connected.
    """

    keyword: str
    is_available: bool = False
    status_message: str = "Not available — no verified data source connected"
    search_volume: Optional[int] = None
    competition_score: Optional[float] = None
    average_views: Optional[int] = None
    video_count: Optional[int] = None
    source_name: Optional[str] = None
    collected_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseSerpMetricsProvider(ABC):
    """Abstract interface for verified search and SERP metrics providers."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True only if a valid, authenticated, verified API connection is established."""
        pass

    @abstractmethod
    def get_metrics(self, keyword: str, language: str = "en", country: str = "US") -> SerpMetrics:
        """Retrieve verified metrics for a keyword, or return honest unavailable status."""
        pass


class UnconnectedSerpMetricsProvider(BaseSerpMetricsProvider):
    """Default provider representing the unconfigured/unconnected state.

    Always reports honest 'Not available — no verified data source connected'
    to prevent misleading the user with synthetic volume/competition numbers.
    """

    def is_connected(self) -> bool:
        return False

    def get_metrics(self, keyword: str, language: str = "en", country: str = "US") -> SerpMetrics:
        return SerpMetrics(
            keyword=keyword,
            is_available=False,
            status_message="Not available — no verified data source connected",
            search_volume=None,
            competition_score=None,
            average_views=None,
            video_count=None,
            source_name="None (Local-first offline mode)",
            collected_at=datetime.now(timezone.utc).isoformat(),
        )


def parse_iso_duration(duration_str: str) -> Tuple[str, int]:
    """Parse ISO 8601 duration string (e.g. PT14M22S, PT1H2M10S, PT45S) into readable format and seconds.

    Returns:
        Tuple of (formatted_duration, total_seconds), e.g. ("14:22", 862) or ("1:02:10", 3730).
    """
    if not duration_str or not isinstance(duration_str, str):
        return ("0:00", 0)

    pattern = re.compile(
        r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
    )
    match = pattern.match(duration_str.strip())
    if not match:
        return ("0:00", 0)

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)

    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds

    if hours > 0 or days > 0:
        total_hours = days * 24 + hours
        formatted = f"{total_hours}:{minutes:02d}:{seconds:02d}"
    else:
        formatted = f"{minutes}:{seconds:02d}"

    return (formatted, total_seconds)


def calculate_relative_age(publish_date_iso: str) -> Tuple[str, int]:
    """Calculate human-readable relative age and elapsed days from an ISO publish date.

    Returns:
        Tuple of (relative_age_text, days_elapsed).
    """
    if not publish_date_iso:
        return ("Unknown", 0)

    try:
        clean_date = publish_date_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = max(0, (now - dt).days)

        if days == 0:
            return ("Today", 0)
        elif days == 1:
            return ("1 day ago", 1)
        elif days < 30:
            return (f"{days} days ago", days)
        elif days < 365:
            months = max(1, days // 30)
            return (f"{months} {'month' if months == 1 else 'months'} ago", days)
        else:
            years = max(1, days // 365)
            return (f"{years} {'year' if years == 1 else 'years'} ago", days)
    except Exception:
        return ("Unknown", 0)


def calculate_opportunity_score(
    videos: List[CompetitorVideoItem],
) -> Tuple[float, str]:
    """Calculate an explainable Opportunity Score (0 to 100) and qualitative label.

    Opportunity Formula Components:
    1. Demand Factor (0-40 pts): Median view count of top ranking videos.
    2. Freshness & Content Gap (0-30 pts): Age of ranking content. Older videos indicate
       viewers have outdated options and new content can rank.
    3. Competition Accessibility (0-30 pts): Presence of videos with moderate view counts (<50k)
       proving non-monopoly creators can rank.

    Returns:
        Tuple of (score, label).
    """
    if not videos:
        return (50.0, "Moderate Opportunity")

    views = [v.view_count for v in videos]
    median_views = statistics.median(views) if views else 0

    # 1. Demand Factor (0-40)
    if median_views >= 200_000:
        demand_score = 40.0
    elif median_views >= 100_000:
        demand_score = 35.0
    elif median_views >= 50_000:
        demand_score = 30.0
    elif median_views >= 10_000:
        demand_score = 22.0
    elif median_views >= 2_000:
        demand_score = 15.0
    else:
        demand_score = 8.0

    # 2. Freshness & Content Gap (0-30)
    ages = []
    for v in videos:
        _, days = calculate_relative_age(v.publish_date)
        ages.append(days)

    avg_age = statistics.mean(ages) if ages else 0
    if avg_age >= 730:  # > 2 years old
        gap_score = 30.0
    elif avg_age >= 365:  # > 1 year old
        gap_score = 25.0
    elif avg_age >= 180:  # > 6 months old
        gap_score = 18.0
    elif avg_age <= 30 and median_views >= 50_000:  # Trending topic
        gap_score = 22.0
    else:
        gap_score = 12.0

    # 3. Competition Accessibility (0-30)
    accessible_videos = sum(1 for v in views if v < 50_000)
    if accessible_videos >= 4:
        accessibility_score = 30.0
    elif accessible_videos >= 2:
        accessibility_score = 22.0
    elif accessible_videos >= 1:
        accessibility_score = 15.0
    else:
        # Check if mega channels dominate completely
        if all(v > 500_000 for v in views):
            accessibility_score = 5.0
        else:
            accessibility_score = 10.0

    total_score = round(demand_score + gap_score + accessibility_score, 1)
    total_score = max(0.0, min(100.0, total_score))

    if total_score >= 75.0:
        label = "High Opportunity (High demand & accessible competition)"
    elif total_score >= 50.0:
        label = "Moderate Opportunity (Consistent demand with established competition)"
    elif total_score >= 25.0:
        label = "Low-to-Moderate Opportunity (High competition saturation)"
    else:
        label = "Challenging / Saturated (Extreme competition or low search demand)"

    return (total_score, label)


def calculate_view_count_distribution(views: List[int]) -> Dict[str, Any]:
    """Calculate view count distribution statistics with sample size."""
    if not views:
        return {
            "min": 0,
            "median": 0.0,
            "average": 0.0,
            "max": 0,
            "p25": 0,
            "p75": 0,
            "sample_size": 0,
        }
    sorted_views = sorted(views)
    n = len(sorted_views)
    return {
        "min": sorted_views[0],
        "median": float(statistics.median(sorted_views)),
        "average": round(float(statistics.mean(sorted_views)), 1),
        "max": sorted_views[-1],
        "p25": sorted_views[n // 4],
        "p75": sorted_views[(n * 3) // 4],
        "sample_size": n,
    }


def calculate_age_distribution(ages_in_days: List[int]) -> Dict[str, int]:
    """Calculate publication date distribution across time brackets."""
    return {
        "recent_under_30d": sum(1 for a in ages_in_days if a < 30),
        "moderate_30_to_180d": sum(1 for a in ages_in_days if 30 <= a < 180),
        "established_180_to_365d": sum(1 for a in ages_in_days if 180 <= a < 365),
        "legacy_over_365d": sum(1 for a in ages_in_days if a >= 365),
    }


def extract_common_title_phrases(
    titles: List[str], seed_keyword: str, max_phrases: int = 10
) -> List[Tuple[str, int]]:
    """Extract frequent 2-word and 3-word n-grams observed across competitor titles."""
    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "is", "it", "this", "that", "you", "your", "i", "my", "how", "what", "which",
        "video", "youtube", "2024", "2025", "2026", "bangla", "tutorial",
    }
    phrases: List[str] = []
    seed_lower = seed_keyword.lower().strip()

    for t in titles:
        clean = re.sub(r"[^\w\s]", " ", t.lower())
        words = [w for w in clean.split() if len(w) > 1 and w not in stopwords]
        # 2-grams
        for i in range(len(words) - 1):
            ngram = f"{words[i]} {words[i+1]}"
            if ngram != seed_lower and len(ngram) > 4:
                phrases.append(ngram)
        # 3-grams
        for i in range(len(words) - 2):
            ngram = f"{words[i]} {words[i+1]} {words[i+2]}"
            if ngram != seed_lower and len(ngram) > 6:
                phrases.append(ngram)

    return Counter(phrases).most_common(max_phrases)


def analyze_title_patterns(
    titles: List[str],
    keyword: str,
    target_audience: str = "General Audience",
    preferred_format: str = "All Formats",
) -> TitlePatternAnalysis:
    """Analyze recurring title structures and generate original suggested content angles (Step 8)."""
    if not titles:
        return TitlePatternAnalysis(
            sample_size=0,
            target_audience=target_audience,
            preferred_format=preferred_format,
        )

    patterns = {
        "Best & Top Lists": re.compile(r"\b(best|top\s*\d+|\d+\s*best)\b", re.IGNORECASE),
        "Reviews & Tests": re.compile(r"\b(review|reviewed|test|unboxing|hands\s*on)\b", re.IGNORECASE),
        "Comparisons (VS)": re.compile(r"\b(vs|versus|compared|comparison|or)\b", re.IGNORECASE),
        "How-To & Guides": re.compile(r"\b(how\s+to|tutorial|guide|walkthrough|step\s+by\s+step|explained)\b", re.IGNORECASE),
        "Problem Solving": re.compile(r"\b(fix|solve|problem|troubleshoot|mistake|avoid|error|wrong)\b", re.IGNORECASE),
        "Audience Specific": re.compile(r"\b(for\s+beginners|for\s+pros|for\s+students|for\s+dummies|for\s+starters)\b", re.IGNORECASE),
        "Year Specific": re.compile(r"\b(202[0-9]|2030)\b", re.IGNORECASE),
    }

    distribution: Dict[str, int] = {}
    detected: List[Dict[str, Any]] = []
    total = len(titles)

    for name, regex in patterns.items():
        matched_count = sum(1 for t in titles if regex.search(t))
        distribution[name] = matched_count
        pct = round((matched_count / total) * 100, 1) if total > 0 else 0.0
        detected.append({
            "format": name,
            "count": matched_count,
            "percentage": pct,
            "sample_size": total,
        })

    # Generate original title ideas based on observed patterns without copying competitor titles
    current_year = datetime.now(timezone.utc).year
    clean_k = keyword.strip().title()

    suggestions = [
        f"How to Master {clean_k}: Complete Step-by-Step Guide",
        f"Top 5 {clean_k} Options Tested & Reviewed ({current_year})",
        f"{clean_k} vs Common Alternatives: Which Is Actually Worth It?",
        f"The Truth About {clean_k}: 3 Mistakes Beginners Make",
        f"Best {clean_k} for {target_audience}: Full Breakdown",
        f"Why You Might Be Using {clean_k} Wrong (And How to Fix It)",
    ]

    return TitlePatternAnalysis(
        format_distribution=distribution,
        sample_size=total,
        detected_patterns=detected,
        suggested_title_ideas=suggestions,
        target_audience=target_audience,
        preferred_format=preferred_format,
    )


def generate_keyword_validation_summary(
    keyword: str,
    videos: List[CompetitorVideoItem],
) -> KeywordValidationSummary:
    """Generate evidence-based keyword validation summary fulfilling Step 7."""
    total = len(videos)
    if total == 0:
        return KeywordValidationSummary(
            keyword=keyword,
            total_videos=0,
            missing_data_limitations=["No video metadata available from provider."],
        )

    # 1. Metadata coverage
    views_present = sum(1 for v in videos if v.view_count > 0)
    likes_present = sum(1 for v in videos if v.like_count is not None)
    duration_present = sum(1 for v in videos if v.duration and v.duration != "0:00")
    tags_present = sum(1 for v in videos if v.tags)
    desc_present = sum(1 for v in videos if v.description)

    coverage = {
        "view_count_pct": round((views_present / total) * 100, 1),
        "like_count_pct": round((likes_present / total) * 100, 1),
        "duration_pct": round((duration_present / total) * 100, 1),
        "tags_pct": round((tags_present / total) * 100, 1),
        "description_pct": round((desc_present / total) * 100, 1),
    }

    # 2. Unique channels
    unique_channels = len(set(v.channel_id for v in videos if v.channel_id))

    # 3. View count distribution
    view_dist = calculate_view_count_distribution([v.view_count for v in videos])

    # 4. Age distribution
    ages = [calculate_relative_age(v.publish_date)[1] for v in videos]
    age_dist = calculate_age_distribution(ages)

    # 5. Common title phrases
    common_phrases = extract_common_title_phrases([v.title for v in videos], keyword)

    # 6. Potential content angles
    angles: List[Dict[str, Any]] = []
    if age_dist["legacy_over_365d"] >= (total * 0.5):
        angles.append({
            "angle": "Fresh Modern Guide",
            "rationale": f"{age_dist['legacy_over_365d']} of {total} top videos are over 1 year old. Modern testing will appeal to current viewers.",
        })
    if any(v.view_count < 50000 for v in videos):
        angles.append({
            "angle": "Niche & Beginner Focus",
            "rationale": "Lower-view-count videos successfully rank, indicating room for focused, accessible creator coverage.",
        })
    if any("vs" in v.title.lower() for v in videos):
        angles.append({
            "angle": "Direct Head-to-Head Comparison",
            "rationale": "Comparison queries show strong viewer intent in this search space.",
        })
    if not angles:
        angles.append({
            "angle": "Comprehensive Walkthrough",
            "rationale": "Sustained view counts indicate ongoing audience search demand.",
        })

    # 7. Limitations
    limitations = [
        "Sample consists only of top-ranking results returned by the provider.",
        "Search results may vary by geographic region, language, and retrieval time.",
        "Analytical suggestions are evidence-based observations, not official ranking guarantees.",
    ]

    return KeywordValidationSummary(
        keyword=keyword,
        total_videos=total,
        metadata_coverage=coverage,
        unique_channels_count=unique_channels,
        view_count_distribution=view_dist,
        age_distribution=age_dist,
        common_title_phrases=common_phrases,
        potential_content_angles=angles,
        missing_data_limitations=limitations,
    )


class YouTubeDataApiSerpProvider(BaseSerpMetricsProvider):
    """Verified YouTube Data API v3 integration for SERP and competitor video inspection.

    Batch Optimization:
    - Search endpoint (100 units): retrieves up to 50 video IDs.
    - Videos endpoint (1 unit): batched retrieval of snippet, statistics, and contentDetails.
    - Total cost = 101 quota units per search.
    - Cached searches = 0 quota units.
    """

    SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
    VERIFY_ENDPOINT = "https://www.googleapis.com/youtube/v3/videoCategories"

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_manager: Optional[Any] = None,
        session: Optional[requests.Session] = None,
        timeout: float = 12.0,
    ) -> None:
        self._explicit_key = api_key
        self.db_manager = db_manager
        self.session = session or requests.Session()
        self.timeout = timeout

    def get_api_key(self) -> Optional[str]:
        """Resolve API key from explicit init, database settings, or environment variable."""
        if self._explicit_key:
            return self._explicit_key.strip()
        if self.db_manager:
            stored = self.db_manager.get_setting("youtube_api_key")
            if stored and stored.strip():
                return stored.strip()
        env_key = os.getenv("YOUTUBE_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()
        return None

    def is_connected(self) -> bool:
        """Return True if an API key is available."""
        key = self.get_api_key()
        return bool(key and len(key) > 5)

    def verify_api_key(self, api_key: str) -> Tuple[bool, str]:
        """Verify an API key by making a lightweight 1-quota request to YouTube API v3."""
        clean_key = (api_key or "").strip()
        if not clean_key:
            return (False, "API key cannot be empty.")

        params = {
            "part": "snippet",
            "regionCode": "US",
            "key": clean_key,
        }
        try:
            resp = self.session.get(
                self.VERIFY_ENDPOINT, params=params, timeout=self.timeout
            )
            if resp.status_code == 200:
                return (
                    True,
                    "API key successfully verified. Connected to YouTube Data API v3.",
                )
            elif resp.status_code in (400, 403):
                try:
                    err_info = resp.json().get("error", {})
                    msg = err_info.get("message", "API key invalid or unauthorized.")
                except Exception:
                    msg = f"HTTP {resp.status_code}: Unauthorized"
                return (False, f"Verification failed: {msg}")
            else:
                return (
                    False,
                    f"Verification returned unexpected HTTP status {resp.status_code}.",
                )
        except requests.exceptions.RequestException as ex:
            return (False, f"Network error during verification: {str(ex)}")

    def analyze_keyword(
        self,
        keyword: str,
        language: str = "en",
        country: str = "US",
        max_results: int = 10,
        order: str = "relevance",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        video_category_id: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl_seconds: int = 86400,
        target_audience: str = "General Audience",
        preferred_format: str = "All Formats",
    ) -> KeywordSerpAnalysis:
        """Fetch and analyze top ranking competitor videos for a search keyword."""
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            return KeywordSerpAnalysis(
                keyword="",
                language=language,
                country=country,
                status_message="Keyword cannot be empty.",
            )

        # 1. Check local SERP cache
        if use_cache and self.db_manager:
            cached_data = self.db_manager.get_cached_serp(
                clean_keyword, language, country, max_age_seconds=cache_ttl_seconds
            )
            if cached_data:
                videos = [
                    CompetitorVideoItem(**v)
                    for v in cached_data.get("videos", [])
                ]
                top_tags = [
                    (t[0], int(t[1]))
                    for t in cached_data.get("top_tags", [])
                    if isinstance(t, (list, tuple)) and len(t) >= 2
                ]

                # Reconstruct validation summary & title analysis if present
                val_data = cached_data.get("validation_summary")
                if val_data and isinstance(val_data, dict):
                    val_summary = KeywordValidationSummary(**val_data)
                else:
                    val_summary = generate_keyword_validation_summary(clean_keyword, videos)

                t_data = cached_data.get("title_analysis")
                if t_data and isinstance(t_data, dict):
                    title_analysis = TitlePatternAnalysis(**t_data)
                else:
                    title_analysis = analyze_title_patterns(
                        [v.title for v in videos], clean_keyword, target_audience, preferred_format
                    )

                unique_ch = int(
                    cached_data.get(
                        "unique_channels_count",
                        len(set(v.channel_id for v in videos if v.channel_id)),
                    )
                )

                analysis = KeywordSerpAnalysis(
                    keyword=clean_keyword,
                    language=cached_data.get("language", language),
                    country=cached_data.get("country", country),
                    videos=videos,
                    total_videos_analyzed=cached_data.get(
                        "total_videos_analyzed", len(videos)
                    ),
                    average_views=float(cached_data.get("average_views", 0.0)),
                    median_views=float(cached_data.get("median_views", 0.0)),
                    min_views=int(cached_data.get("min_views", 0)),
                    max_views=int(cached_data.get("max_views", 0)),
                    newest_video_days=int(cached_data.get("newest_video_days", 0)),
                    median_video_age_days=float(cached_data.get("median_video_age_days", 0.0)),
                    unique_channels_count=unique_ch,
                    avg_daily_views=float(cached_data.get("avg_daily_views", 0.0)),
                    opportunity_score=float(
                        cached_data.get("opportunity_score", 50.0)
                    ),
                    opportunity_label=cached_data.get(
                        "opportunity_label", "Moderate Opportunity"
                    ),
                    top_tags=top_tags,
                    validation_summary=val_summary,
                    title_analysis=title_analysis,
                    is_cached=True,
                    fetched_at=cached_data.get(
                        "fetched_at", datetime.now(timezone.utc).isoformat()
                    ),
                    status_message="Loaded from local SERP cache (0 quota units used)",
                )
                return analysis

        # 2. Check API key
        key = self.get_api_key()
        if not key:
            return KeywordSerpAnalysis(
                keyword=clean_keyword,
                language=language,
                country=country,
                status_message="Not connected — YouTube Data API v3 key required in Settings or YOUTUBE_API_KEY environment variable.",
            )

        # 3. Check daily quota limits
        if self.db_manager:
            daily_used = self.db_manager.get_daily_quota_used()
            if daily_used >= 10000:
                return KeywordSerpAnalysis(
                    keyword=clean_keyword,
                    language=language,
                    country=country,
                    status_message=f"Daily API quota limit (10,000 units) reached ({daily_used} used today). Requests paused to prevent overages.",
                )

        # 4. Search endpoint (100 quota units)
        search_params: Dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "q": clean_keyword,
            "maxResults": max(1, min(max_results, 50)),
            "relevanceLanguage": language,
            "regionCode": country,
            "key": key,
        }
        if order and order in ("relevance", "viewCount", "date", "rating", "title"):
            search_params["order"] = order
        if published_after:
            search_params["publishedAfter"] = published_after
        if published_before:
            search_params["publishedBefore"] = published_before
        if video_category_id:
            search_params["videoCategoryId"] = video_category_id

        try:
            search_resp = self.session.get(
                self.SEARCH_ENDPOINT, params=search_params, timeout=self.timeout
            )
            if search_resp.status_code == 403:
                try:
                    err_msg = search_resp.json().get("error", {}).get("message", "Quota exceeded or forbidden.")
                except Exception:
                    err_msg = "YouTube Data API 403 Forbidden"
                return KeywordSerpAnalysis(
                    keyword=clean_keyword,
                    status_message=f"API Error: {err_msg}",
                )
            search_resp.raise_for_status()
            search_data = search_resp.json()
        except Exception as ex:
            return KeywordSerpAnalysis(
                keyword=clean_keyword,
                status_message=f"Search request failed: {str(ex)}",
            )

        video_items = search_data.get("items", [])
        video_ids = [
            it["id"]["videoId"]
            for it in video_items
            if isinstance(it.get("id"), dict) and "videoId" in it["id"]
        ]

        if not video_ids:
            return KeywordSerpAnalysis(
                keyword=clean_keyword,
                language=language,
                country=country,
                status_message="No matching videos found on YouTube for this keyword.",
            )

        # 5. Batched Videos endpoint (1 quota unit)
        videos_params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": key,
        }

        try:
            videos_resp = self.session.get(
                self.VIDEOS_ENDPOINT, params=videos_params, timeout=self.timeout
            )
            videos_resp.raise_for_status()
            videos_data = videos_resp.json()
        except Exception as ex:
            return KeywordSerpAnalysis(
                keyword=clean_keyword,
                status_message=f"Video details request failed: {str(ex)}",
            )

        # Record quota consumption: 100 + 1 = 101 units
        if self.db_manager:
            self.db_manager.record_quota_usage(101)

        # Index video details by ID
        details_by_id = {
            item["id"]: item for item in videos_data.get("items", []) if "id" in item
        }

        parsed_videos: List[CompetitorVideoItem] = []
        all_tags: List[str] = []
        newest_days = 99999

        for rank, vid in enumerate(video_ids, start=1):
            detail = details_by_id.get(vid)
            if not detail:
                continue

            snippet = detail.get("snippet", {})
            stats = detail.get("statistics", {})
            content = detail.get("contentDetails", {})

            title = snippet.get("title", "")
            channel_id = snippet.get("channelId", "")
            channel_title = snippet.get("channelTitle", "")
            publish_date = snippet.get("publishedAt", "")
            description = snippet.get("description", "")
            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats["likeCount"]) if "likeCount" in stats else None
            comment_count = (
                int(stats["commentCount"]) if "commentCount" in stats else None
            )

            raw_duration = content.get("duration", "")
            duration_str, _ = parse_iso_duration(raw_duration)

            tags = snippet.get("tags", [])
            if tags:
                all_tags.extend(tags)

            thumbs = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("medium", {}).get("url")
                or thumbs.get("default", {}).get("url", "")
            )

            rel_age, days_elapsed = calculate_relative_age(publish_date)
            if days_elapsed < newest_days:
                newest_days = days_elapsed

            daily_v = round(view_count / max(1, days_elapsed), 1)

            parsed_videos.append(
                CompetitorVideoItem(
                    video_id=vid,
                    title=title,
                    channel_id=channel_id,
                    channel_title=channel_title,
                    publish_date=publish_date,
                    view_count=view_count,
                    like_count=like_count,
                    comment_count=comment_count,
                    duration=duration_str,
                    tags=tags,
                    thumbnail_url=thumb_url,
                    description=description,
                    rank=rank,
                    relative_age=rel_age,
                    daily_views=daily_v,
                    provider="YouTube Data API v3",
                    search_query=clean_keyword,
                )
            )

        if not parsed_videos:
            return KeywordSerpAnalysis(
                keyword=clean_keyword,
                status_message="No video details could be retrieved.",
            )

        # 6. Aggregations, Metrics & Validation Summary
        views = [v.view_count for v in parsed_videos]
        avg_views = round(statistics.mean(views), 1)
        med_views = round(float(statistics.median(views)), 1)
        min_v = min(views)
        max_v = max(views)

        ages = [calculate_relative_age(v.publish_date)[1] for v in parsed_videos]
        median_age = float(statistics.median(ages)) if ages else 0.0
        unique_ch = len(set(v.channel_id for v in parsed_videos if v.channel_id))
        avg_daily = round(statistics.mean([v.daily_views for v in parsed_videos]), 1) if parsed_videos else 0.0

        # Top tags frequency counter
        tag_counts = Counter(all_tags).most_common(20)

        # Opportunity Score
        opp_score, opp_label = calculate_opportunity_score(parsed_videos)

        # Validation Summary (Step 7)
        val_summary = generate_keyword_validation_summary(clean_keyword, parsed_videos)

        # Title Pattern Analysis (Step 8)
        title_analysis = analyze_title_patterns(
            [v.title for v in parsed_videos],
            clean_keyword,
            target_audience=target_audience,
            preferred_format=preferred_format,
        )

        analysis = KeywordSerpAnalysis(
            keyword=clean_keyword,
            language=language,
            country=country,
            videos=parsed_videos,
            total_videos_analyzed=len(parsed_videos),
            average_views=avg_views,
            median_views=med_views,
            min_views=min_v,
            max_views=max_v,
            newest_video_days=newest_days if newest_days != 99999 else 0,
            median_video_age_days=median_age,
            unique_channels_count=unique_ch,
            avg_daily_views=avg_daily,
            opportunity_score=opp_score,
            opportunity_label=opp_label,
            top_tags=tag_counts,
            validation_summary=val_summary,
            title_analysis=title_analysis,
            is_cached=False,
            status_message=f"Retrieved {len(parsed_videos)} live ranking videos (101 quota units used)",
        )

        # 7. Store in SQLite cache
        if self.db_manager:
            try:
                self.db_manager.set_cached_serp(
                    clean_keyword, language, country, analysis.to_dict()
                )
            except Exception:
                pass

        return analysis

    def get_metrics(
        self, keyword: str, language: str = "en", country: str = "US"
    ) -> SerpMetrics:
        """Provide verified metrics adhering strictly to zero fabricated data principles."""
        if not self.is_connected():
            return SerpMetrics(
                keyword=keyword,
                is_available=False,
                status_message="Not available — YouTube Data API v3 not configured",
                source_name="None (Local-first offline mode)",
            )

        analysis = self.analyze_keyword(keyword, language, country)
        if analysis.total_videos_analyzed == 0:
            return SerpMetrics(
                keyword=keyword,
                is_available=False,
                status_message=analysis.status_message,
                source_name="YouTube Data API v3",
            )

        return SerpMetrics(
            keyword=keyword,
            is_available=True,
            status_message="Verified from YouTube Data API v3",
            search_volume=None,  # Not provided by YouTube Data API v3
            competition_score=round(100.0 - analysis.opportunity_score, 1),
            average_views=int(analysis.average_views),
            video_count=analysis.total_videos_analyzed,
            source_name="YouTube Data API v3",
            collected_at=analysis.fetched_at,
        )


default_serp_provider = UnconnectedSerpMetricsProvider()

