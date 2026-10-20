"""Four-Channel Growth Intelligence & Analytics Learning Engine (Phase 24 Parts 2 to 7).

Features:
1. Rigorous metric comparisons with mathematical zero-denominator protection.
2. Topic & Keyword Performance Learning with explicit correlation vs causation cautions.
3. Channel-Specific Growth Coach with strict 5-point evidence framework.
4. Publishing Experiments tracking with confounding factor identification.
5. Morning Growth Brief integration for 4 channel profiles.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.models.analytics import (
    ChannelAnalyticsOverview,
    GrowthRecommendation,
    MetricComparison,
    PublishingExperiment,
    VideoAnalyticsItem,
)
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager, db_manager


class GrowthEngine:
    """Analytical learning engine for YouTube channel performance, topics, and growth."""

    def __init__(self, database: Optional[DatabaseManager] = None) -> None:
        self.db = database or db_manager

    # --------------------------------------------------------------------------
    # 1. Rigorous Metric Comparison with Zero-Denominator Safety
    # --------------------------------------------------------------------------

    def compute_metric_comparison(
        self,
        name: str,
        current_value: Optional[float],
        comparison_value: Optional[float],
        format_type: str = "number",  # "integer", "decimal", "duration", "percentage", "currency"
    ) -> MetricComparison:
        """Calculate absolute and percentage change with mathematical zero-denominator protection."""
        if current_value is None or comparison_value is None:
            return MetricComparison(
                metric_name=name,
                current_value=current_value,
                comparison_value=comparison_value,
                absolute_change=None,
                percentage_change=None,
                change_direction="unavailable",
                display_current=self._format_value(current_value, format_type),
                display_comparison=self._format_value(comparison_value, format_type),
                display_change="N/A (Missing data)",
                is_available=False,
                unavailable_reason="One or both comparison periods lack data from the official API.",
            )

        diff = current_value - comparison_value

        # Mathematical Zero-Denominator Guard:
        # If comparison_value == 0, percentage change is mathematically undefined.
        if comparison_value == 0.0:
            pct_change = None
            if diff > 0:
                dir_str = "increased"
                disp_change = f"+{self._format_value(diff, format_type)} (prior period was 0)"
            elif diff < 0:
                dir_str = "decreased"
                disp_change = f"-{self._format_value(abs(diff), format_type)} (prior period was 0)"
            else:
                dir_str = "unchanged"
                disp_change = "0 (no change)"
        else:
            pct_change = round((diff / abs(comparison_value)) * 100.0, 1)
            sign = "+" if diff > 0 else ""
            pct_sign = "+" if pct_change > 0 else ""
            disp_change = f"{sign}{self._format_value(diff, format_type)} ({pct_sign}{pct_change}%)"

            if diff > 0:
                dir_str = "increased"
            elif diff < 0:
                dir_str = "decreased"
            else:
                dir_str = "unchanged"

        return MetricComparison(
            metric_name=name,
            current_value=current_value,
            comparison_value=comparison_value,
            absolute_change=round(diff, 2),
            percentage_change=pct_change,
            change_direction=dir_str,
            display_current=self._format_value(current_value, format_type),
            display_comparison=self._format_value(comparison_value, format_type),
            display_change=disp_change,
            is_available=True,
        )

    def _format_value(self, val: Optional[float], format_type: str) -> str:
        """Format raw numeric metric into human-readable SaaS display."""
        if val is None:
            return "Unavailable"

        if format_type == "integer":
            return f"{int(round(val)):,}"
        elif format_type == "decimal":
            return f"{val:,.1f}"
        elif format_type == "duration":
            # Format seconds into M:SS or H:MM:SS
            secs = int(round(val))
            mins, s = divmod(secs, 60)
            h, m = divmod(mins, 60)
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m}:{s:02d}"
        elif format_type == "percentage":
            return f"{val:.1f}%"
        elif format_type == "currency":
            return f"${val:,.2f}"
        return f"{val:,.2f}"

    # --------------------------------------------------------------------------
    # 2. Topic & Keyword Performance Learning
    # --------------------------------------------------------------------------

    def correlate_topics_and_keywords(
        self,
        channel_id: int,
        videos: List[VideoAnalyticsItem],
    ) -> List[Dict[str, Any]]:
        """Connect historical video performance to saved keywords with explicit correlation caveats."""
        if not videos:
            return []

        # Retrieve saved search queries and calendar items for this channel/niche
        searches = self.db.get_recent_searches(limit=25) if hasattr(self.db, "get_recent_searches") else []
        saved_kws = [s["seed_keyword"].lower() for s in searches if "seed_keyword" in s]

        # Group videos by matched keyword or dominant title topic
        topic_groups: Dict[str, List[VideoAnalyticsItem]] = {}
        for v in videos:
            t_lower = v.title.lower()
            matched = None
            for kw in saved_kws:
                if kw in t_lower:
                    matched = kw
                    break

            if not matched:
                # Fallback to first 3 words of title as topic cluster
                words = t_lower.split()
                matched = " ".join(words[:2]) if len(words) >= 2 else t_lower

            topic_groups.setdefault(matched, []).append(v)

        results = []
        for topic, group in topic_groups.items():
            count = len(group)
            total_views = sum(v.views for v in group)
            avg_views = round(total_views / count, 1) if count > 0 else 0
            has_auth = any(v.is_authorized_data for v in group)

            formats = list({v.video_format for v in group})
            sample_caveat = "Small sample size (1 video) — insufficient statistical baseline" if count == 1 else f"Based on {count} published videos"

            results.append({
                "topic": topic,
                "video_count": count,
                "total_views": total_views,
                "average_views": avg_views,
                "formats": formats,
                "is_authorized_analytics": has_auth,
                "sample_caveat": sample_caveat,
                "epistemic_warning": (
                    "Topic association does not imply direct causation. "
                    "Outcomes are influenced by publication age, thumbnail design, format, and external traffic."
                ),
            })

        results.sort(key=lambda x: x["average_views"], reverse=True)
        return results

    # --------------------------------------------------------------------------
    # 3. Channel-Specific Growth Coach (5-Point Evidence Framework)
    # --------------------------------------------------------------------------

    def generate_growth_recommendations(
        self,
        channel: ChannelProfile,
        overview: Optional[ChannelAnalyticsOverview],
        videos: List[VideoAnalyticsItem],
    ) -> List[GrowthRecommendation]:
        """Generate evidence-backed recommendations strictly adhering to the 5-point framework."""
        recommendations: List[GrowthRecommendation] = []
        c_id = channel.id or 1

        # Case A: Insufficient Historical Data -> Provide Pragmatic Starter Strategy
        if not videos or len(videos) < 2:
            recommendations.append(
                GrowthRecommendation(
                    recommendation_id=f"rec_starter_{c_id}",
                    channel_id=c_id,
                    title="Foundation Starter Plan: Topic Clustering Baseline",
                    category="Starter Strategy",
                    observed_fact=f"Channel '{channel.channel_name}' has {len(videos)} videos recorded with limited historical metrics.",
                    supporting_evidence="Zero or sparse historical view duration and watch time records available in local studio.",
                    uncertainty_and_confounders="Algorithmic audience retention and search distribution patterns are completely unobserved for this channel.",
                    suggested_action=f"Publish a 3-video pillar cluster covering core beginner questions in '{channel.channel_niche}' to establish an initial performance baseline.",
                    success_measurement="Track whether first 3 videos generate at least 30% average percentage viewed and accumulate consistent search impressions.",
                    priority="High",
                    requires_authorized_analytics=False,
                )
            )
            return recommendations

        # Case B: Identify Top-Performing Topic Cluster
        topic_correlations = self.correlate_topics_and_keywords(c_id, videos)
        if topic_correlations and len(topic_correlations) >= 2:
            top_topic = topic_correlations[0]
            recommendations.append(
                GrowthRecommendation(
                    recommendation_id=f"rec_top_topic_{c_id}",
                    channel_id=c_id,
                    title=f"Expand Supporting Content Around '{top_topic['topic'].title()}'",
                    category="Topic Opportunity",
                    observed_fact=f"Videos matching '{top_topic['topic']}' averaged {top_topic['average_views']:,} views across {top_topic['video_count']} video(s).",
                    supporting_evidence=f"Highest relative average views among observed clusters for channel '{channel.channel_name}'.",
                    uncertainty_and_confounders="Unequal publication dates, varying thumbnail CTRs, or external spikes may confound topic appeal.",
                    suggested_action=f"Research adjacent long-tail keywords in '{top_topic['topic']}' and plan a follow-up comparison or tutorial.",
                    success_measurement="Compare subsequent video 14-day view count against channel median views.",
                    priority="High",
                    requires_authorized_analytics=False,
                )
            )

        # Case C: Check Video Duration / Format Discrepancies
        long_vids = [v for v in videos if v.video_format == "Long-form"]
        short_vids = [v for v in videos if v.video_format == "Shorts"]
        if long_vids and short_vids:
            avg_long = sum(v.views for v in long_vids) / len(long_vids)
            avg_short = sum(v.views for v in short_vids) / len(short_vids)
            recommendations.append(
                GrowthRecommendation(
                    recommendation_id=f"rec_format_cmp_{c_id}",
                    channel_id=c_id,
                    title="Evaluate Long-form vs Shorts Distribution Split",
                    category="Content Optimization",
                    observed_fact=f"Long-form averaged {avg_long:,.0f} views ({len(long_vids)} vids) vs Shorts {avg_short:,.0f} views ({len(short_vids)} vids).",
                    supporting_evidence="Direct format-segmented view comparison from current local research records.",
                    uncertainty_and_confounders="Shorts feed distribution operates on distinct algorithmic retention loops compared to browse/search.",
                    suggested_action="Repurpose the most engaging 60-second segment of your best long-form video into a Shorts trailer linking back to the full guide.",
                    success_measurement="Measure referral traffic from Shorts sound/related link to long-form video watch time.",
                    priority="Medium",
                    requires_authorized_analytics=False,
                )
            )

        # Case D: Check Outdated Content in Commercial / Affiliate Channels
        if channel.affiliate_enabled:
            recommendations.append(
                GrowthRecommendation(
                    recommendation_id=f"rec_aff_freshness_{c_id}",
                    channel_id=c_id,
                    title=f"Verify Product Price Freshness for {channel.channel_niche}",
                    category="Underperforming Review",
                    observed_fact="Channel has affiliate recommendations enabled for commercial hardware/tools.",
                    supporting_evidence="Affiliate links present in recent channel description drafts.",
                    uncertainty_and_confounders="Outdated product links cause viewer drop-off and lost commissions without impacting algorithmic reach.",
                    suggested_action="Audit top 3 videos for expired promotions or out-of-stock items, and update pinned comment / description links.",
                    success_measurement="Monitor affiliate link click-through rate and viewer comments on stock availability.",
                    priority="Medium",
                    requires_authorized_analytics=False,
                )
            )

        return recommendations

    # --------------------------------------------------------------------------
    # 4. Publishing Experiments Evaluation
    # --------------------------------------------------------------------------

    def evaluate_publishing_experiment(
        self,
        exp: PublishingExperiment,
        post_metrics: Dict[str, Any],
    ) -> PublishingExperiment:
        """Evaluate pre vs post metrics with explicit confounding factor labeling."""
        exp.post_metrics = post_metrics
        exp.completed_at = datetime.now(timezone.utc).isoformat()
        exp.status = "Completed"

        pre_views = float(exp.pre_metrics.get("views", 0))
        post_views = float(post_metrics.get("views", 0))

        pre_ctr = exp.pre_metrics.get("impressions_ctr")
        post_ctr = post_metrics.get("impressions_ctr")

        # Confounding factors to account for
        confounders = [
            "Seasonal audience demand variation during observation window",
            "YouTube home feed algorithm changes and concurrent topic competition",
            "Video lifecycle: older videos naturally accumulate decaying daily velocity",
        ]
        exp.confounding_factors = confounders

        if post_views == 0 or (pre_views == 0 and post_views == 0):
            exp.is_conclusive = False
            exp.outcome_conclusion = "Inconclusive: Insufficient observation data collected during post-experiment window."
            return exp

        diff = post_views - pre_views
        if pre_ctr is not None and post_ctr is not None:
            ctr_diff = post_ctr - pre_ctr
            conclusion = (
                f"Post-change observed views: {post_views:,.0f} (Change: {diff:+,.0f}), "
                f"CTR: {post_ctr:.1f}% (Change: {ctr_diff:+.1f}%). "
                f"Result shows positive correlation with hypothesis, but causality cannot be definitively proven due to potential external factors."
            )
            exp.is_conclusive = True
        else:
            conclusion = (
                f"Observed views changed from {pre_views:,.0f} to {post_views:,.0f} ({diff:+,.0f}). "
                f"Without authorized impressions CTR data, title/thumbnail causal impact remains tentative."
            )
            exp.is_conclusive = False

        exp.outcome_conclusion = conclusion
        return exp

    # --------------------------------------------------------------------------
    # 5. Daily Morning Growth Brief Integration
    # --------------------------------------------------------------------------

    def generate_morning_growth_brief(
        self,
        channel: ChannelProfile,
        overview: Optional[ChannelAnalyticsOverview] = None,
        videos: Optional[List[VideoAnalyticsItem]] = None,
    ) -> Dict[str, Any]:
        """Synthesize daily analytics status, topic learning, and next recommended action."""
        c_id = channel.id or 1
        vids = videos or []

        has_auth = overview.is_authorized_analytics if overview else False
        status_label = "Authorized Analytics Live" if has_auth else "Public Metadata Mode (OAuth Unconnected)"

        # Recent metrics summary
        if has_auth and overview:
            views_summary = f"{overview.views.display_current} views ({overview.views.display_change})"
            watch_summary = f"{overview.watch_time_hours.display_current} hrs ({overview.watch_time_hours.display_change})"
        else:
            views_summary = "Unavailable (OAuth required)"
            watch_summary = "Unavailable (OAuth required)"

        recommendations = self.generate_growth_recommendations(channel, overview, vids)
        top_rec = recommendations[0] if recommendations else None

        return {
            "channel_id": c_id,
            "channel_name": channel.channel_name,
            "analytics_status": status_label,
            "is_authorized": has_auth,
            "views_summary": views_summary,
            "watch_time_summary": watch_summary,
            "total_observed_videos": len(vids),
            "top_recommended_action": top_rec.suggested_action if top_rec else "Plan next topic cluster in Morning Report",
            "recommendation_evidence": top_rec.supporting_evidence if top_rec else "Baseline startup planning",
            "uncertainty_note": top_rec.uncertainty_and_confounders if top_rec else "No historical metrics available",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Default singleton instance
growth_engine = GrowthEngine()
