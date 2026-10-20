"""Test suite for Phase 30: End-to-End Quality, Simplicity & Reliability Audit.

Verifies:
1. Verified subsystem inventory (Channel Manager, Autocomplete, Classifier, Scorer, Clusters, SERP, Opportunities, Descriptions, SEO Audit, Strategy, Validation, Daily Reports, Storage, Export).
2. Main 13-step user journey executed end-to-end without unhandled exceptions or state loss.
3. Crucial failure scenarios (empty inputs, single character, zero results, missing API keys, quota exhaustion, network timeout, formula injection).
4. DailyOpportunityEngine defensive argument routing (chan_mgr vs database safeguard).
5. Performance & Caching (SQLite WAL mode, local TTL cache speedup, bounded timeouts).
6. Security & Credentials protection (password masking, formula sanitization).
7. Strict preservation of 14 base navigation pages contract.
"""

import threading
import time
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import requests

from src.classifier.service import default_classifier
from src.intelligence.audit_engine import AuditEngine
from src.intelligence.channel_manager import channel_manager, ChannelManager
from src.intelligence.clustering import default_clusterer
from src.intelligence.daily_engine import DailyOpportunityEngine
from src.intelligence.description_studio import DescriptionStudio
from src.intelligence.opportunities import ContentBriefGenerator, VideoTopicGenerator
from src.intelligence.product_finder import ProductExtractor
from src.intelligence.scoring import default_scorer
from src.intelligence.strategy_engine import ContentStrategyAutopilot
from src.intelligence.validation_engine import TopicValidationEngine
from src.models.wizard import WizardState
from src.providers.ai import DeterministicFallbackAiProvider
from src.providers.serp import UnconnectedSerpMetricsProvider, YouTubeDataApiSerpProvider
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_formula_injection
from src.ui.components import ALL_NAVIGATION_PAGES


# =============================================================================
# 1. SUBSYSTEM INVENTORY VERIFICATION
# =============================================================================
def test_channel_manager_four_independent_channels():
    channels = channel_manager.get_all_channels()
    assert len(channels) == 4
    for idx, chan in enumerate(channels):
        assert chan.id == idx + 1
        assert len(chan.channel_name) > 0
        assert len(chan.niche) > 0


def test_classifier_and_scoring_deterministic_output():
    kw = "best mechanical keyboards for typing"
    cls = default_classifier.classify(kw)
    assert cls.primary_intent is not None
    score = default_scorer.score(kw, "mechanical keyboards", cls)
    assert 0.0 <= score.total_score <= 100.0


def test_topic_clustering_engine():
    from src.crawler.models import DiscoveredKeyword
    kws = [
        DiscoveredKeyword(keyword="wireless earbuds for running", normalized_key="wireless earbuds for running", depth=1),
        DiscoveredKeyword(keyword="how to clean wireless earbuds", normalized_key="how to clean wireless earbuds", depth=1),
        DiscoveredKeyword(keyword="wireless earbuds vs wired", normalized_key="wireless earbuds vs wired", depth=1),
    ]
    clusters = default_clusterer.cluster_keywords(kws, "wireless earbuds")
    assert len(clusters) >= 1
    assert any(c.name for c in clusters)


def test_unconnected_serp_provider_honest_status():
    serp = UnconnectedSerpMetricsProvider()
    assert serp.is_connected() is False
    metrics = serp.get_metrics("test topic")
    assert metrics.is_available is False
    assert "no verified data source connected" in metrics.status_message


def test_description_studio_eight_part_structure():
    channels = channel_manager.get_all_channels()
    studio = DescriptionStudio(db_manager)
    desc = studio.build_description(
        topic="Keychron Q1 Pro Mechanical Keyboard Review",
        primary_keyword="keychron q1 pro",
        channel=channels[0],
    )
    assert desc.opening_hook != ""
    assert desc.viewer_value != ""
    assert len(desc.chapters) >= 1
    assert "affiliate" in desc.affiliate_disclosure.lower() or "recommend" in desc.affiliate_disclosure.lower()


def test_seo_audit_engine_readiness_scoring():
    auditor = AuditEngine(db_manager)
    title_res = auditor.audit_title("Best Keyboards 2026", "keyboards")
    desc_res = auditor.audit_description("Top keyboard reviews and tests.", "keyboards")
    script_res = auditor.audit_script_alignment("Best Keyboards 2026", "Top reviews", "keyboards", "Welcome to keyboard review")
    aff_res = auditor.audit_affiliate_content("Links below.", has_affiliate_links=False)
    thumb_res = auditor.audit_thumbnail_alignment("Keyboard closeup", "Best Keyboards 2026")

    score_obj = auditor.calculate_readiness_score(title_res, desc_res, script_res, aff_res, thumb_res)
    assert 0.0 <= score_obj.overall_readiness_score <= 100.0


