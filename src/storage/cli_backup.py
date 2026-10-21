"""Headless CLI Entry Point for YouTube Keyword Studio Automated Backups.

Usage:
    python -m src.storage.cli_backup
    python -m src.storage.cli_backup --force
    python -m src.storage.cli_backup --retention 30
    python -m src.storage.cli_backup --note "Pre-maintenance backup"

Exits with:
    0 on SUCCESS
    1 on FAILURE
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.backup_scheduler import backup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cli_backup")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="YouTube Keyword Studio - Automated Backup & Cloud Sync CLI"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force backup run regardless of schedule interval",
    )
    parser.add_argument(
        "--retention",
        type=int,
        default=None,
        help="Override retention limit (number of cloud backups to keep)",
    )
    parser.add_argument(
        "--note",
        type=str,
        default="CLI/Scheduled Execution",
        help="Annotation note for the backup manifest",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )

    args = parser.parse_args()

    if args.retention is not None:
        backup_scheduler.set_retention_count(args.retention)

    logger.info("Executing Keyword Studio backup cycle (Trigger: %s)...", args.note)
    result = backup_scheduler.run_full_backup_cycle(trigger=f"CLI: {args.note}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("overall_status", "UNKNOWN")
        bundle = result.get("local_bundle_file", "None")
        gdrive = result.get("gdrive_upload_status", "SKIPPED")
        error = result.get("error")

        print("=" * 60)
        print(f"BACKUP CYCLE RESULT: {status}")
        print(f"Local Bundle:        {bundle}")
        print(f"Google Drive Status: {gdrive}")
        if result.get("gdrive_web_link"):
            print(f"Google Drive Link:   {result.get('gdrive_web_link')}")
        if result.get("retention_pruned_count", 0) > 0:
            print(f"Retention Pruned:    {result.get('retention_pruned_count')} older backups")
        if error:
            print(f"Error Details:       {error}")
        print("=" * 60)

    return 0 if result.get("overall_status") in ("SUCCESS", "PARTIAL_SUCCESS") else 1


if __name__ == "__main__":
    sys.exit(main())
