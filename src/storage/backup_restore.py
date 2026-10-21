"""Safe Backup Restore & Recovery Engine.

Provides:
- Integrity validation of backup archives prior to any restoration action.
- Mandatory pre-restore safety snapshot of the active production database.
- Atomic database restoration using SQLite online backup API to copy pages safely.
- Post-restore database verification (PRAGMA integrity_check).
- Isolated sandbox restoration testing that verifies end-to-end recovery without
  touching live production files.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import sqlite3
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from src.config import DATA_DIR, DATABASE_PATH
from src.storage.backup import BackupManager
from src.storage.backup_bundle import backup_bundler, compute_file_sha256

logger = logging.getLogger(__name__)


class BackupRestoreManager:
    """Manages verified, safe restorations of Keyword Studio backups."""

    def __init__(
        self,
        target_db_path: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
    ) -> None:
        self.target_db_path = Path(target_db_path or DATABASE_PATH)
        self.backup_dir = Path(backup_dir or DATA_DIR / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_manager = BackupManager(backup_dir=self.backup_dir)

    def inspect_backup_for_restore(self, zip_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Pre-inspect and validate a backup archive before allowing restore."""
        zip_path = Path(zip_path)
        is_valid, msg, manifest = backup_bundler.validate_backup_bundle(zip_path)
        if not is_valid:
            return False, f"Backup validation failed: {msg}", {}

        # Extract table counts and summary from manifest
        db_stats = manifest.get("database_stats", {})
        summary = {
            "backup_id": manifest.get("backup_id", zip_path.stem),
            "timestamp_utc": manifest.get("timestamp_utc", ""),
            "app_version": manifest.get("app_version", ""),
            "git_commit": manifest.get("git_commit", "N/A"),
            "archive_size_kb": round(zip_path.stat().st_size / 1024, 2),
            "included_files_count": manifest.get("included_files_count", 0),
            "total_searches": db_stats.get("searches_count", 0),
            "total_keywords": db_stats.get("keywords_count", 0),
            "total_cache": db_stats.get("cache_count", 0),
            "manifest": manifest,
        }
        return True, "Backup is valid and ready for safe restoration.", summary

    def restore_backup(
        self,
        zip_path: Path,
        confirmed: bool = False,
        create_safety_snapshot: bool = True,
    ) -> Tuple[bool, str, Optional[Path]]:
        """Safely restore database from a verified backup ZIP archive into the active database.
        
        Guarantees:
        1. Pre-validation of backup zip and database snapshot.
        2. Automatic pre-restore safety snapshot of active database before any changes.
        3. Atomic SQLite restore.
        4. Post-restore verification.
        """
        if not confirmed:
            return False, "Restore aborted: User confirmation is required before replacing data.", None

        zip_path = Path(zip_path)
        is_valid, msg, manifest = self.inspect_backup_for_restore(zip_path)
        if not is_valid:
            return False, f"Restore aborted: {msg}", None

        # 1. Create pre-restore safety backup of active database
        safety_path: Optional[Path] = None
        if create_safety_snapshot and self.target_db_path.exists() and self.target_db_path.stat().st_size > 0:
            try:
                safety_path = self.backup_manager.create_backup(
                    source_db_path=self.target_db_path,
                    prefix="pre_restore_safety",
                )
                logger.info("Created pre-restore safety snapshot: %s", safety_path.name)
            except Exception as ex:
                return False, f"Restore aborted: Failed to create pre-restore safety snapshot ({ex}).", None

        # 2. Extract database snapshot from zip into temporary staging area
        temp_dir = self.backup_dir / f"restore_staging_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract("database/keywords.db", temp_dir)

            staged_db = temp_dir / "database" / "keywords.db"
            if not staged_db.exists():
                return False, "Restore aborted: Extracted database not found in archive.", safety_path

            # 3. Execute atomic SQLite restore from staged snapshot to live target
            success, restore_msg = self.backup_manager.restore_backup(
                backup_path=staged_db,
                target_db_path=self.target_db_path,
                create_safety_backup=False,  # Already created above
            )

            if not success:
                return False, f"Restore failed during SQLite transfer: {restore_msg}", safety_path

            success_msg = (
                f"Successfully restored data from '{zip_path.name}'!\n"
                f"Database integrity verified (PRAGMA integrity_check passed)."
            )
            if safety_path:
                success_msg += f"\nPre-restore safety snapshot preserved at: '{safety_path.name}'."

            logger.info("Restore completed successfully from %s", zip_path.name)
            return True, success_msg, safety_path

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_restore_in_sandbox(
        self,
        zip_path: Path,
        sandbox_dir: Optional[Path] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Verify restore in an isolated sandbox directory without modifying active production data."""
        zip_path = Path(zip_path)
        if not zip_path.exists():
            return False, f"Backup file not found: {zip_path}", {}

        temp_sandbox = Path(sandbox_dir or self.backup_dir / f"sandbox_test_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
        temp_sandbox.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # 1. CRC check
                bad_file = zf.testzip()
                if bad_file:
                    return False, f"Sandbox test failed: Corrupt CRC in {bad_file}", {}

                # 2. Extract into sandbox
                zf.extractall(temp_sandbox)

            # 3. Verify manifest
            manifest_p = temp_sandbox / "backup_manifest.json"
            if not manifest_p.exists():
                return False, "Sandbox test failed: 'backup_manifest.json' missing from extracted files.", {}

            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            # 4. Verify database in sandbox
            sandbox_db = temp_sandbox / "database" / "keywords.db"
            if not sandbox_db.exists():
                return False, "Sandbox test failed: 'database/keywords.db' missing from extracted files.", {}

            conn = sqlite3.connect(sandbox_db)
            try:
                cursor = conn.cursor()
                check = cursor.execute("PRAGMA integrity_check;").fetchone()
                if not check or check[0].lower() != "ok":
                    return False, f"Sandbox database integrity check failed: {check}", {}

                # Verify core tables
                tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                required_tables = {"searches", "keywords", "autocomplete_cache"}
                missing = required_tables - set(tables)
                if missing:
                    return False, f"Sandbox database missing core tables: {missing}", {}

                stats = {
                    "tables_count": len(tables),
                    "integrity": "ok",
                    "backup_id": manifest_data.get("backup_id", ""),
                    "timestamp": manifest_data.get("timestamp_utc", ""),
                }
            finally:
                conn.close()

            return True, "Sandbox test restore passed 100%! All files and database integrity verified.", stats

        finally:
            shutil.rmtree(temp_sandbox, ignore_errors=True)


backup_restore_manager = BackupRestoreManager()
