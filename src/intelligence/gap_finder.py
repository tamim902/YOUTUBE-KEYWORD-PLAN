"""Rolling 60-Day Video & Product Content Gap Finder (Phase 22 Part 7).

Accurately classifies YouTube content saturation across a rolling 60-day window
into one of four distinct states:
1. MATCHING RECENT VIDEOS FOUND (>= 4 videos)
2. FEW MATCHING RECENT VIDEOS FOUND (1-3 videos, sweet-spot content gap)
3. NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES (0 videos across >=2 queries)
4. INSUFFICIENT RESEARCH (API error, quota exhausted, or <2 queries)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.models.morning_report import GapFinderState


class GapFinder:
    """Detects recent 60-day YouTube content saturation and opportunity gaps."""

    def __init__(self, window_days: int = 60) -> None:
        self.window_days = window_days

    def get_rolling_window(self) -> Tuple[datetime, datetime, str]:
        """Compute the exact rolling UTC datetime window and readable string."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=self.window_days)
        window_str = f"{start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')} ({self.window_days} days)"
        return start, now, window_str

    def evaluate_gap_state(
        self,
        matching_videos_count: int,
        queries_executed: int,
        has_api_error: bool = False,
        quota_exhausted: bool = False,
    ) -> Tuple[GapFinderState, str]:
        """Classify research evidence into one of four deterministic gap states.
        
        Returns:
            (GapFinderState, explanation_text)
        """
        # State 4: Insufficient research
        if has_api_error or quota_exhausted or queries_executed < 2:
            reason = "API quota exhausted or network error occurred." if (has_api_error or quota_exhausted) else f"Only {queries_executed} query executed (minimum 2 queries required to confirm a gap)."
            return (
                GapFinderState.INSUFFICIENT_RESEARCH,
                f"INSUFFICIENT RESEARCH: {reason} Do not assume zero competition without verifying search results."
            )

        # State 3: Zero matching videos across valid queries
        if matching_videos_count == 0:
            return (
                GapFinderState.NO_MATCHING_VIDEOS_FOUND,
                f"NO MATCHING VIDEOS FOUND IN EXECUTED SEARCHES: 0 matching videos detected across {queries_executed} executed searches. Potential first-mover opportunity, but confirm audience search demand before recording."
            )

        # State 2: 1 to 3 matching videos (Sweet spot)
        if 1 <= matching_videos_count <= 3:
            return (
                GapFinderState.FEW_MATCHING_RECENT_VIDEOS_FOUND,
                f"FEW MATCHING RECENT VIDEOS FOUND: {matching_videos_count} matching recent video(s) found in {self.window_days}-day window. Excellent emerging content gap with verified search demand and low competition."
            )

        # State 1: 4 or more matching videos (High saturation)
        return (
            GapFinderState.MATCHING_RECENT_VIDEOS_FOUND,
            f"MATCHING RECENT VIDEOS FOUND: {matching_videos_count} recent videos found in {self.window_days}-day window. Topic is actively covered; differentiate with unique hands-on testing, comparison, or specific troubleshooting angle."
        )

    def generate_gap_report(
        self,
        topic: str,
        matching_video_titles: List[str],
        queries: List[str],
        has_api_error: bool = False,
    ) -> Dict[str, Any]:
        """Generate a complete transparent gap audit report for a topic."""
        start_dt, end_dt, window_str = self.get_rolling_window()
        count = len(matching_video_titles)
        q_count = len(queries)

        state, explanation = self.evaluate_gap_state(
            matching_videos_count=count,
            queries_executed=q_count,
            has_api_error=has_api_error,
        )

        return {
            "topic": topic,
            "gap_state": state.value,
            "explanation": explanation,
            "recent_videos_count": count,
            "queries_executed_count": q_count,
            "queries": queries,
            "sample_video_titles": matching_video_titles[:5],
            "exact_research_window": window_str,
            "start_iso": start_dt.isoformat(),
            "end_iso": end_dt.isoformat(),
        }


# Default singleton instance
gap_finder = GapFinder()
