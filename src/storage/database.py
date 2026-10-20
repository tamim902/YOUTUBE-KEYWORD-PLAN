"""SQLite database manager for YouTube Keyword Finder.

Provides local-first persistence for:
- Research projects & session history
- Discovered and categorized keywords with multi-source provenance
- Request response cache (to reduce network load and support offline re-runs)
- Versioned migrations and atomic online backups

Uses standard library sqlite3 with thread safety, WAL mode, foreign keys, and transactions.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from src.config import DATABASE_PATH, config
from src.models.keyword import ClassificationType, KeywordItem, SourceType, infer_tail_length
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
from src.models.product_planner import (
    AffiliateContentBrief,
    AffiliateProductData,
    ContentFormatRecommendation,
    ProductOpportunityShortlist,
    ShortlistStatus,
)
from src.models.channel import ChannelProfile, get_default_four_channels
from src.models.seo import VideoDescription
from src.models.morning_report import DailyIdeaItem, DailyMorningReport
from src.models.audit import VideoSeoAudit
from src.models.analytics import (
    AnalyticsAuthStatus,
    ChannelOAuthCredentials,
    PublishingExperiment,
)
from src.models.strategy import (
    WorkflowStage,
    ProductionEffort,
    TopicUserStatus,
    ContentPillar,
    ContentCluster,
    PrioritizedTopic,
    StrategyCalendarItem,
    ContentBriefDocument,
    ProductionWorkflowProject,
    ChannelStrategySettings,
)
from src.models.validation import (
    TopicReadinessStatus,
    AngleType,
    TopicAngle,
    OwnChannelOverlapResult,
    CompetitorVideoRecord,
    ProductValidationRecord,
    TopicValidationReport,
)
from src.storage.backup import BackupManager
from src.storage.migrations import MigrationManager
from src.utils.normalization import count_tokens, normalize_keyword_key


class DatabaseManager:
    """Manages SQLite connections, schema initialization, versioned migrations, and persistence."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.backup_manager = BackupManager(backup_dir=self.db_path.parent / "backups")
        self.migration_manager = MigrationManager(
            db_path=self.db_path, backup_manager=self.backup_manager
        )

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provide a managed SQLite connection context with row factories, WAL mode, and foreign keys."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create necessary database tables, indices, and apply versioned migrations."""
        self.migration_manager.migrate()
        self._ensure_phase9_columns()
        self._ensure_phase10_tables()
        self._ensure_phase11_tables()
        self._ensure_phase12_tables()
        self._ensure_phase14_tables()
        self._ensure_phase15_tables()
        self._ensure_phase22_tables()
        self._ensure_phase23_tables()
        self._ensure_phase24_tables()
        self._ensure_phase25_tables()
        self._ensure_phase26_tables()
        self._ensure_phase31_tables()
        self._ensure_phase32_tables()

    def _ensure_phase9_columns(self) -> None:
        """Ensure Phase 9 columns exist for databases migrated prior to Phase 9."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(keywords);")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if not existing_cols:
                return
            new_cols = {
                "relevance_score": "REAL DEFAULT 0.0",
                "cluster_name": "TEXT DEFAULT 'Core Seed Variations'",
                "intent_explanation": "TEXT",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE keywords ADD COLUMN {col_name} {col_type};")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_relevance ON keywords(relevance_score);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_keywords_cluster ON keywords(cluster_name);")

    def _ensure_phase10_tables(self) -> None:
        """Ensure Phase 10 tables exist for settings, SERP caching, and quota tracking."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS serp_cache (
                    query TEXT NOT NULL,
                    language TEXT NOT NULL,
                    country TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (query, language, country)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_quota_usage (
                    date TEXT PRIMARY KEY,
                    units_used INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_research_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    language TEXT NOT NULL,
                    country TEXT NOT NULL,
                    total_videos INTEGER NOT NULL,
                    metrics_json TEXT NOT NULL,
                    summary_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_research_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    video_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel_title TEXT,
                    channel_id TEXT,
                    published_at TEXT,
                    view_count INTEGER,
                    like_count INTEGER,
                    comment_count INTEGER,
                    duration TEXT,
                    tags_json TEXT,
                    thumbnail_url TEXT,
                    video_url TEXT,
                    channel_url TEXT,
                    daily_views REAL DEFAULT 0.0,
                    rank INTEGER DEFAULT 1,
                    FOREIGN KEY(session_id) REFERENCES video_research_sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, video_id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_keyword_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    first_observed_at TEXT NOT NULL,
                    last_observed_at TEXT NOT NULL,
                    UNIQUE(video_id, keyword)
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_serp_cache_created ON serp_cache(created_at);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_v_sessions_keyword ON video_research_sessions(keyword);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_v_items_session ON video_research_items(session_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_v_assoc_video ON video_keyword_associations(video_id);"
            )

    def _ensure_phase11_tables(self) -> None:
        """Ensure Phase 11 tables exist for content opportunities, briefs, and calendar planning."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    topic TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    supporting_keywords_json TEXT NOT NULL DEFAULT '[]',
                    target_audience TEXT NOT NULL DEFAULT 'General Audience',
                    search_intent TEXT NOT NULL DEFAULT 'Informational',
                    content_format TEXT NOT NULL DEFAULT 'Step-by-step Guide',
                    opportunity_score REAL NOT NULL DEFAULT 50.0,
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate Evidence',
                    score_breakdown_json TEXT NOT NULL DEFAULT '{}',
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'Idea',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES searches(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_opp_proj ON content_opportunities(project_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_opp_score ON content_opportunities(opportunity_score);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_opp_status ON content_opportunities(status);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER UNIQUE,
                    working_title TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    brief_data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES content_opportunities(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_brief_opp ON content_briefs(opportunity_id);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_calendar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER,
                    title TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    planned_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Idea',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    notes TEXT NOT NULL DEFAULT '',
                    session_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES content_opportunities(id) ON DELETE SET NULL,
                    FOREIGN KEY(session_id) REFERENCES searches(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cal_date ON content_calendar(planned_date);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cal_status ON content_calendar(status);"
            )

    def _ensure_phase12_tables(self) -> None:
        """Ensure Phase 12 tables exist for niche product research sessions, candidate products, and video matches."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_research_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    niche TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    country TEXT NOT NULL DEFAULT 'US',
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    category_filters_json TEXT NOT NULL DEFAULT '[]',
                    search_modes_json TEXT NOT NULL DEFAULT '[]',
                    few_videos_threshold INTEGER NOT NULL DEFAULT 3,
                    min_queries_for_zero_match INTEGER NOT NULL DEFAULT 2,
                    max_queries INTEGER NOT NULL DEFAULT 15,
                    max_videos_per_query INTEGER NOT NULL DEFAULT 20,
                    request_budget INTEGER NOT NULL DEFAULT 10,
                    requests_made INTEGER NOT NULL DEFAULT 0,
                    quota_used INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Completed',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prod_sess_niche ON product_research_sessions(niche);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prod_sess_date ON product_research_sessions(created_at);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discovered_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    niche TEXT NOT NULL DEFAULT '',
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL DEFAULT 'Extracted Candidate',
                    verification_status TEXT NOT NULL DEFAULT 'Extracted Candidate',
                    extraction_confidence TEXT NOT NULL DEFAULT 'High',
                    classification TEXT NOT NULL DEFAULT 'INSUFFICIENT RESEARCH',
                    classification_reason TEXT NOT NULL DEFAULT '',
                    matching_videos_count INTEGER NOT NULL DEFAULT 0,
                    unique_channels_count INTEGER NOT NULL DEFAULT 0,
                    latest_video_date TEXT,
                    queries_executed_json TEXT NOT NULL DEFAULT '[]',
                    queries_succeeded INTEGER NOT NULL DEFAULT 0,
                    queries_failed INTEGER NOT NULL DEFAULT 0,
                    search_coverage_summary TEXT NOT NULL DEFAULT '',
                    opportunity_score REAL NOT NULL DEFAULT 50.0,
                    score_breakdown_json TEXT NOT NULL DEFAULT '{}',
                    confidence_level TEXT NOT NULL DEFAULT 'Low',
                    data_source TEXT NOT NULL DEFAULT 'Live YouTube Data API v3',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES product_research_sessions(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_disc_prod_sess ON discovered_products(session_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_disc_prod_class ON discovered_products(classification);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_disc_prod_score ON discovered_products(opportunity_score);"
            )

            # Idempotent backward-compatible column upgrades (Phase 12 & 13)
            for col_sql in [
                "ALTER TABLE product_research_sessions ADD COLUMN min_queries_for_zero_match INTEGER NOT NULL DEFAULT 2;",
                "ALTER TABLE product_research_sessions ADD COLUMN scoring_weights_json TEXT NOT NULL DEFAULT '{}';",
                "ALTER TABLE product_research_sessions ADD COLUMN ai_summary TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE product_research_sessions ADD COLUMN is_mocked INTEGER NOT NULL DEFAULT 0;",
                "ALTER TABLE product_research_sessions ADD COLUMN cancelled_at TEXT;",
                "ALTER TABLE discovered_products ADD COLUMN data_source TEXT NOT NULL DEFAULT 'Live YouTube Data API v3';",
                "ALTER TABLE discovered_products ADD COLUMN category TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE discovered_products ADD COLUMN evidence_url TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE discovered_products ADD COLUMN evidence_reference TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE discovered_products ADD COLUMN original_name TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE discovered_products ADD COLUMN audit_trail_json TEXT NOT NULL DEFAULT '[]';",
                "ALTER TABLE discovered_products ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium';",
                "ALTER TABLE discovered_products ADD COLUMN first_seen_at TEXT NOT NULL DEFAULT '';",
                "ALTER TABLE product_search_queries ADD COLUMN query_source TEXT NOT NULL DEFAULT 'ALGORITHMIC_TEMPLATE';",
                "ALTER TABLE product_search_queries ADD COLUMN error_message TEXT;",
                "ALTER TABLE product_video_matches ADD COLUMN exclusion_reason TEXT NOT NULL DEFAULT '';",
            ]:
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_video_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    session_id INTEGER,
                    video_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel_id TEXT NOT NULL DEFAULT '',
                    channel_title TEXT NOT NULL DEFAULT '',
                    publish_date TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    views INTEGER NOT NULL DEFAULT 0,
                    match_type TEXT NOT NULL DEFAULT 'Exact Model Match',
                    match_field TEXT NOT NULL DEFAULT 'title',
                    matched_terms_json TEXT NOT NULL DEFAULT '[]',
                    is_excluded INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES discovered_products(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES product_research_sessions(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pvm_product ON product_video_matches(product_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pvm_session ON product_video_matches(session_id);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_search_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    product_id INTEGER,
                    product_name TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    search_mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Success',
                    results_count INTEGER NOT NULL DEFAULT 0,
                    executed_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES product_research_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES discovered_products(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_psq_session ON product_search_queries(session_id);"
            )

    def _ensure_phase14_tables(self) -> None:
        """Ensure Phase 14 tables exist for product opportunity shortlist, affiliate briefs, and catalog."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_opportunity_shortlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    session_id INTEGER,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    niche TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    country TEXT NOT NULL DEFAULT 'US',
                    language TEXT NOT NULL DEFAULT 'en',
                    status TEXT NOT NULL DEFAULT 'Shortlisted',
                    priority TEXT NOT NULL DEFAULT 'Medium',
                    intended_format TEXT NOT NULL DEFAULT 'Product Review',
                    notes TEXT NOT NULL DEFAULT '',
                    opportunity_score REAL NOT NULL DEFAULT 50.0,
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate Evidence',
                    score_breakdown_json TEXT NOT NULL DEFAULT '{}',
                    formula_version TEXT NOT NULL DEFAULT 'v14.0',
                    matching_videos_count INTEGER NOT NULL DEFAULT 0,
                    queries_executed_count INTEGER NOT NULL DEFAULT 0,
                    supporting_keywords_json TEXT NOT NULL DEFAULT '[]',
                    affiliate_data_json TEXT NOT NULL DEFAULT '{}',
                    verification_checklist_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES discovered_products(id) ON DELETE SET NULL,
                    FOREIGN KEY(session_id) REFERENCES product_research_sessions(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shortlist_sess ON product_opportunity_shortlist(session_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shortlist_status ON product_opportunity_shortlist(status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shortlist_score ON product_opportunity_shortlist(opportunity_score);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shortlist_name ON product_opportunity_shortlist(product_name);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_content_briefs_v14 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shortlist_id INTEGER UNIQUE,
                    product_id INTEGER,
                    product_name TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    brief_data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(shortlist_id) REFERENCES product_opportunity_shortlist(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES discovered_products(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_brief_v14_shortlist ON product_content_briefs_v14(shortlist_id);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_affiliate_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    merchant TEXT NOT NULL DEFAULT 'Needs verification',
                    product_page_url TEXT NOT NULL DEFAULT '',
                    price REAL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    affiliate_program TEXT NOT NULL DEFAULT 'Needs verification',
                    commission_info TEXT NOT NULL DEFAULT 'Needs verification',
                    availability TEXT NOT NULL DEFAULT 'Unknown',
                    affiliate_link TEXT NOT NULL DEFAULT '',
                    is_verified_merchant INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(product_name, merchant)
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_aff_catalog_name ON product_affiliate_catalog(product_name);"
            )

    def _ensure_phase15_tables(self) -> None:
        """Ensure Phase 15 tables exist for saved research configurations, runs, snapshots, comparisons, alerts, and schedules."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    niche TEXT NOT NULL,
                    country TEXT NOT NULL DEFAULT 'US',
                    language TEXT NOT NULL DEFAULT 'en',
                    date_window_days INTEGER NOT NULL DEFAULT 60,
                    category_filters_json TEXT NOT NULL DEFAULT '[]',
                    query_templates_json TEXT NOT NULL DEFAULT '[]',
                    max_products_per_run INTEGER NOT NULL DEFAULT 25,
                    max_queries_per_run INTEGER NOT NULL DEFAULT 15,
                    request_budget INTEGER NOT NULL DEFAULT 15,
                    matching_mode TEXT NOT NULL DEFAULT 'Exact Model Match',
                    min_research_coverage INTEGER NOT NULL DEFAULT 2,
                    opportunity_formula_version TEXT NOT NULL DEFAULT 'v14.0',
                    enabled_discovery_methods_json TEXT NOT NULL DEFAULT '[]',
                    is_paused INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_cfg_niche ON research_monitor_configs(niche);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER,
                    niche TEXT NOT NULL,
                    run_number INTEGER NOT NULL DEFAULT 1,
                    trigger_type TEXT NOT NULL DEFAULT 'Manual',
                    status TEXT NOT NULL DEFAULT 'Pending',
                    config_snapshot_json TEXT NOT NULL DEFAULT '{}',
                    queries_attempted INTEGER NOT NULL DEFAULT 0,
                    queries_succeeded INTEGER NOT NULL DEFAULT 0,
                    queries_failed INTEGER NOT NULL DEFAULT 0,
                    failed_query_list_json TEXT NOT NULL DEFAULT '[]',
                    products_discovered INTEGER NOT NULL DEFAULT 0,
                    matching_videos_retrieved INTEGER NOT NULL DEFAULT 0,
                    live_requests_count INTEGER NOT NULL DEFAULT 0,
                    cached_requests_count INTEGER NOT NULL DEFAULT 0,
                    generated_items_count INTEGER NOT NULL DEFAULT 0,
                    provider_name TEXT NOT NULL DEFAULT 'YouTube Data API v3',
                    error_message TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(config_id) REFERENCES research_monitor_configs(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_run_cfg ON research_monitor_runs(config_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_run_niche ON research_monitor_runs(niche);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_run_status ON research_monitor_runs(status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_run_start ON research_monitor_runs(started_at);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    product_id INTEGER,
                    product_name TEXT NOT NULL,
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    niche TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    classification TEXT NOT NULL DEFAULT 'INSUFFICIENT RESEARCH',
                    classification_reason TEXT NOT NULL DEFAULT '',
                    matching_videos_count INTEGER NOT NULL DEFAULT 0,
                    latest_video_date TEXT,
                    unique_channels_count INTEGER NOT NULL DEFAULT 0,
                    observed_channels_json TEXT NOT NULL DEFAULT '[]',
                    opportunity_score REAL NOT NULL DEFAULT 50.0,
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate Evidence',
                    queries_executed_count INTEGER NOT NULL DEFAULT 0,
                    search_coverage_summary TEXT NOT NULL DEFAULT '',
                    verification_status TEXT NOT NULL DEFAULT 'Extracted Candidate',
                    data_source TEXT NOT NULL DEFAULT 'Live YouTube Data API v3',
                    snapshot_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES research_monitor_runs(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_snap_run ON research_monitor_snapshots(run_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_snap_name ON research_monitor_snapshots(product_name);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_snap_score ON research_monitor_snapshots(opportunity_score);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_a_id INTEGER NOT NULL,
                    run_b_id INTEGER NOT NULL,
                    niche TEXT NOT NULL,
                    run_a_date TEXT NOT NULL,
                    run_b_date TEXT NOT NULL,
                    newly_discovered_products_json TEXT NOT NULL DEFAULT '[]',
                    dropped_products_json TEXT NOT NULL DEFAULT '[]',
                    video_count_changes_json TEXT NOT NULL DEFAULT '[]',
                    score_changes_json TEXT NOT NULL DEFAULT '[]',
                    coverage_changes_json TEXT NOT NULL DEFAULT '[]',
                    newly_observed_channels_json TEXT NOT NULL DEFAULT '[]',
                    comparison_matrix_json TEXT NOT NULL DEFAULT '[]',
                    summary_notes TEXT NOT NULL DEFAULT '',
                    empirical_caution TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_cmp_niche ON research_monitor_comparisons(niche);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_cmp_runs ON research_monitor_comparisons(run_a_id, run_b_id);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    config_id INTEGER,
                    niche TEXT NOT NULL,
                    product_name TEXT NOT NULL DEFAULT '',
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'Info',
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    evidence_data_json TEXT NOT NULL DEFAULT '{}',
                    is_dismissed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES research_monitor_runs(id) ON DELETE CASCADE,
                    FOREIGN KEY(config_id) REFERENCES research_monitor_configs(id) ON DELETE SET NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_alr_run ON research_monitor_alerts(run_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_alr_niche ON research_monitor_alerts(niche);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_alr_dismiss ON research_monitor_alerts(is_dismissed);"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_monitor_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER UNIQUE,
                    niche TEXT NOT NULL,
                    frequency TEXT NOT NULL DEFAULT 'Weekly',
                    local_time TEXT NOT NULL DEFAULT '09:00',
                    timezone_name TEXT NOT NULL DEFAULT 'UTC',
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    next_run_at TEXT,
                    last_window_key TEXT NOT NULL DEFAULT '',
                    missed_runs_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(config_id) REFERENCES research_monitor_configs(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mon_sch_cfg ON research_monitor_schedules(config_id);"
            )

    def _ensure_phase22_tables(self) -> None:
        """Ensure Phase 22 tables exist for four-channel profiles, morning reports, ideas, and descriptions."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            # 1. Channel Profiles table (1 to 4 profiles)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_profiles (
                    id INTEGER PRIMARY KEY,
                    channel_name TEXT NOT NULL,
                    channel_handle TEXT NOT NULL DEFAULT '',
                    channel_url TEXT NOT NULL DEFAULT '',
                    channel_niche TEXT NOT NULL DEFAULT '',
                    sub_niches_json TEXT NOT NULL DEFAULT '[]',
                    target_audience TEXT NOT NULL DEFAULT '',
                    target_country TEXT NOT NULL DEFAULT 'US',
                    target_language TEXT NOT NULL DEFAULT 'en',
                    content_format TEXT NOT NULL DEFAULT 'both',
                    affiliate_enabled INTEGER NOT NULL DEFAULT 1,
                    preferred_affiliate_markets_json TEXT NOT NULL DEFAULT '[]',
                    preferred_publishing_frequency TEXT NOT NULL DEFAULT '2 videos / week',
                    existing_video_topics_json TEXT NOT NULL DEFAULT '[]',
                    excluded_topics_json TEXT NOT NULL DEFAULT '[]',
                    excluded_brands_json TEXT NOT NULL DEFAULT '[]',
                    excluded_products_json TEXT NOT NULL DEFAULT '[]',
                    excluded_keywords_json TEXT NOT NULL DEFAULT '[]',
                    channel_footer TEXT NOT NULL DEFAULT '',
                    seo_settings_json TEXT NOT NULL DEFAULT '{}',
                    daily_research_settings_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chan_niche ON channel_profiles(channel_niche);")

            # Auto-seed default 4 channels if empty
            cur = conn.execute("SELECT COUNT(*) FROM channel_profiles;")
            if cur.fetchone()[0] == 0:
                defaults = get_default_four_channels()
                for c in defaults:
                    conn.execute(
                        """
                        INSERT INTO channel_profiles (
                            id, channel_name, channel_handle, channel_url, channel_niche,
                            sub_niches_json, target_audience, target_country, target_language,
                            content_format, affiliate_enabled, preferred_affiliate_markets_json,
                            preferred_publishing_frequency, existing_video_topics_json,
                            excluded_topics_json, excluded_brands_json, excluded_products_json,
                            excluded_keywords_json, channel_footer, seo_settings_json,
                            daily_research_settings_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            c.id, c.channel_name, c.channel_handle, c.channel_url, c.channel_niche,
                            json.dumps(c.sub_niches), c.target_audience, c.target_country, c.target_language,
                            c.content_format, 1 if c.affiliate_enabled else 0,
                            json.dumps(c.preferred_affiliate_markets), c.preferred_publishing_frequency,
                            json.dumps(c.existing_video_topics), json.dumps(c.excluded_topics),
                            json.dumps(c.excluded_brands), json.dumps(c.excluded_products),
                            json.dumps(c.excluded_keywords), c.channel_footer,
                            json.dumps(c.seo_settings), json.dumps(c.daily_research_settings),
                            c.created_at, c.updated_at,
                        ),
                    )

            # 2. Daily Morning Reports
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_morning_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT NOT NULL,
                    timezone_name TEXT NOT NULL DEFAULT 'Asia/Dhaka',
                    scheduled_time TEXT NOT NULL DEFAULT '07:00',
                    status TEXT NOT NULL DEFAULT 'Completed',
                    total_channels_processed INTEGER NOT NULL DEFAULT 4,
                    total_ideas_generated INTEGER NOT NULL DEFAULT 0,
                    total_queries_executed INTEGER NOT NULL DEFAULT 0,
                    api_quota_units_used INTEGER NOT NULL DEFAULT 0,
                    summary_notes TEXT NOT NULL DEFAULT '',
                    error_message TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_morning_rep_date ON daily_morning_reports(run_date);")

            # 3. Daily Idea Items (All 18 Fields)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_idea_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    proposed_topic TEXT NOT NULL,
                    main_keyword TEXT NOT NULL,
                    supporting_keywords_json TEXT NOT NULL DEFAULT '[]',
                    search_intent TEXT NOT NULL DEFAULT 'Informational',
                    target_viewer TEXT NOT NULL DEFAULT 'General Audience',
                    why_topic_worth_researching TEXT NOT NULL DEFAULT '',
                    recent_relevant_videos_found INTEGER NOT NULL DEFAULT 0,
                    exact_research_window TEXT NOT NULL DEFAULT '',
                    source_and_coverage_summary TEXT NOT NULL DEFAULT '',
                    potential_product_match TEXT,
                    affiliate_availability_status TEXT NOT NULL DEFAULT 'Unverified',
                    opportunity_estimate REAL NOT NULL DEFAULT 50.0,
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate Confidence',
                    suggested_video_format TEXT NOT NULL DEFAULT 'Long-form In-depth',
                    seo_focused_title_options_json TEXT NOT NULL DEFAULT '[]',
                    suggested_thumbnail_concept TEXT NOT NULL DEFAULT '',
                    description_draft TEXT NOT NULL DEFAULT '',
                    next_recommended_action TEXT NOT NULL DEFAULT '',
                    review_label TEXT NOT NULL DEFAULT 'Ready for further review',
                    gap_state TEXT NOT NULL DEFAULT 'FEW MATCHING RECENT VIDEOS FOUND',
                    sample_video_ids_json TEXT NOT NULL DEFAULT '[]',
                    sample_video_titles_json TEXT NOT NULL DEFAULT '[]',
                    is_saved INTEGER NOT NULL DEFAULT 0,
                    is_rejected INTEGER NOT NULL DEFAULT 0,
                    is_marked_covered INTEGER NOT NULL DEFAULT 0,
                    is_added_to_calendar INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(report_id) REFERENCES daily_morning_reports(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_idea_rep ON daily_idea_items(report_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_idea_chan ON daily_idea_items(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_idea_saved ON daily_idea_items(is_saved);")

            # 4. Video Descriptions (Description Studio)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    character_count INTEGER NOT NULL DEFAULT 0,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_desc_chan ON video_descriptions(channel_id);")

    def _ensure_phase23_tables(self) -> None:
        """Ensure Phase 23 tables exist for Video SEO Audits and Audit Revisions."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_seo_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    idea_id INTEGER,
                    primary_keyword TEXT NOT NULL,
                    secondary_keywords_json TEXT NOT NULL DEFAULT '[]',
                    proposed_title TEXT NOT NULL,
                    draft_description TEXT NOT NULL DEFAULT '',
                    script_text TEXT NOT NULL DEFAULT '',
                    thumbnail_concept TEXT NOT NULL DEFAULT '',
                    video_url TEXT NOT NULL DEFAULT '',
                    is_published_url INTEGER NOT NULL DEFAULT 0,
                    scores_json TEXT NOT NULL DEFAULT '{}',
                    findings_json TEXT NOT NULL DEFAULT '[]',
                    recommendations_json TEXT NOT NULL DEFAULT '{}',
                    checklist_json TEXT NOT NULL DEFAULT '[]',
                    revision_number INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seo_audits_chan ON video_seo_audits(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seo_audits_created ON video_seo_audits(created_at);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_seo_audit_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id INTEGER NOT NULL,
                    revision_number INTEGER NOT NULL,
                    proposed_title TEXT NOT NULL,
                    draft_description TEXT NOT NULL DEFAULT '',
                    script_text TEXT NOT NULL DEFAULT '',
                    thumbnail_concept TEXT NOT NULL DEFAULT '',
                    scores_json TEXT NOT NULL DEFAULT '{}',
                    findings_json TEXT NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(audit_id) REFERENCES video_seo_audits(id) ON DELETE CASCADE
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seo_audit_rev_audit ON video_seo_audit_revisions(audit_id);")

    def _ensure_phase24_tables(self) -> None:
        """Ensure Phase 24 tables exist for YouTube Analytics OAuth credentials, snapshots, and publishing experiments."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_analytics_credentials (
                    channel_id INTEGER PRIMARY KEY,
                    channel_name TEXT NOT NULL,
                    client_id TEXT NOT NULL DEFAULT '',
                    client_secret TEXT NOT NULL DEFAULT '',
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expiry TEXT,
                    scopes_json TEXT NOT NULL DEFAULT '[]',
                    auth_status TEXT NOT NULL DEFAULT 'NOT_CONNECTED',
                    connected_at TEXT,
                    last_refreshed_at TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_analytics_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    date_start TEXT NOT NULL,
                    date_end TEXT NOT NULL,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    is_authorized INTEGER NOT NULL DEFAULT 0,
                    retrieved_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_chan ON channel_analytics_snapshots(channel_id);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS publishing_experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    experiment_name TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    video_title TEXT NOT NULL DEFAULT '',
                    experiment_type TEXT NOT NULL,
                    hypothesis TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Running',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    pre_metrics_json TEXT NOT NULL DEFAULT '{}',
                    post_metrics_json TEXT NOT NULL DEFAULT '{}',
                    outcome_conclusion TEXT NOT NULL DEFAULT '',
                    is_conclusive INTEGER NOT NULL DEFAULT 0,
                    confounding_factors_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_chan ON publishing_experiments(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_status ON publishing_experiments(status);")

    def _ensure_phase25_tables(self) -> None:
        """Ensure Phase 25 tables exist for Content Strategy Autopilot across four channels."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_strategy_settings (
                    channel_id INTEGER PRIMARY KEY,
                    videos_per_week INTEGER NOT NULL DEFAULT 2,
                    longform_pct INTEGER NOT NULL DEFAULT 70,
                    shorts_pct INTEGER NOT NULL DEFAULT 30,
                    weekly_production_hours_budget REAL NOT NULL DEFAULT 12.0,
                    preferred_publishing_days_json TEXT NOT NULL DEFAULT '["Tuesday", "Saturday"]',
                    preferred_duration_range TEXT NOT NULL DEFAULT '8-15 minutes',
                    strategic_priority TEXT NOT NULL DEFAULT 'Build topical authority with foundational how-to guides',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_pillars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    pillar_name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    audience_problem TEXT NOT NULL DEFAULT '',
                    target_keywords_json TEXT NOT NULL DEFAULT '[]',
                    candidate_topics_json TEXT NOT NULL DEFAULT '[]',
                    existing_coverage_count INTEGER NOT NULL DEFAULT 0,
                    potential_affiliate_relevance TEXT NOT NULL DEFAULT 'Low',
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate Evidence',
                    is_approved INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pillar_chan ON content_pillars(channel_id);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    pillar_id INTEGER,
                    cluster_name TEXT NOT NULL,
                    pillar_video_title TEXT NOT NULL,
                    supporting_video_titles_json TEXT NOT NULL DEFAULT '[]',
                    comparison_video_titles_json TEXT NOT NULL DEFAULT '[]',
                    review_video_titles_json TEXT NOT NULL DEFAULT '[]',
                    faq_video_titles_json TEXT NOT NULL DEFAULT '[]',
                    cluster_rationale TEXT NOT NULL DEFAULT '',
                    anti_cannibalization_notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_chan ON content_clusters(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_pillar ON content_clusters(pillar_id);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prioritized_topics (
                    topic_id TEXT PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    proposed_title TEXT NOT NULL,
                    target_keyword TEXT NOT NULL,
                    search_intent TEXT NOT NULL DEFAULT 'Informational',
                    channel_relevance_score REAL NOT NULL DEFAULT 0.0,
                    search_intent_score REAL NOT NULL DEFAULT 0.0,
                    keyword_evidence_score REAL NOT NULL DEFAULT 0.0,
                    recent_video_evidence_score REAL NOT NULL DEFAULT 0.0,
                    research_coverage_score REAL NOT NULL DEFAULT 0.0,
                    product_relevance_score REAL NOT NULL DEFAULT 0.0,
                    composite_priority_score REAL NOT NULL DEFAULT 0.0,
                    estimated_production_effort TEXT NOT NULL DEFAULT 'Medium',
                    selection_rationale TEXT NOT NULL DEFAULT '',
                    supporting_sources_json TEXT NOT NULL DEFAULT '[]',
                    research_date TEXT NOT NULL DEFAULT '',
                    confidence_level TEXT NOT NULL DEFAULT 'Moderate',
                    missing_evidence TEXT NOT NULL DEFAULT '',
                    suggested_next_step TEXT NOT NULL DEFAULT '',
                    user_status TEXT NOT NULL DEFAULT 'Suggested',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_chan ON prioritized_topics(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_status ON prioritized_topics(user_status);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_calendar_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL DEFAULT '',
                    topic TEXT NOT NULL,
                    target_keyword TEXT NOT NULL DEFAULT '',
                    search_intent TEXT NOT NULL DEFAULT 'Informational',
                    suggested_format TEXT NOT NULL DEFAULT 'Long-form',
                    working_title TEXT NOT NULL DEFAULT '',
                    production_status TEXT NOT NULL DEFAULT 'Planned',
                    planned_date TEXT NOT NULL,
                    evidence_summary TEXT NOT NULL DEFAULT '',
                    required_research TEXT NOT NULL DEFAULT '',
                    affiliate_disclosure_required INTEGER NOT NULL DEFAULT 0,
                    production_hours_estimate REAL NOT NULL DEFAULT 4.0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_chan ON strategy_calendar_items(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_date ON strategy_calendar_items(planned_date);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_brief_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    target_viewer TEXT NOT NULL DEFAULT '',
                    viewer_problem TEXT NOT NULL DEFAULT '',
                    search_intent TEXT NOT NULL DEFAULT 'Informational',
                    primary_keyword TEXT NOT NULL DEFAULT '',
                    supporting_keywords_json TEXT NOT NULL DEFAULT '[]',
                    main_promise TEXT NOT NULL DEFAULT '',
                    title_options_json TEXT NOT NULL DEFAULT '[]',
                    video_structure_json TEXT NOT NULL DEFAULT '[]',
                    questions_to_answer_json TEXT NOT NULL DEFAULT '[]',
                    comparison_criteria_json TEXT NOT NULL DEFAULT '[]',
                    unverified_facts_json TEXT NOT NULL DEFAULT '[]',
                    suggested_research_sources_json TEXT NOT NULL DEFAULT '[]',
                    thumbnail_concept TEXT NOT NULL DEFAULT '',
                    description_draft TEXT NOT NULL DEFAULT '',
                    affiliate_disclosure_reminder TEXT NOT NULL DEFAULT '',
                    seo_prepublish_checklist_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brief_chan ON content_brief_documents(channel_id);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS production_workflow_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL DEFAULT '',
                    current_stage TEXT NOT NULL DEFAULT 'Idea',
                    stage_history_json TEXT NOT NULL DEFAULT '[]',
                    blockers_json TEXT NOT NULL DEFAULT '[]',
                    checklist_completed_json TEXT NOT NULL DEFAULT '{}',
                    brief_id INTEGER,
                    calendar_item_id INTEGER,
                    is_cancelled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_chan ON production_workflow_projects(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_stage ON production_workflow_projects(current_stage);")

    def _ensure_phase26_tables(self) -> None:
        """Ensure Phase 26 tables exist for Topic Validation Engine & Growth Intelligence."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS topic_validation_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    topic TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    secondary_keywords_json TEXT NOT NULL DEFAULT '[]',
                    search_intent TEXT NOT NULL DEFAULT 'Informational / How-To',
                    target_viewer TEXT NOT NULL DEFAULT 'General Audience',
                    niche_match_score REAL NOT NULL DEFAULT 0.0,
                    intent_clarity_score REAL NOT NULL DEFAULT 0.0,
                    keyword_evidence_score REAL NOT NULL DEFAULT 0.0,
                    recent_video_evidence_score REAL NOT NULL DEFAULT 0.0,
                    own_channel_overlap_score REAL NOT NULL DEFAULT 100.0,
                    product_relevance_score REAL NOT NULL DEFAULT 0.0,
                    composite_opportunity_score REAL NOT NULL DEFAULT 0.0,
                    confidence_tier TEXT NOT NULL DEFAULT 'Moderate Evidence',
                    readiness_status TEXT NOT NULL DEFAULT 'Ready for Human Review',
                    what_supports_idea_json TEXT NOT NULL DEFAULT '[]',
                    what_weakens_idea_json TEXT NOT NULL DEFAULT '[]',
                    what_remains_unknown_json TEXT NOT NULL DEFAULT '[]',
                    further_research_needed_json TEXT NOT NULL DEFAULT '[]',
                    gap_state TEXT NOT NULL DEFAULT 'FEW MATCHING RECENT VIDEOS FOUND',
                    queries_executed_json TEXT NOT NULL DEFAULT '[]',
                    recent_videos_count INTEGER NOT NULL DEFAULT 0,
                    competitor_videos_json TEXT NOT NULL DEFAULT '[]',
                    suggested_angles_json TEXT NOT NULL DEFAULT '[]',
                    product_validation_json TEXT,
                    is_approved INTEGER NOT NULL DEFAULT 0,
                    is_rejected INTEGER NOT NULL DEFAULT 0,
                    is_saved INTEGER NOT NULL DEFAULT 0,
                    is_added_to_calendar INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_val_chan ON topic_validation_reports(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_val_status ON topic_validation_reports(readiness_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_val_appr ON topic_validation_reports(is_approved);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_val_saved ON topic_validation_reports(is_saved);")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS competitor_video_records (
                    video_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    channel_title TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    view_count INTEGER,
                    duration TEXT NOT NULL DEFAULT '',
                    video_url TEXT NOT NULL DEFAULT '',
                    matching_query TEXT NOT NULL DEFAULT '',
                    relevance_reason TEXT NOT NULL DEFAULT '',
                    relative_age_days INTEGER NOT NULL DEFAULT 0,
                    views_per_day REAL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comp_query ON competitor_video_records(matching_query);")

    def _ensure_phase31_tables(self) -> None:
        """Ensure Phase 31 tables exist for Personal YouTube SEO Coach & Action Center."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_center_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_key TEXT UNIQUE NOT NULL,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    short_summary TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    target_page TEXT NOT NULL,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    what_to_do TEXT NOT NULL,
                    why_it_matters TEXT NOT NULL,
                    how_to_do_it_json TEXT NOT NULL DEFAULT '[]',
                    what_to_check_json TEXT NOT NULL DEFAULT '[]',
                    what_comes_next TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_task_chan ON action_center_tasks(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_task_status ON action_center_tasks(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action_task_key ON action_center_tasks(task_key);")

    def _ensure_phase32_tables(self) -> None:
        """Ensure Phase 32 tables exist for Video Content Factory & One-Click Packages."""
        if not self.db_path.exists():
            return
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_content_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    primary_keyword TEXT NOT NULL,
                    supporting_keywords_json TEXT NOT NULL DEFAULT '[]',
                    format_type TEXT NOT NULL DEFAULT 'long-form',
                    purpose_type TEXT NOT NULL DEFAULT 'tutorial',
                    target_viewer TEXT NOT NULL DEFAULT '',
                    selected_title TEXT NOT NULL,
                    title_options_json TEXT NOT NULL DEFAULT '[]',
                    outline_json TEXT NOT NULL DEFAULT '{}',
                    description_text TEXT NOT NULL DEFAULT '',
                    thumbnail_concept_json TEXT NOT NULL DEFAULT '{}',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    evidence_checklist_json TEXT NOT NULL DEFAULT '{}',
                    seo_readiness_json TEXT NOT NULL DEFAULT '{}',
                    is_saved INTEGER NOT NULL DEFAULT 1,
                    is_exported INTEGER NOT NULL DEFAULT 0,
                    calendar_item_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pkg_chan ON video_content_packages(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pkg_created ON video_content_packages(created_at);")


    def migrate_db(self, conn: Optional[sqlite3.Connection] = None) -> None:
        """Run all pending schema migrations."""
        self.migration_manager.migrate()
        self._ensure_phase9_columns()
        self._ensure_phase10_tables()
        self._ensure_phase11_tables()
        self._ensure_phase12_tables()
        self._ensure_phase14_tables()
        self._ensure_phase15_tables()
        self._ensure_phase22_tables()
        self._ensure_phase23_tables()
        self._ensure_phase24_tables()
        self._ensure_phase25_tables()
        self._ensure_phase26_tables()
        self._ensure_phase31_tables()
        self._ensure_phase32_tables()


    # --------------------------------------------------------------------------
    # Research Project Management
    # --------------------------------------------------------------------------

    def save_search(
        self,
        seed_keyword: str,
        language: str,
        country: str,
        max_depth: int,
        request_budget: int,
        total_results: int = 0,
        project_name: Optional[str] = None,
        status: str = "completed",
        stop_reason: Optional[str] = None,
        parameters_json: Optional[str] = None,
        requests_made: int = 0,
        error_message: Optional[str] = None,
    ) -> int:
        """Record a research project/session and return its database ID."""
        now = datetime.now(timezone.utc).isoformat()
        proj_name = project_name.strip() if project_name and project_name.strip() else seed_keyword.strip()

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO searches (
                    seed_keyword, language, country, max_depth, request_budget, total_results,
                    created_at, project_name, updated_at, status, stop_reason,
                    parameters_json, requests_made, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    seed_keyword,
                    language,
                    country,
                    max_depth,
                    request_budget,
                    total_results,
                    now,
                    proj_name,
                    now,
                    status,
                    stop_reason,
                    parameters_json,
                    requests_made,
                    error_message,
                ),
            )
            return int(cursor.lastrowid)

    def update_search(
        self,
        search_id: int,
        total_results: Optional[int] = None,
        status: Optional[str] = None,
        stop_reason: Optional[str] = None,
        requests_made: Optional[int] = None,
        error_message: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> bool:
        """Update research project metadata, counters, or status."""
        now = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = ?"]
        params: List[Any] = [now]

        if total_results is not None:
            updates.append("total_results = ?")
            params.append(total_results)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if stop_reason is not None:
            updates.append("stop_reason = ?")
            params.append(stop_reason)
        if requests_made is not None:
            updates.append("requests_made = ?")
            params.append(requests_made)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if project_name is not None and project_name.strip():
            updates.append("project_name = ?")
            params.append(project_name.strip())

        params.append(search_id)
        sql = f"UPDATE searches SET {', '.join(updates)} WHERE id = ?;"

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount > 0

    def rename_project(self, search_id: int, new_name: str) -> bool:
        """Rename an existing research project."""
        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Project name cannot be empty.")
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE searches SET project_name = ?, updated_at = ? WHERE id = ?;",
                (clean_name, now, search_id),
            )
            return cursor.rowcount > 0

    def get_project(self, search_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve complete project metadata for a single research session."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, seed_keyword, language, country, max_depth,
                       request_budget, total_results, created_at,
                       project_name, updated_at, status, stop_reason,
                       parameters_json, requests_made, error_message
                FROM searches
                WHERE id = ?;
                """,
                (search_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if not d.get("project_name"):
                d["project_name"] = d["seed_keyword"]
            if not d.get("updated_at"):
                d["updated_at"] = d["created_at"]
            if not d.get("status"):
                d["status"] = "completed"
            return d

    def list_projects(
        self,
        search_query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List saved research projects, optionally filtered by keyword/name."""
        with self.get_connection() as conn:
            if search_query and search_query.strip():
                term = f"%{search_query.strip()}%"
                cursor = conn.execute(
                    """
                    SELECT id, seed_keyword, language, country, max_depth,
                           request_budget, total_results, created_at,
                           project_name, updated_at, status, stop_reason,
                           parameters_json, requests_made, error_message
                    FROM searches
                    WHERE project_name LIKE ? OR seed_keyword LIKE ?
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (term, term, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, seed_keyword, language, country, max_depth,
                           request_budget, total_results, created_at,
                           project_name, updated_at, status, stop_reason,
                           parameters_json, requests_made, error_message
                    FROM searches
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
            projects = []
            for row in cursor.fetchall():
                d = dict(row)
                if not d.get("project_name"):
                    d["project_name"] = d["seed_keyword"]
                if not d.get("updated_at"):
                    d["updated_at"] = d["created_at"]
                if not d.get("status"):
                    d["status"] = "completed"
                projects.append(d)
            return projects

    def get_recent_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent research sessions ordered by date descending."""
        return self.list_projects(limit=limit)

    def delete_search(self, search_id: int) -> bool:
        """Delete a research session and all its associated keywords."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM keywords WHERE search_id = ?;", (search_id,))
            cursor = conn.execute("DELETE FROM searches WHERE id = ?;", (search_id,))
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Keyword Persistence, Provenance & Upserts
    # --------------------------------------------------------------------------

    def save_keywords(
        self,
        search_id: int,
        items: List[Any],
    ) -> int:
        """Batch save or upsert keyword items associated with a search project.

        Guarantees that rerunning research does not create duplicate keyword records,
        while strictly merging multi-source provenance and updating discovery timestamps.
        """
        if not items:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as conn:
            # 1. Consolidate incoming batch by normalized_key to merge duplicates within the batch
            consolidated: Dict[str, Dict[str, Any]] = {}
            for raw_item in items:
                if not hasattr(raw_item, "keyword"):
                    continue
                kw_text = raw_item.keyword
                norm_key = getattr(raw_item, "normalized_key", None) or normalize_keyword_key(kw_text)
                w_count = getattr(raw_item, "word_count", None) or count_tokens(kw_text)
                tail = getattr(raw_item, "tail_length", None) or infer_tail_length(w_count).value

                intents_list = getattr(raw_item, "intent_labels", None)
                if not intents_list and hasattr(raw_item, "classification"):
                    cls_val = raw_item.classification
                    intents_list = [cls_val.value if hasattr(cls_val, "value") else str(cls_val)]
                if not intents_list:
                    intents_list = ["Informational"]

                raw_src = getattr(raw_item, "source", None) or getattr(raw_item, "source_type", "autocomplete")
                src_val = raw_src.value if hasattr(raw_src, "value") else str(raw_src)
                sources_list = getattr(raw_item, "sources", None) or [src_val]

                parents = getattr(raw_item, "parent_queries", None)
                if not parents and getattr(raw_item, "parent_keyword", None):
                    parents = [raw_item.parent_keyword]
                parents = parents or []

                disc_paths = getattr(raw_item, "discovery_paths", 1)
                paths_list = [disc_paths] if isinstance(disc_paths, int) else (disc_paths or [])

                src_name = getattr(raw_item, "source_name", "youtube_autocomplete")
                depth_val = getattr(raw_item, "depth", 0)
                lang_val = getattr(raw_item, "language", "en")
                country_val = getattr(raw_item, "country", "US")
                seed_val = getattr(raw_item, "seed_keyword", kw_text)

                pat_cat = getattr(raw_item, "pattern_category", None)
                if hasattr(pat_cat, "value"):
                    pat_cat = pat_cat.value
                pat_tpl = getattr(raw_item, "pattern_template", None)

                created_time = getattr(raw_item, "created_at", None)
                if isinstance(created_time, datetime):
                    created_iso = created_time.isoformat()
                elif isinstance(created_time, str):
                    created_iso = created_time
                else:
                    created_iso = getattr(raw_item, "first_discovered_at", now_iso)

                rel_score = float(getattr(raw_item, "relevance_score", 0.0) or 0.0)
                cluster_val = str(getattr(raw_item, "cluster_name", "Core Seed Variations") or "Core Seed Variations")
                intent_expl = str(getattr(raw_item, "intent_explanation", "") or "")

                if norm_key not in consolidated:
                    consolidated[norm_key] = {
                        "kw_text": kw_text,
                        "seed_val": seed_val,
                        "src_val": src_val,
                        "intents_list": list(intents_list),
                        "depth_val": depth_val,
                        "parents": list(parents),
                        "lang_val": lang_val,
                        "country_val": country_val,
                        "created_iso": created_iso,
                        "norm_key": norm_key,
                        "tail": tail,
                        "sources_list": list(sources_list),
                        "w_count": w_count,
                        "src_name": src_name,
                        "paths_list": list(paths_list),
                        "pat_cat": pat_cat,
                        "pat_tpl": pat_tpl,
                        "rel_score": rel_score,
                        "cluster_val": cluster_val,
                        "intent_expl": intent_expl,
                    }
                else:
                    entry = consolidated[norm_key]
                    merged_srcs = set(entry["sources_list"]) | set(sources_list)
                    entry["sources_list"] = list(sorted(merged_srcs))
                    if "autocomplete" in entry["sources_list"] or SourceType.AUTOCOMPLETE.value in entry["sources_list"]:
                        entry["src_val"] = "autocomplete"
                    for p in parents:
                        if p not in entry["parents"]:
                            entry["parents"].append(p)
                    for path in paths_list:
                        if path not in entry["paths_list"]:
                            entry["paths_list"].append(path)
                    for intent in intents_list:
                        if intent not in entry["intents_list"]:
                            entry["intents_list"].append(intent)
                    if depth_val < entry["depth_val"]:
                        entry["depth_val"] = depth_val
                    if rel_score > entry.get("rel_score", 0.0):
                        entry["rel_score"] = rel_score
                    if cluster_val and cluster_val != "Core Seed Variations":
                        entry["cluster_val"] = cluster_val
                    if intent_expl:
                        entry["intent_expl"] = intent_expl

            # 2. Fetch existing records for this search to prevent duplicates across runs
            cursor = conn.execute(
                """
                SELECT id, normalized_key, source_type, sources_json,
                       parent_queries_json, discovery_paths_json
                FROM keywords
                WHERE search_id = ?;
                """,
                (search_id,),
            )
            existing_records = {
                row["normalized_key"]: {
                    "id": row["id"],
                    "source_type": row["source_type"],
                    "sources_json": row["sources_json"],
                    "parent_queries_json": row["parent_queries_json"],
                    "discovery_paths_json": row["discovery_paths_json"],
                }
                for row in cursor.fetchall()
                if row["normalized_key"]
            }

            rows_to_insert = []
            for norm_key, item_data in consolidated.items():
                intents_json = json.dumps(item_data["intents_list"])
                sources_json = json.dumps(item_data["sources_list"])

                if norm_key in existing_records:
                    # Update existing record: merge sources, parents, and update last_seen_at
                    rec = existing_records[norm_key]
                    row_id = rec["id"]

                    try:
                        prev_sources = json.loads(rec["sources_json"]) if rec["sources_json"] else []
                    except Exception:
                        prev_sources = [rec["source_type"]]

                    try:
                        prev_parents = json.loads(rec["parent_queries_json"]) if rec["parent_queries_json"] else []
                    except Exception:
                        prev_parents = []

                    merged_sources = list(sorted(set(prev_sources) | set(item_data["sources_list"])))
                    merged_parents = list(dict.fromkeys(prev_parents + item_data["parents"]))

                    # Retain autocomplete source_type if ever discovered via autocomplete
                    final_source_type = rec["source_type"]
                    if SourceType.AUTOCOMPLETE.value in merged_sources or "autocomplete" in merged_sources:
                        final_source_type = "autocomplete"

                    conn.execute(
                        """
                        UPDATE keywords
                        SET sources_json = ?, parent_queries_json = ?, source_type = ?, last_seen_at = ?,
                            relevance_score = MAX(COALESCE(relevance_score, 0), ?),
                            cluster_name = CASE WHEN ? != 'Core Seed Variations' THEN ? ELSE COALESCE(cluster_name, 'Core Seed Variations') END
                        WHERE id = ?;
                        """,
                        (
                            json.dumps(merged_sources),
                            json.dumps(merged_parents),
                            final_source_type,
                            now_iso,
                            item_data["rel_score"],
                            item_data["cluster_val"],
                            item_data["cluster_val"],
                            row_id,
                        ),
                    )
                else:
                    rows_to_insert.append(
                        (
                            search_id,
                            item_data["kw_text"],
                            item_data["seed_val"],
                            item_data["src_val"],
                            item_data["intents_list"][0],
                            item_data["depth_val"],
                            item_data["parents"][0] if item_data["parents"] else None,
                            item_data["lang_val"],
                            item_data["country_val"],
                            item_data["created_iso"],
                            norm_key,
                            item_data["tail"],
                            intents_json,
                            sources_json,
                            item_data["w_count"],
                            item_data["src_name"],
                            now_iso,
                            json.dumps(item_data["paths_list"]),
                            json.dumps(item_data["parents"]),
                            item_data["pat_cat"],
                            item_data["pat_tpl"],
                            item_data["rel_score"],
                            item_data["cluster_val"],
                            item_data["intent_expl"],
                        )
                    )

            if rows_to_insert:
                conn.executemany(
                    """
                    INSERT INTO keywords (
                        search_id, keyword, seed_keyword, source_type, classification,
                        depth, parent_keyword, language, country, created_at,
                        normalized_key, tail_length, intent_labels, sources_json, word_count,
                        source_name, last_seen_at, discovery_paths_json, parent_queries_json,
                        pattern_category, pattern_template, relevance_score, cluster_name, intent_explanation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    rows_to_insert,
                )

            # Update total results count in searches
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM keywords WHERE search_id = ?;", (search_id,)
            )
            count = cursor.fetchone()["cnt"]
            conn.execute(
                "UPDATE searches SET total_results = ?, updated_at = ? WHERE id = ?;",
                (count, now_iso, search_id),
            )

        return len(items)

    def get_keywords_by_search_id(self, search_id: int) -> List[Dict[str, Any]]:
        """Retrieve all keyword records belonging to a search session with parsed JSON provenance."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, search_id, keyword, seed_keyword, source_type,
                       classification, depth, parent_keyword, language,
                       country, created_at, normalized_key, tail_length,
                       intent_labels, sources_json, word_count,
                       source_name, last_seen_at, discovery_paths_json,
                       parent_queries_json, pattern_category, pattern_template,
                       COALESCE(relevance_score, 0.0) as relevance_score,
                       COALESCE(cluster_name, 'Core Seed Variations') as cluster_name,
                       COALESCE(intent_explanation, '') as intent_explanation
                FROM keywords
                WHERE search_id = ?
                ORDER BY id ASC;
                """,
                (search_id,),
            )
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                try:
                    d["intent_labels"] = (
                        json.loads(d["intent_labels"]) if d.get("intent_labels") else []
                    )
                except Exception:
                    d["intent_labels"] = [d.get("classification") or "Informational"]

                try:
                    d["sources"] = (
                        json.loads(d["sources_json"])
                        if d.get("sources_json")
                        else [d["source_type"]]
                    )
                except Exception:
                    d["sources"] = [d["source_type"]]

                try:
                    d["parent_queries"] = (
                        json.loads(d["parent_queries_json"])
                        if d.get("parent_queries_json")
                        else ([d["parent_keyword"]] if d.get("parent_keyword") else [])
                    )
                except Exception:
                    d["parent_queries"] = [d["parent_keyword"]] if d.get("parent_keyword") else []

                try:
                    d["discovery_paths"] = (
                        json.loads(d["discovery_paths_json"])
                        if d.get("discovery_paths_json")
                        else [1]
                    )
                except Exception:
                    d["discovery_paths"] = [1]

                results.append(d)
            return results

    def update_keyword_cluster(self, search_id: int, keyword: str, new_cluster: str) -> bool:
        """Move a keyword to a new cluster in the database."""
        clean_cluster = new_cluster.strip()
        if not clean_cluster:
            return False
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE keywords
                SET cluster_name = ?
                WHERE search_id = ? AND keyword = ?;
                """,
                (clean_cluster, search_id, keyword.strip()),
            )
            return cursor.rowcount > 0

    def rename_project_cluster(self, search_id: int, old_cluster: str, new_cluster: str) -> int:
        """Rename an entire cluster within a search project."""
        clean_new = new_cluster.strip()
        if not clean_new:
            return 0
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE keywords
                SET cluster_name = ?
                WHERE search_id = ? AND cluster_name = ?;
                """,
                (clean_new, search_id, old_cluster.strip()),
            )
            return cursor.rowcount

    # --------------------------------------------------------------------------
    # Autocomplete Caching & Cache Policies
    # --------------------------------------------------------------------------

    def get_cached_suggestions(
        self,
        query: str,
        language: str,
        country: str,
        max_age_seconds: Optional[int] = None,
    ) -> Optional[List[str]]:
        """Retrieve cached autocomplete responses if available and within TTL."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT results_json, created_at FROM autocomplete_cache
                WHERE query = ? AND language = ? AND country = ?;
                """,
                (query.strip(), language, country),
            )
            row = cursor.fetchone()
            if row:
                if max_age_seconds is not None:
                    try:
                        cached_time = datetime.fromisoformat(row["created_at"])
                        if cached_time.tzinfo is None:
                            cached_time = cached_time.replace(tzinfo=timezone.utc)
                        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
                        if age > max_age_seconds:
                            return None  # Expired cache
                    except Exception:
                        return None

                try:
                    return json.loads(row["results_json"])
                except json.JSONDecodeError:
                    return None
            return None

    def set_cached_suggestions(
        self, query: str, language: str, country: str, results: List[str]
    ) -> None:
        """Store autocomplete suggestions into local cache with locale-specific key."""
        now = datetime.now(timezone.utc).isoformat()
        results_json = json.dumps(results, ensure_ascii=False)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO autocomplete_cache (
                    query, language, country, results_json, created_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (query.strip(), language, country, results_json, now),
            )

    def get_cache_stats(self, max_age_seconds: int = 86400) -> Dict[str, Any]:
        """Inspect cache entries and return statistics regarding active and expired items."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT query, language, country, created_at FROM autocomplete_cache;")
            rows = cursor.fetchall()

        total = len(rows)
        expired = 0
        now = datetime.now(timezone.utc)
        oldest_ts = None
        newest_ts = None

        for r in rows:
            ts_str = r["created_at"]
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if (now - dt).total_seconds() > max_age_seconds:
                    expired += 1
                if oldest_ts is None or dt < oldest_ts:
                    oldest_ts = dt
                if newest_ts is None or dt > newest_ts:
                    newest_ts = dt
            except Exception:
                expired += 1

        active = total - expired
        return {
            "total_cached_queries": total,
            "active_cached_queries": active,
            "expired_cached_queries": expired,
            "cache_ttl_seconds": max_age_seconds,
            "oldest_entry": oldest_ts.isoformat() if oldest_ts else None,
            "newest_entry": newest_ts.isoformat() if newest_ts else None,
        }

    def clear_cache(self, expired_only: bool = False, max_age_seconds: int = 86400) -> int:
        """Clear cached autocomplete responses without altering research project history."""
        with self.get_connection() as conn:
            if not expired_only:
                cursor = conn.execute("DELETE FROM autocomplete_cache;")
                return cursor.rowcount
            else:
                cursor = conn.execute("SELECT query, language, country, created_at FROM autocomplete_cache;")
                rows = cursor.fetchall()
                expired_keys = []
                now = datetime.now(timezone.utc)
                for r in rows:
                    try:
                        cached_time = datetime.fromisoformat(r["created_at"])
                        if cached_time.tzinfo is None:
                            cached_time = cached_time.replace(tzinfo=timezone.utc)
                        if (now - cached_time).total_seconds() > max_age_seconds:
                            expired_keys.append((r["query"], r["language"], r["country"]))
                    except Exception:
                        expired_keys.append((r["query"], r["language"], r["country"]))

                if expired_keys:
                    conn.executemany(
                        "DELETE FROM autocomplete_cache WHERE query = ? AND language = ? AND country = ?;",
                        expired_keys,
                    )
                return len(expired_keys)

    # --------------------------------------------------------------------------
    # Settings Persistence
    # --------------------------------------------------------------------------

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a stored application setting value."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM app_settings WHERE key = ?;", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def set_setting(self, key: str, value: str) -> None:
        """Store or update an application setting value."""
        self._ensure_phase10_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?);
                """,
                (key, str(value), now),
            )

    def delete_setting(self, key: str) -> bool:
        """Delete an application setting by key."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM app_settings WHERE key = ?;", (key,))
            return cursor.rowcount > 0

    def delete_settings_by_prefix(self, prefix: str) -> int:
        """Delete all application settings starting with a given prefix."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM app_settings WHERE key LIKE ?;", (f"{prefix}%",))
            return cursor.rowcount

    # --------------------------------------------------------------------------
    # SERP Caching & Quota Tracking
    # --------------------------------------------------------------------------

    def get_cached_serp(
        self,
        query: str,
        language: str,
        country: str,
        max_age_seconds: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached SERP analysis if present and within max_age_seconds."""
        self._ensure_phase10_tables()
        norm_q = normalize_keyword_key(query)
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT data_json, created_at FROM serp_cache
                WHERE query = ? AND language = ? AND country = ?;
                """,
                (norm_q, language.strip().lower(), country.strip().upper()),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if max_age_seconds is not None:
                try:
                    dt = datetime.fromisoformat(row["created_at"])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - dt).total_seconds() > max_age_seconds:
                        return None
                except Exception:
                    return None
            try:
                return json.loads(row["data_json"])
            except json.JSONDecodeError:
                return None

    def set_cached_serp(
        self,
        query: str,
        language: str,
        country: str,
        data: Union[Dict[str, Any], str],
    ) -> None:
        """Store SERP analysis in cache."""
        self._ensure_phase10_tables()
        norm_q = normalize_keyword_key(query)
        data_str = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO serp_cache (query, language, country, data_json, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (norm_q, language.strip().lower(), country.strip().upper(), data_str, now),
            )

    def clear_serp_cache(self) -> int:
        """Delete all cached SERP results."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM serp_cache;")
            return cursor.rowcount

    def record_quota_usage(self, units: int, date_str: Optional[str] = None) -> int:
        """Record YouTube Data API quota units consumed for the specified date (default UTC today)."""
        self._ensure_phase10_tables()
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT units_used FROM api_quota_usage WHERE date = ?;", (date_str,)
            )
            row = cursor.fetchone()
            current = row["units_used"] if row else 0
            new_total = current + units
            conn.execute(
                "INSERT OR REPLACE INTO api_quota_usage (date, units_used) VALUES (?, ?);",
                (date_str, new_total),
            )
            return new_total

    def get_daily_quota_used(self, date_str: Optional[str] = None) -> int:
        """Get total quota units consumed for the specified date."""
        self._ensure_phase10_tables()
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT units_used FROM api_quota_usage WHERE date = ?;", (date_str,)
            )
            row = cursor.fetchone()
            return row["units_used"] if row else 0

    def reset_daily_quota(self, date_str: Optional[str] = None) -> None:
        """Reset quota counter for the date."""
        self._ensure_phase10_tables()
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            conn.execute("DELETE FROM api_quota_usage WHERE date = ?;", (date_str,))

    # --------------------------------------------------------------------------
    # Video Research Sessions Persistence (Step 10)
    # --------------------------------------------------------------------------

    def save_video_research_session(
        self,
        analysis: Any,
        provider_name: str = "YouTube Data API v3",
        provider: Optional[str] = None,
        associated_keywords: Optional[List[str]] = None,
    ) -> int:
        """Save a video competitor research session and all associated video items to SQLite."""
        self._ensure_phase10_tables()
        now = datetime.now(timezone.utc).isoformat()
        resolved_provider = provider or provider_name

        metrics_data = {
            "total_videos_analyzed": getattr(analysis, "total_videos_analyzed", 0),
            "average_views": getattr(analysis, "average_views", 0.0),
            "median_views": getattr(analysis, "median_views", 0.0),
            "min_views": getattr(analysis, "min_views", 0),
            "max_views": getattr(analysis, "max_views", 0),
            "newest_video_days": getattr(analysis, "newest_video_days", 0),
            "median_video_age_days": getattr(analysis, "median_video_age_days", 0.0),
            "unique_channels_count": getattr(analysis, "unique_channels_count", 0),
            "avg_daily_views": getattr(analysis, "avg_daily_views", 0.0),
            "opportunity_score": getattr(analysis, "opportunity_score", 50.0),
            "opportunity_label": getattr(analysis, "opportunity_label", ""),
            "top_tags": getattr(analysis, "top_tags", []),
        }

        summary_data = {}
        if getattr(analysis, "validation_summary", None):
            summary_data = (
                analysis.validation_summary.to_dict()
                if hasattr(analysis.validation_summary, "to_dict")
                else dict(analysis.validation_summary)
            )

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO video_research_sessions (
                    keyword, provider, language, country, total_videos,
                    metrics_json, summary_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    getattr(analysis, "keyword", ""),
                    resolved_provider,
                    getattr(analysis, "language", "en"),
                    getattr(analysis, "country", "US"),
                    getattr(analysis, "total_videos_analyzed", len(getattr(analysis, "videos", []))),
                    json.dumps(metrics_data, ensure_ascii=False),
                    json.dumps(summary_data, ensure_ascii=False),
                    now,
                ),
            )
            session_id = cursor.lastrowid

            # Determine keywords to associate
            kws_to_associate = list(associated_keywords) if associated_keywords else []
            seed_kw = getattr(analysis, "keyword", "")
            if seed_kw and seed_kw not in kws_to_associate:
                kws_to_associate.append(seed_kw)

            videos = getattr(analysis, "videos", [])
            for v in videos:
                vid = getattr(v, "video_id", "")
                if not vid:
                    continue
                tags_json = json.dumps(getattr(v, "tags", []), ensure_ascii=False)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO video_research_items (
                        session_id, video_id, title, channel_title, channel_id,
                        published_at, view_count, like_count, comment_count,
                        duration, tags_json, thumbnail_url, video_url,
                        channel_url, daily_views, rank
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        session_id,
                        vid,
                        getattr(v, "title", ""),
                        getattr(v, "channel_title", ""),
                        getattr(v, "channel_id", ""),
                        getattr(v, "publish_date", ""),
                        getattr(v, "view_count", 0),
                        getattr(v, "like_count", None),
                        getattr(v, "comment_count", None),
                        getattr(v, "duration", ""),
                        tags_json,
                        getattr(v, "thumbnail_url", ""),
                        getattr(v, "video_url", ""),
                        getattr(v, "channel_url", ""),
                        getattr(v, "daily_views", 0.0),
                        getattr(v, "rank", 1),
                    ),
                )

                # Track associations between video and all keywords
                for kw in kws_to_associate:
                    if kw.strip():
                        conn.execute(
                            """
                            INSERT INTO video_keyword_associations (video_id, keyword, first_observed_at, last_observed_at)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(video_id, keyword) DO UPDATE SET last_observed_at = excluded.last_observed_at;
                            """,
                            (vid, kw.strip(), now, now),
                        )

            return session_id

    def get_video_research_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent video research sessions ordered by latest first."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, keyword, provider, language, country, total_videos,
                       metrics_json, summary_json, created_at
                FROM video_research_sessions
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["metrics"] = json.loads(d["metrics_json"])
                except Exception:
                    d["metrics"] = {}
                try:
                    d["summary"] = json.loads(d["summary_json"]) if d.get("summary_json") else {}
                except Exception:
                    d["summary"] = {}
                rows.append(d)
            return rows

    def get_video_research_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific video research session and its full list of competitor videos."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, keyword, provider, language, country, total_videos,
                       metrics_json, summary_json, created_at
                FROM video_research_sessions
                WHERE id = ?;
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            session_dict = dict(row)
            try:
                session_dict["metrics"] = json.loads(session_dict["metrics_json"])
            except Exception:
                session_dict["metrics"] = {}

            # Load items
            item_cursor = conn.execute(
                """
                SELECT video_id, title, channel_title, channel_id, published_at,
                       view_count, like_count, comment_count, duration, tags_json,
                       thumbnail_url, video_url, channel_url, daily_views, rank
                FROM video_research_items
                WHERE session_id = ?
                ORDER BY rank ASC;
                """,
                (session_id,),
            )
            videos = []
            for ir in item_cursor.fetchall():
                vd = dict(ir)
                try:
                    vd["tags"] = json.loads(vd["tags_json"]) if vd.get("tags_json") else []
                except Exception:
                    vd["tags"] = []
                videos.append(vd)
            session_dict["videos"] = videos
            return session_dict

    def get_keywords_for_video(self, video_id: str) -> List[str]:
        """Retrieve all research keywords associated with a video ID."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT keyword FROM video_keyword_associations WHERE video_id = ? ORDER BY last_observed_at DESC;",
                (video_id,),
            )
            return [r["keyword"] for r in cursor.fetchall()]

    def delete_video_research_session(self, session_id: int) -> bool:
        """Delete a video research session and its items."""
        self._ensure_phase10_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM video_research_sessions WHERE id = ?;", (session_id,))
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Content Opportunities & Planning Persistence (Phase 11)
    # --------------------------------------------------------------------------

    def save_content_opportunity(self, opportunity: Any) -> int:
        """Save or update a content opportunity item to SQLite."""
        self._ensure_phase11_tables()
        now = datetime.now(timezone.utc).isoformat()
        sup_json = json.dumps(getattr(opportunity, "supporting_keywords", []), ensure_ascii=False)
        breakdown_json = json.dumps(getattr(opportunity, "score_breakdown", {}), ensure_ascii=False)
        evidence_json = json.dumps(getattr(opportunity, "evidence", {}), ensure_ascii=False)

        opp_id = getattr(opportunity, "id", None)
        with self.get_connection() as conn:
            if opp_id:
                conn.execute(
                    """
                    UPDATE content_opportunities
                    SET topic = ?, primary_keyword = ?, supporting_keywords_json = ?,
                        target_audience = ?, search_intent = ?, content_format = ?,
                        opportunity_score = ?, confidence_level = ?, score_breakdown_json = ?,
                        evidence_json = ?, status = ?, priority = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        getattr(opportunity, "topic", ""),
                        getattr(opportunity, "primary_keyword", ""),
                        sup_json,
                        getattr(opportunity, "target_audience", "General Audience"),
                        getattr(opportunity, "search_intent", "Informational"),
                        getattr(opportunity, "content_format", "Step-by-step Guide"),
                        getattr(opportunity, "opportunity_score", 50.0),
                        getattr(opportunity, "confidence_level", "Moderate Evidence"),
                        breakdown_json,
                        evidence_json,
                        getattr(opportunity, "status", "Idea"),
                        getattr(opportunity, "priority", "Medium"),
                        now,
                        opp_id,
                    ),
                )
                return opp_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO content_opportunities (
                        project_id, topic, primary_keyword, supporting_keywords_json,
                        target_audience, search_intent, content_format,
                        opportunity_score, confidence_level, score_breakdown_json,
                        evidence_json, status, priority, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        getattr(opportunity, "project_id", None),
                        getattr(opportunity, "topic", ""),
                        getattr(opportunity, "primary_keyword", ""),
                        sup_json,
                        getattr(opportunity, "target_audience", "General Audience"),
                        getattr(opportunity, "search_intent", "Informational"),
                        getattr(opportunity, "content_format", "Step-by-step Guide"),
                        getattr(opportunity, "opportunity_score", 50.0),
                        getattr(opportunity, "confidence_level", "Moderate Evidence"),
                        breakdown_json,
                        evidence_json,
                        getattr(opportunity, "status", "Idea"),
                        getattr(opportunity, "priority", "Medium"),
                        getattr(opportunity, "created_at", now),
                        now,
                    ),
                )
                return cursor.lastrowid

    def get_content_opportunities(
        self,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve stored content opportunities with optional project and status filters."""
        self._ensure_phase11_tables()
        query = "SELECT * FROM content_opportunities WHERE 1=1"
        params: List[Any] = []
        if project_id is not None:
            query += " AND project_id = ?"
            params.append(project_id)
        if status and status != "All":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY opportunity_score DESC, id DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["supporting_keywords"] = json.loads(d.get("supporting_keywords_json", "[]"))
                except Exception:
                    d["supporting_keywords"] = []
                try:
                    d["score_breakdown"] = json.loads(d.get("score_breakdown_json", "{}"))
                except Exception:
                    d["score_breakdown"] = {}
                try:
                    d["evidence"] = json.loads(d.get("evidence_json", "{}"))
                except Exception:
                    d["evidence"] = {}
                rows.append(d)
            return rows

    def get_content_opportunity(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific content opportunity by its primary ID."""
        self._ensure_phase11_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM content_opportunities WHERE id = ?;", (opportunity_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["supporting_keywords"] = json.loads(d.get("supporting_keywords_json", "[]"))
            except Exception:
                d["supporting_keywords"] = []
            try:
                d["score_breakdown"] = json.loads(d.get("score_breakdown_json", "{}"))
            except Exception:
                d["score_breakdown"] = {}
            try:
                d["evidence"] = json.loads(d.get("evidence_json", "{}"))
            except Exception:
                d["evidence"] = {}
            return d

    def update_content_opportunity_status(
        self,
        opportunity_id: int,
        status: str,
        priority: Optional[str] = None,
    ) -> bool:
        """Update the workflow status and optionally priority of an opportunity."""
        self._ensure_phase11_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if priority:
                cursor = conn.execute(
                    "UPDATE content_opportunities SET status = ?, priority = ?, updated_at = ? WHERE id = ?;",
                    (status, priority, now, opportunity_id),
                )
            else:
                cursor = conn.execute(
                    "UPDATE content_opportunities SET status = ?, updated_at = ? WHERE id = ?;",
                    (status, now, opportunity_id),
                )
            return cursor.rowcount > 0

    def delete_content_opportunity(self, opportunity_id: int) -> bool:
        """Delete a content opportunity and its associated brief."""
        self._ensure_phase11_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM content_opportunities WHERE id = ?;", (opportunity_id,))
            return cursor.rowcount > 0

    def save_content_brief(self, brief: Any) -> int:
        """Save or replace a content brief in SQLite."""
        self._ensure_phase11_tables()
        now = datetime.now(timezone.utc).isoformat()
        brief_data = (
            brief.to_dict() if hasattr(brief, "to_dict") else dict(brief)
        )
        brief_json = json.dumps(brief_data, ensure_ascii=False)
        opp_id = getattr(brief, "opportunity_id", None)
        working_title = getattr(brief, "working_title", "")
        primary_kw = getattr(brief, "primary_keyword", "")

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO content_briefs (opportunity_id, working_title, primary_keyword, brief_data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(opportunity_id) DO UPDATE SET
                    working_title = excluded.working_title,
                    primary_keyword = excluded.primary_keyword,
                    brief_data_json = excluded.brief_data_json,
                    updated_at = excluded.updated_at;
                """,
                (opp_id, working_title, primary_kw, brief_json, now, now),
            )
            return cursor.lastrowid

    def get_content_brief(
        self,
        opportunity_id: Optional[int] = None,
        brief_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a content brief by opportunity ID or brief ID."""
        self._ensure_phase11_tables()
        with self.get_connection() as conn:
            if brief_id:
                cursor = conn.execute("SELECT * FROM content_briefs WHERE id = ?;", (brief_id,))
            elif opportunity_id:
                cursor = conn.execute("SELECT * FROM content_briefs WHERE opportunity_id = ?;", (opportunity_id,))
            else:
                return None
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["brief_data"] = json.loads(d.get("brief_data_json", "{}"))
            except Exception:
                d["brief_data"] = {}
            return d

    def delete_content_brief(self, brief_id: int) -> bool:
        """Delete a content brief by its ID."""
        self._ensure_phase11_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM content_briefs WHERE id = ?;", (brief_id,))
            return cursor.rowcount > 0

    def save_calendar_entry(self, entry: Any) -> int:
        """Save or update a YouTube content calendar entry."""
        self._ensure_phase11_tables()
        now = datetime.now(timezone.utc).isoformat()
        entry_id = getattr(entry, "id", None)

        with self.get_connection() as conn:
            if entry_id:
                conn.execute(
                    """
                    UPDATE content_calendar
                    SET title = ?, primary_keyword = ?, planned_date = ?, status = ?,
                        priority = ?, notes = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        getattr(entry, "title", ""),
                        getattr(entry, "primary_keyword", ""),
                        getattr(entry, "planned_date", ""),
                        getattr(entry, "status", "Idea"),
                        getattr(entry, "priority", "Medium"),
                        getattr(entry, "notes", ""),
                        now,
                        entry_id,
                    ),
                )
                return entry_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO content_calendar (
                        opportunity_id, title, primary_keyword, planned_date,
                        status, priority, notes, session_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        getattr(entry, "opportunity_id", None),
                        getattr(entry, "title", ""),
                        getattr(entry, "primary_keyword", ""),
                        getattr(entry, "planned_date", ""),
                        getattr(entry, "status", "Idea"),
                        getattr(entry, "priority", "Medium"),
                        getattr(entry, "notes", ""),
                        getattr(entry, "session_id", None),
                        getattr(entry, "created_at", now),
                        now,
                    ),
                )
                return cursor.lastrowid

    def get_calendar_entries(
        self,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve scheduled calendar entries with optional status and date filters."""
        self._ensure_phase11_tables()
        query = "SELECT * FROM content_calendar WHERE 1=1"
        params: List[Any] = []
        if status and status != "All":
            query += " AND status = ?"
            params.append(status)
        if start_date:
            query += " AND planned_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND planned_date <= ?"
            params.append(end_date)
        query += " ORDER BY planned_date ASC, id ASC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]

    def update_calendar_entry(
        self,
        entry_id: int,
        status: str,
        planned_date: str,
        priority: str = "Medium",
        notes: str = "",
    ) -> bool:
        """Update an existing calendar entry's status, date, priority, or notes."""
        self._ensure_phase11_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE content_calendar
                SET status = ?, planned_date = ?, priority = ?, notes = ?, updated_at = ?
                WHERE id = ?;
                """,
                (status, planned_date, priority, notes, now, entry_id),
            )
            return cursor.rowcount > 0

    def delete_calendar_entry(self, entry_id: int) -> bool:
        """Delete a calendar entry by ID."""
        self._ensure_phase11_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM content_calendar WHERE id = ?;", (entry_id,))
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Niche Product Opportunity Discovery & Gap Analyzer (Phase 12)
    # --------------------------------------------------------------------------

    def save_product_research_session(self, session: Any) -> int:
        """Save or update a niche product research session."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        filters_json = json.dumps(getattr(session, "category_filters", []), ensure_ascii=False)
        modes_json = json.dumps(getattr(session, "search_modes", []), ensure_ascii=False)
        weights_json = json.dumps(getattr(session, "scoring_weights", {}), ensure_ascii=False)
        sess_id = getattr(session, "id", None)

        with self.get_connection() as conn:
            if sess_id:
                conn.execute(
                    """
                    UPDATE product_research_sessions
                    SET niche = ?, language = ?, country = ?, start_date = ?, end_date = ?,
                        category_filters_json = ?, search_modes_json = ?, few_videos_threshold = ?,
                        min_queries_for_zero_match = ?, max_queries = ?, max_videos_per_query = ?, request_budget = ?,
                        requests_made = ?, quota_used = ?, status = ?, error_message = ?,
                        scoring_weights_json = ?, ai_summary = ?, is_mocked = ?, cancelled_at = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        getattr(session, "niche", ""),
                        getattr(session, "language", "en"),
                        getattr(session, "country", "US"),
                        getattr(session, "start_date", ""),
                        getattr(session, "end_date", ""),
                        filters_json,
                        modes_json,
                        getattr(session, "few_videos_threshold", 3),
                        getattr(session, "min_queries_for_zero_match", 2),
                        getattr(session, "max_queries", 15),
                        getattr(session, "max_videos_per_query", 20),
                        getattr(session, "request_budget", 10),
                        getattr(session, "requests_made", 0),
                        getattr(session, "quota_used", 0),
                        getattr(session, "status", "Completed"),
                        getattr(session, "error_message", None),
                        weights_json,
                        getattr(session, "ai_summary", ""),
                        1 if getattr(session, "is_mocked", False) else 0,
                        getattr(session, "cancelled_at", None),
                        now,
                        sess_id,
                    ),
                )
                return sess_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO product_research_sessions (
                        niche, language, country, start_date, end_date,
                        category_filters_json, search_modes_json, few_videos_threshold,
                        min_queries_for_zero_match, max_queries, max_videos_per_query, request_budget,
                        requests_made, quota_used, status, error_message,
                        scoring_weights_json, ai_summary, is_mocked, cancelled_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        getattr(session, "niche", ""),
                        getattr(session, "language", "en"),
                        getattr(session, "country", "US"),
                        getattr(session, "start_date", ""),
                        getattr(session, "end_date", ""),
                        filters_json,
                        modes_json,
                        getattr(session, "few_videos_threshold", 3),
                        getattr(session, "min_queries_for_zero_match", 2),
                        getattr(session, "max_queries", 15),
                        getattr(session, "max_videos_per_query", 20),
                        getattr(session, "request_budget", 10),
                        getattr(session, "requests_made", 0),
                        getattr(session, "quota_used", 0),
                        getattr(session, "status", "Completed"),
                        getattr(session, "error_message", None),
                        weights_json,
                        getattr(session, "ai_summary", ""),
                        1 if getattr(session, "is_mocked", False) else 0,
                        getattr(session, "cancelled_at", None),
                        getattr(session, "created_at", now),
                        now,
                    ),
                )
                return cursor.lastrowid

    def get_product_research_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent product research sessions."""
        self._ensure_phase12_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_research_sessions ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["category_filters"] = json.loads(d.get("category_filters_json", "[]"))
                except Exception:
                    d["category_filters"] = []
                try:
                    d["search_modes"] = json.loads(d.get("search_modes_json", "[]"))
                except Exception:
                    d["search_modes"] = []
                try:
                    d["scoring_weights"] = json.loads(d.get("scoring_weights_json", "{}"))
                except Exception:
                    d["scoring_weights"] = {}
                d["is_mocked"] = bool(d.get("is_mocked", 0))
                rows.append(d)
            return rows

    get_all_product_research_sessions = get_product_research_sessions

    def get_product_research_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific product research session by ID."""
        self._ensure_phase12_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM product_research_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["category_filters"] = json.loads(d.get("category_filters_json", "[]"))
            except Exception:
                d["category_filters"] = []
            try:
                d["search_modes"] = json.loads(d.get("search_modes_json", "[]"))
            except Exception:
                d["search_modes"] = []
            try:
                d["scoring_weights"] = json.loads(d.get("scoring_weights_json", "{}"))
            except Exception:
                d["scoring_weights"] = {}
            d["is_mocked"] = bool(d.get("is_mocked", 0))
            return d

    def delete_product_research_session(self, session_id: int) -> bool:
        """Delete a product research session and all linked products and matches."""
        self._ensure_phase12_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM product_research_sessions WHERE id = ?;", (session_id,))
            return cursor.rowcount > 0

    def cancel_product_research_session(self, session_id: int) -> bool:
        """Mark a product research session as cancelled with timestamp."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE product_research_sessions SET status = 'Cancelled', cancelled_at = ?, updated_at = ? WHERE id = ?;",
                (now, now, session_id),
            )
            return cursor.rowcount > 0

    def update_session_ai_summary(self, session_id: int, ai_summary: str) -> bool:
        """Persist generated AI summary to research session."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE product_research_sessions SET ai_summary = ?, updated_at = ? WHERE id = ?;",
                (ai_summary, now, session_id),
            )
            return cursor.rowcount > 0

    def save_discovered_product(self, product: Any) -> int:
        """Save or update a discovered product in SQLite."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        aliases_json = json.dumps(getattr(product, "aliases", []), ensure_ascii=False)
        queries_json = json.dumps(getattr(product, "queries_executed", []), ensure_ascii=False)
        breakdown_json = json.dumps(getattr(product, "opportunity_score_breakdown", {}), ensure_ascii=False)
        audit_trail_json = json.dumps(getattr(product, "audit_trail", []), ensure_ascii=False)
        prod_id = getattr(product, "id", None)

        with self.get_connection() as conn:
            if prod_id:
                conn.execute(
                    """
                    UPDATE discovered_products
                    SET product_name = ?, brand = ?, model = ?, niche = ?, category = ?,
                        aliases_json = ?, source = ?, evidence_url = ?, evidence_reference = ?,
                        verification_status = ?, extraction_confidence = ?,
                        classification = ?, classification_reason = ?, matching_videos_count = ?,
                        unique_channels_count = ?, latest_video_date = ?, queries_executed_json = ?,
                        queries_succeeded = ?, queries_failed = ?, search_coverage_summary = ?,
                        opportunity_score = ?, score_breakdown_json = ?, confidence_level = ?,
                        data_source = ?, notes = ?, original_name = ?, audit_trail_json = ?,
                        priority = ?, first_seen_at = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        getattr(product, "product_name", ""),
                        getattr(product, "brand", ""),
                        getattr(product, "model", ""),
                        getattr(product, "niche", ""),
                        getattr(product, "category", ""),
                        aliases_json,
                        getattr(product, "source", "Extracted Candidate"),
                        getattr(product, "evidence_url", ""),
                        getattr(product, "evidence_reference", ""),
                        getattr(product, "verification_status", "Extracted Candidate"),
                        getattr(product, "extraction_confidence", "High"),
                        getattr(product, "classification", "INSUFFICIENT RESEARCH"),
                        getattr(product, "classification_reason", ""),
                        getattr(product, "matching_videos_count", 0),
                        getattr(product, "unique_channels_count", 0),
                        getattr(product, "latest_video_date", None),
                        queries_json,
                        getattr(product, "queries_succeeded", 0),
                        getattr(product, "queries_failed", 0),
                        getattr(product, "search_coverage_summary", ""),
                        getattr(product, "opportunity_score", 50.0),
                        breakdown_json,
                        getattr(product, "confidence_level", "Low"),
                        getattr(product, "data_source", "Live YouTube Data API v3"),
                        getattr(product, "notes", ""),
                        getattr(product, "original_name", getattr(product, "product_name", "")),
                        audit_trail_json,
                        getattr(product, "priority", "Medium"),
                        getattr(product, "first_seen_at", getattr(product, "created_at", now)),
                        now,
                        prod_id,
                    ),
                )
                return prod_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO discovered_products (
                        session_id, product_name, brand, model, niche, category,
                        aliases_json, source, evidence_url, evidence_reference,
                        verification_status, extraction_confidence,
                        classification, classification_reason, matching_videos_count,
                        unique_channels_count, latest_video_date, queries_executed_json,
                        queries_succeeded, queries_failed, search_coverage_summary,
                        opportunity_score, score_breakdown_json, confidence_level,
                        data_source, notes, original_name, audit_trail_json,
                        priority, first_seen_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        getattr(product, "session_id", None),
                        getattr(product, "product_name", ""),
                        getattr(product, "brand", ""),
                        getattr(product, "model", ""),
                        getattr(product, "niche", ""),
                        getattr(product, "category", ""),
                        aliases_json,
                        getattr(product, "source", "Extracted Candidate"),
                        getattr(product, "evidence_url", ""),
                        getattr(product, "evidence_reference", ""),
                        getattr(product, "verification_status", "Extracted Candidate"),
                        getattr(product, "extraction_confidence", "High"),
                        getattr(product, "classification", "INSUFFICIENT RESEARCH"),
                        getattr(product, "classification_reason", ""),
                        getattr(product, "matching_videos_count", 0),
                        getattr(product, "unique_channels_count", 0),
                        getattr(product, "latest_video_date", None),
                        queries_json,
                        getattr(product, "queries_succeeded", 0),
                        getattr(product, "queries_failed", 0),
                        getattr(product, "search_coverage_summary", ""),
                        getattr(product, "opportunity_score", 50.0),
                        breakdown_json,
                        getattr(product, "confidence_level", "Low"),
                        getattr(product, "data_source", "Live YouTube Data API v3"),
                        getattr(product, "notes", ""),
                        getattr(product, "original_name", getattr(product, "product_name", "")),
                        audit_trail_json,
                        getattr(product, "priority", "Medium"),
                        getattr(product, "first_seen_at", getattr(product, "created_at", now)),
                        getattr(product, "created_at", now),
                        now,
                    ),
                )
                return cursor.lastrowid

    def get_discovered_products(
        self,
        session_id: Optional[int] = None,
        classification: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Retrieve discovered products with optional session and classification filters."""
        self._ensure_phase12_tables()
        query = "SELECT * FROM discovered_products WHERE 1=1"
        params: List[Any] = []
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if classification and classification != "All":
            query += " AND classification = ?"
            params.append(classification)
        query += " ORDER BY opportunity_score DESC, id ASC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["aliases"] = json.loads(d.get("aliases_json", "[]"))
                except Exception:
                    d["aliases"] = []
                try:
                    d["queries_executed"] = json.loads(d.get("queries_executed_json", "[]"))
                except Exception:
                    d["queries_executed"] = []
                try:
                    d["opportunity_score_breakdown"] = json.loads(d.get("score_breakdown_json", "{}"))
                except Exception:
                    d["opportunity_score_breakdown"] = {}
                try:
                    d["audit_trail"] = json.loads(d.get("audit_trail_json", "[]"))
                except Exception:
                    d["audit_trail"] = []
                rows.append(d)
            return rows

    def get_discovered_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific candidate product by ID."""
        self._ensure_phase12_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM discovered_products WHERE id = ?;", (product_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["aliases"] = json.loads(d.get("aliases_json", "[]"))
            except Exception:
                d["aliases"] = []
            try:
                d["queries_executed"] = json.loads(d.get("queries_executed_json", "[]"))
            except Exception:
                d["queries_executed"] = []
            try:
                d["opportunity_score_breakdown"] = json.loads(d.get("score_breakdown_json", "{}"))
            except Exception:
                d["opportunity_score_breakdown"] = {}
            try:
                d["audit_trail"] = json.loads(d.get("audit_trail_json", "[]"))
            except Exception:
                d["audit_trail"] = []
            return d

    def update_product_classification(
        self,
        product_id: int,
        classification: str,
        reason: str = "",
        score: Optional[float] = None,
        confidence: Optional[str] = None,
    ) -> bool:
        """Update a product's classification category and reason."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if score is not None and confidence is not None:
                cursor = conn.execute(
                    """
                    UPDATE discovered_products
                    SET classification = ?, classification_reason = ?, opportunity_score = ?,
                        confidence_level = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (classification, reason, score, confidence, now, product_id),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE discovered_products
                    SET classification = ?, classification_reason = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (classification, reason, now, product_id),
                )
            return cursor.rowcount > 0

    def record_product_correction(
        self,
        product_id: int,
        field_name: str,
        old_val: Any,
        new_val: Any,
        reason: str = "",
    ) -> bool:
        """Record an audit trail entry and update the product column without losing provenance."""
        prod = self.get_discovered_product(product_id)
        if not prod:
            return False
        audit_trail = prod.get("audit_trail", [])
        audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "field": field_name,
            "old_value": old_val,
            "new_value": new_val,
            "reason": reason,
        })
        now = datetime.now(timezone.utc).isoformat()
        audit_json = json.dumps(audit_trail, ensure_ascii=False)

        allowed_fields = {
            "product_name", "brand", "model", "category", "verification_status",
            "priority", "notes", "classification",
        }
        with self.get_connection() as conn:
            if field_name in allowed_fields:
                sql = f"UPDATE discovered_products SET {field_name} = ?, audit_trail_json = ?, updated_at = ? WHERE id = ?;"
                conn.execute(sql, (new_val, audit_json, now, product_id))
            else:
                conn.execute(
                    "UPDATE discovered_products SET audit_trail_json = ?, updated_at = ? WHERE id = ?;",
                    (audit_json, now, product_id),
                )
            return True

    def update_product_user_fields(
        self,
        product_id: int,
        verification_status: Optional[str] = None,
        priority: Optional[str] = None,
        notes: Optional[str] = None,
        product_name: Optional[str] = None,
        aliases: Optional[List[str]] = None,
    ) -> bool:
        """Update user-modifiable fields with optional audit entry."""
        prod = self.get_discovered_product(product_id)
        if not prod:
            return False
        now = datetime.now(timezone.utc).isoformat()
        updates = []
        params = []

        if verification_status is not None:
            updates.append("verification_status = ?")
            params.append(verification_status)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if product_name is not None and product_name != prod.get("product_name"):
            updates.append("product_name = ?")
            params.append(product_name)
            # also record correction
            self.record_product_correction(
                product_id, "product_name", prod.get("product_name"), product_name, "User edited product name"
            )
        if aliases is not None:
            updates.append("aliases_json = ?")
            params.append(json.dumps(aliases, ensure_ascii=False))

        if not updates:
            return True

        updates.append("updated_at = ?")
        params.append(now)
        params.append(product_id)

        sql = f"UPDATE discovered_products SET {', '.join(updates)} WHERE id = ?;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            return cursor.rowcount > 0

    def save_product_video_match(self, match: Any) -> int:
        """Save a video evidence match for a candidate product."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        terms_json = json.dumps(getattr(match, "matched_terms", []), ensure_ascii=False)
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO product_video_matches (
                    product_id, session_id, video_id, title, channel_id, channel_title,
                    publish_date, url, views, match_type, match_field, matched_terms_json,
                    is_excluded, exclusion_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    getattr(match, "product_id", None),
                    getattr(match, "session_id", None),
                    getattr(match, "video_id", ""),
                    getattr(match, "title", ""),
                    getattr(match, "channel_id", ""),
                    getattr(match, "channel_title", ""),
                    getattr(match, "publish_date", ""),
                    getattr(match, "url", ""),
                    getattr(match, "views", 0),
                    getattr(match, "match_type", "Exact Model Match"),
                    getattr(match, "match_field", "title"),
                    terms_json,
                    1 if getattr(match, "is_excluded", False) else 0,
                    getattr(match, "exclusion_reason", ""),
                    getattr(match, "created_at", now),
                ),
            )
            return cursor.lastrowid

    def get_product_video_matches(
        self,
        product_id: int,
        include_excluded: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve video matches linked to a product."""
        self._ensure_phase12_tables()
        query = "SELECT * FROM product_video_matches WHERE product_id = ?"
        params: List[Any] = [product_id]
        if not include_excluded:
            query += " AND is_excluded = 0"
        query += " ORDER BY publish_date DESC, id ASC;"

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                try:
                    d["matched_terms"] = json.loads(d.get("matched_terms_json", "[]"))
                except Exception:
                    d["matched_terms"] = []
                d["is_excluded"] = bool(d.get("is_excluded", 0))
                rows.append(d)
            return rows

    def exclude_video_match(self, match_id: int, is_excluded: bool = True, exclusion_reason: str = "") -> bool:
        """Mark or unmark a video match as excluded from product calculations."""
        self._ensure_phase12_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE product_video_matches SET is_excluded = ?, exclusion_reason = ? WHERE id = ?;",
                (1 if is_excluded else 0, exclusion_reason, match_id),
            )
            return cursor.rowcount > 0

    def save_product_search_query(self, query: Any) -> int:
        """Log an executed search query for a product research session."""
        self._ensure_phase12_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO product_search_queries (
                    session_id, product_id, product_name, query_text, search_mode,
                    status, results_count, executed_at, query_source, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    getattr(query, "session_id", None),
                    getattr(query, "product_id", None),
                    getattr(query, "product_name", ""),
                    getattr(query, "query_text", ""),
                    getattr(query, "search_mode", ""),
                    getattr(query, "status", "Success"),
                    getattr(query, "results_count", 0),
                    getattr(query, "executed_at", now),
                    getattr(query, "query_source", "ALGORITHMIC_TEMPLATE"),
                    getattr(query, "error_message", None),
                ),
            )
            return cursor.lastrowid

    def get_product_search_queries(
        self,
        session_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve logged search queries with optional session and product filters."""
        self._ensure_phase12_tables()
        query = "SELECT * FROM product_search_queries WHERE 1=1"
        params: List[Any] = []
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if product_id is not None:
            query += " AND product_id = ?"
            params.append(product_id)
        query += " ORDER BY id ASC;"

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]

    # --------------------------------------------------------------------------
    # Phase 14 Product Opportunity Shortlist & Affiliate Content Planner
    # --------------------------------------------------------------------------

    def save_shortlist_product(self, item: ProductOpportunityShortlist) -> int:
        """Insert or update a product opportunity shortlist entry."""
        self._ensure_phase14_tables()
        now = datetime.now(timezone.utc).isoformat()
        sb_json = json.dumps(item.score_breakdown or {})
        sk_json = json.dumps(item.supporting_keywords or [])
        aff_json = json.dumps(item.affiliate_data or {})
        chk_json = json.dumps(item.verification_checklist or {})

        with self.get_connection() as conn:
            if item.id is not None:
                conn.execute(
                    """
                    UPDATE product_opportunity_shortlist SET
                        product_id = ?, session_id = ?, product_name = ?, brand = ?,
                        model = ?, niche = ?, category = ?, country = ?, language = ?,
                        status = ?, priority = ?, intended_format = ?, notes = ?,
                        opportunity_score = ?, confidence_level = ?, score_breakdown_json = ?,
                        formula_version = ?, matching_videos_count = ?, queries_executed_count = ?,
                        supporting_keywords_json = ?, affiliate_data_json = ?,
                        verification_checklist_json = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        item.product_id, item.session_id, item.product_name, item.brand,
                        item.model, item.niche, item.category, item.country, item.language,
                        item.status, item.priority, item.intended_format, item.notes,
                        item.opportunity_score, item.confidence_level, sb_json,
                        item.formula_version, item.matching_videos_count, item.queries_executed_count,
                        sk_json, aff_json, chk_json, now, item.id,
                    ),
                )
                return item.id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO product_opportunity_shortlist (
                        product_id, session_id, product_name, brand, model,
                        niche, category, country, language, status, priority,
                        intended_format, notes, opportunity_score, confidence_level,
                        score_breakdown_json, formula_version, matching_videos_count,
                        queries_executed_count, supporting_keywords_json,
                        affiliate_data_json, verification_checklist_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item.product_id, item.session_id, item.product_name, item.brand, item.model,
                        item.niche, item.category, item.country, item.language, item.status, item.priority,
                        item.intended_format, item.notes, item.opportunity_score, item.confidence_level,
                        sb_json, item.formula_version, item.matching_videos_count,
                        item.queries_executed_count, sk_json, aff_json, chk_json,
                        item.created_at or now, now,
                    ),
                )
                item.id = cursor.lastrowid
                return item.id

    def get_shortlist_products(
        self,
        session_id: Optional[int] = None,
        status: Optional[str] = None,
        niche: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 500,
    ) -> List[ProductOpportunityShortlist]:
        """Retrieve shortlist products with optional filters."""
        self._ensure_phase14_tables()
        query = "SELECT * FROM product_opportunity_shortlist WHERE 1=1"
        params: List[Any] = []
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if status and status != "All":
            query += " AND status = ?"
            params.append(status)
        if niche and niche != "All":
            query += " AND niche = ?"
            params.append(niche)
        if priority and priority != "All":
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY opportunity_score DESC, id DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["score_breakdown"] = json.loads(d.pop("score_breakdown_json", "{}") or "{}")
                d["supporting_keywords"] = json.loads(d.pop("supporting_keywords_json", "[]") or "[]")
                d["affiliate_data"] = json.loads(d.pop("affiliate_data_json", "{}") or "{}")
                d["verification_checklist"] = json.loads(d.pop("verification_checklist_json", "{}") or "{}")
                results.append(ProductOpportunityShortlist.from_dict(d))
            return results

    def get_shortlist_product(self, shortlist_id: int) -> Optional[ProductOpportunityShortlist]:
        """Retrieve single shortlist product by ID."""
        self._ensure_phase14_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_opportunity_shortlist WHERE id = ?;", (shortlist_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["score_breakdown"] = json.loads(d.pop("score_breakdown_json", "{}") or "{}")
            d["supporting_keywords"] = json.loads(d.pop("supporting_keywords_json", "[]") or "[]")
            d["affiliate_data"] = json.loads(d.pop("affiliate_data_json", "{}") or "{}")
            d["verification_checklist"] = json.loads(d.pop("verification_checklist_json", "{}") or "{}")
            return ProductOpportunityShortlist.from_dict(d)

    def update_shortlist_status(
        self,
        shortlist_id: int,
        status: str,
        priority: Optional[str] = None,
        notes: Optional[str] = None,
        intended_format: Optional[str] = None,
    ) -> bool:
        """Update workflow status, priority, or notes of a shortlist product."""
        self._ensure_phase14_tables()
        now = datetime.now(timezone.utc).isoformat()
        updates = ["status = ?", "updated_at = ?"]
        params: List[Any] = [status, now]
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if intended_format is not None:
            updates.append("intended_format = ?")
            params.append(intended_format)
        params.append(shortlist_id)

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE product_opportunity_shortlist SET {', '.join(updates)} WHERE id = ?;",
                tuple(params),
            )
            return cursor.rowcount > 0

    def delete_shortlist_product(self, shortlist_id: int) -> bool:
        """Delete a shortlisted product entry and associated brief."""
        self._ensure_phase14_tables()
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM product_content_briefs_v14 WHERE shortlist_id = ?;", (shortlist_id,)
            )
            cursor = conn.execute(
                "DELETE FROM product_opportunity_shortlist WHERE id = ?;", (shortlist_id,)
            )
            return cursor.rowcount > 0

    def save_affiliate_brief(self, brief: AffiliateContentBrief) -> int:
        """Save or update an affiliate content brief."""
        self._ensure_phase14_tables()
        now = datetime.now(timezone.utc).isoformat()
        payload = brief.to_dict()
        b_data = json.dumps(payload)

        with self.get_connection() as conn:
            if brief.id is not None:
                conn.execute(
                    """
                    UPDATE product_content_briefs_v14 SET
                        shortlist_id = ?, product_id = ?, product_name = ?,
                        primary_keyword = ?, brand = ?, model = ?, category = ?,
                        brief_data_json = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        brief.shortlist_id, brief.product_id, brief.product_name,
                        brief.primary_keyword, brief.brand, brief.model, brief.category,
                        b_data, now, brief.id,
                    ),
                )
                return brief.id
            elif brief.shortlist_id is not None:
                cursor = conn.execute(
                    "SELECT id FROM product_content_briefs_v14 WHERE shortlist_id = ?;",
                    (brief.shortlist_id,),
                )
                row = cursor.fetchone()
                if row:
                    existing_id = row[0]
                    brief.id = existing_id
                    conn.execute(
                        """
                        UPDATE product_content_briefs_v14 SET
                            product_id = ?, product_name = ?, primary_keyword = ?,
                            brand = ?, model = ?, category = ?, brief_data_json = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            brief.product_id, brief.product_name, brief.primary_keyword,
                            brief.brand, brief.model, brief.category, b_data, now, existing_id,
                        ),
                    )
                    return existing_id

            cursor = conn.execute(
                """
                INSERT INTO product_content_briefs_v14 (
                    shortlist_id, product_id, product_name, primary_keyword,
                    brand, model, category, brief_data_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    brief.shortlist_id, brief.product_id, brief.product_name,
                    brief.primary_keyword, brief.brand, brief.model, brief.category,
                    b_data, brief.created_at or now, now,
                ),
            )
            brief.id = cursor.lastrowid
            return brief.id

    def get_affiliate_brief(self, shortlist_id: int) -> Optional[AffiliateContentBrief]:
        """Retrieve affiliate content brief for a shortlist product."""
        self._ensure_phase14_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_content_briefs_v14 WHERE shortlist_id = ?;",
                (shortlist_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            brief_dict = json.loads(d.get("brief_data_json", "{}"))
            brief_dict["id"] = d["id"]
            brief_dict["shortlist_id"] = d["shortlist_id"]
            brief_dict["product_id"] = d["product_id"]
            return AffiliateContentBrief.from_dict(brief_dict)

    def get_affiliate_brief_by_id(self, brief_id: int) -> Optional[AffiliateContentBrief]:
        """Retrieve affiliate content brief by brief ID."""
        self._ensure_phase14_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_content_briefs_v14 WHERE id = ?;",
                (brief_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            brief_dict = json.loads(d.get("brief_data_json", "{}"))
            brief_dict["id"] = d["id"]
            brief_dict["shortlist_id"] = d["shortlist_id"]
            brief_dict["product_id"] = d["product_id"]
            return AffiliateContentBrief.from_dict(brief_dict)

    def delete_affiliate_brief(self, brief_id: int) -> bool:
        """Delete an affiliate content brief."""
        self._ensure_phase14_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM product_content_briefs_v14 WHERE id = ?;", (brief_id,)
            )
            return cursor.rowcount > 0

    def save_affiliate_catalog_entry(self, entry: AffiliateProductData) -> int:
        """Insert or replace an affiliate product catalog entry."""
        self._ensure_phase14_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO product_affiliate_catalog (
                    product_name, brand, model, merchant, product_page_url,
                    price, currency, affiliate_program, commission_info,
                    availability, affiliate_link, is_verified_merchant, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_name, merchant) DO UPDATE SET
                    brand = excluded.brand,
                    model = excluded.model,
                    product_page_url = excluded.product_page_url,
                    price = excluded.price,
                    currency = excluded.currency,
                    affiliate_program = excluded.affiliate_program,
                    commission_info = excluded.commission_info,
                    availability = excluded.availability,
                    affiliate_link = excluded.affiliate_link,
                    is_verified_merchant = excluded.is_verified_merchant,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at;
                """,
                (
                    entry.product_name, entry.brand, entry.model, entry.merchant,
                    entry.product_page_url, entry.price, entry.currency,
                    entry.affiliate_program, entry.commission_info, entry.availability,
                    entry.affiliate_link, 1 if entry.is_verified_merchant else 0,
                    entry.notes, entry.retrieved_at or now, now,
                ),
            )
            return cursor.lastrowid

    def get_affiliate_catalog_entry(
        self, product_name: str, brand: str = "", model: str = ""
    ) -> Optional[AffiliateProductData]:
        """Look up an affiliate product from the local catalog."""
        self._ensure_phase14_tables()
        clean_name = product_name.strip()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM product_affiliate_catalog WHERE LOWER(product_name) = LOWER(?) LIMIT 1;",
                (clean_name,),
            )
            row = cursor.fetchone()
            if not row and model:
                cursor = conn.execute(
                    "SELECT * FROM product_affiliate_catalog WHERE LOWER(model) = LOWER(?) LIMIT 1;",
                    (model.strip(),),
                )
                row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            return AffiliateProductData(
                product_name=d["product_name"],
                brand=d["brand"],
                model=d["model"],
                product_page_url=d["product_page_url"],
                merchant=d["merchant"],
                price=d["price"],
                currency=d["currency"],
                affiliate_program=d["affiliate_program"],
                commission_info=d["commission_info"],
                availability=d["availability"],
                affiliate_link=d["affiliate_link"],
                is_verified_merchant=bool(d["is_verified_merchant"]),
                retrieved_at=d["updated_at"],
                notes=d["notes"],
            )

    # --------------------------------------------------------------------------
    # Phase 15 Research Monitor & Automated Opportunity Intelligence
    # --------------------------------------------------------------------------

    def save_monitor_config(self, cfg: SavedResearchConfig) -> int:
        """Insert or update a saved niche research configuration."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        cat_json = json.dumps(cfg.category_filters or [])
        tmpl_json = json.dumps(cfg.query_templates or [])
        meth_json = json.dumps(cfg.enabled_discovery_methods or [])

        with self.get_connection() as conn:
            if cfg.id is not None:
                conn.execute(
                    """
                    UPDATE research_monitor_configs SET
                        name = ?, niche = ?, country = ?, language = ?,
                        date_window_days = ?, category_filters_json = ?,
                        query_templates_json = ?, max_products_per_run = ?,
                        max_queries_per_run = ?, request_budget = ?,
                        matching_mode = ?, min_research_coverage = ?,
                        opportunity_formula_version = ?, enabled_discovery_methods_json = ?,
                        is_paused = ?, notes = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        cfg.name, cfg.niche, cfg.country, cfg.language,
                        cfg.date_window_days, cat_json, tmpl_json,
                        cfg.max_products_per_run, cfg.max_queries_per_run,
                        cfg.request_budget, cfg.matching_mode,
                        cfg.min_research_coverage, cfg.opportunity_formula_version,
                        meth_json, 1 if cfg.is_paused else 0, cfg.notes, now, cfg.id,
                    ),
                )
                return cfg.id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO research_monitor_configs (
                        name, niche, country, language, date_window_days,
                        category_filters_json, query_templates_json,
                        max_products_per_run, max_queries_per_run, request_budget,
                        matching_mode, min_research_coverage, opportunity_formula_version,
                        enabled_discovery_methods_json, is_paused, notes,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        cfg.name or f"{cfg.niche} Monitor", cfg.niche, cfg.country, cfg.language,
                        cfg.date_window_days, cat_json, tmpl_json,
                        cfg.max_products_per_run, cfg.max_queries_per_run,
                        cfg.request_budget, cfg.matching_mode,
                        cfg.min_research_coverage, cfg.opportunity_formula_version,
                        meth_json, 1 if cfg.is_paused else 0, cfg.notes,
                        cfg.created_at or now, now,
                    ),
                )
                cfg.id = cursor.lastrowid
                return cfg.id

    def get_monitor_configs(
        self, include_paused: bool = True, niche: Optional[str] = None
    ) -> List[SavedResearchConfig]:
        """Retrieve saved configurations with optional filtering."""
        self._ensure_phase15_tables()
        query = "SELECT * FROM research_monitor_configs WHERE 1=1"
        params: List[Any] = []
        if not include_paused:
            query += " AND is_paused = 0"
        if niche and niche != "All":
            query += " AND LOWER(niche) = LOWER(?)"
            params.append(niche.strip())
        query += " ORDER BY id DESC;"

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["category_filters"] = json.loads(d.pop("category_filters_json", "[]") or "[]")
                d["query_templates"] = json.loads(d.pop("query_templates_json", "[]") or "[]")
                d["enabled_discovery_methods"] = json.loads(d.pop("enabled_discovery_methods_json", "[]") or "[]")
                d["is_paused"] = bool(d.get("is_paused", 0))
                results.append(SavedResearchConfig.from_dict(d))
            return results

    def get_monitor_config(self, config_id: int) -> Optional[SavedResearchConfig]:
        """Retrieve single saved research configuration by ID."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM research_monitor_configs WHERE id = ?;", (config_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["category_filters"] = json.loads(d.pop("category_filters_json", "[]") or "[]")
            d["query_templates"] = json.loads(d.pop("query_templates_json", "[]") or "[]")
            d["enabled_discovery_methods"] = json.loads(d.pop("enabled_discovery_methods_json", "[]") or "[]")
            d["is_paused"] = bool(d.get("is_paused", 0))
            return SavedResearchConfig.from_dict(d)

    def update_monitor_config_status(self, config_id: int, is_paused: bool) -> bool:
        """Pause or resume a saved research configuration."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE research_monitor_configs SET is_paused = ?, updated_at = ? WHERE id = ?;",
                (1 if is_paused else 0, now, config_id),
            )
            return cursor.rowcount > 0

    def duplicate_monitor_config(self, config_id: int, new_name: Optional[str] = None) -> Optional[int]:
        """Duplicate an existing configuration with a new name."""
        orig = self.get_monitor_config(config_id)
        if not orig:
            return None
        orig.id = None
        orig.name = new_name or f"{orig.name} (Copy)"
        now = datetime.now(timezone.utc).isoformat()
        orig.created_at = now
        orig.updated_at = now
        return self.save_monitor_config(orig)

    def delete_monitor_config(self, config_id: int) -> bool:
        """Delete a saved configuration with cascading runs/schedules preserved or cleaned."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            conn.execute("DELETE FROM research_monitor_schedules WHERE config_id = ?;", (config_id,))
            cursor = conn.execute("DELETE FROM research_monitor_configs WHERE id = ?;", (config_id,))
            return cursor.rowcount > 0

    def save_monitor_run(self, run: ResearchMonitorRun) -> int:
        """Insert or update a research monitor execution record."""
        self._ensure_phase15_tables()
        snap_json = json.dumps(run.config_snapshot or {})
        fail_json = json.dumps(run.failed_query_list or [])

        with self.get_connection() as conn:
            if run.id is not None:
                conn.execute(
                    """
                    UPDATE research_monitor_runs SET
                        config_id = ?, niche = ?, run_number = ?, trigger_type = ?,
                        status = ?, config_snapshot_json = ?, queries_attempted = ?,
                        queries_succeeded = ?, queries_failed = ?, failed_query_list_json = ?,
                        products_discovered = ?, matching_videos_retrieved = ?,
                        live_requests_count = ?, cached_requests_count = ?,
                        generated_items_count = ?, provider_name = ?, error_message = ?,
                        started_at = ?, completed_at = ?
                    WHERE id = ?;
                    """,
                    (
                        run.config_id, run.niche, run.run_number, run.trigger_type,
                        run.status, snap_json, run.queries_attempted,
                        run.queries_succeeded, run.queries_failed, fail_json,
                        run.products_discovered, run.matching_videos_retrieved,
                        run.live_requests_count, run.cached_requests_count,
                        run.generated_items_count, run.provider_name, run.error_message,
                        run.started_at, run.completed_at, run.id,
                    ),
                )
                return run.id
            else:
                # Calculate next run_number for this config/niche
                cursor_num = conn.execute(
                    "SELECT COALESCE(MAX(run_number), 0) + 1 FROM research_monitor_runs WHERE LOWER(niche) = LOWER(?);",
                    (run.niche,),
                )
                run.run_number = cursor_num.fetchone()[0]

                cursor = conn.execute(
                    """
                    INSERT INTO research_monitor_runs (
                        config_id, niche, run_number, trigger_type, status,
                        config_snapshot_json, queries_attempted, queries_succeeded,
                        queries_failed, failed_query_list_json, products_discovered,
                        matching_videos_retrieved, live_requests_count,
                        cached_requests_count, generated_items_count, provider_name,
                        error_message, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        run.config_id, run.niche, run.run_number, run.trigger_type,
                        run.status, snap_json, run.queries_attempted,
                        run.queries_succeeded, run.queries_failed, fail_json,
                        run.products_discovered, run.matching_videos_retrieved,
                        run.live_requests_count, run.cached_requests_count,
                        run.generated_items_count, run.provider_name, run.error_message,
                        run.started_at, run.completed_at,
                    ),
                )
                run.id = cursor.lastrowid
                return run.id

    def get_monitor_runs(
        self, config_id: Optional[int] = None, niche: Optional[str] = None, limit: int = 100
    ) -> List[ResearchMonitorRun]:
        """Retrieve research run execution history."""
        self._ensure_phase15_tables()
        query = "SELECT * FROM research_monitor_runs WHERE 1=1"
        params: List[Any] = []
        if config_id is not None:
            query += " AND config_id = ?"
            params.append(config_id)
        if niche and niche != "All":
            query += " AND LOWER(niche) = LOWER(?)"
            params.append(niche.strip())
        query += " ORDER BY id DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["config_snapshot"] = json.loads(d.pop("config_snapshot_json", "{}") or "{}")
                d["failed_query_list"] = json.loads(d.pop("failed_query_list_json", "[]") or "[]")
                results.append(ResearchMonitorRun.from_dict(d))
            return results

    def get_monitor_run(self, run_id: int) -> Optional[ResearchMonitorRun]:
        """Retrieve single research monitor run by ID."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM research_monitor_runs WHERE id = ?;", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["config_snapshot"] = json.loads(d.pop("config_snapshot_json", "{}") or "{}")
            d["failed_query_list"] = json.loads(d.pop("failed_query_list_json", "[]") or "[]")
            return ResearchMonitorRun.from_dict(d)

    def update_monitor_run_status(
        self, run_id: int, status: str, error_message: Optional[str] = None, completed: bool = False
    ) -> bool:
        """Update status and completion timestamp of a research run."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if completed:
                cursor = conn.execute(
                    "UPDATE research_monitor_runs SET status = ?, error_message = ?, completed_at = ? WHERE id = ?;",
                    (status, error_message, now, run_id),
                )
            else:
                cursor = conn.execute(
                    "UPDATE research_monitor_runs SET status = ?, error_message = ? WHERE id = ?;",
                    (status, error_message, run_id),
                )
            return cursor.rowcount > 0

    def save_product_snapshots(
        self,
        arg1: Any,
        arg2: Optional[List[ProductSnapshotItem]] = None,
    ) -> int:
        """Batch insert product snapshots for a research run.

        Supports both:
        - save_product_snapshots(snapshots) where each item has item.run_id
        - save_product_snapshots(run_id, snapshots)
        """
        self._ensure_phase15_tables()
        if isinstance(arg1, int):
            default_run_id = arg1
            snapshots = arg2 or []
        else:
            snapshots = arg1 or []
            default_run_id = snapshots[0].run_id if snapshots and hasattr(snapshots[0], "run_id") and snapshots[0].run_id else None

        now = datetime.now(timezone.utc).isoformat()
        count = 0
        with self.get_connection() as conn:
            for s in snapshots:
                effective_run_id = s.run_id if s.run_id is not None else default_run_id
                ch_json = json.dumps(s.observed_channels or [])
                conn.execute(
                    """
                    INSERT INTO research_monitor_snapshots (
                        run_id, product_id, product_name, brand, model,
                        niche, category, classification, classification_reason,
                        matching_videos_count, latest_video_date, unique_channels_count,
                        observed_channels_json, opportunity_score, confidence_level,
                        queries_executed_count, search_coverage_summary,
                        verification_status, data_source, snapshot_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        effective_run_id, s.product_id, s.product_name, s.brand, s.model,
                        s.niche, s.category, s.classification, s.classification_reason,
                        s.matching_videos_count, s.latest_video_date, s.unique_channels_count,
                        ch_json, s.opportunity_score, s.confidence_level,
                        s.queries_executed_count, s.search_coverage_summary,
                        s.verification_status, s.data_source, s.snapshot_at or now,
                    ),
                )
                count += 1
        return count

    def get_product_snapshots(self, run_id: int) -> List[ProductSnapshotItem]:
        """Retrieve all product snapshots associated with a specific run."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM research_monitor_snapshots WHERE run_id = ? ORDER BY opportunity_score DESC, id ASC;",
                (run_id,),
            )
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["observed_channels"] = json.loads(d.pop("observed_channels_json", "[]") or "[]")
                results.append(ProductSnapshotItem.from_dict(d))
            return results

    def get_all_snapshots_by_niche(self, niche: str) -> Dict[int, List[ProductSnapshotItem]]:
        """Retrieve all snapshots grouped by run_id for historical analytics."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.* FROM research_monitor_snapshots s
                JOIN research_monitor_runs r ON s.run_id = r.id
                WHERE LOWER(r.niche) = LOWER(?)
                ORDER BY s.run_id ASC, s.opportunity_score DESC;
                """,
                (niche.strip(),),
            )
            grouped: Dict[int, List[ProductSnapshotItem]] = {}
            for r in cursor.fetchall():
                d = dict(r)
                rid = d["run_id"]
                d["observed_channels"] = json.loads(d.pop("observed_channels_json", "[]") or "[]")
                if rid not in grouped:
                    grouped[rid] = []
                grouped[rid].append(ProductSnapshotItem.from_dict(d))
            return grouped

    def save_snapshot_comparison(self, comp: SnapshotComparisonResult) -> int:
        """Insert or replace a snapshot comparison result."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_monitor_comparisons (
                    run_a_id, run_b_id, niche, run_a_date, run_b_date,
                    newly_discovered_products_json, dropped_products_json,
                    video_count_changes_json, score_changes_json,
                    coverage_changes_json, newly_observed_channels_json,
                    comparison_matrix_json, summary_notes, empirical_caution,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    comp.run_a_id, comp.run_b_id, comp.niche, comp.run_a_date, comp.run_b_date,
                    json.dumps(comp.newly_discovered_products or []),
                    json.dumps(comp.dropped_products or []),
                    json.dumps(comp.video_count_changes or []),
                    json.dumps(comp.score_changes or []),
                    json.dumps(comp.coverage_changes or []),
                    json.dumps(comp.newly_observed_channels or []),
                    json.dumps(comp.comparison_matrix or []),
                    comp.summary_notes, comp.empirical_caution, comp.created_at or now,
                ),
            )
            comp.id = cursor.lastrowid
            return comp.id

    def get_snapshot_comparison(self, comp_id: int) -> Optional[SnapshotComparisonResult]:
        """Retrieve a saved snapshot comparison result by ID."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM research_monitor_comparisons WHERE id = ?;", (comp_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["newly_discovered_products"] = json.loads(d.pop("newly_discovered_products_json", "[]") or "[]")
            d["dropped_products"] = json.loads(d.pop("dropped_products_json", "[]") or "[]")
            d["video_count_changes"] = json.loads(d.pop("video_count_changes_json", "[]") or "[]")
            d["score_changes"] = json.loads(d.pop("score_changes_json", "[]") or "[]")
            d["coverage_changes"] = json.loads(d.pop("coverage_changes_json", "[]") or "[]")
            d["newly_observed_channels"] = json.loads(d.pop("newly_observed_channels_json", "[]") or "[]")
            d["comparison_matrix"] = json.loads(d.pop("comparison_matrix_json", "[]") or "[]")
            return SnapshotComparisonResult.from_dict(d)

    def get_comparison_by_runs(self, run_a_id: int, run_b_id: int) -> Optional[SnapshotComparisonResult]:
        """Retrieve comparison between two specific runs if previously calculated."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM research_monitor_comparisons WHERE run_a_id = ? AND run_b_id = ? LIMIT 1;",
                (run_a_id, run_b_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["newly_discovered_products"] = json.loads(d.pop("newly_discovered_products_json", "[]") or "[]")
            d["dropped_products"] = json.loads(d.pop("dropped_products_json", "[]") or "[]")
            d["video_count_changes"] = json.loads(d.pop("video_count_changes_json", "[]") or "[]")
            d["score_changes"] = json.loads(d.pop("score_changes_json", "[]") or "[]")
            d["coverage_changes"] = json.loads(d.pop("coverage_changes_json", "[]") or "[]")
            d["newly_observed_channels"] = json.loads(d.pop("newly_observed_channels_json", "[]") or "[]")
            d["comparison_matrix"] = json.loads(d.pop("comparison_matrix_json", "[]") or "[]")
            return SnapshotComparisonResult.from_dict(d)

    def get_latest_comparisons(
        self, niche: Optional[str] = None, limit: int = 50
    ) -> List[SnapshotComparisonResult]:
        """Retrieve recent comparison results."""
        self._ensure_phase15_tables()
        query = "SELECT * FROM research_monitor_comparisons WHERE 1=1"
        params: List[Any] = []
        if niche and niche != "All":
            query += " AND LOWER(niche) = LOWER(?)"
            params.append(niche.strip())
        query += " ORDER BY id DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["newly_discovered_products"] = json.loads(d.pop("newly_discovered_products_json", "[]") or "[]")
                d["dropped_products"] = json.loads(d.pop("dropped_products_json", "[]") or "[]")
                d["video_count_changes"] = json.loads(d.pop("video_count_changes_json", "[]") or "[]")
                d["score_changes"] = json.loads(d.pop("score_changes_json", "[]") or "[]")
                d["coverage_changes"] = json.loads(d.pop("coverage_changes_json", "[]") or "[]")
                d["newly_observed_channels"] = json.loads(d.pop("newly_observed_channels_json", "[]") or "[]")
                d["comparison_matrix"] = json.loads(d.pop("comparison_matrix_json", "[]") or "[]")
                results.append(SnapshotComparisonResult.from_dict(d))
            return results

    def save_monitor_alerts(self, alerts: List[MonitorAlert]) -> int:
        """Batch save detected in-app change alerts."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        with self.get_connection() as conn:
            for a in alerts:
                ev_json = json.dumps(a.evidence_data or {})
                conn.execute(
                    """
                    INSERT INTO research_monitor_alerts (
                        run_id, config_id, niche, product_name, alert_type,
                        severity, title, message, evidence_data_json,
                        is_dismissed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        a.run_id, a.config_id, a.niche, a.product_name,
                        a.alert_type, a.severity, a.title, a.message,
                        ev_json, 1 if a.is_dismissed else 0, a.created_at or now,
                    ),
                )
                count += 1
        return count

    def get_monitor_alerts(
        self,
        niche: Optional[str] = None,
        include_dismissed: bool = False,
        unread_only: Optional[bool] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[MonitorAlert]:
        """Retrieve change alerts with optional status and severity filtering."""
        self._ensure_phase15_tables()
        if unread_only is not None:
            include_dismissed = not unread_only

        query = "SELECT * FROM research_monitor_alerts WHERE 1=1"
        params: List[Any] = []
        if not include_dismissed:
            query += " AND is_dismissed = 0"
        if niche and niche != "All":
            query += " AND LOWER(niche) = LOWER(?)"
            params.append(niche.strip())
        if severity and severity != "All":
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY id DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["evidence_data"] = json.loads(d.pop("evidence_data_json", "{}") or "{}")
                d["is_dismissed"] = bool(d.get("is_dismissed", 0))
                results.append(MonitorAlert.from_dict(d))
            return results

    def dismiss_monitor_alert(self, alert_id: int) -> bool:
        """Mark an in-app alert as dismissed."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE research_monitor_alerts SET is_dismissed = 1 WHERE id = ?;", (alert_id,)
            )
            return cursor.rowcount > 0

    def clear_all_alerts(self, niche: Optional[str] = None) -> int:
        """Dismiss all alerts for a niche or across the application."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            if niche and niche != "All":
                cursor = conn.execute(
                    "UPDATE research_monitor_alerts SET is_dismissed = 1 WHERE LOWER(niche) = LOWER(?);",
                    (niche.strip(),),
                )
            else:
                cursor = conn.execute("UPDATE research_monitor_alerts SET is_dismissed = 1;")
            return cursor.rowcount

    def save_monitor_schedule(self, sched: ResearchSchedule) -> int:
        """Insert or update a recurring research schedule."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_monitor_schedules (
                    config_id, niche, frequency, local_time, timezone_name,
                    is_enabled, last_run_at, next_run_at, last_window_key,
                    missed_runs_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(config_id) DO UPDATE SET
                    frequency = excluded.frequency,
                    local_time = excluded.local_time,
                    timezone_name = excluded.timezone_name,
                    is_enabled = excluded.is_enabled,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    last_window_key = excluded.last_window_key,
                    missed_runs_count = excluded.missed_runs_count,
                    updated_at = excluded.updated_at;
                """,
                (
                    sched.config_id, sched.niche, sched.frequency, sched.local_time,
                    sched.timezone_name, 1 if sched.is_enabled else 0,
                    sched.last_run_at, sched.next_run_at, sched.last_window_key,
                    sched.missed_runs_count, sched.created_at or now, now,
                ),
            )
            sched.id = cursor.lastrowid
            return sched.id

    def get_monitor_schedules(self, only_enabled: bool = False) -> List[ResearchSchedule]:
        """Retrieve research schedule definitions."""
        self._ensure_phase15_tables()
        query = "SELECT * FROM research_monitor_schedules WHERE 1=1"
        if only_enabled:
            query += " AND is_enabled = 1"
        query += " ORDER BY id ASC;"

        with self.get_connection() as conn:
            cursor = conn.execute(query)
            results = []
            for r in cursor.fetchall():
                d = dict(r)
                d["is_enabled"] = bool(d.get("is_enabled", 1))
                results.append(ResearchSchedule.from_dict(d))
            return results

    def get_monitor_schedule_by_config(self, config_id: int) -> Optional[ResearchSchedule]:
        """Retrieve schedule for a specific config."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM research_monitor_schedules WHERE config_id = ? LIMIT 1;", (config_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_enabled"] = bool(d.get("is_enabled", 1))
            return ResearchSchedule.from_dict(d)

    def update_schedule_window(
        self,
        schedule_id: int,
        window_key: Optional[str] = None,
        last_run_at: Optional[str] = None,
        next_run_at: Optional[str] = None,
        last_window_key: Optional[str] = None,
    ) -> bool:
        """Update last window deduplication key and execution timestamps."""
        self._ensure_phase15_tables()
        now = datetime.now(timezone.utc).isoformat()
        effective_window = last_window_key if last_window_key is not None else (window_key or "")
        effective_last_run = last_run_at or now

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE research_monitor_schedules SET
                    last_window_key = ?, last_run_at = ?, next_run_at = COALESCE(?, next_run_at), updated_at = ?
                WHERE id = ?;
                """,
                (effective_window, effective_last_run, next_run_at, now, schedule_id),
            )
            return cursor.rowcount > 0

    def delete_monitor_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule definition."""
        self._ensure_phase15_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM research_monitor_schedules WHERE id = ?;", (schedule_id,)
            )
            return cursor.rowcount > 0

    # --------------------------------------------------------------------------
    # Phase 22: Four-Channel Portfolio, Daily Morning Reports, Ideas & Descriptions
    # --------------------------------------------------------------------------

    def get_channel_profiles(self) -> List[ChannelProfile]:
        """Retrieve all configured channel profiles ordered by ID."""
        self._ensure_phase22_tables()
        profiles: List[ChannelProfile] = []
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, channel_name, channel_handle, channel_url, channel_niche,
                       sub_niches_json, target_audience, target_country, target_language,
                       content_format, affiliate_enabled, preferred_affiliate_markets_json,
                       preferred_publishing_frequency, existing_video_topics_json,
                       excluded_topics_json, excluded_brands_json, excluded_products_json,
                       excluded_keywords_json, channel_footer, seo_settings_json,
                       daily_research_settings_json, created_at, updated_at
                FROM channel_profiles
                ORDER BY id ASC;
                """
            )
            for row in cursor.fetchall():
                try:
                    p = ChannelProfile(
                        id=row[0],
                        channel_name=row[1],
                        channel_handle=row[2],
                        channel_url=row[3],
                        channel_niche=row[4],
                        sub_niches=json.loads(row[5] or "[]"),
                        target_audience=row[6],
                        target_country=row[7],
                        target_language=row[8],
                        content_format=row[9],
                        affiliate_enabled=bool(row[10]),
                        preferred_affiliate_markets=json.loads(row[11] or "[]"),
                        preferred_publishing_frequency=row[12],
                        existing_video_topics=json.loads(row[13] or "[]"),
                        excluded_topics=json.loads(row[14] or "[]"),
                        excluded_brands=json.loads(row[15] or "[]"),
                        excluded_products=json.loads(row[16] or "[]"),
                        excluded_keywords=json.loads(row[17] or "[]"),
                        channel_footer=row[18],
                        seo_settings=json.loads(row[19] or "{}"),
                        daily_research_settings=json.loads(row[20] or "{}"),
                        created_at=row[21],
                        updated_at=row[22],
                    )
                    profiles.append(p)
                except Exception:
                    continue
        return profiles

    def get_channel_profile(self, channel_id: int) -> Optional[ChannelProfile]:
        """Retrieve a specific channel profile by its ID (1-4)."""
        self._ensure_phase22_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, channel_name, channel_handle, channel_url, channel_niche,
                       sub_niches_json, target_audience, target_country, target_language,
                       content_format, affiliate_enabled, preferred_affiliate_markets_json,
                       preferred_publishing_frequency, existing_video_topics_json,
                       excluded_topics_json, excluded_brands_json, excluded_products_json,
                       excluded_keywords_json, channel_footer, seo_settings_json,
                       daily_research_settings_json, created_at, updated_at
                FROM channel_profiles
                WHERE id = ?;
                """,
                (channel_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return ChannelProfile(
                id=row[0],
                channel_name=row[1],
                channel_handle=row[2],
                channel_url=row[3],
                channel_niche=row[4],
                sub_niches=json.loads(row[5] or "[]"),
                target_audience=row[6],
                target_country=row[7],
                target_language=row[8],
                content_format=row[9],
                affiliate_enabled=bool(row[10]),
                preferred_affiliate_markets=json.loads(row[11] or "[]"),
                preferred_publishing_frequency=row[12],
                existing_video_topics=json.loads(row[13] or "[]"),
                excluded_topics=json.loads(row[14] or "[]"),
                excluded_brands=json.loads(row[15] or "[]"),
                excluded_products=json.loads(row[16] or "[]"),
                excluded_keywords=json.loads(row[17] or "[]"),
                channel_footer=row[18],
                seo_settings=json.loads(row[19] or "{}"),
                daily_research_settings=json.loads(row[20] or "{}"),
                created_at=row[21],
                updated_at=row[22],
            )

    def save_channel_profile(self, profile: ChannelProfile) -> int:
        """Upsert a channel profile and return its ID."""
        self._ensure_phase22_tables()
        now = datetime.now(timezone.utc).isoformat()
        if not profile.created_at:
            profile.created_at = now
        profile.updated_at = now
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO channel_profiles (
                    id, channel_name, channel_handle, channel_url, channel_niche,
                    sub_niches_json, target_audience, target_country, target_language,
                    content_format, affiliate_enabled, preferred_affiliate_markets_json,
                    preferred_publishing_frequency, existing_video_topics_json,
                    excluded_topics_json, excluded_brands_json, excluded_products_json,
                    excluded_keywords_json, channel_footer, seo_settings_json,
                    daily_research_settings_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    profile.id,
                    profile.channel_name,
                    profile.channel_handle,
                    profile.channel_url,
                    profile.channel_niche,
                    json.dumps(profile.sub_niches),
                    profile.target_audience,
                    profile.target_country,
                    profile.target_language,
                    profile.content_format,
                    1 if profile.affiliate_enabled else 0,
                    json.dumps(profile.preferred_affiliate_markets),
                    profile.preferred_publishing_frequency,
                    json.dumps(profile.existing_video_topics),
                    json.dumps(profile.excluded_topics),
                    json.dumps(profile.excluded_brands),
                    json.dumps(profile.excluded_products),
                    json.dumps(profile.excluded_keywords),
                    profile.channel_footer,
                    json.dumps(profile.seo_settings),
                    json.dumps(profile.daily_research_settings),
                    profile.created_at,
                    profile.updated_at,
                ),
            )
            return profile.id or 1

    def save_daily_morning_report(self, report: DailyMorningReport) -> int:
        """Save a daily morning report with all nested idea items."""
        self._ensure_phase22_tables()
        now = datetime.now(timezone.utc).isoformat()
        if not report.started_at:
            report.started_at = now
        if not report.completed_at:
            report.completed_at = now
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO daily_morning_reports (
                    run_date, timezone_name, scheduled_time, status,
                    total_channels_processed, total_ideas_generated,
                    total_queries_executed, api_quota_units_used,
                    summary_notes, error_message, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    report.run_date,
                    report.timezone_name,
                    report.scheduled_time,
                    report.status,
                    report.total_channels_processed,
                    len(report.ideas),
                    report.total_queries_executed,
                    report.api_quota_units_used,
                    report.summary_notes,
                    report.error_message,
                    report.started_at,
                    report.completed_at,
                ),
            )
            report_id = cursor.lastrowid
            report.id = report_id

            for idea in report.ideas:
                idea.report_id = report_id
                if not idea.created_at:
                    idea.created_at = now
                conn.execute(
                    """
                    INSERT INTO daily_idea_items (
                        report_id, channel_id, channel_name, proposed_topic,
                        main_keyword, supporting_keywords_json, search_intent,
                        target_viewer, why_topic_worth_researching,
                        recent_relevant_videos_found, exact_research_window,
                        source_and_coverage_summary, potential_product_match,
                        affiliate_availability_status, opportunity_estimate,
                        confidence_level, suggested_video_format,
                        seo_focused_title_options_json, suggested_thumbnail_concept,
                        description_draft, next_recommended_action, review_label,
                        gap_state, sample_video_ids_json, sample_video_titles_json,
                        is_saved, is_rejected, is_marked_covered, is_added_to_calendar,
                        created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                    """,
                    (
                        idea.report_id,
                        idea.channel_id,
                        idea.channel_name,
                        idea.proposed_topic,
                        idea.main_keyword,
                        json.dumps(idea.supporting_keywords),
                        idea.search_intent,
                        idea.target_viewer,
                        idea.why_topic_worth_researching,
                        idea.recent_relevant_videos_found,
                        idea.exact_research_window,
                        idea.source_and_coverage_summary,
                        idea.potential_product_match,
                        idea.affiliate_availability_status,
                        idea.opportunity_estimate,
                        idea.confidence_level,
                        idea.suggested_video_format,
                        json.dumps(idea.seo_focused_title_options),
                        idea.suggested_thumbnail_concept,
                        idea.description_draft,
                        idea.next_recommended_action,
                        idea.review_label,
                        idea.gap_state,
                        json.dumps(idea.sample_video_ids),
                        json.dumps(idea.sample_video_titles),
                        1 if idea.is_saved else 0,
                        1 if idea.is_rejected else 0,
                        1 if idea.is_marked_covered else 0,
                        1 if idea.is_added_to_calendar else 0,
                        idea.created_at,
                    ),
                )
            return report_id

    def get_daily_morning_reports(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieve recent daily morning report runs."""
        self._ensure_phase22_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, run_date, timezone_name, scheduled_time, status,
                       total_channels_processed, total_ideas_generated,
                       total_queries_executed, api_quota_units_used,
                       summary_notes, error_message, started_at, completed_at
                FROM daily_morning_reports
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "run_date": r[1],
                    "timezone_name": r[2],
                    "scheduled_time": r[3],
                    "status": r[4],
                    "total_channels_processed": r[5],
                    "total_ideas_generated": r[6],
                    "total_queries_executed": r[7],
                    "api_quota_units_used": r[8],
                    "summary_notes": r[9],
                    "error_message": r[10],
                    "started_at": r[11],
                    "completed_at": r[12],
                }
                for r in rows
            ]

    def _row_to_daily_idea_item(self, row: Any) -> DailyIdeaItem:
        """Helper to transform an SQLite row into a DailyIdeaItem."""
        return DailyIdeaItem(
            id=row[0],
            report_id=row[1],
            channel_id=row[2],
            channel_name=row[3],
            proposed_topic=row[4],
            main_keyword=row[5],
            supporting_keywords=json.loads(row[6] or "[]"),
            search_intent=row[7],
            target_viewer=row[8],
            why_topic_worth_researching=row[9],
            recent_relevant_videos_found=row[10],
            exact_research_window=row[11],
            source_and_coverage_summary=row[12],
            potential_product_match=row[13],
            affiliate_availability_status=row[14],
            opportunity_estimate=row[15],
            confidence_level=row[16],
            suggested_video_format=row[17],
            seo_focused_title_options=json.loads(row[18] or "[]"),
            suggested_thumbnail_concept=row[19],
            description_draft=row[20],
            next_recommended_action=row[21],
            review_label=row[22],
            gap_state=row[23],
            sample_video_ids=json.loads(row[24] or "[]"),
            sample_video_titles=json.loads(row[25] or "[]"),
            is_saved=bool(row[26]),
            is_rejected=bool(row[27]),
            is_marked_covered=bool(row[28]),
            is_added_to_calendar=bool(row[29]),
            created_at=row[30],
        )

    def get_daily_ideas_by_channel(self, channel_id: int, limit: int = 50) -> List[DailyIdeaItem]:
        """Retrieve daily ideas generated for a specific channel."""
        self._ensure_phase22_tables()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, report_id, channel_id, channel_name, proposed_topic,
                       main_keyword, supporting_keywords_json, search_intent,
                       target_viewer, why_topic_worth_researching,
                       recent_relevant_videos_found, exact_research_window,
                       source_and_coverage_summary, potential_product_match,
                       affiliate_availability_status, opportunity_estimate,
                       confidence_level, suggested_video_format,
                       seo_focused_title_options_json, suggested_thumbnail_concept,
                       description_draft, next_recommended_action, review_label,
                       gap_state, sample_video_ids_json, sample_video_titles_json,
                       is_saved, is_rejected, is_marked_covered, is_added_to_calendar,
                       created_at
                FROM daily_idea_items
                WHERE channel_id = ?
                ORDER BY id DESC
                LIMIT ?;
                """,
                (channel_id, limit),
            )
            return [self._row_to_daily_idea_item(r) for r in cursor.fetchall()]

    def get_all_daily_ideas(self, limit: int = 200, channel_id: Optional[int] = None) -> List[DailyIdeaItem]:
        """Retrieve latest ideas across channels."""
        self._ensure_phase22_tables()
        with self.get_connection() as conn:
            if channel_id is not None:
                cursor = conn.execute(
                    """
                    SELECT id, report_id, channel_id, channel_name, proposed_topic,
                           main_keyword, supporting_keywords_json, search_intent,
                           target_viewer, why_topic_worth_researching,
                           recent_relevant_videos_found, exact_research_window,
                           source_and_coverage_summary, potential_product_match,
                           affiliate_availability_status, opportunity_estimate,
                           confidence_level, suggested_video_format,
                           seo_focused_title_options_json, suggested_thumbnail_concept,
                           description_draft, next_recommended_action, review_label,
                           gap_state, sample_video_ids_json, sample_video_titles_json,
                           is_saved, is_rejected, is_marked_covered, is_added_to_calendar,
                           created_at
                    FROM daily_idea_items
                    WHERE channel_id = ?
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (channel_id, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, report_id, channel_id, channel_name, proposed_topic,
                           main_keyword, supporting_keywords_json, search_intent,
                           target_viewer, why_topic_worth_researching,
                           recent_relevant_videos_found, exact_research_window,
                           source_and_coverage_summary, potential_product_match,
                           affiliate_availability_status, opportunity_estimate,
                           confidence_level, suggested_video_format,
                           seo_focused_title_options_json, suggested_thumbnail_concept,
                           description_draft, next_recommended_action, review_label,
                           gap_state, sample_video_ids_json, sample_video_titles_json,
                           is_saved, is_rejected, is_marked_covered, is_added_to_calendar,
                           created_at
                    FROM daily_idea_items
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
            return [self._row_to_daily_idea_item(r) for r in cursor.fetchall()]

    def update_daily_idea_action(
        self,
        idea_id: int,
        is_saved: Optional[bool] = None,
        is_rejected: Optional[bool] = None,
        is_marked_covered: Optional[bool] = None,
        is_added_to_calendar: Optional[bool] = None,
        review_label: Optional[str] = None,
    ) -> bool:
        """Update actions and review status for a specific daily idea."""
        self._ensure_phase22_tables()
        updates = []
        params = []
        if is_saved is not None:
            updates.append("is_saved = ?")
            params.append(1 if is_saved else 0)
        if is_rejected is not None:
            updates.append("is_rejected = ?")
            params.append(1 if is_rejected else 0)
        if is_marked_covered is not None:
            updates.append("is_marked_covered = ?")
            params.append(1 if is_marked_covered else 0)
        if is_added_to_calendar is not None:
            updates.append("is_added_to_calendar = ?")
            params.append(1 if is_added_to_calendar else 0)
        if review_label is not None:
            updates.append("review_label = ?")
            params.append(review_label)

        if not updates:
            return False

        params.append(idea_id)
        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE daily_idea_items SET {', '.join(updates)} WHERE id = ?;",
                tuple(params),
            )
            return cursor.rowcount > 0

    def save_video_description(
        self,
        channel_id: int,
        channel_name: str,
        topic: str,
        primary_keyword: str,
        full_text: str,
        character_count: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Persist a generated or edited YouTube video description."""
        self._ensure_phase22_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO video_descriptions (
                    channel_id, channel_name, topic, primary_keyword,
                    full_text, character_count, data_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    channel_id,
                    channel_name,
                    topic,
                    primary_keyword,
                    full_text,
                    character_count,
                    json.dumps(data or {}),
                    now,
                    now,
                ),
            )
            return cursor.lastrowid

    def get_video_descriptions(self, channel_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent video descriptions."""
        self._ensure_phase22_tables()
        with self.get_connection() as conn:
            if channel_id is not None:
                cursor = conn.execute(
                    """
                    SELECT id, channel_id, channel_name, topic, primary_keyword,
                           full_text, character_count, data_json, created_at, updated_at
                    FROM video_descriptions
                    WHERE channel_id = ?
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (channel_id, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT id, channel_id, channel_name, topic, primary_keyword,
                           full_text, character_count, data_json, created_at, updated_at
                    FROM video_descriptions
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "channel_name": r[2],
                    "topic": r[3],
                    "primary_keyword": r[4],
                    "full_text": r[5],
                    "character_count": r[6],
                    "data": json.loads(r[7] or "{}"),
                    "created_at": r[8],
                    "updated_at": r[9],
                }
                for r in rows
            ]

    # --------------------------------------------------------------------------
    # Phase 23: Video SEO & Content Quality Audit Persistence
    # --------------------------------------------------------------------------

    def save_seo_audit(self, audit: VideoSeoAudit) -> int:
        """Save or update a Video SEO Audit record and record revision snapshot."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if audit.id is not None:
                conn.execute(
                    """
                    UPDATE video_seo_audits
                    SET channel_id = ?, channel_name = ?, idea_id = ?, primary_keyword = ?,
                        secondary_keywords_json = ?, proposed_title = ?, draft_description = ?,
                        script_text = ?, thumbnail_concept = ?, video_url = ?, is_published_url = ?,
                        scores_json = ?, findings_json = ?, recommendations_json = ?,
                        checklist_json = ?, revision_number = revision_number + 1, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        audit.channel_id,
                        audit.channel_name,
                        audit.idea_id,
                        audit.primary_keyword,
                        json.dumps(audit.secondary_keywords),
                        audit.proposed_title,
                        audit.draft_description,
                        audit.script_text,
                        audit.thumbnail_concept,
                        audit.video_url,
                        1 if audit.is_published_url else 0,
                        json.dumps({
                            "overall": audit.scores.overall_readiness_score,
                            "title": audit.scores.title_score,
                            "description": audit.scores.description_score,
                            "script": audit.scores.script_alignment_score,
                            "affiliate": audit.scores.affiliate_quality_score,
                            "thumbnail": audit.scores.thumbnail_score,
                            "deductions": audit.scores.deductions,
                            "checked": audit.scores.checked_categories,
                            "not_checked": audit.scores.not_checked_categories,
                            "not_applicable": audit.scores.not_applicable_categories,
                            "prioritized_actions": audit.scores.prioritized_actions,
                        }),
                        json.dumps([
                            {
                                "category": f.category,
                                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                                "title": f.title,
                                "message": f.message,
                                "evidence_source": f.evidence_source,
                                "suggestion": f.suggestion,
                                "is_objective": f.is_objective,
                            }
                            for f in audit.findings
                        ]),
                        json.dumps({
                            "title_alternatives": audit.title_result.alternatives,
                            "truncation_risk": audit.title_result.truncation_risk,
                            "script_status": audit.script_result.status.value if hasattr(audit.script_result.status, "value") else str(audit.script_result.status),
                            "affiliate_status": audit.affiliate_result.status.value if hasattr(audit.affiliate_result.status, "value") else str(audit.affiliate_result.status),
                            "thumbnail_readability": audit.thumbnail_result.readability_assessment,
                        }),
                        json.dumps([
                            {
                                "item_id": c.item_id,
                                "label": c.label,
                                "category": c.category,
                                "is_completed": c.is_completed,
                                "is_manual_required": c.is_manual_required,
                                "help_text": c.help_text,
                            }
                            for c in audit.checklist
                        ]),
                        now_iso,
                        audit.id,
                    ),
                )
                audit_id = audit.id
                cur = conn.execute("SELECT revision_number FROM video_seo_audits WHERE id = ?;", (audit_id,))
                rev_num = cur.fetchone()[0]
                audit.revision_number = rev_num
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO video_seo_audits (
                        channel_id, channel_name, idea_id, primary_keyword,
                        secondary_keywords_json, proposed_title, draft_description,
                        script_text, thumbnail_concept, video_url, is_published_url,
                        scores_json, findings_json, recommendations_json,
                        checklist_json, revision_number, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
                    """,
                    (
                        audit.channel_id,
                        audit.channel_name,
                        audit.idea_id,
                        audit.primary_keyword,
                        json.dumps(audit.secondary_keywords),
                        audit.proposed_title,
                        audit.draft_description,
                        audit.script_text,
                        audit.thumbnail_concept,
                        audit.video_url,
                        1 if audit.is_published_url else 0,
                        json.dumps({
                            "overall": audit.scores.overall_readiness_score,
                            "title": audit.scores.title_score,
                            "description": audit.scores.description_score,
                            "script": audit.scores.script_alignment_score,
                            "affiliate": audit.scores.affiliate_quality_score,
                            "thumbnail": audit.scores.thumbnail_score,
                            "deductions": audit.scores.deductions,
                            "checked": audit.scores.checked_categories,
                            "not_checked": audit.scores.not_checked_categories,
                            "not_applicable": audit.scores.not_applicable_categories,
                            "prioritized_actions": audit.scores.prioritized_actions,
                        }),
                        json.dumps([
                            {
                                "category": f.category,
                                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                                "title": f.title,
                                "message": f.message,
                                "evidence_source": f.evidence_source,
                                "suggestion": f.suggestion,
                                "is_objective": f.is_objective,
                            }
                            for f in audit.findings
                        ]),
                        json.dumps({
                            "title_alternatives": audit.title_result.alternatives,
                            "truncation_risk": audit.title_result.truncation_risk,
                            "script_status": audit.script_result.status.value if hasattr(audit.script_result.status, "value") else str(audit.script_result.status),
                            "affiliate_status": audit.affiliate_result.status.value if hasattr(audit.affiliate_result.status, "value") else str(audit.affiliate_result.status),
                            "thumbnail_readability": audit.thumbnail_result.readability_assessment,
                        }),
                        json.dumps([
                            {
                                "item_id": c.item_id,
                                "label": c.label,
                                "category": c.category,
                                "is_completed": c.is_completed,
                                "is_manual_required": c.is_manual_required,
                                "help_text": c.help_text,
                            }
                            for c in audit.checklist
                        ]),
                        now_iso,
                        now_iso,
                    ),
                )
                audit_id = cursor.lastrowid
                audit.id = audit_id
                audit.revision_number = 1

            # Save revision snapshot
            conn.execute(
                """
                INSERT INTO video_seo_audit_revisions (
                    audit_id, revision_number, proposed_title, draft_description,
                    script_text, thumbnail_concept, scores_json, findings_json,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_id,
                    audit.revision_number,
                    audit.proposed_title,
                    audit.draft_description,
                    audit.script_text,
                    audit.thumbnail_concept,
                    json.dumps({
                        "overall": audit.scores.overall_readiness_score,
                        "title": audit.scores.title_score,
                        "description": audit.scores.description_score,
                        "script": audit.scores.script_alignment_score,
                        "affiliate": audit.scores.affiliate_quality_score,
                        "thumbnail": audit.scores.thumbnail_score,
                    }),
                    json.dumps([f.title for f in audit.findings]),
                    f"Revision #{audit.revision_number}",
                    now_iso,
                ),
            )
            return audit_id

    def get_seo_audit(self, audit_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full audit record by ID as a dictionary."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, channel_id, channel_name, idea_id, primary_keyword,
                       secondary_keywords_json, proposed_title, draft_description,
                       script_text, thumbnail_concept, video_url, is_published_url,
                       scores_json, findings_json, recommendations_json,
                       checklist_json, revision_number, created_at, updated_at
                FROM video_seo_audits
                WHERE id = ?;
                """,
                (audit_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "channel_id": row[1],
                "channel_name": row[2],
                "idea_id": row[3],
                "primary_keyword": row[4],
                "secondary_keywords": json.loads(row[5] or "[]"),
                "proposed_title": row[6],
                "draft_description": row[7],
                "script_text": row[8],
                "thumbnail_concept": row[9],
                "video_url": row[10],
                "is_published_url": bool(row[11]),
                "scores": json.loads(row[12] or "{}"),
                "findings": json.loads(row[13] or "[]"),
                "recommendations": json.loads(row[14] or "{}"),
                "checklist": json.loads(row[15] or "[]"),
                "revision_number": row[16],
                "created_at": row[17],
                "updated_at": row[18],
            }

    def get_seo_audits_by_channel(self, channel_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent SEO audits for a channel (or all channels)."""
        with self.get_connection() as conn:
            if channel_id is not None:
                cur = conn.execute(
                    """
                    SELECT id, channel_id, channel_name, idea_id, primary_keyword,
                           proposed_title, revision_number, scores_json, created_at, updated_at
                    FROM video_seo_audits
                    WHERE channel_id = ?
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (channel_id, limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT id, channel_id, channel_name, idea_id, primary_keyword,
                           proposed_title, revision_number, scores_json, created_at, updated_at
                    FROM video_seo_audits
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "channel_name": r[2],
                    "idea_id": r[3],
                    "primary_keyword": r[4],
                    "proposed_title": r[5],
                    "revision_number": r[6],
                    "scores": json.loads(r[7] or "{}"),
                    "created_at": r[8],
                    "updated_at": r[9],
                }
                for r in rows
            ]

    def get_audit_revisions(self, audit_id: int) -> List[Dict[str, Any]]:
        """Retrieve all revision snapshots for an audit ID."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, audit_id, revision_number, proposed_title, draft_description,
                       script_text, thumbnail_concept, scores_json, findings_json,
                       notes, created_at
                FROM video_seo_audit_revisions
                WHERE audit_id = ?
                ORDER BY revision_number ASC;
                """,
                (audit_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "audit_id": r[1],
                    "revision_number": r[2],
                    "proposed_title": r[3],
                    "draft_description": r[4],
                    "script_text": r[5],
                    "thumbnail_concept": r[6],
                    "scores": json.loads(r[7] or "{}"),
                    "findings": json.loads(r[8] or "[]"),
                    "notes": r[9],
                    "created_at": r[10],
                }
                for r in rows
            ]

    def delete_seo_audit(self, audit_id: int) -> bool:
        """Delete an SEO audit and its cascade revisions."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM video_seo_audits WHERE id = ?;", (audit_id,))
            return cur.rowcount > 0

    # --------------------------------------------------------------------------
    # Phase 24: YouTube Analytics & Four-Channel Growth Intelligence Persistence
    # --------------------------------------------------------------------------

    def save_channel_credentials(self, creds: ChannelOAuthCredentials) -> bool:
        """Save or update OAuth credentials for a channel."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO channel_analytics_credentials (
                    channel_id, channel_name, client_id, client_secret,
                    access_token, refresh_token, token_expiry, scopes_json,
                    auth_status, connected_at, last_refreshed_at, error_message,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_name = excluded.channel_name,
                    client_id = excluded.client_id,
                    client_secret = excluded.client_secret,
                    access_token = excluded.access_token,
                    refresh_token = COALESCE(excluded.refresh_token, channel_analytics_credentials.refresh_token),
                    token_expiry = excluded.token_expiry,
                    scopes_json = excluded.scopes_json,
                    auth_status = excluded.auth_status,
                    connected_at = COALESCE(excluded.connected_at, channel_analytics_credentials.connected_at),
                    last_refreshed_at = excluded.last_refreshed_at,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at;
                """,
                (
                    creds.channel_id,
                    creds.channel_name,
                    creds.client_id,
                    creds.client_secret,
                    creds.access_token,
                    creds.refresh_token,
                    creds.token_expiry,
                    json.dumps(creds.scopes),
                    creds.auth_status.value if hasattr(creds.auth_status, "value") else str(creds.auth_status),
                    creds.connected_at or now_iso,
                    creds.last_refreshed_at or now_iso,
                    creds.error_message,
                    now_iso,
                    now_iso,
                ),
            )
            return True

    def get_channel_credentials(self, channel_id: int) -> Optional[ChannelOAuthCredentials]:
        """Retrieve stored OAuth credentials for a channel."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT channel_id, channel_name, client_id, client_secret,
                       access_token, refresh_token, token_expiry, scopes_json,
                       auth_status, connected_at, last_refreshed_at, error_message
                FROM channel_analytics_credentials
                WHERE channel_id = ?;
                """,
                (channel_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                status = AnalyticsAuthStatus(row[8])
            except (ValueError, KeyError):
                status = AnalyticsAuthStatus.NOT_CONNECTED

            return ChannelOAuthCredentials(
                channel_id=row[0],
                channel_name=row[1],
                client_id=row[2],
                client_secret=row[3],
                access_token=row[4],
                refresh_token=row[5],
                token_expiry=row[6],
                scopes=json.loads(row[7] or "[]"),
                auth_status=status,
                connected_at=row[9],
                last_refreshed_at=row[10],
                error_message=row[11],
            )

    def delete_channel_credentials(self, channel_id: int) -> bool:
        """Revoke and delete OAuth credentials for a channel."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM channel_analytics_credentials WHERE channel_id = ?;", (channel_id,))
            return cur.rowcount > 0

    def save_analytics_snapshot(
        self,
        channel_id: int,
        date_start: str,
        date_end: str,
        metrics: Dict[str, Any],
        is_authorized: bool = True,
    ) -> int:
        """Persist an analytics overview snapshot for historical tracking."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO channel_analytics_snapshots (
                    channel_id, date_start, date_end, metrics_json,
                    is_authorized, retrieved_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    channel_id,
                    date_start,
                    date_end,
                    json.dumps(metrics),
                    1 if is_authorized else 0,
                    now_iso,
                    now_iso,
                ),
            )
            return cur.lastrowid

    def get_recent_analytics_snapshots(self, channel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent analytics snapshots for a channel."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, channel_id, date_start, date_end, metrics_json,
                       is_authorized, retrieved_at, created_at
                FROM channel_analytics_snapshots
                WHERE channel_id = ?
                ORDER BY id DESC
                LIMIT ?;
                """,
                (channel_id, limit),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "date_start": r[2],
                    "date_end": r[3],
                    "metrics": json.loads(r[4] or "{}"),
                    "is_authorized": bool(r[5]),
                    "retrieved_at": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]

    def save_publishing_experiment(self, exp: PublishingExperiment) -> int:
        """Insert or update a publishing experiment."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if exp.id is not None:
                conn.execute(
                    """
                    UPDATE publishing_experiments
                    SET channel_id = ?, experiment_name = ?, video_id = ?, video_title = ?,
                        experiment_type = ?, hypothesis = ?, status = ?, started_at = ?,
                        completed_at = ?, pre_metrics_json = ?, post_metrics_json = ?,
                        outcome_conclusion = ?, is_conclusive = ?, confounding_factors_json = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        exp.channel_id,
                        exp.experiment_name,
                        exp.video_id,
                        exp.video_title,
                        exp.experiment_type,
                        exp.hypothesis,
                        exp.status,
                        exp.started_at,
                        exp.completed_at,
                        json.dumps(exp.pre_metrics),
                        json.dumps(exp.post_metrics),
                        exp.outcome_conclusion,
                        1 if exp.is_conclusive else 0,
                        json.dumps(exp.confounding_factors),
                        now_iso,
                        exp.id,
                    ),
                )
                return exp.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO publishing_experiments (
                        channel_id, experiment_name, video_id, video_title,
                        experiment_type, hypothesis, status, started_at,
                        completed_at, pre_metrics_json, post_metrics_json,
                        outcome_conclusion, is_conclusive, confounding_factors_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        exp.channel_id,
                        exp.experiment_name,
                        exp.video_id,
                        exp.video_title,
                        exp.experiment_type,
                        exp.hypothesis,
                        exp.status,
                        exp.started_at or now_iso,
                        exp.completed_at,
                        json.dumps(exp.pre_metrics),
                        json.dumps(exp.post_metrics),
                        exp.outcome_conclusion,
                        1 if exp.is_conclusive else 0,
                        json.dumps(exp.confounding_factors),
                        now_iso,
                        now_iso,
                    ),
                )
                exp.id = cur.lastrowid
                return exp.id

    def get_publishing_experiments(
        self,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve publishing experiments filtered by channel or status."""
        query = (
            "SELECT id, channel_id, experiment_name, video_id, video_title, "
            "experiment_type, hypothesis, status, started_at, completed_at, "
            "pre_metrics_json, post_metrics_json, outcome_conclusion, is_conclusive, "
            "confounding_factors_json, created_at, updated_at "
            "FROM publishing_experiments WHERE 1=1"
        )
        params: List[Any] = []
        if channel_id is not None:
            query += " AND channel_id = ?"
            params.append(channel_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC;"

        with self.get_connection() as conn:
            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "experiment_name": r[2],
                    "video_id": r[3],
                    "video_title": r[4],
                    "experiment_type": r[5],
                    "hypothesis": r[6],
                    "status": r[7],
                    "started_at": r[8],
                    "completed_at": r[9],
                    "pre_metrics": json.loads(r[10] or "{}"),
                    "post_metrics": json.loads(r[11] or "{}"),
                    "outcome_conclusion": r[12],
                    "is_conclusive": bool(r[13]),
                    "confounding_factors": json.loads(r[14] or "[]"),
                    "created_at": r[15],
                    "updated_at": r[16],
                }
                for r in rows
            ]

    def update_publishing_experiment(self, exp_id: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a publishing experiment."""
        if not updates:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso
        cols = []
        vals = []
        for k, v in updates.items():
            cols.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            elif isinstance(v, bool):
                vals.append(1 if v else 0)
            else:
                vals.append(v)
        vals.append(exp_id)
        sql = f"UPDATE publishing_experiments SET {', '.join(cols)} WHERE id = ?;"
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(vals))
            return cur.rowcount > 0

    def delete_publishing_experiment(self, exp_id: int) -> bool:
        """Delete a publishing experiment by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM publishing_experiments WHERE id = ?;", (exp_id,))
            return cur.rowcount > 0

    # --------------------------------------------------------------------------
    # Phase 25: YouTube Content Strategy Autopilot Facilities
    # --------------------------------------------------------------------------

    def get_channel_strategy_settings(self, channel_id: int) -> ChannelStrategySettings:
        """Get strategy settings for a channel, returning defaults if not saved."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT channel_id, videos_per_week, longform_pct, shorts_pct,
                       weekly_production_hours_budget, preferred_publishing_days_json,
                       preferred_duration_range, strategic_priority, created_at, updated_at
                FROM channel_strategy_settings WHERE channel_id = ?;
                """,
                (channel_id,),
            ).fetchone()
            if not row:
                return ChannelStrategySettings(channel_id=channel_id)
            return ChannelStrategySettings(
                channel_id=row[0],
                videos_per_week=row[1],
                longform_pct=row[2],
                shorts_pct=row[3],
                weekly_production_hours_budget=row[4],
                preferred_publishing_days=json.loads(row[5]) if row[5] else ["Tuesday", "Saturday"],
                preferred_duration_range=row[6],
                strategic_priority=row[7],
                created_at=row[8],
                updated_at=row[9],
            )

    def save_channel_strategy_settings(self, settings: ChannelStrategySettings) -> None:
        """Save or update strategy settings for a channel."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = settings.created_at or now_iso
        updated_at = now_iso
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO channel_strategy_settings (
                    channel_id, videos_per_week, longform_pct, shorts_pct,
                    weekly_production_hours_budget, preferred_publishing_days_json,
                    preferred_duration_range, strategic_priority, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    videos_per_week = excluded.videos_per_week,
                    longform_pct = excluded.longform_pct,
                    shorts_pct = excluded.shorts_pct,
                    weekly_production_hours_budget = excluded.weekly_production_hours_budget,
                    preferred_publishing_days_json = excluded.preferred_publishing_days_json,
                    preferred_duration_range = excluded.preferred_duration_range,
                    strategic_priority = excluded.strategic_priority,
                    updated_at = excluded.updated_at;
                """,
                (
                    settings.channel_id,
                    settings.videos_per_week,
                    settings.longform_pct,
                    settings.shorts_pct,
                    settings.weekly_production_hours_budget,
                    json.dumps(settings.preferred_publishing_days),
                    settings.preferred_duration_range,
                    settings.strategic_priority,
                    created_at,
                    updated_at,
                ),
            )

    def save_content_pillar(self, pillar: ContentPillar) -> int:
        """Save a new content pillar or update an existing one."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = pillar.created_at or now_iso
        updated_at = now_iso
        with self.get_connection() as conn:
            if pillar.id:
                conn.execute(
                    """
                    UPDATE content_pillars SET
                        pillar_name = ?, description = ?, audience_problem = ?,
                        target_keywords_json = ?, candidate_topics_json = ?,
                        existing_coverage_count = ?, potential_affiliate_relevance = ?,
                        confidence_level = ?, is_approved = ?, notes = ?, updated_at = ?
                    WHERE id = ? AND channel_id = ?;
                    """,
                    (
                        pillar.pillar_name,
                        pillar.description,
                        pillar.audience_problem,
                        json.dumps(pillar.target_keywords),
                        json.dumps(pillar.candidate_topics),
                        pillar.existing_coverage_count,
                        pillar.potential_affiliate_relevance,
                        pillar.confidence_level,
                        1 if pillar.is_approved else 0,
                        pillar.notes,
                        updated_at,
                        pillar.id,
                        pillar.channel_id,
                    ),
                )
                return pillar.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO content_pillars (
                        channel_id, pillar_name, description, audience_problem,
                        target_keywords_json, candidate_topics_json,
                        existing_coverage_count, potential_affiliate_relevance,
                        confidence_level, is_approved, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        pillar.channel_id,
                        pillar.pillar_name,
                        pillar.description,
                        pillar.audience_problem,
                        json.dumps(pillar.target_keywords),
                        json.dumps(pillar.candidate_topics),
                        pillar.existing_coverage_count,
                        pillar.potential_affiliate_relevance,
                        pillar.confidence_level,
                        1 if pillar.is_approved else 0,
                        pillar.notes,
                        created_at,
                        updated_at,
                    ),
                )
                return cur.lastrowid

    def get_content_pillars(self, channel_id: int) -> List[ContentPillar]:
        """Retrieve all content pillars for a given channel."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, pillar_name, description, audience_problem,
                       target_keywords_json, candidate_topics_json,
                       existing_coverage_count, potential_affiliate_relevance,
                       confidence_level, is_approved, notes, created_at, updated_at
                FROM content_pillars WHERE channel_id = ? ORDER BY id ASC;
                """,
                (channel_id,),
            ).fetchall()
            return [
                ContentPillar(
                    id=r[0],
                    channel_id=r[1],
                    pillar_name=r[2],
                    description=r[3],
                    audience_problem=r[4],
                    target_keywords=json.loads(r[5]) if r[5] else [],
                    candidate_topics=json.loads(r[6]) if r[6] else [],
                    existing_coverage_count=r[7],
                    potential_affiliate_relevance=r[8],
                    confidence_level=r[9],
                    is_approved=bool(r[10]),
                    notes=r[11],
                    created_at=r[12],
                    updated_at=r[13],
                )
                for r in rows
            ]

    def get_content_pillar_by_id(self, pillar_id: int) -> Optional[ContentPillar]:
        """Retrieve a content pillar by primary key."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT id, channel_id, pillar_name, description, audience_problem,
                       target_keywords_json, candidate_topics_json,
                       existing_coverage_count, potential_affiliate_relevance,
                       confidence_level, is_approved, notes, created_at, updated_at
                FROM content_pillars WHERE id = ?;
                """,
                (pillar_id,),
            ).fetchone()
            if not r:
                return None
            return ContentPillar(
                id=r[0],
                channel_id=r[1],
                pillar_name=r[2],
                description=r[3],
                audience_problem=r[4],
                target_keywords=json.loads(r[5]) if r[5] else [],
                candidate_topics=json.loads(r[6]) if r[6] else [],
                existing_coverage_count=r[7],
                potential_affiliate_relevance=r[8],
                confidence_level=r[9],
                is_approved=bool(r[10]),
                notes=r[11],
                created_at=r[12],
                updated_at=r[13],
            )

    def delete_content_pillar(self, pillar_id: int) -> bool:
        """Delete a content pillar by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM content_pillars WHERE id = ?;", (pillar_id,))
            return cur.rowcount > 0

    def save_content_cluster(self, cluster: ContentCluster) -> int:
        """Save a new content cluster / video series."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = cluster.created_at or now_iso
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO content_clusters (
                    channel_id, pillar_id, cluster_name, pillar_video_title,
                    supporting_video_titles_json, comparison_video_titles_json,
                    review_video_titles_json, faq_video_titles_json,
                    cluster_rationale, anti_cannibalization_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    cluster.channel_id,
                    cluster.pillar_id,
                    cluster.cluster_name,
                    cluster.pillar_video_title,
                    json.dumps(cluster.supporting_video_titles),
                    json.dumps(cluster.comparison_video_titles),
                    json.dumps(cluster.review_video_titles),
                    json.dumps(cluster.faq_video_titles),
                    cluster.cluster_rationale,
                    cluster.anti_cannibalization_notes,
                    created_at,
                ),
            )
            return cur.lastrowid

    def get_content_clusters(self, channel_id: int, pillar_id: Optional[int] = None) -> List[ContentCluster]:
        """Retrieve content clusters for a channel, optionally filtered by pillar."""
        with self.get_connection() as conn:
            if pillar_id is not None:
                rows = conn.execute(
                    """
                    SELECT id, channel_id, pillar_id, cluster_name, pillar_video_title,
                           supporting_video_titles_json, comparison_video_titles_json,
                           review_video_titles_json, faq_video_titles_json,
                           cluster_rationale, anti_cannibalization_notes, created_at
                    FROM content_clusters WHERE channel_id = ? AND pillar_id = ? ORDER BY id DESC;
                    """,
                    (channel_id, pillar_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, channel_id, pillar_id, cluster_name, pillar_video_title,
                           supporting_video_titles_json, comparison_video_titles_json,
                           review_video_titles_json, faq_video_titles_json,
                           cluster_rationale, anti_cannibalization_notes, created_at
                    FROM content_clusters WHERE channel_id = ? ORDER BY id DESC;
                    """,
                    (channel_id,),
                ).fetchall()
            return [
                ContentCluster(
                    id=r[0],
                    channel_id=r[1],
                    pillar_id=r[2],
                    cluster_name=r[3],
                    pillar_video_title=r[4],
                    supporting_video_titles=json.loads(r[5]) if r[5] else [],
                    comparison_video_titles=json.loads(r[6]) if r[6] else [],
                    review_video_titles=json.loads(r[7]) if r[7] else [],
                    faq_video_titles=json.loads(r[8]) if r[8] else [],
                    cluster_rationale=r[9],
                    anti_cannibalization_notes=r[10],
                    created_at=r[11],
                )
                for r in rows
            ]

    def delete_content_cluster(self, cluster_id: int) -> bool:
        """Delete a content cluster by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM content_clusters WHERE id = ?;", (cluster_id,))
            return cur.rowcount > 0

    def save_prioritized_topic(self, topic: PrioritizedTopic) -> str:
        """Save or update a prioritized topic in SQLite."""
        now_iso = datetime.now(timezone.utc).isoformat()
        research_date = topic.research_date or now_iso[:10]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO prioritized_topics (
                    topic_id, channel_id, proposed_title, target_keyword, search_intent,
                    channel_relevance_score, search_intent_score, keyword_evidence_score,
                    recent_video_evidence_score, research_coverage_score, product_relevance_score,
                    composite_priority_score, estimated_production_effort, selection_rationale,
                    supporting_sources_json, research_date, confidence_level, missing_evidence,
                    suggested_next_step, user_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic_id) DO UPDATE SET
                    proposed_title = excluded.proposed_title,
                    target_keyword = excluded.target_keyword,
                    search_intent = excluded.search_intent,
                    channel_relevance_score = excluded.channel_relevance_score,
                    search_intent_score = excluded.search_intent_score,
                    keyword_evidence_score = excluded.keyword_evidence_score,
                    recent_video_evidence_score = excluded.recent_video_evidence_score,
                    research_coverage_score = excluded.research_coverage_score,
                    product_relevance_score = excluded.product_relevance_score,
                    composite_priority_score = excluded.composite_priority_score,
                    estimated_production_effort = excluded.estimated_production_effort,
                    selection_rationale = excluded.selection_rationale,
                    supporting_sources_json = excluded.supporting_sources_json,
                    confidence_level = excluded.confidence_level,
                    missing_evidence = excluded.missing_evidence,
                    suggested_next_step = excluded.suggested_next_step,
                    user_status = excluded.user_status,
                    updated_at = excluded.updated_at;
                """,
                (
                    topic.topic_id,
                    topic.channel_id,
                    topic.proposed_title,
                    topic.target_keyword,
                    topic.search_intent,
                    topic.channel_relevance_score,
                    topic.search_intent_score,
                    topic.keyword_evidence_score,
                    topic.recent_video_evidence_score,
                    topic.research_coverage_score,
                    topic.product_relevance_score,
                    topic.composite_priority_score,
                    topic.estimated_production_effort.value if hasattr(topic.estimated_production_effort, 'value') else str(topic.estimated_production_effort),
                    topic.selection_rationale,
                    json.dumps(topic.supporting_sources),
                    research_date,
                    topic.confidence_level,
                    topic.missing_evidence,
                    topic.suggested_next_step,
                    topic.user_status.value if hasattr(topic.user_status, 'value') else str(topic.user_status),
                    now_iso,
                    now_iso,
                ),
            )
            return topic.topic_id

    def save_prioritized_topics(self, topics: List[PrioritizedTopic]) -> int:
        """Batch save multiple prioritized topics."""
        count = 0
        for t in topics:
            self.save_prioritized_topic(t)
            count += 1
        return count

    def get_prioritized_topics(self, channel_id: int, status: Optional[str] = None) -> List[PrioritizedTopic]:
        """Retrieve prioritized topics for a channel, optionally filtered by user status."""
        with self.get_connection() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT topic_id, channel_id, proposed_title, target_keyword, search_intent,
                           channel_relevance_score, search_intent_score, keyword_evidence_score,
                           recent_video_evidence_score, research_coverage_score, product_relevance_score,
                           composite_priority_score, estimated_production_effort, selection_rationale,
                           supporting_sources_json, research_date, confidence_level, missing_evidence,
                           suggested_next_step, user_status
                    FROM prioritized_topics WHERE channel_id = ? AND user_status = ?
                    ORDER BY composite_priority_score DESC;
                    """,
                    (channel_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT topic_id, channel_id, proposed_title, target_keyword, search_intent,
                           channel_relevance_score, search_intent_score, keyword_evidence_score,
                           recent_video_evidence_score, research_coverage_score, product_relevance_score,
                           composite_priority_score, estimated_production_effort, selection_rationale,
                           supporting_sources_json, research_date, confidence_level, missing_evidence,
                           suggested_next_step, user_status
                    FROM prioritized_topics WHERE channel_id = ?
                    ORDER BY composite_priority_score DESC;
                    """,
                    (channel_id,),
                ).fetchall()

            result = []
            for r in rows:
                try:
                    effort = ProductionEffort(r[12])
                except Exception:
                    effort = ProductionEffort.MEDIUM
                try:
                    ustatus = TopicUserStatus(r[19])
                except Exception:
                    ustatus = TopicUserStatus.SUGGESTED
                result.append(
                    PrioritizedTopic(
                        topic_id=r[0],
                        channel_id=r[1],
                        proposed_title=r[2],
                        target_keyword=r[3],
                        search_intent=r[4],
                        channel_relevance_score=r[5],
                        search_intent_score=r[6],
                        keyword_evidence_score=r[7],
                        recent_video_evidence_score=r[8],
                        research_coverage_score=r[9],
                        product_relevance_score=r[10],
                        composite_priority_score=r[11],
                        estimated_production_effort=effort,
                        selection_rationale=r[13],
                        supporting_sources=json.loads(r[14]) if r[14] else [],
                        research_date=r[15],
                        confidence_level=r[16],
                        missing_evidence=r[17],
                        suggested_next_step=r[18],
                        user_status=ustatus,
                    )
                )
            return result

    def get_prioritized_topic_by_id(self, topic_id: str) -> Optional[PrioritizedTopic]:
        """Retrieve a specific prioritized topic by ID."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT topic_id, channel_id, proposed_title, target_keyword, search_intent,
                       channel_relevance_score, search_intent_score, keyword_evidence_score,
                       recent_video_evidence_score, research_coverage_score, product_relevance_score,
                       composite_priority_score, estimated_production_effort, selection_rationale,
                       supporting_sources_json, research_date, confidence_level, missing_evidence,
                       suggested_next_step, user_status
                FROM prioritized_topics WHERE topic_id = ?;
                """,
                (topic_id,),
            ).fetchone()
            if not r:
                return None
            try:
                effort = ProductionEffort(r[12])
            except Exception:
                effort = ProductionEffort.MEDIUM
            try:
                ustatus = TopicUserStatus(r[19])
            except Exception:
                ustatus = TopicUserStatus.SUGGESTED
            return PrioritizedTopic(
                topic_id=r[0],
                channel_id=r[1],
                proposed_title=r[2],
                target_keyword=r[3],
                search_intent=r[4],
                channel_relevance_score=r[5],
                search_intent_score=r[6],
                keyword_evidence_score=r[7],
                recent_video_evidence_score=r[8],
                research_coverage_score=r[9],
                product_relevance_score=r[10],
                composite_priority_score=r[11],
                estimated_production_effort=effort,
                selection_rationale=r[13],
                supporting_sources=json.loads(r[14]) if r[14] else [],
                research_date=r[15],
                confidence_level=r[16],
                missing_evidence=r[17],
                suggested_next_step=r[18],
                user_status=ustatus,
            )

    def update_topic_user_status(self, topic_id: str, new_status: TopicUserStatus) -> bool:
        """Update a topic's user decision status (e.g. Approved, In Calendar, Rejected)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status_val = new_status.value if hasattr(new_status, "value") else str(new_status)
        with self.get_connection() as conn:
            cur = conn.execute(
                "UPDATE prioritized_topics SET user_status = ?, updated_at = ? WHERE topic_id = ?;",
                (status_val, now_iso, topic_id),
            )
            return cur.rowcount > 0

    def delete_prioritized_topic(self, topic_id: str) -> bool:
        """Delete a prioritized topic by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM prioritized_topics WHERE topic_id = ?;", (topic_id,))
            return cur.rowcount > 0

    def save_strategy_calendar_item(self, item: StrategyCalendarItem) -> int:
        """Save a new calendar item or update an existing one."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = item.created_at or now_iso
        updated_at = now_iso
        with self.get_connection() as conn:
            if item.id:
                conn.execute(
                    """
                    UPDATE strategy_calendar_items SET
                        channel_name = ?, topic = ?, target_keyword = ?, search_intent = ?,
                        suggested_format = ?, working_title = ?, production_status = ?,
                        planned_date = ?, evidence_summary = ?, required_research = ?,
                        affiliate_disclosure_required = ?, production_hours_estimate = ?,
                        notes = ?, updated_at = ?
                    WHERE id = ? AND channel_id = ?;
                    """,
                    (
                        item.channel_name,
                        item.topic,
                        item.target_keyword,
                        item.search_intent,
                        item.suggested_format,
                        item.working_title,
                        item.production_status,
                        item.planned_date,
                        item.evidence_summary,
                        item.required_research,
                        1 if item.affiliate_disclosure_required else 0,
                        item.production_hours_estimate,
                        item.notes,
                        updated_at,
                        item.id,
                        item.channel_id,
                    ),
                )
                return item.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO strategy_calendar_items (
                        channel_id, channel_name, topic, target_keyword, search_intent,
                        suggested_format, working_title, production_status, planned_date,
                        evidence_summary, required_research, affiliate_disclosure_required,
                        production_hours_estimate, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item.channel_id,
                        item.channel_name,
                        item.topic,
                        item.target_keyword,
                        item.search_intent,
                        item.suggested_format,
                        item.working_title,
                        item.production_status,
                        item.planned_date,
                        item.evidence_summary,
                        item.required_research,
                        1 if item.affiliate_disclosure_required else 0,
                        item.production_hours_estimate,
                        item.notes,
                        created_at,
                        updated_at,
                    ),
                )
                return cur.lastrowid

    def get_strategy_calendar_items(
        self, channel_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[StrategyCalendarItem]:
        """Retrieve calendar items for a channel, optionally filtered by date range."""
        with self.get_connection() as conn:
            query = """
                SELECT id, channel_id, channel_name, topic, target_keyword, search_intent,
                       suggested_format, working_title, production_status, planned_date,
                       evidence_summary, required_research, affiliate_disclosure_required,
                       production_hours_estimate, notes, created_at, updated_at
                FROM strategy_calendar_items WHERE channel_id = ?
            """
            params: List[Any] = [channel_id]
            if start_date:
                query += " AND planned_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND planned_date <= ?"
                params.append(end_date)
            query += " ORDER BY planned_date ASC;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                StrategyCalendarItem(
                    id=r[0],
                    channel_id=r[1],
                    channel_name=r[2],
                    topic=r[3],
                    target_keyword=r[4],
                    search_intent=r[5],
                    suggested_format=r[6],
                    working_title=r[7],
                    production_status=r[8],
                    planned_date=r[9],
                    evidence_summary=r[10],
                    required_research=r[11],
                    affiliate_disclosure_required=bool(r[12]),
                    production_hours_estimate=r[13],
                    notes=r[14],
                    created_at=r[15],
                    updated_at=r[16],
                )
                for r in rows
            ]

    def get_strategy_calendar_item_by_id(self, item_id: int) -> Optional[StrategyCalendarItem]:
        """Retrieve a specific calendar item by ID."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT id, channel_id, channel_name, topic, target_keyword, search_intent,
                       suggested_format, working_title, production_status, planned_date,
                       evidence_summary, required_research, affiliate_disclosure_required,
                       production_hours_estimate, notes, created_at, updated_at
                FROM strategy_calendar_items WHERE id = ?;
                """,
                (item_id,),
            ).fetchone()
            if not r:
                return None
            return StrategyCalendarItem(
                id=r[0],
                channel_id=r[1],
                channel_name=r[2],
                topic=r[3],
                target_keyword=r[4],
                search_intent=r[5],
                suggested_format=r[6],
                working_title=r[7],
                production_status=r[8],
                planned_date=r[9],
                evidence_summary=r[10],
                required_research=r[11],
                affiliate_disclosure_required=bool(r[12]),
                production_hours_estimate=r[13],
                notes=r[14],
                created_at=r[15],
                updated_at=r[16],
            )

    def update_strategy_calendar_item(self, item_id: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a calendar item."""
        if not updates:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso
        cols = []
        vals = []
        for k, v in updates.items():
            cols.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            elif isinstance(v, bool):
                vals.append(1 if v else 0)
            else:
                vals.append(v)
        vals.append(item_id)
        sql = f"UPDATE strategy_calendar_items SET {', '.join(cols)} WHERE id = ?;"
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(vals))
            return cur.rowcount > 0

    def delete_strategy_calendar_item(self, item_id: int) -> bool:
        """Delete a strategy calendar item by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM strategy_calendar_items WHERE id = ?;", (item_id,))
            return cur.rowcount > 0

    def save_content_brief_document(self, brief: ContentBriefDocument) -> int:
        """Save a new content brief document or update an existing one."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = brief.created_at or now_iso
        updated_at = now_iso
        with self.get_connection() as conn:
            if brief.id:
                conn.execute(
                    """
                    UPDATE content_brief_documents SET
                        topic = ?, target_viewer = ?, viewer_problem = ?, search_intent = ?,
                        primary_keyword = ?, supporting_keywords_json = ?, main_promise = ?,
                        title_options_json = ?, video_structure_json = ?, questions_to_answer_json = ?,
                        comparison_criteria_json = ?, unverified_facts_json = ?,
                        suggested_research_sources_json = ?, thumbnail_concept = ?,
                        description_draft = ?, affiliate_disclosure_reminder = ?,
                        seo_prepublish_checklist_json = ?, updated_at = ?
                    WHERE id = ? AND channel_id = ?;
                    """,
                    (
                        brief.topic,
                        brief.target_viewer,
                        brief.viewer_problem,
                        brief.search_intent,
                        brief.primary_keyword,
                        json.dumps(brief.supporting_keywords),
                        brief.main_promise,
                        json.dumps(brief.title_options),
                        json.dumps(brief.video_structure),
                        json.dumps(brief.questions_to_answer),
                        json.dumps(brief.comparison_criteria),
                        json.dumps(brief.unverified_facts),
                        json.dumps(brief.suggested_research_sources),
                        brief.thumbnail_concept,
                        brief.description_draft,
                        brief.affiliate_disclosure_reminder,
                        json.dumps(brief.seo_prepublish_checklist),
                        updated_at,
                        brief.id,
                        brief.channel_id,
                    ),
                )
                return brief.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO content_brief_documents (
                        channel_id, topic, target_viewer, viewer_problem, search_intent,
                        primary_keyword, supporting_keywords_json, main_promise,
                        title_options_json, video_structure_json, questions_to_answer_json,
                        comparison_criteria_json, unverified_facts_json,
                        suggested_research_sources_json, thumbnail_concept,
                        description_draft, affiliate_disclosure_reminder,
                        seo_prepublish_checklist_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        brief.channel_id,
                        brief.topic,
                        brief.target_viewer,
                        brief.viewer_problem,
                        brief.search_intent,
                        brief.primary_keyword,
                        json.dumps(brief.supporting_keywords),
                        brief.main_promise,
                        json.dumps(brief.title_options),
                        json.dumps(brief.video_structure),
                        json.dumps(brief.questions_to_answer),
                        json.dumps(brief.comparison_criteria),
                        json.dumps(brief.unverified_facts),
                        json.dumps(brief.suggested_research_sources),
                        brief.thumbnail_concept,
                        brief.description_draft,
                        brief.affiliate_disclosure_reminder,
                        json.dumps(brief.seo_prepublish_checklist),
                        created_at,
                        updated_at,
                    ),
                )
                return cur.lastrowid

    def get_content_brief_documents(self, channel_id: int) -> List[ContentBriefDocument]:
        """Retrieve all content brief documents for a channel."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, topic, target_viewer, viewer_problem, search_intent,
                       primary_keyword, supporting_keywords_json, main_promise,
                       title_options_json, video_structure_json, questions_to_answer_json,
                       comparison_criteria_json, unverified_facts_json,
                       suggested_research_sources_json, thumbnail_concept,
                       description_draft, affiliate_disclosure_reminder,
                       seo_prepublish_checklist_json, created_at, updated_at
                FROM content_brief_documents WHERE channel_id = ? ORDER BY id DESC;
                """,
                (channel_id,),
            ).fetchall()
            return [
                ContentBriefDocument(
                    id=r[0],
                    channel_id=r[1],
                    topic=r[2],
                    target_viewer=r[3],
                    viewer_problem=r[4],
                    search_intent=r[5],
                    primary_keyword=r[6],
                    supporting_keywords=json.loads(r[7]) if r[7] else [],
                    main_promise=r[8],
                    title_options=json.loads(r[9]) if r[9] else [],
                    video_structure=json.loads(r[10]) if r[10] else [],
                    questions_to_answer=json.loads(r[11]) if r[11] else [],
                    comparison_criteria=json.loads(r[12]) if r[12] else [],
                    unverified_facts=json.loads(r[13]) if r[13] else [],
                    suggested_research_sources=json.loads(r[14]) if r[14] else [],
                    thumbnail_concept=r[15],
                    description_draft=r[16],
                    affiliate_disclosure_reminder=r[17],
                    seo_prepublish_checklist=json.loads(r[18]) if r[18] else [],
                    created_at=r[19],
                    updated_at=r[20],
                )
                for r in rows
            ]

    def get_content_brief_document_by_id(self, brief_id: int) -> Optional[ContentBriefDocument]:
        """Retrieve a content brief document by ID."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT id, channel_id, topic, target_viewer, viewer_problem, search_intent,
                       primary_keyword, supporting_keywords_json, main_promise,
                       title_options_json, video_structure_json, questions_to_answer_json,
                       comparison_criteria_json, unverified_facts_json,
                       suggested_research_sources_json, thumbnail_concept,
                       description_draft, affiliate_disclosure_reminder,
                       seo_prepublish_checklist_json, created_at, updated_at
                FROM content_brief_documents WHERE id = ?;
                """,
                (brief_id,),
            ).fetchone()
            if not r:
                return None
            return ContentBriefDocument(
                id=r[0],
                channel_id=r[1],
                topic=r[2],
                target_viewer=r[3],
                viewer_problem=r[4],
                search_intent=r[5],
                primary_keyword=r[6],
                supporting_keywords=json.loads(r[7]) if r[7] else [],
                main_promise=r[8],
                title_options=json.loads(r[9]) if r[9] else [],
                video_structure=json.loads(r[10]) if r[10] else [],
                questions_to_answer=json.loads(r[11]) if r[11] else [],
                comparison_criteria=json.loads(r[12]) if r[12] else [],
                unverified_facts=json.loads(r[13]) if r[13] else [],
                suggested_research_sources=json.loads(r[14]) if r[14] else [],
                thumbnail_concept=r[15],
                description_draft=r[16],
                affiliate_disclosure_reminder=r[17],
                seo_prepublish_checklist=json.loads(r[18]) if r[18] else [],
                created_at=r[19],
                updated_at=r[20],
            )

    def delete_content_brief_document(self, brief_id: int) -> bool:
        """Delete a content brief document by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM content_brief_documents WHERE id = ?;", (brief_id,))
            return cur.rowcount > 0

    def save_production_workflow_project(self, project: ProductionWorkflowProject) -> int:
        """Save a new workflow project or update an existing one."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = project.created_at or now_iso
        updated_at = now_iso
        stage_str = project.current_stage.value if hasattr(project.current_stage, "value") else str(project.current_stage)
        with self.get_connection() as conn:
            if project.id:
                conn.execute(
                    """
                    UPDATE production_workflow_projects SET
                        project_name = ?, primary_keyword = ?, current_stage = ?,
                        stage_history_json = ?, blockers_json = ?, checklist_completed_json = ?,
                        brief_id = ?, calendar_item_id = ?, is_cancelled = ?, updated_at = ?
                    WHERE id = ? AND channel_id = ?;
                    """,
                    (
                        project.project_name,
                        project.primary_keyword,
                        stage_str,
                        json.dumps(project.stage_history),
                        json.dumps(project.blockers),
                        json.dumps(project.checklist_completed),
                        project.brief_id,
                        project.calendar_item_id,
                        1 if project.is_cancelled else 0,
                        updated_at,
                        project.id,
                        project.channel_id,
                    ),
                )
                return project.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO production_workflow_projects (
                        channel_id, project_name, primary_keyword, current_stage,
                        stage_history_json, blockers_json, checklist_completed_json,
                        brief_id, calendar_item_id, is_cancelled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        project.channel_id,
                        project.project_name,
                        project.primary_keyword,
                        stage_str,
                        json.dumps(project.stage_history),
                        json.dumps(project.blockers),
                        json.dumps(project.checklist_completed),
                        project.brief_id,
                        project.calendar_item_id,
                        1 if project.is_cancelled else 0,
                        created_at,
                        updated_at,
                    ),
                )
                return cur.lastrowid

    def get_production_workflow_projects(
        self, channel_id: int, stage: Optional[WorkflowStage] = None
    ) -> List[ProductionWorkflowProject]:
        """Retrieve workflow projects for a channel, optionally filtered by stage."""
        with self.get_connection() as conn:
            if stage:
                stage_val = stage.value if hasattr(stage, "value") else str(stage)
                rows = conn.execute(
                    """
                    SELECT id, channel_id, project_name, primary_keyword, current_stage,
                           stage_history_json, blockers_json, checklist_completed_json,
                           brief_id, calendar_item_id, is_cancelled, created_at, updated_at
                    FROM production_workflow_projects WHERE channel_id = ? AND current_stage = ?
                    ORDER BY id DESC;
                    """,
                    (channel_id, stage_val),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, channel_id, project_name, primary_keyword, current_stage,
                           stage_history_json, blockers_json, checklist_completed_json,
                           brief_id, calendar_item_id, is_cancelled, created_at, updated_at
                    FROM production_workflow_projects WHERE channel_id = ?
                    ORDER BY id DESC;
                    """,
                    (channel_id,),
                ).fetchall()

            result = []
            for r in rows:
                try:
                    cstage = WorkflowStage(r[4])
                except Exception:
                    cstage = WorkflowStage.IDEA
                result.append(
                    ProductionWorkflowProject(
                        id=r[0],
                        channel_id=r[1],
                        project_name=r[2],
                        primary_keyword=r[3],
                        current_stage=cstage,
                        stage_history=json.loads(r[5]) if r[5] else [],
                        blockers=json.loads(r[6]) if r[6] else [],
                        checklist_completed=json.loads(r[7]) if r[7] else {},
                        brief_id=r[8],
                        calendar_item_id=r[9],
                        is_cancelled=bool(r[10]),
                        created_at=r[11],
                        updated_at=r[12],
                    )
                )
            return result

    def get_production_workflow_project_by_id(self, project_id: int) -> Optional[ProductionWorkflowProject]:
        """Retrieve a specific workflow project by ID."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT id, channel_id, project_name, primary_keyword, current_stage,
                       stage_history_json, blockers_json, checklist_completed_json,
                       brief_id, calendar_item_id, is_cancelled, created_at, updated_at
                FROM production_workflow_projects WHERE id = ?;
                """,
                (project_id,),
            ).fetchone()
            if not r:
                return None
            try:
                cstage = WorkflowStage(r[4])
            except Exception:
                cstage = WorkflowStage.IDEA
            return ProductionWorkflowProject(
                id=r[0],
                channel_id=r[1],
                project_name=r[2],
                primary_keyword=r[3],
                current_stage=cstage,
                stage_history=json.loads(r[5]) if r[5] else [],
                blockers=json.loads(r[6]) if r[6] else [],
                checklist_completed=json.loads(r[7]) if r[7] else {},
                brief_id=r[8],
                calendar_item_id=r[9],
                is_cancelled=bool(r[10]),
                created_at=r[11],
                updated_at=r[12],
            )

    def update_production_workflow_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a production workflow project."""
        if not updates:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso
        cols = []
        vals = []
        for k, v in updates.items():
            cols.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            elif isinstance(v, bool):
                vals.append(1 if v else 0)
            elif isinstance(v, WorkflowStage):
                vals.append(v.value)
            else:
                vals.append(v)
        vals.append(project_id)
        sql = f"UPDATE production_workflow_projects SET {', '.join(cols)} WHERE id = ?;"
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(vals))
            return cur.rowcount > 0

    def delete_production_workflow_project(self, project_id: int) -> bool:
        """Delete a workflow project by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM production_workflow_projects WHERE id = ?;", (project_id,))
            return cur.rowcount > 0

    # --------------------------------------------------------------------------
    # Phase 26: Topic Validation Engine & Growth Intelligence Facilities
    # --------------------------------------------------------------------------

    def save_topic_validation_report(self, report: TopicValidationReport) -> int:
        """Save or update a topic validation report."""
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at = report.created_at or now_iso
        updated_at = now_iso
        with self.get_connection() as conn:
            if report.id:
                conn.execute(
                    """
                    UPDATE topic_validation_reports SET
                        topic = ?, primary_keyword = ?, secondary_keywords_json = ?,
                        search_intent = ?, target_viewer = ?, niche_match_score = ?,
                        intent_clarity_score = ?, keyword_evidence_score = ?,
                        recent_video_evidence_score = ?, own_channel_overlap_score = ?,
                        product_relevance_score = ?, composite_opportunity_score = ?,
                        confidence_tier = ?, readiness_status = ?, what_supports_idea_json = ?,
                        what_weakens_idea_json = ?, what_remains_unknown_json = ?,
                        further_research_needed_json = ?, gap_state = ?,
                        queries_executed_json = ?, recent_videos_count = ?,
                        competitor_videos_json = ?, suggested_angles_json = ?,
                        product_validation_json = ?, is_approved = ?, is_rejected = ?,
                        is_saved = ?, is_added_to_calendar = ?, updated_at = ?
                    WHERE id = ? AND channel_id = ?;
                    """,
                    (
                        report.topic,
                        report.primary_keyword,
                        json.dumps(report.secondary_keywords),
                        report.search_intent,
                        report.target_viewer,
                        report.niche_match_score,
                        report.intent_clarity_score,
                        report.keyword_evidence_score,
                        report.recent_video_evidence_score,
                        report.own_channel_overlap_score,
                        report.product_relevance_score,
                        report.composite_opportunity_score,
                        report.confidence_tier,
                        report.readiness_status,
                        json.dumps(report.what_supports_idea),
                        json.dumps(report.what_weakens_idea),
                        json.dumps(report.what_remains_unknown),
                        json.dumps(report.further_research_needed),
                        report.gap_state,
                        json.dumps(report.queries_executed),
                        report.recent_videos_count,
                        json.dumps(report.competitor_videos),
                        json.dumps(report.suggested_angles),
                        json.dumps(report.product_validation) if report.product_validation else None,
                        1 if report.is_approved else 0,
                        1 if report.is_rejected else 0,
                        1 if report.is_saved else 0,
                        1 if report.is_added_to_calendar else 0,
                        updated_at,
                        report.id,
                        report.channel_id,
                    ),
                )
                return report.id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO topic_validation_reports (
                        channel_id, topic, primary_keyword, secondary_keywords_json,
                        search_intent, target_viewer, niche_match_score,
                        intent_clarity_score, keyword_evidence_score,
                        recent_video_evidence_score, own_channel_overlap_score,
                        product_relevance_score, composite_opportunity_score,
                        confidence_tier, readiness_status, what_supports_idea_json,
                        what_weakens_idea_json, what_remains_unknown_json,
                        further_research_needed_json, gap_state,
                        queries_executed_json, recent_videos_count,
                        competitor_videos_json, suggested_angles_json,
                        product_validation_json, is_approved, is_rejected,
                        is_saved, is_added_to_calendar, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        report.channel_id,
                        report.topic,
                        report.primary_keyword,
                        json.dumps(report.secondary_keywords),
                        report.search_intent,
                        report.target_viewer,
                        report.niche_match_score,
                        report.intent_clarity_score,
                        report.keyword_evidence_score,
                        report.recent_video_evidence_score,
                        report.own_channel_overlap_score,
                        report.product_relevance_score,
                        report.composite_opportunity_score,
                        report.confidence_tier,
                        report.readiness_status,
                        json.dumps(report.what_supports_idea),
                        json.dumps(report.what_weakens_idea),
                        json.dumps(report.what_remains_unknown),
                        json.dumps(report.further_research_needed),
                        report.gap_state,
                        json.dumps(report.queries_executed),
                        report.recent_videos_count,
                        json.dumps(report.competitor_videos),
                        json.dumps(report.suggested_angles),
                        json.dumps(report.product_validation) if report.product_validation else None,
                        1 if report.is_approved else 0,
                        1 if report.is_rejected else 0,
                        1 if report.is_saved else 0,
                        1 if report.is_added_to_calendar else 0,
                        created_at,
                        updated_at,
                    ),
                )
                return cur.lastrowid

    def get_topic_validation_reports(
        self,
        channel_id: int,
        status: Optional[str] = None,
        is_approved: Optional[bool] = None,
        is_saved: Optional[bool] = None,
    ) -> List[TopicValidationReport]:
        """Retrieve topic validation reports for a channel, optionally filtered."""
        with self.get_connection() as conn:
            query = """
                SELECT id, channel_id, topic, primary_keyword, secondary_keywords_json,
                       search_intent, target_viewer, niche_match_score,
                       intent_clarity_score, keyword_evidence_score,
                       recent_video_evidence_score, own_channel_overlap_score,
                       product_relevance_score, composite_opportunity_score,
                       confidence_tier, readiness_status, what_supports_idea_json,
                       what_weakens_idea_json, what_remains_unknown_json,
                       further_research_needed_json, gap_state,
                       queries_executed_json, recent_videos_count,
                       competitor_videos_json, suggested_angles_json,
                       product_validation_json, is_approved, is_rejected,
                       is_saved, is_added_to_calendar, created_at, updated_at
                FROM topic_validation_reports WHERE channel_id = ?
            """
            params: List[Any] = [channel_id]
            if status is not None:
                query += " AND readiness_status = ?"
                params.append(status)
            if is_approved is not None:
                query += " AND is_approved = ?"
                params.append(1 if is_approved else 0)
            if is_saved is not None:
                query += " AND is_saved = ?"
                params.append(1 if is_saved else 0)
            query += " ORDER BY composite_opportunity_score DESC, id DESC;"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                TopicValidationReport(
                    id=r[0],
                    channel_id=r[1],
                    topic=r[2],
                    primary_keyword=r[3],
                    secondary_keywords=json.loads(r[4]) if r[4] else [],
                    search_intent=r[5],
                    target_viewer=r[6],
                    niche_match_score=r[7],
                    intent_clarity_score=r[8],
                    keyword_evidence_score=r[9],
                    recent_video_evidence_score=r[10],
                    own_channel_overlap_score=r[11],
                    product_relevance_score=r[12],
                    composite_opportunity_score=r[13],
                    confidence_tier=r[14],
                    readiness_status=r[15],
                    what_supports_idea=json.loads(r[16]) if r[16] else [],
                    what_weakens_idea=json.loads(r[17]) if r[17] else [],
                    what_remains_unknown=json.loads(r[18]) if r[18] else [],
                    further_research_needed=json.loads(r[19]) if r[19] else [],
                    gap_state=r[20],
                    queries_executed=json.loads(r[21]) if r[21] else [],
                    recent_videos_count=r[22],
                    competitor_videos=json.loads(r[23]) if r[23] else [],
                    suggested_angles=json.loads(r[24]) if r[24] else [],
                    product_validation=json.loads(r[25]) if r[25] else None,
                    is_approved=bool(r[26]),
                    is_rejected=bool(r[27]),
                    is_saved=bool(r[28]),
                    is_added_to_calendar=bool(r[29]),
                    created_at=r[30],
                    updated_at=r[31],
                )
                for r in rows
            ]

    def get_topic_validation_report_by_id(self, report_id: int) -> Optional[TopicValidationReport]:
        """Retrieve a specific topic validation report by ID."""
        with self.get_connection() as conn:
            r = conn.execute(
                """
                SELECT id, channel_id, topic, primary_keyword, secondary_keywords_json,
                       search_intent, target_viewer, niche_match_score,
                       intent_clarity_score, keyword_evidence_score,
                       recent_video_evidence_score, own_channel_overlap_score,
                       product_relevance_score, composite_opportunity_score,
                       confidence_tier, readiness_status, what_supports_idea_json,
                       what_weakens_idea_json, what_remains_unknown_json,
                       further_research_needed_json, gap_state,
                       queries_executed_json, recent_videos_count,
                       competitor_videos_json, suggested_angles_json,
                       product_validation_json, is_approved, is_rejected,
                       is_saved, is_added_to_calendar, created_at, updated_at
                FROM topic_validation_reports WHERE id = ?;
                """,
                (report_id,),
            ).fetchone()
            if not r:
                return None
            return TopicValidationReport(
                id=r[0],
                channel_id=r[1],
                topic=r[2],
                primary_keyword=r[3],
                secondary_keywords=json.loads(r[4]) if r[4] else [],
                search_intent=r[5],
                target_viewer=r[6],
                niche_match_score=r[7],
                intent_clarity_score=r[8],
                keyword_evidence_score=r[9],
                recent_video_evidence_score=r[10],
                own_channel_overlap_score=r[11],
                product_relevance_score=r[12],
                composite_opportunity_score=r[13],
                confidence_tier=r[14],
                readiness_status=r[15],
                what_supports_idea=json.loads(r[16]) if r[16] else [],
                what_weakens_idea=json.loads(r[17]) if r[17] else [],
                what_remains_unknown=json.loads(r[18]) if r[18] else [],
                further_research_needed=json.loads(r[19]) if r[19] else [],
                gap_state=r[20],
                queries_executed=json.loads(r[21]) if r[21] else [],
                recent_videos_count=r[22],
                competitor_videos=json.loads(r[23]) if r[23] else [],
                suggested_angles=json.loads(r[24]) if r[24] else [],
                product_validation=json.loads(r[25]) if r[25] else None,
                is_approved=bool(r[26]),
                is_rejected=bool(r[27]),
                is_saved=bool(r[28]),
                is_added_to_calendar=bool(r[29]),
                created_at=r[30],
                updated_at=r[31],
            )

    def update_topic_validation_report(self, report_id: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields of a topic validation report."""
        if not updates:
            return False
        now_iso = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now_iso
        cols = []
        vals = []
        for k, v in updates.items():
            cols.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            elif isinstance(v, bool):
                vals.append(1 if v else 0)
            else:
                vals.append(v)
        vals.append(report_id)
        sql = f"UPDATE topic_validation_reports SET {', '.join(cols)} WHERE id = ?;"
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(vals))
            return cur.rowcount > 0

    def delete_topic_validation_report(self, report_id: int) -> bool:
        """Delete a topic validation report by ID."""
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM topic_validation_reports WHERE id = ?;", (report_id,))
            return cur.rowcount > 0

    def save_competitor_video_record(self, record: CompetitorVideoRecord) -> str:
        """Save or replace a competitor video record."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO competitor_video_records (
                    video_id, title, channel_title, published_at, view_count,
                    duration, video_url, matching_query, relevance_reason,
                    relative_age_days, views_per_day, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    channel_title = excluded.channel_title,
                    published_at = excluded.published_at,
                    view_count = excluded.view_count,
                    duration = excluded.duration,
                    video_url = excluded.video_url,
                    matching_query = excluded.matching_query,
                    relevance_reason = excluded.relevance_reason,
                    relative_age_days = excluded.relative_age_days,
                    views_per_day = excluded.views_per_day;
                """,
                (
                    record.video_id,
                    record.title,
                    record.channel_title,
                    record.published_at,
                    record.view_count,
                    record.duration,
                    record.video_url,
                    record.matching_query,
                    record.relevance_reason,
                    record.relative_age_days,
                    record.views_per_day,
                    record.created_at or datetime.now(timezone.utc).isoformat(),
                ),
            )
            return record.video_id

    def get_competitor_videos_by_query(self, query: str, limit: int = 20) -> List[CompetitorVideoRecord]:
        """Retrieve competitor videos matching a query string."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT video_id, title, channel_title, published_at, view_count,
                       duration, video_url, matching_query, relevance_reason,
                       relative_age_days, views_per_day, created_at
                FROM competitor_video_records WHERE matching_query LIKE ?
                ORDER BY view_count DESC LIMIT ?;
                """,
                (f"%{query}%", limit),
            ).fetchall()
            return [
                CompetitorVideoRecord(
                    video_id=r[0],
                    title=r[1],
                    channel_title=r[2],
                    published_at=r[3],
                    view_count=r[4],
                    duration=r[5],
                    video_url=r[6],
                    matching_query=r[7],
                    relevance_reason=r[8],
                    relative_age_days=r[9],
                    views_per_day=r[10],
                    created_at=r[11],
                )
                for r in rows
            ]


    # --------------------------------------------------------------------------
    # Phase 31: Personal YouTube SEO Coach & Action Center
    # --------------------------------------------------------------------------

    def save_action_task(self, task: Dict[str, Any]) -> int:
        """Save or update an action task in SQLite. Does not overwrite dismissed/completed status unless specified."""
        self._ensure_phase31_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT id, status FROM action_center_tasks WHERE task_key = ?;",
                (task["task_key"],),
            ).fetchone()

            how_json = json.dumps(task.get("how_to_do_it", [])) if isinstance(task.get("how_to_do_it"), list) else task.get("how_to_do_it_json", "[]")
            check_json = json.dumps(task.get("what_to_check", [])) if isinstance(task.get("what_to_check"), list) else task.get("what_to_check_json", "[]")
            ctx_json = json.dumps(task.get("context_data", {})) if isinstance(task.get("context_data"), dict) else task.get("context_json", "{}")

            if existing:
                task_id, current_status = existing
                # If already completed or dismissed, preserve unless explicit change requested
                new_status = task.get("status", current_status)
                if current_status in ("completed", "dismissed") and task.get("status") == "pending":
                    new_status = current_status

                conn.execute(
                    """
                    UPDATE action_center_tasks
                    SET channel_name = ?, task_type = ?, title = ?, short_summary = ?,
                        priority = ?, target_page = ?, context_json = ?, what_to_do = ?,
                        why_it_matters = ?, how_to_do_it_json = ?, what_to_check_json = ?,
                        what_comes_next = ?, status = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        task.get("channel_name", ""),
                        task.get("task_type", ""),
                        task.get("title", ""),
                        task.get("short_summary", ""),
                        task.get("priority", "normal"),
                        task.get("target_page", ""),
                        ctx_json,
                        task.get("what_to_do", ""),
                        task.get("why_it_matters", ""),
                        how_json,
                        check_json,
                        task.get("what_comes_next", ""),
                        new_status,
                        now,
                        task_id,
                    ),
                )
                return task_id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO action_center_tasks (
                        task_key, channel_id, channel_name, task_type, title,
                        short_summary, priority, target_page, context_json,
                        what_to_do, why_it_matters, how_to_do_it_json,
                        what_to_check_json, what_comes_next, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        task["task_key"],
                        int(task["channel_id"]),
                        task.get("channel_name", ""),
                        task.get("task_type", ""),
                        task.get("title", ""),
                        task.get("short_summary", ""),
                        task.get("priority", "normal"),
                        task.get("target_page", ""),
                        ctx_json,
                        task.get("what_to_do", ""),
                        task.get("why_it_matters", ""),
                        how_json,
                        check_json,
                        task.get("what_comes_next", ""),
                        task.get("status", "pending"),
                        task.get("created_at", now),
                        now,
                    ),
                )
                return cur.lastrowid

    def get_action_tasks(
        self,
        channel_id: Optional[int] = None,
        status: Optional[str] = "pending",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve action tasks filtered by channel and status."""
        self._ensure_phase31_tables()
        with self.get_connection() as conn:
            query = "SELECT * FROM action_center_tasks WHERE 1=1"
            params: List[Any] = []
            if channel_id is not None:
                query += " AND channel_id = ?"
                params.append(channel_id)
            if status is not None:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            cols = [col[0] for col in conn.execute("SELECT * FROM action_center_tasks LIMIT 0;").description]
            result = []
            for r in rows:
                row_dict = dict(zip(cols, r))
                row_dict["how_to_do_it"] = json.loads(row_dict.get("how_to_do_it_json") or "[]")
                row_dict["what_to_check"] = json.loads(row_dict.get("what_to_check_json") or "[]")
                row_dict["context_data"] = json.loads(row_dict.get("context_json") or "{}")
                result.append(row_dict)
            return result

    def update_action_task_status(self, task_key: str, status: str) -> bool:
        """Update the status of an action task (e.g. 'completed', 'dismissed', 'pending')."""
        self._ensure_phase31_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                "UPDATE action_center_tasks SET status = ?, updated_at = ? WHERE task_key = ?;",
                (status, now, task_key),
            )
            return cur.rowcount > 0

    def get_channel_progress_counts(self, channel_id: int) -> Dict[str, int]:
        """Compute real, verified project counts for a channel from SQLite records."""
        self._ensure_phase31_tables()
        with self.get_connection() as conn:
            # 1. Total saved research sessions
            searches_count = conn.execute("SELECT COUNT(*) FROM searches;").fetchone()[0]

            # 2. Topics awaiting review for this channel
            ideas_count = conn.execute(
                "SELECT COUNT(*) FROM daily_idea_items WHERE channel_id = ? AND is_saved = 0 AND is_rejected = 0;",
                (channel_id,),
            ).fetchone()[0]
            topics_count = conn.execute(
                "SELECT COUNT(*) FROM prioritized_topics WHERE channel_id = ? AND user_status = 'Suggested';",
                (channel_id,),
            ).fetchone()[0]
            topics_awaiting = ideas_count + topics_count

            # 3. Content briefs completed
            briefs_count = conn.execute(
                "SELECT COUNT(*) FROM content_brief_documents WHERE channel_id = ?;",
                (channel_id,),
            ).fetchone()[0]

            # 4. Videos in production
            proj_count = conn.execute(
                "SELECT COUNT(*) FROM production_workflow_projects WHERE channel_id = ? AND is_cancelled = 0 AND current_stage != 'Published';",
                (channel_id,),
            ).fetchone()[0]
            cal_count = conn.execute(
                "SELECT COUNT(*) FROM strategy_calendar_items WHERE channel_id = ? AND production_status IN ('Planned', 'In Production', 'Ready for Recording');",
                (channel_id,),
            ).fetchone()[0]
            in_production = max(proj_count, cal_count)

            # 5. SEO audits requiring attention (score < 80)
            audits_cur = conn.execute(
                "SELECT scores_json FROM video_seo_audits WHERE channel_id = ?;",
                (channel_id,),
            ).fetchall()
            audits_needing_attention = 0
            for a in audits_cur:
                try:
                    s = json.loads(a[0] or "{}")
                    if s.get("overall_score", 100) < 80:
                        audits_needing_attention += 1
                except Exception:
                    pass

            return {
                "saved_searches": searches_count,
                "topics_awaiting_review": topics_awaiting,
                "briefs_completed": briefs_count,
                "videos_in_production": in_production,
                "audits_requiring_attention": audits_needing_attention,
            }

    # --------------------------------------------------------------------------
    # Phase 32: YouTube SEO Content Factory & One-Click Video Package
    # --------------------------------------------------------------------------

    def save_video_content_package(self, pkg: Dict[str, Any]) -> int:
        """Save a new video content package or update an existing one."""
        self._ensure_phase32_tables()
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            pkg_id = pkg.get("id")
            supp_json = json.dumps(pkg.get("supporting_keywords", [])) if isinstance(pkg.get("supporting_keywords"), list) else pkg.get("supporting_keywords_json", "[]")
            titles_json = json.dumps(pkg.get("title_options", [])) if isinstance(pkg.get("title_options"), list) else pkg.get("title_options_json", "[]")
            outline_json = json.dumps(pkg.get("outline", {})) if isinstance(pkg.get("outline"), dict) else pkg.get("outline_json", "{}")
            thumb_json = json.dumps(pkg.get("thumbnail_concept", {})) if isinstance(pkg.get("thumbnail_concept"), dict) else pkg.get("thumbnail_concept_json", "{}")
            tags_json = json.dumps(pkg.get("tags", [])) if isinstance(pkg.get("tags"), list) else pkg.get("tags_json", "[]")
            evidence_json = json.dumps(pkg.get("evidence_checklist", {})) if isinstance(pkg.get("evidence_checklist"), dict) else pkg.get("evidence_checklist_json", "{}")
            readiness_json = json.dumps(pkg.get("seo_readiness", {})) if isinstance(pkg.get("seo_readiness"), dict) else pkg.get("seo_readiness_json", "{}")

            if pkg_id:
                conn.execute(
                    """
                    UPDATE video_content_packages SET
                        channel_id = ?, channel_name = ?, topic = ?, primary_keyword = ?,
                        supporting_keywords_json = ?, format_type = ?, purpose_type = ?,
                        target_viewer = ?, selected_title = ?, title_options_json = ?,
                        outline_json = ?, description_text = ?, thumbnail_concept_json = ?,
                        tags_json = ?, evidence_checklist_json = ?, seo_readiness_json = ?,
                        is_saved = ?, is_exported = ?, calendar_item_id = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        int(pkg["channel_id"]),
                        pkg.get("channel_name", ""),
                        pkg.get("topic", ""),
                        pkg.get("primary_keyword", ""),
                        supp_json,
                        pkg.get("format_type", "long-form"),
                        pkg.get("purpose_type", "tutorial"),
                        pkg.get("target_viewer", ""),
                        pkg.get("selected_title", ""),
                        titles_json,
                        outline_json,
                        pkg.get("description_text", ""),
                        thumb_json,
                        tags_json,
                        evidence_json,
                        readiness_json,
                        1 if pkg.get("is_saved", True) else 0,
                        1 if pkg.get("is_exported", False) else 0,
                        pkg.get("calendar_item_id"),
                        now,
                        pkg_id,
                    ),
                )
                return pkg_id
            else:
                cur = conn.execute(
                    """
                    INSERT INTO video_content_packages (
                        channel_id, channel_name, topic, primary_keyword,
                        supporting_keywords_json, format_type, purpose_type,
                        target_viewer, selected_title, title_options_json,
                        outline_json, description_text, thumbnail_concept_json,
                        tags_json, evidence_checklist_json, seo_readiness_json,
                        is_saved, is_exported, calendar_item_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        int(pkg["channel_id"]),
                        pkg.get("channel_name", ""),
                        pkg.get("topic", ""),
                        pkg.get("primary_keyword", ""),
                        supp_json,
                        pkg.get("format_type", "long-form"),
                        pkg.get("purpose_type", "tutorial"),
                        pkg.get("target_viewer", ""),
                        pkg.get("selected_title", ""),
                        titles_json,
                        outline_json,
                        pkg.get("description_text", ""),
                        thumb_json,
                        tags_json,
                        evidence_json,
                        readiness_json,
                        1 if pkg.get("is_saved", True) else 0,
                        1 if pkg.get("is_exported", False) else 0,
                        pkg.get("calendar_item_id"),
                        pkg.get("created_at", now),
                        now,
                    ),
                )
                return cur.lastrowid

    def get_video_content_packages(
        self, channel_id: Optional[int] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve recent video content packages."""
        self._ensure_phase32_tables()
        with self.get_connection() as conn:
            query = "SELECT * FROM video_content_packages WHERE 1=1"
            params: List[Any] = []
            if channel_id is not None:
                query += " AND channel_id = ?"
                params.append(channel_id)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            cols = [col[0] for col in conn.execute("SELECT * FROM video_content_packages LIMIT 0;").description]
            result = []
            for r in rows:
                d = dict(zip(cols, r))
                d["supporting_keywords"] = json.loads(d.get("supporting_keywords_json") or "[]")
                d["title_options"] = json.loads(d.get("title_options_json") or "[]")
                d["outline"] = json.loads(d.get("outline_json") or "{}")
                d["thumbnail_concept"] = json.loads(d.get("thumbnail_concept_json") or "{}")
                d["tags"] = json.loads(d.get("tags_json") or "[]")
                d["evidence_checklist"] = json.loads(d.get("evidence_checklist_json") or "{}")
                d["seo_readiness"] = json.loads(d.get("seo_readiness_json") or "{}")
                result.append(d)
            return result

    def get_video_content_package_by_id(self, pkg_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific content package by ID."""
        self._ensure_phase32_tables()
        with self.get_connection() as conn:
            r = conn.execute("SELECT * FROM video_content_packages WHERE id = ?;", (pkg_id,)).fetchone()
            if not r:
                return None
            cols = [col[0] for col in conn.execute("SELECT * FROM video_content_packages LIMIT 0;").description]
            d = dict(zip(cols, r))
            d["supporting_keywords"] = json.loads(d.get("supporting_keywords_json") or "[]")
            d["title_options"] = json.loads(d.get("title_options_json") or "[]")
            d["outline"] = json.loads(d.get("outline_json") or "{}")
            d["thumbnail_concept"] = json.loads(d.get("thumbnail_concept_json") or "{}")
            d["tags"] = json.loads(d.get("tags_json") or "[]")
            d["evidence_checklist"] = json.loads(d.get("evidence_checklist_json") or "{}")
            d["seo_readiness"] = json.loads(d.get("seo_readiness_json") or "{}")
            return d

    def delete_video_content_package(self, pkg_id: int) -> bool:
        """Delete a video content package."""
        self._ensure_phase32_tables()
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM video_content_packages WHERE id = ?;", (pkg_id,))
            return cur.rowcount > 0

    # --------------------------------------------------------------------------
    # Database Diagnostics & Backup Facilities
    # --------------------------------------------------------------------------

    def get_database_stats(self) -> Dict[str, Any]:
        """Retrieve aggregated database metrics, schema version, and storage statistics."""
        with self.get_connection() as conn:
            searches_count = conn.execute("SELECT COUNT(*) FROM searches;").fetchone()[0]
            keywords_count = conn.execute("SELECT COUNT(*) FROM keywords;").fetchone()[0]
            cache_count = conn.execute("SELECT COUNT(*) FROM autocomplete_cache;").fetchone()[0]
            schema_ver = self.migration_manager.get_current_schema_version()

        file_size_bytes = 0
        if self.db_path.exists():
            file_size_bytes = self.db_path.stat().st_size

        return {
            "total_searches": searches_count,
            "total_keywords": keywords_count,
            "total_cached_queries": cache_count,
            "schema_version": schema_ver,
            "file_size_bytes": file_size_bytes,
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "wal_mode": True,
        }

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a consistent online SQLite backup of the database."""
        return self.backup_manager.create_backup(self.db_path, backup_name=backup_name)

    def validate_backup(self, backup_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate an SQLite backup for corruption and integrity."""
        return self.backup_manager.validate_backup(backup_path)

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups with metadata."""
        return self.backup_manager.list_backups()

    def restore_backup(self, backup_path: Path) -> Tuple[bool, str]:
        """Safely restore a backup after creating a pre-restore safety snapshot."""
        return self.backup_manager.restore_backup(backup_path, self.db_path)


# Default singleton instance
db_manager = DatabaseManager()
