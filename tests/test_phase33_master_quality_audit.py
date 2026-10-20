"""
Phase 33 Master Quality Audit & Release Gate Verification Test Suite.

Validates:
1. Master Application Architecture & 14 Navigation Pages Contract.
2. Four-Channel Profile Isolation & UTF-8 Bangla Unicode Support.
3. Epistemic Modesty & Honest Fallbacks (No Fake Search Volumes or CPC).
4. Complete 16-Step User Journey from Autocomplete to One-Click Video Packages.
5. Security & Spreadsheet Formula Injection Sanitization.
6. Automation Telemetry & Scheduler Reliability.
"""

import json
from pathlib import Path
import pytest

from src.storage.database import DatabaseManager, db_manager
from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.providers.youtube import YouTubeAutocompleteProvider
from src.classifier.service import default_classifier
from src.intelligence.scoring import default_scorer
from src.providers.serp import UnconnectedSerpMetricsProvider
from src.intelligence.daily_engine import DailyOpportunityEngine
from src.intelligence.product_finder import ProductExtractor
from src.intelligence.decision_helper import KeywordDecisionHelper
from src.intelligence.content_factory import (
    ContentFactoryEngine,
    VideoFormat,
    VideoPurpose,
    ReadinessStatus,
    VideoContentPackage,
)
from src.intelligence.action_center import ActionCenterEngine
from src.storage.export import sanitize_formula_injection
from src.ui.components import ALL_NAVIGATION_PAGES
from src.utils.validators import sanitize_seed_keyword


@pytest.fixture
def isolated_db(tmp_path: Path) -> DatabaseManager:
    """Fixture providing an isolated SQLite database in WAL mode."""
    db_file = tmp_path / "test_release_gate.db"
    db = DatabaseManager(db_file)
    db.init_db()
    return db


@pytest.fixture
def isolated_chan_mgr(isolated_db: DatabaseManager) -> ChannelManager:
    """Fixture providing a ChannelManager wired to test database."""
    mgr = ChannelManager(isolated_db)
    mgr.get_all_channels()
    return mgr


# ==============================================================================
# 1. ARCHITECTURE & NAVIGATION CONTRACT
# ==============================================================================

def test_sqlite_wal_mode_and_core_schema(isolated_db: DatabaseManager):
    """Verify SQLite WAL mode and all 11+ critical application tables."""
    with isolated_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0].lower()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        
    assert journal_mode == "wal", f"Expected WAL mode, got {journal_mode}"
    
    required_tables = [
        "searches", "keywords", "autocomplete_cache", "channel_profiles",
        "serp_cache", "daily_morning_reports", "video_descriptions",
        "video_seo_audits", "strategy_calendar_items", "action_center_tasks",
        "video_content_packages"
    ]
    for table in required_tables:
        assert table in tables, f"Missing critical table: {table}"


def test_navigation_contract_fourteen_destinations():
    """Verify strict preservation of the 14 base navigation pages contract."""
    assert len(ALL_NAVIGATION_PAGES) == 14
    expected_sample = [
        "Dashboard",
        "New Keyword Research",
        "Keyword Results",
        "Pattern Generator",
        "YouTube Video Research",
        "Content Opportunities",
        "Saved Research",
    ]
    for page in expected_sample:
        assert any(page in p for p in ALL_NAVIGATION_PAGES), f"Missing expected page pattern: {page}"


# ==============================================================================
# 2. FOUR-CHANNEL ISOLATION & BANGLA UNICODE SUPPORT
# ==============================================================================

def test_four_channel_profiles_integrity_and_isolation(isolated_chan_mgr: ChannelManager):
    """Verify all 4 configured channels exist with distinct niches, audiences, and languages."""
    channels = isolated_chan_mgr.get_all_channels()
    assert len(channels) == 4
    
    names = [c.channel_name for c in channels]
    assert "TechGear Pulse" in names
    assert "CodeCraft বাংলা" in names
    assert "HomeChef Artisan" in names
    assert "FitPulse Active" in names
    
    # Verify Bangla Unicode channel properties
    bangla_ch = next(c for c in channels if c.channel_name == "CodeCraft বাংলা")
    assert bangla_ch.target_language == "bn"
    assert bangla_ch.target_country == "BD"
    assert "পাইথন" in " ".join(bangla_ch.sub_niches) or "Python" in " ".join(bangla_ch.sub_niches)


def test_channel_data_separation_across_tasks_and_packages(
    isolated_db: DatabaseManager, isolated_chan_mgr: ChannelManager
):
    """Verify zero cross-channel data bleed across action tasks and content packages."""
    action_engine = ActionCenterEngine(database=isolated_db, chan_mgr=isolated_chan_mgr)
    factory = ContentFactoryEngine(database=isolated_db, chan_mgr=isolated_chan_mgr)
    
    # Sync tasks for Channel 1 and Channel 2
    tasks_ch1 = action_engine.sync_tasks_for_channel(1)
    tasks_ch2 = action_engine.sync_tasks_for_channel(2)
    
    assert all(t.channel_id == 1 for t in tasks_ch1)
    assert all(t.channel_id == 2 for t in tasks_ch2)
    
    # Generate packages for Channel 1 and Channel 2
    pkg1 = factory.generate_package(channel_id=1, topic="Keyboard Switches", primary_keyword="switches")
    pkg2 = factory.generate_package(channel_id=2, topic="FastAPI Microservices", primary_keyword="fastapi")
    
    id1 = factory.save_package(pkg1)
    id2 = factory.save_package(pkg2)
    
    ch1_pkgs = isolated_db.get_video_content_packages(channel_id=1)
    ch2_pkgs = isolated_db.get_video_content_packages(channel_id=2)
    
    assert all(p["channel_id"] == 1 for p in ch1_pkgs)
    assert all(p["channel_id"] == 2 for p in ch2_pkgs)


