"""Database backup and restore service using SQLite's online backup facility.

Provides:
- Atomic, non-blocking snapshots even in WAL mode.
- Backup validation via PRAGMA integrity_check and table verification.
- Safe restore with mandatory pre-restore safety backup.
- Local-only storage with zero network exposure.
"""

import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages consistent SQLite database backups and safe restorations."""

    def __init__(self, backup_dir: Optional[Path] = None) -> None:
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            from src.config import DATA_DIR
            self.backup_dir = DATA_DIR / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        source_db_path: Path,
        backup_name: Optional[str] = None,
        prefix: str = "backup",
    ) -> Path:
        """Create a consistent snapshot of the source SQLite database using SQLite's backup API.

        Works safely even while the source database is in WAL mode and actively accessed.
        """
        source_db_path = Path(source_db_path)
        if not source_db_path.exists():
            raise FileNotFoundError(f"Source database not found: {source_db_path}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if backup_name:
            # Strip path traversal elements and enforce .db extension
            base_cleaned = Path(backup_name).name
            clean_name = base_cleaned if base_cleaned.endswith(".db") else f"{base_cleaned}.db"
        else:
            prefix_cleaned = re.sub(r"[^\w-]", "", prefix) or "backup"
            clean_name = f"{prefix_cleaned}_{timestamp}.db"

        target_path = (self.backup_dir / clean_name).resolve()
        if self.backup_dir.resolve() not in target_path.parents and target_path.parent != self.backup_dir.resolve():
            raise ValueError(f"Target path escapes backup directory: {target_path}")

        src_conn = sqlite3.connect(source_db_path, timeout=10.0)
        dst_conn = sqlite3.connect(target_path, timeout=10.0)
        try:
            src_conn.backup(dst_conn)
            logger.info("Database backup created successfully: %s", target_path)
        finally:
            dst_conn.close()
            src_conn.close()

        return target_path

    def validate_backup(self, backup_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate an SQLite backup file for corruption, integrity, and expected tables.

        Returns:
            Tuple of (is_valid, status_message, metadata_dict).
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return False, f"Backup file not found: {backup_path}", {}

        if backup_path.stat().st_size == 0:
            return False, "Backup file is empty (0 bytes).", {}

        try:
            conn = sqlite3.connect(backup_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            try:
                # 1. Run SQLite integrity check
                cursor = conn.execute("PRAGMA integrity_check;")
                check_result = cursor.fetchone()[0]
                if check_result != "ok":
                    return False, f"Integrity check failed: {check_result}", {}

                # 2. Check for expected core tables
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
                )
                tables = {row["name"] for row in cursor.fetchall()}
                required_tables = {"searches", "keywords", "autocomplete_cache"}
                missing = required_tables - tables
                if missing:
                    return (
                        False,
                        f"Backup is missing required tables: {', '.join(sorted(missing))}",
                        {"tables": list(tables)},
                    )

                # 3. Collect statistics
                searches_count = conn.execute("SELECT COUNT(*) FROM searches;").fetchone()[0]
                keywords_count = conn.execute("SELECT COUNT(*) FROM keywords;").fetchone()[0]
                cache_count = conn.execute("SELECT COUNT(*) FROM autocomplete_cache;").fetchone()[0]

                stats = {
                    "file_name": backup_path.name,
                    "file_size_bytes": backup_path.stat().st_size,
                    "file_size_kb": round(backup_path.stat().st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(
                        backup_path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                    "tables": list(tables),
                    "searches_count": searches_count,
                    "keywords_count": keywords_count,
                    "cache_count": cache_count,
                    "integrity": "ok",
                }
                return True, "Backup verified successfully (PRAGMA integrity_check passed).", stats
            finally:
                conn.close()
        except Exception as e:
            logger.error("Error validating backup %s: %s", backup_path, e)
            return False, f"Failed to validate backup: {str(e)}", {}

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available SQLite backups in the backup directory with validation metadata."""
        backups = []
        for file in sorted(self.backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True):
            is_valid, msg, stats = self.validate_backup(file)
            backups.append(
                {
                    "path": str(file),
                    "name": file.name,
                    "is_valid": is_valid,
                    "message": msg,
                    "size_kb": round(file.stat().st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(
                        file.stat().st_mtime, timezone.utc
                    ).isoformat(),
                    "stats": stats,
                }
            )
        return backups

    def restore_backup(
        self,
        backup_path: Path,
        target_db_path: Path,
        create_safety_backup: bool = True,
    ) -> Tuple[bool, str]:
        """Restore a verified backup into the target database location.

        Safety guarantees:
        1. Validates the backup file prior to restoring.
        2. Creates an automatic pre-restore safety backup of target_db_path.
        3. Uses atomic SQLite online backup API to copy pages safely.
        4. Validates the restored target database immediately after copy.
        """
        backup_path = Path(backup_path)
        target_db_path = Path(target_db_path)

        # 1. Pre-validation of backup source
        is_valid, msg, _ = self.validate_backup(backup_path)
        if not is_valid:
            return False, f"Restore aborted: Backup file is invalid or corrupted ({msg})."

        # 2. Safety snapshot of current database
        safety_path = None
        if create_safety_backup and target_db_path.exists() and target_db_path.stat().st_size > 0:
            try:
                safety_path = self.create_backup(
                    source_db_path=target_db_path,
                    prefix="pre_restore_safety",
                )
                logger.info("Created pre-restore safety snapshot: %s", safety_path)
            except Exception as e:
                return False, f"Restore aborted: Failed to create pre-restore safety backup ({e})."

        # 3. Execute atomic restore
        src_conn = sqlite3.connect(backup_path, timeout=10.0)
        target_db_path.parent.mkdir(parents=True, exist_ok=True)
        dst_conn = sqlite3.connect(target_db_path, timeout=10.0)
        try:
            src_conn.backup(dst_conn)
            logger.info("Restored database from %s to %s", backup_path, target_db_path)
        except Exception as e:
            return False, f"Restore failed during SQLite backup transfer: {str(e)}"
        finally:
            dst_conn.close()
            src_conn.close()

        # 4. Post-validation of target
        is_restored_valid, target_msg, _ = self.validate_backup(target_db_path)
        if not is_restored_valid:
            return (
                False,
                f"Restore completed with errors: Target database validation failed ({target_msg}). "
                f"Safety copy is available at: {safety_path}",
            )

        success_msg = f"Database restored successfully from '{backup_path.name}'."
        if safety_path:
            success_msg += f" (Pre-restore safety backup saved as '{safety_path.name}')"
        return True, success_msg
