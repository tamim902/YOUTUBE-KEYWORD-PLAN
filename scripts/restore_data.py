"""Keyword Studio - Safe Database Restore Utility.

Safely restores a previous backup file to the active keywords.db location.
Creates a safety backup of the current database before replacement.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import config


def restore_database(
    backup_file_path: Path | str,
    target_db_path: Path | str | None = None,
    create_safety_backup: bool = True,
) -> bool:
    """Restore target database from backup file with pre-restore safety snapshots."""
    backup_path = Path(backup_file_path).resolve()
    target_path = Path(target_db_path or config.database_path).resolve()

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file does not exist: {backup_path}")

    # 1. Verify backup file integrity
    print(f"[INFO] Verifying integrity of backup file: {backup_path.name}...")
    backup_conn = sqlite3.connect(str(backup_path))
    try:
        integrity_row = backup_conn.execute("PRAGMA integrity_check;").fetchone()
        status = integrity_row[0] if integrity_row else "unknown"
        if status.lower() != "ok":
            raise RuntimeError(f"Backup file failed integrity check: {status}")
        
        tables = [
            r[0]
            for r in backup_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
        ]
        if len(tables) < 40:
            raise RuntimeError(f"Backup file contains only {len(tables)} tables, expected at least 40.")
    finally:
        backup_conn.close()

    print(f"[SUCCESS] Backup integrity verified ({len(tables)} tables present).")

    # 2. Create safety copy of current target database if it exists
    if target_path.exists() and create_safety_backup:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safety_path = target_path.parent / f"keywords_pre_restore_{ts}.db"
        print(f"[INFO] Creating safety copy of current active database to: {safety_path.name}...")
        shutil.copy2(target_path, safety_path)
        print("[SUCCESS] Safety backup created.")

    # 3. Clean up existing WAL/SHM companion files to avoid stale locks
    wal_file = target_path.with_name(f"{target_path.name}-wal")
    shm_file = target_path.with_name(f"{target_path.name}-shm")
    if wal_file.exists():
        wal_file.unlink()
    if shm_file.exists():
        shm_file.unlink()

    # 4. Copy backup to target location
    print(f"[INFO] Restoring {backup_path.name} -> {target_path.name}...")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)

    # 5. Post-restore verification
    target_conn = sqlite3.connect(str(target_path))
    try:
        post_row = target_conn.execute("PRAGMA integrity_check;").fetchone()
        post_status = post_row[0] if post_row else "unknown"
        if post_status.lower() != "ok":
            raise RuntimeError(f"Restored target database integrity check failed: {post_status}")
    finally:
        target_conn.close()

    print("[SUCCESS] Target database restored and verified successfully.")
    return True


def list_available_backups(backup_dir: Path | str | None = None) -> list[Path]:
    """List available backups ordered from newest to oldest."""
    b_dir = Path(backup_dir or config.data_dir / "backups").resolve()
    if not b_dir.exists():
        return []
    backups = sorted(b_dir.glob("keywords_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups


def main():
    parser = argparse.ArgumentParser(description="Restore Keyword Studio SQLite Database")
    parser.add_argument("backup_file", nargs="?", default=None, help="Path to backup .db file")
    parser.add_argument("--target", type=str, default=None, help="Custom destination database path")
    parser.add_argument("--list", action="store_true", help="List available backups")
    args = parser.parse_args()

    if args.list:
        backups = list_available_backups()
        if not backups:
            print("No backups found in data/backups/")
        else:
            print("Available backups:")
            for b in backups:
                dt_str = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                size_kb = b.stat().st_size / 1024
                print(f" - {b.name} ({size_kb:.1f} KB, Modified: {dt_str})")
        return

    backup_file = args.backup_file
    if not backup_file:
        # Prompt user or pick newest
        backups = list_available_backups()
        if not backups:
            print("[ERROR] No backups found in data/backups/ to restore.", file=sys.stderr)
            sys.exit(1)
        backup_file = backups[0]
        print(f"[INFO] No backup file specified. Selecting most recent backup: {backup_file.name}")

    try:
        restore_database(backup_file_path=backup_file, target_db_path=args.target)
        print("\n[DONE] Database restoration completed successfully.")
    except Exception as exc:
        print(f"[ERROR] Restore failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
