"""Keyword Studio - Safe Online Database Backup Utility.

Safely backs up the production SQLite WAL database without interrupting running sessions.
Uses SQLite's native online backup API (conn.backup) to ensure transaction consistency.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import config


def backup_database(
    source_db_path: Path | str | None = None,
    backup_dir: Path | str | None = None,
    note: str = "Manual backup",
) -> Path:
    """Safely back up SQLite database to a timestamped backup file using SQLite Online Backup API."""
    src_path = Path(source_db_path or config.database_path).resolve()
    dest_dir = Path(backup_dir or config.data_dir / "backups").resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not src_path.exists():
        raise FileNotFoundError(f"Source database not found at: {src_path}")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"keywords_backup_{timestamp_str}.db"
    backup_path = dest_dir / backup_filename
    manifest_path = dest_dir / f"keywords_backup_{timestamp_str}.json"

    print(f"[INFO] Connecting to source database: {src_path}")
    source_conn = sqlite3.connect(str(src_path))
    dest_conn = sqlite3.connect(str(backup_path))

    try:
        # 1. Execute online backup
        print(f"[INFO] Executing SQLite online backup to: {backup_path.name}...")
        source_conn.backup(dest_conn)
        dest_conn.commit()
        print("[SUCCESS] Online database backup completed.")

        # 2. Verify integrity of the backup file
        dest_cursor = dest_conn.cursor()
        integrity_row = dest_cursor.execute("PRAGMA integrity_check;").fetchone()
        integrity_status = integrity_row[0] if integrity_row else "unknown"
        if integrity_status.lower() != "ok":
            raise RuntimeError(f"Backup file integrity check failed: {integrity_status}")

        # 3. Collect inventory manifest
        tables = [
            r[0]
            for r in dest_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
        ]
        table_counts = {}
        for t in tables:
            try:
                cnt = dest_cursor.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
                table_counts[t] = cnt
            except Exception:
                table_counts[t] = -1

        manifest = {
            "backup_filename": backup_filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_db_path": str(src_path),
            "source_file_size_bytes": src_path.stat().st_size,
            "backup_file_size_bytes": backup_path.stat().st_size,
            "integrity_status": integrity_status,
            "total_tables": len(tables),
            "table_counts": table_counts,
            "note": note,
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[SUCCESS] Integrity Check: {integrity_status.upper()}")
        print(f"[SUCCESS] Total Tables Backed Up: {len(tables)}")
        print(f"[SUCCESS] Manifest saved to: {manifest_path.name}")
        return backup_path

    finally:
        dest_conn.close()
        source_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Backup Keyword Studio SQLite Database")
    parser.add_argument("--source", type=str, default=None, help="Custom path to source keywords.db")
    parser.add_argument("--dest", type=str, default=None, help="Custom directory for backup storage")
    parser.add_argument("--note", type=str, default="CLI manual backup", help="Optional note in manifest")
    args = parser.parse_args()

    try:
        backed_up_file = backup_database(
            source_db_path=args.source,
            backup_dir=args.dest,
            note=args.note,
        )
        print(f"\n[DONE] Backup successfully created at:\n       {backed_up_file}")
    except Exception as exc:
        print(f"[ERROR] Backup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
