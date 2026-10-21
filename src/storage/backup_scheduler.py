"""Automated Backup Scheduler & Execution Engine.

Handles:
- Configurable daily automated backup schedule (default: 03:00 UTC / local).
- Manual on-demand backup triggers.
- Optional automatic backup trigger following significant data updates.
- Background worker daemon checking schedule while Streamlit app is active.
- End-to-end execution: bundle creation → integrity check → Google Drive sync → retention pruning.
- Full provenance and audit logging in SQLite app_settings.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import logging
import threading
import time as time_mod
from typing import Any, Dict, List, Optional, Tuple

from src.storage.backup_bundle import BackupManifest, backup_bundler
from src.storage.database import db_manager
from src.storage.gdrive_client import gdrive_client

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled and event-driven backup runs."""

    def __init__(self) -> None:
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def is_schedule_enabled(self) -> bool:
        """Check if automated daily backups are enabled in settings."""
        val = db_manager.get_setting("backup_schedule_enabled")
        if val is None:
            return True  # Default enabled
        return val.lower() in ("true", "1", "yes")

    def set_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable automated daily backups."""
        db_manager.set_setting("backup_schedule_enabled", "true" if enabled else "false")

    def get_schedule_hour(self) -> int:
        """Return configured hour of day (0-23) for daily backup (default: 3 AM)."""
        val = db_manager.get_setting("backup_schedule_hour")
        try:
            return int(val) if val is not None else 3
        except Exception:
            return 3

    def set_schedule_hour(self, hour: int) -> None:
        """Set scheduled hour of day (0-23)."""
        clamped = max(0, min(23, hour))
        db_manager.set_setting("backup_schedule_hour", str(clamped))

    def get_retention_count(self) -> int:
        """Return number of recent backups to keep in Google Drive (default: 30)."""
        val = db_manager.get_setting("backup_retention_days")
        try:
            return int(val) if val is not None else 30
        except Exception:
            return 30

    def set_retention_count(self, count: int) -> None:
        """Set retention count for Google Drive backups."""
        clamped = max(1, min(365, count))
        db_manager.set_setting("backup_retention_days", str(clamped))

    def is_auto_on_change_enabled(self) -> bool:
        """Check if automatic backup on important data changes is enabled."""
        val = db_manager.get_setting("backup_on_important_change")
        return val.lower() in ("true", "1", "yes") if val else False

    def set_auto_on_change_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic backup on important changes."""
        db_manager.set_setting("backup_on_important_change", "true" if enabled else "false")

    def is_backup_due(self) -> bool:
        """Determine if a scheduled daily backup is due right now."""
        if not self.is_schedule_enabled():
            return False

        last_backup_str = db_manager.get_setting("backup_last_run_timestamp")
        now = datetime.now(timezone.utc)

        if not last_backup_str:
            return True

        try:
            last_dt = datetime.fromisoformat(last_backup_str)
            # If last backup was more than 24 hours ago, it is due
            if now - last_dt >= timedelta(hours=24):
                return True

            # If it hasn't run today and the scheduled hour has passed
            sched_hour = self.get_schedule_hour()
            if last_dt.date() < now.date() and now.hour >= sched_hour:
                return True

        except Exception:
            return True

        return False

    def get_next_scheduled_time_str(self) -> str:
        """Compute the estimated next scheduled backup timestamp."""
        if not self.is_schedule_enabled():
            return "Disabled"

        now = datetime.now(timezone.utc)
        sched_hour = self.get_schedule_hour()
        target_today = now.replace(hour=sched_hour, minute=0, second=0, microsecond=0)

        if now < target_today:
            next_dt = target_today
        else:
            next_dt = target_today + timedelta(days=1)

        return next_dt.strftime("%Y-%m-%d %H:00 UTC")

    def run_full_backup_cycle(
        self,
        trigger: str = "MANUAL",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Execute complete backup cycle: bundle creation → verification → Google Drive upload → retention.
        
        Thread-safe to prevent concurrent conflicting runs.
        """
        with self._lock:
            start_time = datetime.now(timezone.utc)
            report: Dict[str, Any] = {
                "trigger": trigger,
                "started_at": start_time.isoformat(),
                "local_bundle_status": "PENDING",
                "gdrive_upload_status": "SKIPPED",
                "retention_status": "SKIPPED",
                "overall_status": "FAILED",
                "error": None,
            }

            try:
                # 1. Create local validated bundle
                logger.info("Executing backup bundle creation (Trigger: %s)...", trigger)
                zip_path, manifest = backup_bundler.create_backup_bundle(note=f"Trigger: {trigger}")
                report["local_bundle_file"] = zip_path.name
                report["archive_size_bytes"] = zip_path.stat().st_size
                report["local_bundle_status"] = "SUCCESS"

                # 2. Check Google Drive connectivity
                if gdrive_client.is_authenticated():
                    logger.info("Google Drive is authenticated. Starting cloud upload...")
                    up_success, up_msg, up_meta = gdrive_client.upload_backup(
                        zip_path=zip_path,
                        manifest=manifest.to_dict(),
                    )
                    if up_success:
                        report["gdrive_upload_status"] = "SUCCESS"
                        report["gdrive_file_id"] = up_meta.get("id")
                        report["gdrive_web_link"] = up_meta.get("webViewLink")

                        # 3. Apply retention policy
                        retention_limit = self.get_retention_count()
                        pruned_count, pruned_files = gdrive_client.apply_retention_policy(keep_count=retention_limit)
                        report["retention_status"] = "SUCCESS"
                        report["retention_pruned_count"] = pruned_count
                        report["retention_pruned_files"] = pruned_files
                    else:
                        report["gdrive_upload_status"] = "FAILED"
                        report["gdrive_error"] = up_msg
                        report["error"] = f"Google Drive upload failed: {up_msg}"
                else:
                    report["gdrive_upload_status"] = "NOT_AUTHENTICATED"
                    report["gdrive_note"] = "Local backup saved successfully. Google Drive is disconnected."

                # 4. Finalize status
                is_overall_success = (report["local_bundle_status"] == "SUCCESS") and (
                    report["gdrive_upload_status"] in ("SUCCESS", "NOT_AUTHENTICATED")
                )

                now_iso = datetime.now(timezone.utc).isoformat()
                report["completed_at"] = now_iso
                report["overall_status"] = "SUCCESS" if is_overall_success else "PARTIAL_SUCCESS"

                db_manager.set_setting("backup_last_run_timestamp", now_iso)
                db_manager.set_setting("backup_last_status", report["overall_status"])
                db_manager.set_setting("backup_last_trigger", trigger)
                if report.get("error"):
                    db_manager.set_setting("backup_last_error", str(report["error"]))
                else:
                    db_manager.set_setting("backup_last_error", "")

                logger.info("Backup cycle completed with status: %s", report["overall_status"])
                return report

            except Exception as ex:
                logger.error("Error during backup cycle: %s", ex, exc_info=True)
                now_iso = datetime.now(timezone.utc).isoformat()
                report["completed_at"] = now_iso
                report["overall_status"] = "FAILED"
                report["error"] = str(ex)

                db_manager.set_setting("backup_last_run_timestamp", now_iso)
                db_manager.set_setting("backup_last_status", "FAILED")
                db_manager.set_setting("backup_last_error", str(ex))
                return report

    def trigger_post_change_backup(self, reason: str = "Important change") -> Optional[Dict[str, Any]]:
        """Trigger automated backup if post-change backup setting is enabled."""
        if self.is_auto_on_change_enabled():
            logger.info("Triggering post-change backup: %s", reason)
            return self.run_full_backup_cycle(trigger=f"ON_CHANGE: {reason}")
        return None

    def start_background_daemon(self, check_interval_seconds: int = 3600) -> None:
        """Start a background daemon thread checking the schedule periodically while app is open."""
        if self._daemon_thread and self._daemon_thread.is_alive():
            return

        self._stop_event.clear()

        def _worker():
            logger.info("Backup scheduler daemon started (Interval: %ds)", check_interval_seconds)
            while not self._stop_event.is_set():
                try:
                    if self.is_backup_due():
                        logger.info("Scheduled backup is due. Running backup cycle...")
                        self.run_full_backup_cycle(trigger="SCHEDULED_DAILY")
                except Exception as ex:
                    logger.warning("Error in backup scheduler daemon: %s", ex)

                # Sleep in short bursts so thread responds quickly to shutdown signal
                for _ in range(check_interval_seconds):
                    if self._stop_event.is_set():
                        break
                    time_mod.sleep(1)

            logger.info("Backup scheduler daemon stopped.")

        self._daemon_thread = threading.Thread(target=_worker, daemon=True, name="BackupSchedulerDaemon")
        self._daemon_thread.start()

    def stop_background_daemon(self) -> None:
        """Signal background daemon to terminate cleanly."""
        self._stop_event.set()


backup_scheduler = BackupScheduler()
