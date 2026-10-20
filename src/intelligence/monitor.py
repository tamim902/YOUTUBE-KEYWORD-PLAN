"""Niche Research Monitoring, Snapshot Comparison & Change Detection Intelligence (Phase 15).

Provides:
- ResearchComparisonEngine: Differential analysis between research snapshots
- ChangeAlertDetector: Evidence-based in-app alert generation
- HistoricalAnalyticsAggregator: Longitudinal trend telemetry across runs
- ResearchSchedulerService: In-process scheduling and window-based deduplication
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.monitor import (
    AlertSeverity,
    MonitorAlert,
    MonitorRunStatus,
    ProductSnapshotItem,
    ResearchMonitorRun,
    ResearchSchedule,
    ResearchScheduleFrequency,
    SnapshotComparisonResult,
)

logger = logging.getLogger(__name__)


class ResearchComparisonEngine:
    """Computes differential analysis between two completed research run snapshots."""

    @staticmethod
    def compare_snapshots(
        run_a: ResearchMonitorRun,
        run_b: ResearchMonitorRun,
        snapshots_a: List[ProductSnapshotItem],
        snapshots_b: List[ProductSnapshotItem],
    ) -> SnapshotComparisonResult:
        """Compare two runs. Run A is the earlier baseline; Run B is the newer comparison.

        Handles:
        - Newly discovered products
        - Products that no longer appear (accounting for failed queries)
        - Matching video count deltas
        - Score shifts
        - Channel discovery
        - Coverage differences
        """
        map_a = {p.product_name.lower().strip(): p for p in snapshots_a}
        map_b = {p.product_name.lower().strip(): p for p in snapshots_b}

        failed_queries_b = {
            f.get("query", "").lower() for f in (run_b.failed_query_list or [])
        }

        newly_discovered: List[Dict[str, Any]] = []
        dropped: List[Dict[str, Any]] = []
        video_changes: List[Dict[str, Any]] = []
        score_changes: List[Dict[str, Any]] = []
        coverage_changes: List[Dict[str, Any]] = []
        matrix_rows: List[Dict[str, Any]] = []

        all_channels_a: Set[str] = set()
        for p in snapshots_a:
            all_channels_a.update(p.observed_channels or [])

        new_channels_found: List[Dict[str, Any]] = []

        # 1. Evaluate items in Run B (New or Updated)
        for key, p_b in map_b.items():
            for ch in (p_b.observed_channels or []):
                if ch and ch not in all_channels_a:
                    new_channels_found.append(
                        {
                            "channel": ch,
                            "product": p_b.product_name,
                            "run_id": run_b.id,
                        }
                    )

            if key not in map_a:
                newly_discovered.append(
                    {
                        "product_name": p_b.product_name,
                        "brand": p_b.brand,
                        "model": p_b.model,
                        "opportunity_score": p_b.opportunity_score,
                        "confidence_level": p_b.confidence_level,
                        "classification": p_b.classification,
                        "matching_videos_count": p_b.matching_videos_count,
                        "verification_status": p_b.verification_status,
                    }
                )
                matrix_rows.append(
                    {
                        "Product Name": p_b.product_name,
                        "Status in Run A": "Not Observed",
                        "Status in Run B": p_b.classification,
                        "Score Run A": "Unavailable",
                        "Score Run B": p_b.opportunity_score,
                        "Score Delta": f"+{p_b.opportunity_score:.1f} (New)",
                        "Videos Run A": "Unavailable",
                        "Videos Run B": p_b.matching_videos_count,
                        "Video Delta": f"+{p_b.matching_videos_count} (New)",
                        "Coverage Delta": f"{p_b.queries_executed_count} queries in B",
                        "Change Type": "Newly Discovered Candidate",
                    }
                )
            else:
                p_a = map_a[key]
                v_delta = p_b.matching_videos_count - p_a.matching_videos_count
                s_delta = round(p_b.opportunity_score - p_a.opportunity_score, 1)
                cov_delta = p_b.queries_executed_count - p_a.queries_executed_count

                if v_delta != 0:
                    video_changes.append(
                        {
                            "product_name": p_b.product_name,
                            "previous_videos": p_a.matching_videos_count,
                            "current_videos": p_b.matching_videos_count,
                            "delta": v_delta,
                        }
                    )

                if abs(s_delta) >= 1.0:
                    score_changes.append(
                        {
                            "product_name": p_b.product_name,
                            "previous_score": p_a.opportunity_score,
                            "current_score": p_b.opportunity_score,
                            "delta": s_delta,
                            "confidence_previous": p_a.confidence_level,
                            "confidence_current": p_b.confidence_level,
                        }
                    )

                if cov_delta != 0:
                    coverage_changes.append(
                        {
                            "product_name": p_b.product_name,
                            "previous_queries": p_a.queries_executed_count,
                            "current_queries": p_b.queries_executed_count,
                            "delta": cov_delta,
                        }
                    )

                v_sign = "+" if v_delta > 0 else ""
                s_sign = "+" if s_delta > 0 else ""
                matrix_rows.append(
                    {
                        "Product Name": p_b.product_name,
                        "Status in Run A": p_a.classification,
                        "Status in Run B": p_b.classification,
                        "Score Run A": p_a.opportunity_score,
                        "Score Run B": p_b.opportunity_score,
                        "Score Delta": f"{s_sign}{s_delta}",
                        "Videos Run A": p_a.matching_videos_count,
                        "Videos Run B": p_b.matching_videos_count,
                        "Video Delta": f"{v_sign}{v_delta}",
                        "Coverage Delta": f"{cov_delta:+d} queries ({p_a.queries_executed_count} -> {p_b.queries_executed_count})",
                        "Change Type": "Updated Existing Candidate",
                    }
                )

        # 2. Evaluate items in Run A that are missing in Run B
        for key, p_a in map_a.items():
            if key not in map_b:
                # Check if search queries for this product failed in Run B
                has_failed = any(
                    p_a.product_name.lower() in fq or (p_a.model and p_a.model.lower() in fq)
                    for fq in failed_queries_b
                )
                caveat = (
                    "Omission may be due to search query failure in Run B, not absence from YouTube."
                    if has_failed
                    else "Not observed in executed search sample for Run B."
                )

                dropped.append(
                    {
                        "product_name": p_a.product_name,
                        "brand": p_a.brand,
                        "model": p_a.model,
                        "previous_score": p_a.opportunity_score,
                        "previous_videos": p_a.matching_videos_count,
                        "caveat": caveat,
                    }
                )
                matrix_rows.append(
                    {
                        "Product Name": p_a.product_name,
                        "Status in Run A": p_a.classification,
                        "Status in Run B": "Not Observed in Sample",
                        "Score Run A": p_a.opportunity_score,
                        "Score Run B": "Unavailable",
                        "Score Delta": "Dropped from Sample",
                        "Videos Run A": p_a.matching_videos_count,
                        "Videos Run B": "Unavailable",
                        "Video Delta": f"-{p_a.matching_videos_count} (Unobserved)",
                        "Coverage Delta": f"0 queries in B ({caveat})",
                        "Change Type": "Dropped Candidate",
                    }
                )

        summary_notes = (
            f"Compared Run #{run_a.run_number} ({run_a.started_at[:10]}) vs "
            f"Run #{run_b.run_number} ({run_b.started_at[:10]}): "
            f"{len(newly_discovered)} new products discovered, {len(dropped)} products dropped from sample, "
            f"{len(video_changes)} products with matching video count changes, "
            f"{len(score_changes)} products with opportunity score shifts, "
            f"{len(new_channels_found)} new channels observed."
        )

        return SnapshotComparisonResult(
            run_a_id=run_a.id or 0,
            run_b_id=run_b.id or 0,
            niche=run_b.niche,
            run_a_date=run_a.started_at,
            run_b_date=run_b.started_at,
            newly_discovered_products=newly_discovered,
            dropped_products=dropped,
            video_count_changes=video_changes,
            score_changes=score_changes,
            coverage_changes=coverage_changes,
            newly_observed_channels=new_channels_found,
            comparison_matrix=matrix_rows,
            summary_notes=summary_notes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class ChangeAlertDetector:
    """Evaluates runs and comparisons to generate evidence-based in-app alerts."""

    def __init__(
        self,
        min_score_delta: float = 15.0,
        min_video_increase: int = 3,
        notify_new_verified: bool = True,
        notify_gap_shift: bool = True,
        notify_budget_or_failure: bool = True,
    ) -> None:
        self.min_score_delta = min_score_delta
        self.min_video_increase = min_video_increase
        self.notify_new_verified = notify_new_verified
        self.notify_gap_shift = notify_gap_shift
        self.notify_budget_or_failure = notify_budget_or_failure

    def detect_alerts(
        self,
        run: ResearchMonitorRun,
        comparison: Optional[SnapshotComparisonResult] = None,
        snapshots: Optional[List[ProductSnapshotItem]] = None,
    ) -> List[MonitorAlert]:
        """Generate targeted alerts with supporting evidence."""
        alerts: List[MonitorAlert] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Run-level failure or budget exhaustion alerts
        if self.notify_budget_or_failure:
            if run.status == MonitorRunStatus.FAILED.value:
                alerts.append(
                    MonitorAlert(
                        run_id=run.id,
                        config_id=run.config_id,
                        niche=run.niche,
                        alert_type="Run Failed",
                        severity=AlertSeverity.CRITICAL.value,
                        title=f"Research Run #{run.run_number} Failed",
                        message=f"Run failed for niche '{run.niche}': {run.error_message or 'Unknown network or provider failure'}.",
                        evidence_data={
                            "status": run.status,
                            "error": run.error_message,
                            "queries_attempted": run.queries_attempted,
                            "queries_failed": run.queries_failed,
                        },
                        created_at=now_iso,
                    )
                )
            elif run.queries_failed > 0 and run.queries_failed >= run.queries_attempted * 0.5:
                alerts.append(
                    MonitorAlert(
                        run_id=run.id,
                        config_id=run.config_id,
                        niche=run.niche,
                        alert_type="High Query Failure Rate",
                        severity=AlertSeverity.WARNING.value,
                        title=f"Elevated Search Failures in Run #{run.run_number}",
                        message=f"{run.queries_failed} of {run.queries_attempted} queries failed during niche research.",
                        evidence_data={
                            "queries_failed": run.queries_failed,
                            "queries_attempted": run.queries_attempted,
                            "failed_queries": run.failed_query_list,
                        },
                        created_at=now_iso,
                    )
                )

            # Check request budget ceiling
            max_budget = (run.config_snapshot or {}).get("request_budget", 0)
            if max_budget > 0 and run.live_requests_count >= max_budget:
                alerts.append(
                    MonitorAlert(
                        run_id=run.id,
                        config_id=run.config_id,
                        niche=run.niche,
                        alert_type="Budget Exhausted",
                        severity=AlertSeverity.WARNING.value,
                        title=f"API Request Budget Exhausted (Run #{run.run_number})",
                        message=f"Reached request budget ceiling ({run.live_requests_count}/{max_budget} requests). Partial results safely preserved.",
                        evidence_data={
                            "live_requests": run.live_requests_count,
                            "budget_limit": max_budget,
                        },
                        created_at=now_iso,
                    )
                )

        # 2. Comparison-level alerts
        if comparison:
            # Newly discovered verified candidates
            if self.notify_new_verified:
                for item in comparison.newly_discovered_products:
                    status = item.get("verification_status", "")
                    if status in ["Verified Model Match", "Brand & Model Verified", "Verified Real Product"]:
                        alerts.append(
                            MonitorAlert(
                                run_id=run.id,
                                config_id=run.config_id,
                                niche=run.niche,
                                product_name=item["product_name"],
                                alert_type="New Verified Candidate",
                                severity=AlertSeverity.HIGH_OPPORTUNITY.value,
                                title=f"New Verified Candidate: {item['product_name']}",
                                message=f"Discovered '{item['product_name']}' with score {item.get('opportunity_score', 0):.1f} ({item.get('confidence_level')}). Matching videos: {item.get('matching_videos_count', 0)}.",
                                evidence_data=item,
                                created_at=now_iso,
                            )
                        )

            # Significant video increases
            for vc in comparison.video_count_changes:
                delta = vc.get("delta", 0)
                if delta >= self.min_video_increase:
                    alerts.append(
                        MonitorAlert(
                            run_id=run.id,
                            config_id=run.config_id,
                            niche=run.niche,
                            product_name=vc["product_name"],
                            alert_type="Video Increase",
                            severity=AlertSeverity.INFO.value,
                            title=f"Competitor Videos Increased: {vc['product_name']}",
                            message=f"Observed matching videos increased by +{delta} (from {vc.get('previous_videos')} to {vc.get('current_videos')}).",
                            evidence_data=vc,
                            created_at=now_iso,
                        )
                    )

            # Large score shifts
            for sc in comparison.score_changes:
                delta = sc.get("delta", 0.0)
                if abs(delta) >= self.min_score_delta:
                    sev = AlertSeverity.HIGH_OPPORTUNITY.value if delta > 0 else AlertSeverity.WARNING.value
                    direction = "Increased" if delta > 0 else "Decreased"
                    alerts.append(
                        MonitorAlert(
                            run_id=run.id,
                            config_id=run.config_id,
                            niche=run.niche,
                            product_name=sc["product_name"],
                            alert_type="Score Shift",
                            severity=sev,
                            title=f"Opportunity Score {direction}: {sc['product_name']}",
                            message=f"Opportunity score shifted by {delta:+0.1f} points (from {sc.get('previous_score')} to {sc.get('current_score')}).",
                            evidence_data=sc,
                            created_at=now_iso,
                        )
                    )

        return alerts


class HistoricalAnalyticsAggregator:
    """Compiles longitudinal trend analytics across stored research runs."""

    @staticmethod
    def aggregate_niche_trends(
        runs: List[ResearchMonitorRun],
        all_snapshots_by_run: Dict[int, List[ProductSnapshotItem]],
    ) -> Dict[str, Any]:
        """Aggregate stored snapshot time series without synthetic extrapolation."""
        # Sort runs chronologically
        sorted_runs = sorted(runs, key=lambda r: r.started_at)
        timeline: List[Dict[str, Any]] = []

        all_products_seen: Set[str] = set()
        product_score_history: Dict[str, List[Dict[str, Any]]] = {}
        channel_diversity: Dict[str, Set[str]] = {}

        for r in sorted_runs:
            run_id = r.id or 0
            snapshots = all_snapshots_by_run.get(run_id, [])

            prod_count = len(snapshots)
            total_score = sum(p.opportunity_score for p in snapshots)
            avg_score = round(total_score / prod_count, 1) if prod_count > 0 else 0.0
            tot_videos = sum(p.matching_videos_count for p in snapshots)
            insufficient_count = sum(1 for p in snapshots if "INSUFFICIENT" in p.classification.upper())

            # Success rate
            attempted = r.queries_attempted
            success_rate = (
                round((r.queries_succeeded / attempted) * 100, 1) if attempted > 0 else 100.0
            )

            # Channels
            run_channels = set()
            for p in snapshots:
                for ch in (p.observed_channels or []):
                    if ch:
                        run_channels.add(ch)

            timeline.append(
                {
                    "run_id": run_id,
                    "run_number": r.run_number,
                    "date": r.started_at[:10],
                    "timestamp": r.started_at,
                    "products_count": prod_count,
                    "avg_opportunity_score": avg_score,
                    "total_matching_videos": tot_videos,
                    "insufficient_research_count": insufficient_count,
                    "query_success_rate": success_rate,
                    "unique_channels_count": len(run_channels),
                    "status": r.status,
                }
            )

            for p in snapshots:
                p_name = p.product_name
                all_products_seen.add(p_name)
                if p_name not in product_score_history:
                    product_score_history[p_name] = []
                product_score_history[p_name].append(
                    {
                        "date": r.started_at[:10],
                        "run_id": run_id,
                        "score": p.opportunity_score,
                        "videos": p.matching_videos_count,
                    }
                )

        return {
            "timeline": timeline,
            "total_runs_analyzed": len(sorted_runs),
            "total_unique_products_tracked": len(all_products_seen),
            "product_histories": product_score_history,
            "data_disclaimer": (
                "Historical Analytics Notice: Charts and trends reflect actual stored research snapshots "
                "within user-executed search samples. No missing data is extrapolated."
            ),
        }


class ResearchSchedulerService:
    """Manages in-process recurring research schedule calculation and deduplication."""

    @staticmethod
    def get_window_key(frequency: str, ref_dt: Optional[datetime] = None) -> str:
        """Compute deduplication window key for daily, weekly, or monthly schedules."""
        dt = ref_dt or datetime.now(timezone.utc)
        if frequency == ResearchScheduleFrequency.DAILY.value:
            return dt.strftime("%Y-%m-%d")
        elif frequency == ResearchScheduleFrequency.WEEKLY.value:
            return dt.strftime("%Y-W%W")
        elif frequency == ResearchScheduleFrequency.MONTHLY.value:
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y-%m-%d-%H")

    @staticmethod
    def compute_next_run(
        frequency: str,
        local_time_str: str = "09:00",
        ref_dt: Optional[datetime] = None,
    ) -> str:
        """Calculate next scheduled execution timestamp in ISO format."""
        now = ref_dt or datetime.now(timezone.utc)
        try:
            hour_str, min_str = local_time_str.split(":")
            h, m = int(hour_str), int(min_str)
        except Exception:
            h, m = 9, 0

        target = now.replace(hour=h, minute=m, second=0, microsecond=0)

        if frequency == ResearchScheduleFrequency.DAILY.value:
            if target <= now:
                target += timedelta(days=1)
        elif frequency == ResearchScheduleFrequency.WEEKLY.value:
            if target <= now:
                target += timedelta(days=7)
        elif frequency == ResearchScheduleFrequency.MONTHLY.value:
            # Add ~30 days
            if target <= now:
                target += timedelta(days=30)
        else:
            target += timedelta(days=7)

        return target.isoformat()

    @staticmethod
    def is_run_due(
        schedule: ResearchSchedule,
        current_dt: Optional[datetime] = None,
    ) -> bool:
        """Determine if a scheduled run is due while enforcing window deduplication."""
        if not schedule.is_enabled:
            return False

        now = current_dt or datetime.now(timezone.utc)
        current_window = ResearchSchedulerService.get_window_key(schedule.frequency, now)

        # If already ran in this exact frequency window, prevent duplicate run
        if schedule.last_window_key and schedule.last_window_key == current_window:
            return False

        if not schedule.next_run_at:
            return True

        try:
            next_dt = datetime.fromisoformat(schedule.next_run_at)
            return now >= next_dt
        except Exception:
            return True
