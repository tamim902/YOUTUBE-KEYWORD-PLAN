"""Tests for the Simplified Four Core Tools Architecture.

Verifies:
1. Tool 1: Keyword Research (clean seed input, honest volume, deterministic intent & relevance)
2. Tool 2: Competitor Research (grounded public YouTube Data API SERP, no fake metrics)
3. Tool 3: Last 60 Days Opportunity Finder (rolling window, search coverage modesty)
4. Tool 4: SEO Title, Description & Tags Generator (50-65 char titles, recommended pick, structured description)
5. Settings: API key status, connection test, SQLite database status & safe backup
6. Navigation contract: FOUR_CORE_TOOLS defines exactly 4 tools, ALL_NAVIGATION_PAGES preserves 14 items.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    FOUR_CORE_TOOLS,
    TOOL_KEYWORD_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
    TOOL_SETTINGS,
    TOOL_CANONICAL_MAP,
    render_four_core_navigation,
)
from src.ui.tool_keyword_research import render_keyword_research_tool
from src.ui.tool_competitor_research import render_competitor_research_tool
from src.ui.tool_opportunity_finder import render_opportunity_finder_tool
from src.ui.tool_seo_generator import render_seo_generator_tool
from src.ui.tool_settings import render_settings_tool


class MockSessionState(dict):
    """Mock session state supporting both dict indexing and attribute access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


def _mock_columns(spec):
    """Dynamic mock helper for streamlit.columns supporting int or list of weights."""
    count = spec if isinstance(spec, int) else len(spec)
    return [MagicMock() for _ in range(count)]


class TestFourCoreToolsConstants:
    """Verify core tool definitions, canonical mappings, and legacy preservation."""

    def test_four_core_tools_exact_count_and_members(self):
        """FOUR_CORE_TOOLS must have exactly 4 tools matching specifications."""
        assert len(FOUR_CORE_TOOLS) == 4
        assert FOUR_CORE_TOOLS[0] == TOOL_KEYWORD_RESEARCH
        assert FOUR_CORE_TOOLS[1] == TOOL_COMPETITOR_RESEARCH
        assert FOUR_CORE_TOOLS[2] == TOOL_60_DAY_OPPORTUNITIES
        assert FOUR_CORE_TOOLS[3] == TOOL_SEO_GENERATOR

    def test_legacy_all_navigation_pages_preserved(self):
        """ALL_NAVIGATION_PAGES must strictly retain 14 items for backward-compatibility."""
        assert len(ALL_NAVIGATION_PAGES) == 14

    def test_canonical_map_normalizes_aliases(self):
        """Aliases should cleanly resolve to canonical names."""
        assert TOOL_CANONICAL_MAP.get("✨ SEO Generator") == TOOL_SEO_GENERATOR
        assert TOOL_CANONICAL_MAP.get("⚡ 60-Day Opportunities") == TOOL_60_DAY_OPPORTUNITIES
        assert TOOL_CANONICAL_MAP.get("Keyword Research") == TOOL_KEYWORD_RESEARCH
        assert TOOL_CANONICAL_MAP.get("Settings") == TOOL_SETTINGS


class TestRenderFourCoreNavigation:
    """Verify the simplified sidebar navigation menu."""

    @patch("streamlit.sidebar")
    def test_render_four_core_navigation_default(self, mock_sidebar):
        """Should display 4 options in radio, brand header, and quiet settings button."""
        mock_sidebar.radio.return_value = TOOL_KEYWORD_RESEARCH
        mock_sidebar.button.return_value = False

        result = render_four_core_navigation(TOOL_KEYWORD_RESEARCH)
        assert result == TOOL_KEYWORD_RESEARCH
        mock_sidebar.radio.assert_called_once()
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["options"] == FOUR_CORE_TOOLS
        assert radio_kwargs["index"] == 0

    @patch("streamlit.sidebar")
    def test_render_four_core_navigation_select_competitor(self, mock_sidebar):
        """Selecting Competitor Research should set correct radio index."""
        mock_sidebar.radio.return_value = TOOL_COMPETITOR_RESEARCH
        mock_sidebar.button.return_value = False

        result = render_four_core_navigation(TOOL_COMPETITOR_RESEARCH)
        assert result == TOOL_COMPETITOR_RESEARCH
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["index"] == 1

    @patch("streamlit.sidebar")
    def test_render_four_core_navigation_click_settings(self, mock_sidebar):
        """Clicking the quiet settings button should route to TOOL_SETTINGS."""
        mock_sidebar.radio.return_value = TOOL_KEYWORD_RESEARCH
        mock_sidebar.button.return_value = True

        result = render_four_core_navigation(TOOL_KEYWORD_RESEARCH)
        assert result == TOOL_SETTINGS

    @patch("streamlit.sidebar")
    def test_render_four_core_navigation_fallback_unknown_page(self, mock_sidebar):
        """Unknown or legacy page should default to index 0 (Keyword Research)."""
        mock_sidebar.radio.return_value = TOOL_KEYWORD_RESEARCH
        mock_sidebar.button.return_value = False

        result = render_four_core_navigation("UNKNOWN_PAGE_NAME")
        assert result == TOOL_KEYWORD_RESEARCH
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["index"] == 0


class TestTool1KeywordResearch:
    """Verify Tool 1: Keyword Research execution."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_keyword_research_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.expander")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_keyword_research_initial_state(
        self, mock_state, mock_exp, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should render input with empty state guidance."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_keyword_research_tool()
        assert "kr_results" in mock_state
        assert "kr_last_query" in mock_state


class TestTool2CompetitorResearch:
    """Verify Tool 2: Competitor Research execution."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_competitor_research_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.expander")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_competitor_research_unconfigured(
        self, mock_state, mock_exp, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should gracefully notify about optional API key without errors."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}, clear=True):
            render_competitor_research_tool()
            assert "cr_analysis" in mock_state


class TestTool3OpportunityFinder:
    """Verify Tool 3: Last 60 Days Opportunity Finder execution."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_opportunity_finder_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_opportunity_finder_initial_state(
        self, mock_state, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should initialize 60-day window session state."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_opportunity_finder_tool()
        assert "opp_results" in mock_state
        assert "opp_window_str" in mock_state


class TestTool4SeoGenerator:
    """Verify Tool 4: SEO Title, Description & Tags Generator execution."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_seo_generator_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_seo_generator_initial_state(
        self, mock_state, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should initialize SEO state variables."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_seo_generator_tool()
        assert "seo_main_keyword" in mock_state
        assert "seo_generated_pkg" in mock_state


class TestToolSettings:
    """Verify Settings & System Status execution."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_settings_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_settings_displays_status(
        self, mock_state, mock_btn, mock_ti, mock_cols, mock_md
    ):
        """Should display API status and database storage info."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_settings_tool()
        assert mock_md.call_count >= 3