# ==============================================================================
# 3. EPISTEMIC MODESTY & ACCURACY
# ==============================================================================

def test_epistemic_modesty_unconnected_serp_provider():
    """Verify unconnected SERP provider honestly discloses missing credentials without fake metrics."""
    provider = UnconnectedSerpMetricsProvider()
    assert not provider.is_connected()
    
    metrics = provider.get_metrics("mechanical keyboard")
    assert not metrics.is_available
    assert metrics.search_volume is None
    assert metrics.competition_score is None
    assert "Not available" in metrics.status_message


def test_epistemic_modesty_classifier_scoring_bounds():
    """Verify keyword scoring is deterministic within [0, 100] without synthetic volume claims."""
    cls = default_classifier.classify("best mechanical keyboards 2026")
    score = default_scorer.score("best mechanical keyboards 2026", "mechanical keyboards", cls)
    
    assert 0.0 <= score.total_score <= 100.0
    assert hasattr(cls, "primary_intent")


# ==============================================================================
# 4. COMPLETE USER JOURNEY SUBSYSTEMS
# ==============================================================================

def test_seed_keyword_sanitization_and_bangla():
    """Verify input validation handles empty, whitespace, and Unicode Bengali safely."""
    ok_en, k_en, _ = sanitize_seed_keyword("best budget mechanical keyboard")
    assert ok_en is True
    assert k_en == "best budget mechanical keyboard"
    
    ok_bn, k_bn, _ = sanitize_seed_keyword("বাংলা কোডিং টিউটোরিয়াল")
    assert ok_bn is True
    assert "বাংলা" in k_bn
    
    ok_ws, _, err_ws = sanitize_seed_keyword("     ")
    assert ok_ws is False
    assert "whitespace" in err_ws or "empty" in err_ws


def test_keyword_decision_helper_evaluation():
    """Verify Decision Helper evaluates candidates without false ranking promises."""
    helper = KeywordDecisionHelper(database=db_manager)
    ch = channel_manager.get_channel(1)
    
    decision = helper.evaluate_keyword(
        keyword="custom mechanical keyboard build guide",
        channel=ch,
        source_type="autocomplete"
    )
    
    assert decision.keyword == "custom mechanical keyboard build guide"
    assert decision.verdict in ["🟢 Strong Candidate", "🔵 Moderate Potential", "🟡 Low Signal"]
    assert "does not promise guaranteed search rankings" in decision.disclaimer


def test_one_click_content_package_generation_and_export(
    isolated_db: DatabaseManager, isolated_chan_mgr: ChannelManager
):
    """Verify Content Factory generates 6-part package with SEO readiness and exports cleanly."""
    factory = ContentFactoryEngine(database=isolated_db, chan_mgr=isolated_chan_mgr)
    
    pkg = factory.generate_package(
        channel_id=1,
        topic="Keychron Q1 Pro Review",
        primary_keyword="keychron q1 pro",
        format_type=VideoFormat.LONG_FORM,
        purpose_type=VideoPurpose.REVIEW,
        supporting_keywords=["mechanical keyboard", "wireless keyboard", "typing test"],
        target_viewer="Desk setup enthusiasts and mechanical keyboard hobbyists",
        user_notes="Tested for 30 days.",
        product_info={"specs": "Wireless, QMK/VIA support, double gasket mount."},
        source_links=["https://keychron.com"]
    )
    
    assert isinstance(pkg, VideoContentPackage)
    assert len(pkg.title_options) >= 4
    assert len(pkg.outline.get("sections", [])) >= 4
    assert len(pkg.description_text) > 200
    assert pkg.thumbnail_concept is not None
    assert len(pkg.seo_readiness) >= 5
    
    # Save and reload
    pkg_id = factory.save_package(pkg)
    reloaded = factory.get_package(pkg_id)
    assert reloaded is not None
    assert reloaded.id == pkg_id
    assert reloaded.topic == pkg.topic
    
    # Markdown Export
    md = factory.export_as_markdown(pkg)
    assert "## 1. Title Options" in md
    assert "## 3. Video Outline" in md
    assert "Keychron Q1 Pro" in md


# ==============================================================================
# 5. SECURITY & SPREADSHEET FORMULA INJECTION SANITIZATION
# ==============================================================================

def test_spreadsheet_formula_injection_defense():
    """Verify dangerous formula prefixes (=, +, -, @, \\t, \\r) are neutralized."""
    dangerous = [
        "=1+1",
        "+cmd|' /C calc'!A0",
        "-5+2",
        "@SUM(A1:A100)",
        "\tmalicious_tab",
        "\rmalicious_return"
    ]
    for d in dangerous:
        sanitized = sanitize_formula_injection(d)
        assert sanitized.startswith("'"), f"Failed to sanitize formula injection: {d} -> {sanitized}"


# ==============================================================================
# 6. AUTOMATION & SCHEDULER TELEMETRY
# ==============================================================================

def test_action_center_scheduler_telemetry(isolated_db: DatabaseManager, isolated_chan_mgr: ChannelManager):
    """Verify Action Center telemetry reports 07:00 AM Asia/Dhaka and local runner notice."""
    action_engine = ActionCenterEngine(database=isolated_db, chan_mgr=isolated_chan_mgr)
    telemetry = action_engine.get_scheduler_status()
    
    assert "07:00 AM" in telemetry.get("next_scheduled_run", "")
    assert "Asia/Dhaka" in telemetry.get("timezone", "")
    assert "must remain running" in telemetry.get("local_runner_notice", "").lower()
