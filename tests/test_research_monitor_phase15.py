"""Unit and integration tests for Phase 15: Automated Niche Research Reports & Opportunity Monitoring."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import pytest

from src.models.monitor import (
    AlertSeverity,
    MonitorAlert,
    MonitorRunStatus,
    ProductSnapshotItem,
    ResearchMonitorRun,
    ResearchSchedule,
    ResearchScheduleFrequency,
    SavedResearchConfig,
    SnapshotComparisonResult,
)
from src.intelligence.monitor import (
    ChangeAlertDetector,
    HistoricalAnalyticsAggregator,
    ResearchComparisonEngine,
    ResearchSchedulerService,
)
from src.storage.database import DatabaseManager
from src.storage.export import ExportService
from src.ui.components import ALL_NAVIGATION_PAGES, PAGE_RESEARCH_MONITOR


class TestPhase15Models:
    """Test suite for Phase 15 domain models, enums, and serialization."""

    def test_schedule_frequencies(self):
        """Verify all expected frequency modes exist."""
        freqs = [f.value for f in ResearchScheduleFrequency]
        expected = ["Daily", "Weekly", "Monthly", "Manual Queue Only"]
        assert set(expected).issubset(set(freqs))

    def test_monitor_run_statuses(self):
        """Verify run lifecycle statuses."""
        statuses = [s.value for s in MonitorRunStatus]
        expected = ["Pending", "Running", "Completed", "Cancelled", "Failed", "Partial"]
        assert set(expected).issubset(set(statuses))

    def test_alert_severities(self):
        """Verify alert severity tiers."""
        severities = [s.value for s in AlertSeverity]
        expected = ["Info", "Warning", "High Opportunity", "Critical"]
        assert set(expected).issubset(set(severities))

    def test_saved_research_config_serialization(self):
        """Verify SavedResearchConfig round-trip dictionary serialization."""
        config = SavedResearchConfig(
            id=10,
            name="Earbuds Scan",
            niche="Wireless Earbuds",
            country="US",
            language="en",
            date_window_days=60,
            category_filters=["ANC", "Sports"],
            query_templates=["{brand} {model} review"],
            max_products_per_run=25,
            max_queries_per_run=15,
            request_budget=20,
            matching_mode="Exact Model Match",
            min_research_coverage=2,
            opportunity_formula_version="v14.0",
            enabled_discovery_methods=["seed", "catalog"],
            is_paused=False,
            notes="Testing config",
        )
        d = config.to_dict()
        assert d["niche"] == "Wireless Earbuds"
        assert d["request_budget"] == 20
        assert d["category_filters"] == ["ANC", "Sports"]

        restored = SavedResearchConfig.from_dict(d)
        assert restored.id == 10
        assert restored.name == "Earbuds Scan"
        assert restored.matching_mode == "Exact Model Match"
        assert restored.category_filters == ["ANC", "Sports"]

    def test_product_snapshot_item_serialization(self):
        """Verify ProductSnapshotItem round-trip dictionary serialization."""
        item = ProductSnapshotItem(
            id=5,
            run_id=1,
            product_name="Sony WF-1000XM5",
            brand="Sony",
            model="WF-1000XM5",
            niche="Wireless Earbuds",
            category="ANC Earbuds",
            classification="FEW MATCHING VIDEOS",
            classification_reason="Observed 2 matching videos across 3 queries.",
            matching_videos_count=2,
            latest_video_date="2026-09-15T12:00:00Z",
            unique_channels_count=2,
            observed_channels=["TechSpurt", "The Verge"],
            opportunity_score=78.5,
            confidence_level="High Evidence",
            queries_executed_count=3,
            search_coverage_summary="3 queries executed",
            verification_status="Verified Model Match",
            data_source="Live YouTube Data API v3",
        )
        d = item.to_dict()
        assert d["product_name"] == "Sony WF-1000XM5"
        assert d["opportunity_score"] == 78.5
        assert len(d["observed_channels"]) == 2

        restored = ProductSnapshotItem.from_dict(d)
        assert restored.product_name == item.product_name
        assert restored.opportunity_score == item.opportunity_score
        assert restored.observed_channels == item.observed_channels

    def test_research_monitor_run_serialization(self):
        """Verify ResearchMonitorRun round-trip dictionary serialization."""
        run = ResearchMonitorRun(
            id=1,
            config_id=10,
            niche="Wireless Earbuds",
            run_number=1,
            trigger_type="Manual",
            status=MonitorRunStatus.COMPLETED.value,
            config_snapshot={"request_budget": 20},
            queries_attempted=15,
            queries_succeeded=14,
            queries_failed=1,
            failed_query_list=[{"query": "bad query", "error": "timeout"}],
            products_discovered=5,
            matching_videos_retrieved=10,
            live_requests_count=15,
            cached_requests_count=2,
        )
        d = run.to_dict()
        assert d["queries_succeeded"] == 14
        assert len(d["failed_query_list"]) == 1

        restored = ResearchMonitorRun.from_dict(d)
        assert restored.niche == "Wireless Earbuds"
        assert restored.queries_failed == 1
        assert restored.failed_query_list[0]["query"] == "bad query"

    def test_monitor_alert_serialization(self):
        """Verify MonitorAlert round-trip dictionary serialization."""
        alert = MonitorAlert(
            id=1,
            run_id=2,
            config_id=10,
            niche="Wireless Earbuds",
            product_name="Moondrop Space Travel",
            alert_type="New Verified Candidate",
            severity=AlertSeverity.HIGH_OPPORTUNITY.value,
            title="New Verified Candidate",
            message="Discovered Moondrop Space Travel with 0 matching videos.",
            evidence_data={"score": 88.0, "videos": 0},
            is_dismissed=False,
        )
        d = alert.to_dict()
        assert d["severity"] == "High Opportunity"
        assert d["evidence_data"]["score"] == 88.0

        restored = MonitorAlert.from_dict(d)
        assert restored.product_name == "Moondrop Space Travel"
        assert restored.evidence_data["score"] == 88.0


class TestResearchComparisonEngine:
    """Test suite for snapshot differential analysis and delta detection."""

    def test_differential_comparison_new_and_dropped(self):
        """Verify identification of newly discovered and dropped products."""
        run_a = ResearchMonitorRun(id=1, config_id=1, niche="Wireless Earbuds", run_number=1, started_at="2026-10-01T00:00:00Z")
        run_b = ResearchMonitorRun(id=2, config_id=1, niche="Wireless Earbuds", run_number=2, started_at="2026-10-15T00:00:00Z")

        snaps_a = [
            ProductSnapshotItem(product_name="Product Alpha", brand="AlphaBrand", opportunity_score=80.0, matching_videos_count=1, queries_executed_count=2),
            ProductSnapshotItem(product_name="Product Beta", brand="BetaBrand", opportunity_score=70.0, matching_videos_count=2, queries_executed_count=2),
        ]
        snaps_b = [
            ProductSnapshotItem(product_name="Product Beta", brand="BetaBrand", opportunity_score=60.0, matching_videos_count=5, queries_executed_count=3, observed_channels=["NewChannel"]),
            ProductSnapshotItem(product_name="Product Gamma", brand="GammaBrand", opportunity_score=85.0, matching_videos_count=0, queries_executed_count=2, verification_status="Verified Model Match"),
        ]

        result = ResearchComparisonEngine.compare_snapshots(run_a, run_b, snaps_a, snaps_b)

        # 1. Newly discovered in Run B
        assert len(result.newly_discovered_products) == 1
        assert result.newly_discovered_products[0]["product_name"] == "Product Gamma"

        # 2. Dropped in Run B
        assert len(result.dropped_products) == 1
        assert result.dropped_products[0]["product_name"] == "Product Alpha"
        assert "Not observed" in result.dropped_products[0]["caveat"]

        # 3. Video count changes for Product Beta
        assert len(result.video_count_changes) == 1
        assert result.video_count_changes[0]["product_name"] == "Product Beta"
        assert result.video_count_changes[0]["delta"] == 3  # from 2 to 5

        # 4. Score changes for Product Beta
        assert len(result.score_changes) == 1
        assert result.score_changes[0]["product_name"] == "Product Beta"
        assert result.score_changes[0]["delta"] == -10.0  # from 70 to 60

        # 5. Channel discovery
        assert len(result.newly_observed_channels) == 1
        assert result.newly_observed_channels[0]["channel"] == "NewChannel"

        # 6. Comparison matrix
        assert len(result.comparison_matrix) == 3

    def test_dropped_product_with_failed_query_caveat(self):
        """Verify that when Run B had failed queries, dropped products explicitly show the caveat."""
        run_a = ResearchMonitorRun(id=1, config_id=1, niche="Wireless Earbuds", run_number=1, started_at="2026-10-01T00:00:00Z")
        run_b = ResearchMonitorRun(
            id=2,
            config_id=1,
            niche="Wireless Earbuds",
            run_number=2,
            started_at="2026-10-15T00:00:00Z",
            queries_failed=1,
            failed_query_list=[{"query": "sony wf-1000xm5 review", "error": "rate limit"}],
        )

        snaps_a = [
            ProductSnapshotItem(product_name="Sony WF-1000XM5", brand="Sony", model="WF-1000XM5", opportunity_score=85.0, matching_videos_count=0),
        ]
        snaps_b = []  # Omitted because query failed

        result = ResearchComparisonEngine.compare_snapshots(run_a, run_b, snaps_a, snaps_b)
        assert len(result.dropped_products) == 1
        caveat = result.dropped_products[0]["caveat"]
        assert "Omission may be due to search query failure in Run B, not absence from YouTube." in caveat


class TestChangeAlertDetector:
    """Test suite for evidence-based alert generation and trigger thresholds."""

    def test_alert_detection_new_verified_candidate(self):
        """Verify alert generated for a new verified product candidate."""
        detector = ChangeAlertDetector(notify_new_verified=True)
        run = ResearchMonitorRun(id=2, config_id=1, niche="Earbuds", run_number=2, started_at="2026-10-15T00:00:00Z")
        comparison = SnapshotComparisonResult(
            run_a_id=1,
            run_b_id=2,
            niche="Earbuds",
            newly_discovered_products=[
                {
                    "product_name": "Moondrop Space Travel",
                    "verification_status": "Verified Model Match",
                    "opportunity_score": 82.0,
                    "confidence_level": "High Evidence",
                    "matching_videos_count": 0,
                }
            ],
        )

        alerts = detector.detect_alerts(run=run, comparison=comparison)
        verified_alerts = [a for a in alerts if a.alert_type == "New Verified Candidate"]
        assert len(verified_alerts) == 1
        assert verified_alerts[0].severity == AlertSeverity.HIGH_OPPORTUNITY.value
        assert verified_alerts[0].product_name == "Moondrop Space Travel"

    def test_alert_detection_score_shift_and_video_increase(self):
        """Verify alerts for large score shifts and video count increases."""
        detector = ChangeAlertDetector(min_score_delta=10.0, min_video_increase=3)
        run = ResearchMonitorRun(id=2, config_id=1, niche="Earbuds", run_number=2, started_at="2026-10-15T00:00:00Z")
        comparison = SnapshotComparisonResult(
            run_a_id=1,
            run_b_id=2,
            niche="Earbuds",
            video_count_changes=[{"product_name": "Product X", "previous_videos": 1, "current_videos": 5, "delta": 4}],
            score_changes=[{"product_name": "Product X", "previous_score": 50.0, "current_score": 75.0, "delta": 25.0}],
        )

        alerts = detector.detect_alerts(run=run, comparison=comparison)
        types = {a.alert_type for a in alerts}
        assert "Video Increase" in types
        assert "Score Shift" in types

    def test_alert_detection_budget_exhausted_and_failure(self):
        """Verify warnings for budget exhaustion and run failure."""
        detector = ChangeAlertDetector(notify_budget_or_failure=True)
        # Budget exhausted run
        run_budget = ResearchMonitorRun(
            id=3,
            config_id=1,
            niche="Earbuds",
            run_number=3,
            live_requests_count=15,
            config_snapshot={"request_budget": 15},
        )
        alerts_budget = detector.detect_alerts(run=run_budget)
        assert any(a.alert_type == "Budget Exhausted" for a in alerts_budget)

        # Failed run
        run_fail = ResearchMonitorRun(
            id=4,
            config_id=1,
            niche="Earbuds",
            run_number=4,
            status=MonitorRunStatus.FAILED.value,
            error_message="Connection aborted",
        )
        alerts_fail = detector.detect_alerts(run=run_fail)
        fail_alerts = [a for a in alerts_fail if a.alert_type == "Run Failed"]
        assert len(fail_alerts) == 1
        assert fail_alerts[0].severity == AlertSeverity.CRITICAL.value


class TestResearchSchedulerService:
    """Test suite for schedule calculation and window deduplication."""

    def test_window_key_generation(self):
        """Verify window keys for daily, weekly, and monthly frequencies."""
        dt = datetime(2026, 10, 19, 14, 30, 0, tzinfo=timezone.utc)
        daily_key = ResearchSchedulerService.get_window_key(ResearchScheduleFrequency.DAILY.value, ref_dt=dt)
        weekly_key = ResearchSchedulerService.get_window_key(ResearchScheduleFrequency.WEEKLY.value, ref_dt=dt)
        monthly_key = ResearchSchedulerService.get_window_key(ResearchScheduleFrequency.MONTHLY.value, ref_dt=dt)

        assert daily_key == "2026-10-19"
        assert weekly_key == "2026-W42"
        assert monthly_key == "2026-10"

    def test_next_run_calculation(self):
        """Verify computation of next run timestamp."""
        now = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
        # Target 09:00 today (since now is 08:00)
        next_run = ResearchSchedulerService.compute_next_run(
            frequency=ResearchScheduleFrequency.DAILY.value,
            local_time_str="09:00",
            ref_dt=now,
        )
        parsed = datetime.fromisoformat(next_run)
        assert parsed.hour == 9
        assert parsed.minute == 0
        assert parsed.day == 19

    def test_schedule_window_deduplication(self):
        """Verify is_run_due prevents duplicate runs within the same window."""
        now = datetime(2026, 10, 19, 10, 0, 0, tzinfo=timezone.utc)
        sched = ResearchSchedule(
            config_id=1,
            niche="Earbuds",
            frequency=ResearchScheduleFrequency.DAILY.value,
            is_enabled=True,
            last_window_key="2026-10-19",  # Already ran today
            next_run_at="2026-10-19T09:00:00+00:00",
        )
        # Should return False because it already executed in today's window
        assert ResearchSchedulerService.is_run_due(sched, current_dt=now) is False

        # If window is yesterday's, should be due
        sched.last_window_key = "2026-10-18"
        assert ResearchSchedulerService.is_run_due(sched, current_dt=now) is True

        # If disabled, never due
        sched.is_enabled = False
        assert ResearchSchedulerService.is_run_due(sched, current_dt=now) is False


class TestHistoricalAnalyticsAggregator:
    """Test suite for longitudinal trends telemetry across multiple snapshots."""

    def test_aggregate_trends_without_extrapolation(self):
        """Verify metric compilation across 2 runs without synthetic extrapolation."""
        run_1 = ResearchMonitorRun(id=1, config_id=1, niche="Earbuds", run_number=1, started_at="2026-10-01T10:00:00Z", queries_attempted=10, queries_succeeded=10)
        run_2 = ResearchMonitorRun(id=2, config_id=1, niche="Earbuds", run_number=2, started_at="2026-10-15T10:00:00Z", queries_attempted=10, queries_succeeded=9)

        snaps_1 = [
            ProductSnapshotItem(product_name="Product A", opportunity_score=80.0, matching_videos_count=0, classification="ZERO OBSERVED MATCHES"),
            ProductSnapshotItem(product_name="Product B", opportunity_score=60.0, matching_videos_count=2, classification="FEW MATCHING VIDEOS"),
        ]
        snaps_2 = [
            ProductSnapshotItem(product_name="Product A", opportunity_score=75.0, matching_videos_count=1, classification="FEW MATCHING VIDEOS"),
            ProductSnapshotItem(product_name="Product B", opportunity_score=65.0, matching_videos_count=3, classification="FEW MATCHING VIDEOS"),
            ProductSnapshotItem(product_name="Product C", opportunity_score=50.0, matching_videos_count=0, classification="INSUFFICIENT RESEARCH"),
        ]

        snaps_map = {1: snaps_1, 2: snaps_2}
        trends = HistoricalAnalyticsAggregator.aggregate_niche_trends([run_1, run_2], snaps_map)

        assert trends["total_runs_analyzed"] == 2
        assert trends["total_unique_products_tracked"] == 3
        timeline = trends["timeline"]
        assert len(timeline) == 2

        # Check Run 1 metrics
        assert timeline[0]["products_count"] == 2
        assert timeline[0]["avg_opportunity_score"] == 70.0  # (80 + 60) / 2
        assert timeline[0]["total_matching_videos"] == 2
        assert timeline[0]["query_success_rate"] == 100.0

        # Check Run 2 metrics
        assert timeline[1]["products_count"] == 3
        assert timeline[1]["avg_opportunity_score"] == round((75.0 + 65.0 + 50.0) / 3, 1)
        assert timeline[1]["insufficient_research_count"] == 1
        assert timeline[1]["query_success_rate"] == 90.0  # 9/10 succeeded


class TestDatabasePersistencePhase15:
    """Test suite for Phase 15 SQLite database operations and integrity."""

    @pytest.fixture
    def test_db(self):
        """Create a fresh isolated temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_monitor.db"
            db = DatabaseManager(db_path=db_path)
            db.init_db()
            yield db

    def test_config_crud_and_status(self, test_db):
        """Verify configuration create, read, update status, duplicate, and delete."""
        cfg = SavedResearchConfig(
            name="Earbuds Pro Scan",
            niche="Wireless Earbuds",
            country="US",
            language="en",
            request_budget=25,
            category_filters=["ANC"],
        )
        cfg_id = test_db.save_monitor_config(cfg)
        assert cfg_id > 0

        # Read
        retrieved = test_db.get_monitor_config(cfg_id)
        assert retrieved is not None
        assert retrieved.name == "Earbuds Pro Scan"
        assert retrieved.category_filters == ["ANC"]

        # Pause / Resume
        test_db.update_monitor_config_status(cfg_id, is_paused=True)
        assert test_db.get_monitor_config(cfg_id).is_paused is True
        test_db.update_monitor_config_status(cfg_id, is_paused=False)
        assert test_db.get_monitor_config(cfg_id).is_paused is False

        # Duplicate
        dup_id = test_db.duplicate_monitor_config(cfg_id)
        assert dup_id is not None
        assert dup_id != cfg_id
        dup = test_db.get_monitor_config(dup_id)
        assert "Copy" in dup.name

        # Delete
        assert test_db.delete_monitor_config(dup_id) is True
        assert test_db.get_monitor_config(dup_id) is None

    def test_runs_and_snapshots_persistence(self, test_db):
        """Verify run creation, snapshot bulk insert, and snapshot retrieval."""
        cfg = SavedResearchConfig(niche="Mechanical Keyboards")
        cfg_id = test_db.save_monitor_config(cfg)

        run = ResearchMonitorRun(
            config_id=cfg_id,
            niche="Mechanical Keyboards",
            run_number=1,
            trigger_type="Manual",
            status=MonitorRunStatus.COMPLETED.value,
            queries_attempted=10,
            queries_succeeded=10,
        )
        run_id = test_db.save_monitor_run(run)
        assert run_id > 0

        # Insert snapshots
        snaps = [
            ProductSnapshotItem(run_id=run_id, product_name="Keychron Q1", niche="Mechanical Keyboards", opportunity_score=85.0),
            ProductSnapshotItem(run_id=run_id, product_name="GMMK Pro", niche="Mechanical Keyboards", opportunity_score=72.0),
        ]
        inserted = test_db.save_product_snapshots(snaps)
        assert inserted == 2

        # Retrieve snapshots
        loaded = test_db.get_product_snapshots(run_id)
        assert len(loaded) == 2
        names = {p.product_name for p in loaded}
        assert "Keychron Q1" in names

        # Retrieve all snapshots by niche
        all_by_niche = test_db.get_all_snapshots_by_niche("Mechanical Keyboards")
        assert run_id in all_by_niche
        assert len(all_by_niche[run_id]) == 2

    def test_alerts_and_schedules_persistence(self, test_db):
        """Verify alerts insert, read, dismiss, and schedules operations."""
        alert = MonitorAlert(
            niche="Smartwatches",
            alert_type="New Verified Candidate",
            title="Garmin Venu 3",
            message="New opportunity found",
            evidence_data={"score": 90.0},
        )
        test_db.save_monitor_alerts([alert])

        alerts = test_db.get_monitor_alerts(niche="Smartwatches", unread_only=True)
        assert len(alerts) == 1
        a_id = alerts[0].id

        # Dismiss
        test_db.dismiss_monitor_alert(a_id)
        assert len(test_db.get_monitor_alerts(niche="Smartwatches", unread_only=True)) == 0

        # Schedule (requires valid config_id for FK constraint)
        cfg = SavedResearchConfig(niche="Smartwatches")
        cfg_id = test_db.save_monitor_config(cfg)

        sched = ResearchSchedule(
            config_id=cfg_id,
            niche="Smartwatches",
            frequency=ResearchScheduleFrequency.WEEKLY.value,
            local_time="10:00",
            next_run_at="2026-10-26T10:00:00Z",
        )
        s_id = test_db.save_monitor_schedule(sched)
        assert s_id > 0

        loaded_sched = test_db.get_monitor_schedule_by_config(cfg_id)
        assert loaded_sched is not None
        assert loaded_sched.local_time == "10:00"

        # Update window
        test_db.update_schedule_window(s_id, last_window_key="2026-W43")
        assert test_db.get_monitor_schedule_by_config(cfg_id).last_window_key == "2026-W43"


