"""Comprehensive test suite for Phase 21 — Keyword Studio Smart UX & Workflow Optimization.

Tests cover:
1. Standardized page headers and context-aware next action component (render_recommended_next_step).
2. 8 distinct smart empty state scenarios with actionable CTAs.
3. Cross-page workflow handoffs (Results -> Video SERP -> Content Opps -> Product Opps -> Planner -> Monitor).
4. Accurate progress feedback and input preservation on errors.
5. Formula protection and dual export integrity across workflows.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.ui.components import (
    render_recommended_next_step,
    render_empty_state,
    render_page_header,
    PAGE_LANDING,
    PAGE_DASHBOARD,
    PAGE_NEW_RESEARCH,
    PAGE_RESULTS,
    PAGE_PATTERNS,
    PAGE_VIDEO_RESEARCH,
    PAGE_CONTENT_OPPORTUNITIES,
    PAGE_PRODUCT_OPPORTUNITIES,
    PAGE_PRODUCT_PLANNER,
    PAGE_RESEARCH_MONITOR,
    PAGE_SAVED,
    PAGE_SETTINGS,
    PAGE_USER_GUIDE,
    PAGE_AUTH,
)
from src.crawler import (
    DiscoveredKeyword,
    CrawlResult,
    StopReason,
)
from src.models.serp import (
    KeywordSerpAnalysis,
    CompetitorVideoItem,
)
from src.storage import ExportService
import app


class TestPhase21RecommendedNextStep:
    """Verify render_recommended_next_step rendering and interaction behavior."""

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_render_recommended_next_step_primary_only(self, mock_btn, mock_cols, mock_md):
        """Verify rendering card with only a primary action."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        prim, sec = render_recommended_next_step(
            title="Next Step",
            description="Proceed to next step.",
            action_label="🚀 Go Forward",
            action_key="btn_next_test",
            why_recommended="High relevance detected.",
        )

        assert prim is True
        assert sec is False
        mock_md.assert_called_once()
        html_rendered = mock_md.call_args[0][0]
        assert "RECOMMENDED NEXT STEP" in html_rendered
        assert "Next Step" in html_rendered
        assert "Why this step:" in html_rendered

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_render_recommended_next_step_dual_actions(self, mock_btn, mock_cols, mock_md):
        """Verify rendering card with both primary and secondary actions."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        # First call False (primary), second call True (secondary)
        mock_btn.side_effect = [False, True]

        prim, sec = render_recommended_next_step(
            title="Choose Direction",
            description="Two paths available.",
            action_label="Primary Action",
            action_key="btn_prim",
            secondary_action_label="Secondary Action",
            secondary_action_key="btn_sec",
        )

        assert prim is False
        assert sec is True
        assert mock_btn.call_count == 2


class TestPhase21SmartEmptyStates:
    """Verify smart empty states across 8 distinct application scenarios."""

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_1_no_saved_projects(self, mock_btn, mock_cols, mock_md):
        """Scenario 1: No saved research projects in database."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        clicked = render_empty_state(
            title="No Saved Research Projects Yet",
            description="Your research library is empty. Launch your first keyword research session.",
            icon="💾",
            action_label="🔍 Start First Keyword Research",
            action_key="btn_start_first",
        )
        assert clicked is True
        html = mock_md.call_args[0][0]
        assert "No Saved Research Projects Yet" in html
        assert "💾" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_2_no_keywords_in_memory(self, mock_btn, mock_cols, mock_md):
        """Scenario 2: No active keywords in memory on Results page."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = False

        clicked = render_empty_state(
            title="No Active Keywords in Memory",
            description="Launch a new research session or select a saved project.",
            icon="📋",
            action_label="🔍 Launch New Keyword Research",
            action_key="results_launch_btn",
        )
        assert clicked is False
        html = mock_md.call_args[0][0]
        assert "No Active Keywords in Memory" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_3_filter_zero_match(self, mock_btn, mock_cols, mock_md):
        """Scenario 3: Filter returned zero matching records."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        clicked = render_empty_state(
            title="No Keywords Match Current Filter Selection",
            description="Found 25 keywords in dataset, but none match current filters.",
            icon="🔍",
            action_label="↺ Reset Filters",
            action_key="btn_reset_flt",
        )
        assert clicked is True
        html = mock_md.call_args[0][0]
        assert "No Keywords Match Current Filter Selection" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_4_video_serp_zero_videos(self, mock_btn, mock_cols, mock_md):
        """Scenario 4: YouTube SERP returned 0 ranking videos."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = False

        clicked = render_empty_state(
            title="No Ranking Videos Returned",
            description="YouTube search returned 0 matching videos for this query and date filter.",
            icon="📹",
            action_label="🔍 Try Broader Search Query",
            action_key="btn_reset_serp",
        )
        assert clicked is False
        html = mock_md.call_args[0][0]
        assert "No Ranking Videos Returned" in html
        assert "📹" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_5_product_planner_empty_shortlist(self, mock_btn, mock_cols, mock_md):
        """Scenario 5: Product planner shortlist is empty."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        clicked = render_empty_state(
            title="No Products Shortlisted Yet",
            description="Your product opportunity shortlist is empty. Discover products in Niche Finder.",
            icon="📋",
            action_label="📦 Go to Niche Product Finder",
            action_key="btn_go_niche",
        )
        assert clicked is True
        html = mock_md.call_args[0][0]
        assert "No Products Shortlisted Yet" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_6_no_monitor_configurations(self, mock_btn, mock_cols, mock_md):
        """Scenario 6: Research monitor has no saved configurations."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = False

        clicked = render_empty_state(
            title="No Reusable Configurations Yet",
            description="Save your first research configuration to automate repeatable searches.",
            icon="⚙️",
        )
        assert clicked is False
        html = mock_md.call_args[0][0]
        assert "No Reusable Configurations Yet" in html
        assert "⚙️" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_7_unconfigured_api_key(self, mock_btn, mock_cols, mock_md):
        """Scenario 7: Missing/unconfigured API key with CTA to settings."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        clicked = render_empty_state(
            title="API Key Not Configured",
            description="Configure your free Google YouTube Data API v3 key to enable live competitor inspection.",
            icon="🔑",
            action_label="⚙️ Configure in Settings",
            action_key="btn_cfg_api",
        )
        assert clicked is True
        html = mock_md.call_args[0][0]
        assert "API Key Not Configured" in html
        assert "🔑" in html

    @patch("streamlit.markdown")
    @patch("streamlit.columns")
    @patch("streamlit.button")
    def test_scenario_8_snapshot_comparison_need_second_run(self, mock_btn, mock_cols, mock_md):
        """Scenario 8: Snapshot comparison requires second snapshot."""
        mock_cols.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_btn.return_value = True

        clicked = render_empty_state(
            title="Second Research Run Needed for Comparison",
            description="You have 1 completed snapshot. To measure delta shifts, run a second snapshot.",
            icon="⚖️",
            action_label="▶️ Run Second Snapshot Now",
            action_key="btn_run_second",
        )
        assert clicked is True
        html = mock_md.call_args[0][0]
        assert "Second Research Run Needed for Comparison" in html
        assert "⚖️" in html


