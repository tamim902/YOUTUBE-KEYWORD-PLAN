"""Versioned schema migration system for SQLite database.

Guarantees:
- Predictable, sequential execution of database schema versions.
- Atomic execution within transactions with rollback on failure.
- Automated safety backup before applying migrations on populated databases.
- Preservation of all existing projects, keywords, provenance, and timestamps.
- Idempotent column and table checks.
- Zero silent data loss or destructive drops.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.models.keyword import infer_tail_length
from src.storage.backup import BackupManager
from src.utils.normalization import count_tokens, normalize_keyword_key

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when a schema migration fails."""
    pass


class MigrationManager:
    """Manages versioned database migrations with pre-migration backups and rollback."""

    def __init__(
        self,
        db_path: Path,
        backup_manager: Optional[BackupManager] = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.backup_manager = backup_manager or BackupManager(
            backup_dir=self.db_path.parent / "backups"
        )

    def get_applied_versions(self, conn: sqlite3.Connection) -> Set[int]:
        """Query schema_migrations table to determine which versions have been applied."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
        return {row[0] for row in cursor.fetchall()}

    def get_current_schema_version(self) -> int:
        """Inspect active database and return the highest applied migration version (or 0)."""
        if not self.db_path.exists():
            return 0
        conn = sqlite3.connect(self.db_path)
        try:
            versions = self.get_applied_versions(conn)
            return max(versions) if versions else 0
        finally:
            conn.close()

    def record_migration(self, conn: sqlite3.Connection, version: int, name: str) -> None:
        """Record a successful migration version in schema_migrations."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
            (version, name, now),
        )

    # --------------------------------------------------------------------------
    # Migration Definitions
    # --------------------------------------------------------------------------

    def _migration_v1_initial(self, conn: sqlite3.Connection) -> None:
        """v1: Initial schema for searches, keywords, and autocomplete_cache."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seed_keyword TEXT NOT NULL,
                language TEXT NOT NULL,
                country TEXT NOT NULL,
                max_depth INTEGER NOT NULL,
                request_budget INTEGER NOT NULL,
                total_results INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                keyword TEXT NOT NULL,
                seed_keyword TEXT NOT NULL,
                source_type TEXT NOT NULL,
                classification TEXT NOT NULL,
                depth INTEGER NOT NULL,
                parent_keyword TEXT,
                language TEXT NOT NULL,
                country TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_search_id ON keywords(search_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_seed ON keywords(seed_keyword);")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS autocomplete_cache (
                query TEXT NOT NULL,
                language TEXT NOT NULL,
                country TEXT NOT NULL,
                results_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (query, language, country)
            );
            """
        )

    def _migration_v2_phase5_columns(self, conn: sqlite3.Connection) -> None:
        """v2: Phase 5 classification, canonical normalized key, and sources_json columns."""
        cursor = conn.execute("PRAGMA table_info(keywords);")
        existing_cols = {row[1] for row in cursor.fetchall()}

        new_cols = {
            "normalized_key": "TEXT",
            "tail_length": "TEXT",
            "intent_labels": "TEXT",
            "sources_json": "TEXT",
            "word_count": "INTEGER",
        }
        for col_name, col_type in new_cols.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE keywords ADD COLUMN {col_name} {col_type};")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_norm_key ON keywords(normalized_key);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_tail ON keywords(tail_length);")

        # Backfill rows where normalized_key is NULL
        cursor = conn.execute(
            "SELECT id, keyword, source_type, classification FROM keywords WHERE normalized_key IS NULL;"
        )
        legacy_rows = cursor.fetchall()
        for r in legacy_rows:
            row_id, kw, stype, _ = r[0], r[1], r[2], r[3]
            norm_key = normalize_keyword_key(kw)
            w_count = count_tokens(kw)
            tail = infer_tail_length(w_count).value
            sources_str = json.dumps([stype])
            intents_str = json.dumps(["Informational"])
            conn.execute(
                """
                UPDATE keywords
                SET normalized_key = ?, tail_length = ?, intent_labels = ?, sources_json = ?, word_count = ?
                WHERE id = ?;
                """,
                (norm_key, tail, intents_str, sources_str, w_count, row_id),
            )

    def _migration_v3_phase7_projects_provenance(self, conn: sqlite3.Connection) -> None:
        """v3: Phase 7 research projects metadata, timestamps, and multi-path provenance."""
        # 1. Searches table additions
        cursor = conn.execute("PRAGMA table_info(searches);")
        searches_cols = {row[1] for row in cursor.fetchall()}

        searches_new_cols = {
            "project_name": "TEXT",
            "updated_at": "TEXT",
            "status": "TEXT DEFAULT 'completed'",
            "stop_reason": "TEXT",
            "parameters_json": "TEXT",
            "requests_made": "INTEGER DEFAULT 0",
            "error_message": "TEXT",
        }
        for col_name, col_type in searches_new_cols.items():
            if col_name not in searches_cols:
                conn.execute(f"ALTER TABLE searches ADD COLUMN {col_name} {col_type};")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_searches_project_name ON searches(project_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_searches_status ON searches(status);")

        # Backfill searches: project_name defaults to seed_keyword, updated_at to created_at
        conn.execute(
            """
            UPDATE searches
            SET project_name = seed_keyword
            WHERE project_name IS NULL OR project_name = '';
            """
        )
        conn.execute(
            """
            UPDATE searches
            SET updated_at = created_at
            WHERE updated_at IS NULL OR updated_at = '';
            """
        )
        conn.execute(
            """
            UPDATE searches
            SET status = 'completed'
            WHERE status IS NULL OR status = '';
            """
        )

        # 2. Keywords table additions
        cursor = conn.execute("PRAGMA table_info(keywords);")
        keywords_cols = {row[1] for row in cursor.fetchall()}

        keywords_new_cols = {
            "source_name": "TEXT DEFAULT 'youtube_autocomplete'",
            "last_seen_at": "TEXT",
            "discovery_paths_json": "TEXT",
            "parent_queries_json": "TEXT",
            "pattern_category": "TEXT",
            "pattern_template": "TEXT",
            "relevance_score": "REAL DEFAULT 0.0",
            "cluster_name": "TEXT DEFAULT 'Core Seed Variations'",
            "intent_explanation": "TEXT",
        }
        for col_name, col_type in keywords_new_cols.items():
            if col_name not in keywords_cols:
                conn.execute(f"ALTER TABLE keywords ADD COLUMN {col_name} {col_type};")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_keywords_norm_search ON keywords(search_id, normalized_key);"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_relevance ON keywords(relevance_score);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_cluster ON keywords(cluster_name);")

        # Backfill keywords: last_seen_at defaults to created_at
        conn.execute(
            """
            UPDATE keywords
            SET last_seen_at = created_at
            WHERE last_seen_at IS NULL OR last_seen_at = '';
            """
        )
        conn.execute(
            """
            UPDATE keywords
            SET source_name = 'youtube_autocomplete'
            WHERE source_name IS NULL OR source_name = '';
            """
        )
        conn.execute(
            """
            UPDATE keywords
            SET discovery_paths_json = '[]'
            WHERE discovery_paths_json IS NULL;
            """
        )

        # Backfill parent_queries_json from legacy parent_keyword
        cursor = conn.execute("SELECT id, parent_keyword FROM keywords WHERE parent_queries_json IS NULL;")
        for row in cursor.fetchall():
            row_id, parent_kw = row[0], row[1]
            parent_list = [parent_kw] if parent_kw else []
            conn.execute(
                "UPDATE keywords SET parent_queries_json = ? WHERE id = ?;",
                (json.dumps(parent_list), row_id),
            )

    # --------------------------------------------------------------------------
    # Migration Execution Pipeline
    # --------------------------------------------------------------------------

    def get_migrations(self) -> List[Tuple[int, str, Callable[[sqlite3.Connection], None]]]:
        """Return ordered list of migration tuples: (version, name, handler)."""
        return [
            (1, "v1_initial_schema", self._migration_v1_initial),
            (2, "v2_phase5_classification_columns", self._migration_v2_phase5_columns),
            (3, "v3_phase7_projects_provenance_columns", self._migration_v3_phase7_projects_provenance),
        ]

    def migrate(self) -> Tuple[int, List[str]]:
        """Run all pending database migrations in order.

        Returns:
            Tuple of (new_schema_version, list_of_applied_migration_names).
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if database file exists and has data before running
        has_existing_data = False
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            has_existing_data = True

        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        applied_names: List[str] = []

        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            applied_versions = self.get_applied_versions(conn)

            migrations = self.get_migrations()
            pending_migrations = [m for m in migrations if m[0] not in applied_versions]

            if not pending_migrations:
                current_ver = max(applied_versions) if applied_versions else 0
                return current_ver, []

            # If there is existing data and pending migrations, take an automatic safety backup
            if has_existing_data:
                try:
                    conn.commit()  # Flush pending WAL
                    bkp_path = self.backup_manager.create_backup(
                        source_db_path=self.db_path,
                        prefix=f"pre_migration_v{pending_migrations[0][0]}",
                    )
                    logger.info("Created pre-migration safety backup at %s", bkp_path)
                except Exception as e:
                    logger.warning("Could not create pre-migration backup: %s", e)

            # Apply pending migrations in order
            for version, name, handler in pending_migrations:
                logger.info("Applying database migration %d: %s", version, name)
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    handler(conn)
                    self.record_migration(conn, version, name)
                    conn.commit()
                    applied_names.append(name)
                    logger.info("Successfully applied migration %d: %s", version, name)
                except Exception as e:
                    conn.rollback()
                    logger.error("Failed to apply migration %d (%s): %s", version, name, e)
                    raise MigrationError(f"Migration {version} ({name}) failed: {e}") from e

            final_versions = self.get_applied_versions(conn)
            current_ver = max(final_versions) if final_versions else 0
            return current_ver, applied_names

        finally:
            conn.close()