class TestPhase15Exports:
    """Test suite for CSV and Excel exports with formula injection neutralization."""

    def test_monitor_runs_exports(self):
        """Verify research runs CSV and Excel exports."""
        runs = [
            ResearchMonitorRun(
                id=1,
                config_id=1,
                niche="Wireless Earbuds",
                run_number=1,
                status=MonitorRunStatus.COMPLETED.value,
                queries_attempted=10,
                queries_succeeded=10,
                products_discovered=5,
                matching_videos_retrieved=8,
            )
        ]
        csv_bytes = ExportService.export_monitor_runs_csv(runs)
        assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        assert b"Wireless Earbuds" in csv_bytes

        xlsx_bytes = ExportService.export_monitor_runs_excel(runs)
        assert len(xlsx_bytes) > 1000

    def test_snapshot_comparison_exports(self):
        """Verify snapshot comparison matrix CSV and Excel exports."""
        comp = SnapshotComparisonResult(
            run_a_id=1,
            run_b_id=2,
            niche="Wireless Earbuds",
            comparison_matrix=[
                {
                    "Product Name": "=1+1 Formula Injection Attempt",
                    "Score Delta": "+15.0",
                    "Change Type": "Newly Discovered Candidate",
                }
            ],
        )
        csv_bytes = ExportService.export_snapshot_comparison_csv(comp)
        assert csv_bytes.startswith(b"\xef\xbb\xbf")
        # Formula injection should be sanitized
        assert b"'=1+1 Formula Injection Attempt" in csv_bytes

        xlsx_bytes = ExportService.export_snapshot_comparison_excel(comp)
        assert len(xlsx_bytes) > 1000

    def test_change_alerts_and_trends_exports(self):
        """Verify change alerts and trend timeline exports."""
        alerts = [
            MonitorAlert(
                niche="Wireless Earbuds",
                alert_type="Score Shift",
                title="Sony WF-1000XM5 Shift",
                message="Score increased by 20 points",
                evidence_data={"score_delta": 20.0},
            )
        ]
        csv_al = ExportService.export_monitor_alerts_csv(alerts)
        assert csv_al.startswith(b"\xef\xbb\xbf")
        assert b"Sony WF-1000XM5 Shift" in csv_al

        xlsx_al = ExportService.export_monitor_alerts_excel(alerts)
        assert len(xlsx_al) > 1000

        timeline = [
            {
                "run_id": 1,
                "date": "2026-10-19",
                "avg_opportunity_score": 75.5,
                "products_count": 10,
            }
        ]
        csv_tr = ExportService.export_historical_trends_csv(timeline)
        assert csv_tr.startswith(b"\xef\xbb\xbf")
        xlsx_tr = ExportService.export_historical_trends_excel(timeline)
        assert len(xlsx_tr) > 1000


class TestUINavigationPhase15:
    """Test suite for UI navigation constants and export verification."""

    def test_research_monitor_in_navigation(self):
        """Verify PAGE_RESEARCH_MONITOR is registered in ALL_NAVIGATION_PAGES."""
        assert PAGE_RESEARCH_MONITOR == "📡 Research Monitor"
        assert PAGE_RESEARCH_MONITOR in ALL_NAVIGATION_PAGES
        assert len(ALL_NAVIGATION_PAGES) >= 11