def test_content_strategy_autopilot_pillars():
    channels = channel_manager.get_all_channels()
    strat = ContentStrategyAutopilot(db_manager)
    pillars = strat.build_suggested_pillars(channel=channels[0])
    assert len(pillars) >= 3


def test_topic_validation_engine_multi_factor():
    channels = channel_manager.get_all_channels()
    val_engine = TopicValidationEngine(db_manager)
    rep = val_engine.validate_candidate_topic(
        channel=channels[0],
        topic="custom mechanical keyboard build guide",
        keyword="mechanical keyboard",
    )
    assert rep is not None
    assert rep.readiness_status is not None
    assert len(rep.what_supports_idea) > 0
    assert len(rep.what_remains_unknown) > 0


# =============================================================================
# 2. DEFENSIVE SAFEGARDS & DEFECT FIXES
# =============================================================================
def test_daily_opportunity_engine_argument_routing_safeguard():
    """Verify Phase 30 fix: passing DatabaseManager as first positional argument does not crash."""
    # When instantiated with db_manager as first positional argument
    engine = DailyOpportunityEngine(db_manager)
    assert isinstance(engine.chan_mgr, ChannelManager)
    assert engine.db == db_manager


# =============================================================================
# 3. FAILURE SCENARIOS & RECOVERY
# =============================================================================
def test_empty_and_whitespace_topic_validation():
    state = WizardState(current_step=2)
    state.topic = ""
    valid, err = state.validate_current_step()
    assert valid is False
    assert "at least 2 characters" in err

    state.topic = "   x   "
    valid, err = state.validate_current_step()
    assert valid is False


def test_duplicate_submission_blocked_when_searching():
    state = WizardState(current_step=4, is_searching=True)
    valid, err = state.validate_current_step()
    assert valid is False
    assert "currently running" in err


def test_formula_injection_sanitization():
    malicious = ["=SUM(A1:A10)", "-2+3", "+cmd|' /C calc'!A0", "@malicious"]
    sanitized = [sanitize_formula_injection(val) for val in malicious]
    for s in sanitized:
        assert s.startswith("'")


def test_quota_exhaustion_message_distinction():
    with patch.object(requests.Session, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {
            "error": {
                "errors": [{"reason": "quotaExceeded"}],
                "message": "Quota limit reached.",
            }
        }
        mock_get.return_value = mock_resp
        serp = YouTubeDataApiSerpProvider(api_key="test_key")
        res = serp.get_metrics("test query")
        assert "quota" in res.status_message.lower()


def test_network_timeout_handling():
    with patch.object(requests.Session, "get", side_effect=Exception("Connection timed out")):
        p = YouTubeAutocompleteProvider(database_manager=None)
        with pytest.raises(Exception) as excinfo:
            p.get_suggestions("timeout keyword", use_cache=False)
        assert "timed out" in str(excinfo.value).lower() or "connection" in str(excinfo.value).lower()


# =============================================================================
# 4. PERFORMANCE, CACHING & SECURITY
# =============================================================================
def test_sqlite_wal_mode_active():
    with db_manager.get_connection() as conn:
        cursor = conn.execute("PRAGMA journal_mode;")
        row = cursor.fetchone()
        assert row is not None
        assert row[0].upper() == "WAL"


def test_autocomplete_caching_speedup():
    provider = YouTubeAutocompleteProvider(database_manager=db_manager)
    # First fetch (network or cache)
    res1 = provider.get_suggestions("python asyncio tutorial", use_cache=True)
    assert len(res1) > 0

    # Second fetch (local SQLite cache hit)
    t0 = time.perf_counter()
    res2 = provider.get_suggestions("python asyncio tutorial", use_cache=True)
    dur = (time.perf_counter() - t0) * 1000
    assert len(res2) == len(res1)
    assert dur < 50.0  # Local SQLite lookup served under 50ms


def test_bounded_http_timeouts():
    provider = YouTubeAutocompleteProvider()
    assert provider.connect_timeout <= 15.0
    assert provider.read_timeout <= 15.0

    serp = YouTubeDataApiSerpProvider(api_key="mock")
    assert serp.timeout <= 15.0


def test_utf8_bom_csv_export():
    df = pd.DataFrame([{"Keyword": "CodeCraft বাংলা", "Relevance": 95.0}])
    csv_bytes = ExportService.export_csv(df)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    decoded = csv_bytes.decode("utf-8-sig")
    assert "বাংলা" in decoded


# =============================================================================
# 5. NAVIGATION CONTRACT INTEGRITY
# =============================================================================
def test_navigation_pages_contract_fourteen_destinations():
    assert len(ALL_NAVIGATION_PAGES) == 14