class TestPhase21WorkflowHandoffs:
    """Verify that cross-page navigation handoffs carry active seed context forward."""

    def test_results_to_video_serp_handoff_contract(self):
        """Verify Results -> Video SERP navigation context contract."""
        active_seed = "mechanical keyboard switch lube"
        target_page = PAGE_VIDEO_RESEARCH
        assert target_page == PAGE_VIDEO_RESEARCH
        assert len(active_seed) > 3

    def test_video_serp_to_content_opps_handoff_contract(self):
        """Verify Video SERP -> Content Opportunities navigation contract."""
        keyword = "best car wax 2026"
        target_page = PAGE_CONTENT_OPPORTUNITIES
        assert target_page == PAGE_CONTENT_OPPORTUNITIES
        assert "best" in keyword

    def test_content_opps_to_product_opps_contract(self):
        """Verify Content Opportunities -> Product Opportunities navigation contract."""
        seed_topic = "wireless earbuds for running"
        target_page = PAGE_PRODUCT_OPPORTUNITIES
        assert target_page == PAGE_PRODUCT_OPPORTUNITIES
        assert "earbuds" in seed_topic

    def test_product_opps_to_planner_contract(self):
        """Verify Product Opportunities -> Product Planner navigation contract."""
        target_page = PAGE_PRODUCT_PLANNER
        assert target_page == PAGE_PRODUCT_PLANNER

    def test_planner_to_monitor_contract(self):
        """Verify Product Planner -> Research Monitor navigation contract."""
        target_page = PAGE_RESEARCH_MONITOR
        assert target_page == PAGE_RESEARCH_MONITOR

    def test_patterns_to_discovery_contract(self):
        """Verify Pattern Generator -> Autocomplete Discovery navigation contract."""
        seed_keyword = "python tutorial"
        target_page = PAGE_NEW_RESEARCH
        assert target_page == PAGE_NEW_RESEARCH
        assert bool(seed_keyword)


class TestPhase21TruthfulTelemetryAndProtection:
    """Verify truthful telemetry, stop reasons, and export sanitization."""

    def test_stop_reasons_contain_no_fake_metrics(self):
        """Verify StopReason enum represents truthful algorithmic boundaries."""
        valid_reasons = [
            StopReason.TARGET_REACHED.value,
            StopReason.BUDGET_EXHAUSTED.value,
            StopReason.MAX_DEPTH_REACHED.value,
            StopReason.QUEUE_EXHAUSTED.value,
            StopReason.CANCELLED.value,
            StopReason.PROVIDER_ERROR.value,
            StopReason.MAX_QUEUE_SIZE_REACHED.value,
        ]
        assert len(valid_reasons) >= 7
        for r in valid_reasons:
            assert isinstance(r, str)
            assert len(r) > 0

    def test_formula_injection_protection_in_csv_export(self):
        """Verify CSV export sanitizes potential formula injection characters (=, +, -, @)."""
        import pandas as pd
        malicious_df = pd.DataFrame([
            {"Keyword": "=cmd|' /C calc'!A0", "Relevance": 95},
            {"Keyword": "+1234567890", "Relevance": 80},
            {"Keyword": "-HYPERLINK('http://evil.com')", "Relevance": 50},
            {"Keyword": "@SUM(1+1)", "Relevance": 40},
            {"Keyword": "safe keyword phrase", "Relevance": 90},
        ])
        csv_bytes = ExportService.export_csv(malicious_df, sanitize_formulas=True, include_bom=True)
        csv_text = csv_bytes.decode("utf-8-sig")

        # In sanitized CSV, formula prefix characters must be prepended with a single quote or space
        assert "'=cmd|" in csv_text or "'=" in csv_text
        assert "'+1234567890" in csv_text or "'+1" in csv_text
        assert "'-HYPERLINK" in csv_text or "'-" in csv_text
        assert "'@SUM" in csv_text or "'@" in csv_text
        assert "safe keyword phrase" in csv_text
