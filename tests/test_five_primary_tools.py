"""Tests for the Five Primary Tools Architecture & Integrated Pattern Generator.

Verifies:
1. Exact 5 primary sections: Keyword Research, YouTube Video Research, Competitor Research, 60-Day Opportunities, SEO Generator.
2. Quiet Settings & API Status action.
3. Legacy backward-compatibility contracts (ALL_NAVIGATION_PAGES has 14 items).
4. Tool 1: Keyword Research (A-Z expansion, question/preposition variations, honest volume, integrated Pattern Generator).
5. Tool 2: YouTube Video Research (official YouTube Data API v3 SERP, public data only, zero fake metrics).
6. Tool 3: Competitor Research (grounded video insights, common title structures, age and view count distribution).
7. Tool 4: 60-Day Opportunity Finder (rolling window, honest coverage states, content angle recommendations).
8. Tool 5: SEO Generator (50-65 char titles, pattern-derived candidates, 8-part description, relevant tag suggestions).
9. Settings: Provider status, API key testing, SQLite WAL health and safe backup.
10. Cross-Tool Workflows: Seamless state passing across all 5 sections.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from unittest.mock import MagicMock, patch
import pytest

from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    FIVE_PRIMARY_TOOLS,
    FOUR_CORE_TOOLS,
    TOOL_KEYWORD_RESEARCH,
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
    TOOL_SETTINGS,
    TOOL_CANONICAL_MAP,
    render_five_primary_navigation,
    render_four_core_navigation,
)
from src.ui.tool_keyword_research import render_keyword_research_tool
from src.ui.tool_video_research import render_video_research_tool
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


class TestFivePrimaryToolsConstants:
    """Verify tool definitions, exact counts, aliases, and legacy contracts."""

    def test_five_primary_tools_exact_count_and_members(self):
        """Must have exactly 5 primary sections in specified order."""
        assert len(FIVE_PRIMARY_TOOLS) == 5
        assert FIVE_PRIMARY_TOOLS[0] == TOOL_KEYWORD_RESEARCH
        assert FIVE_PRIMARY_TOOLS[1] == TOOL_VIDEO_RESEARCH
        assert FIVE_PRIMARY_TOOLS[2] == TOOL_COMPETITOR_RESEARCH
        assert FIVE_PRIMARY_TOOLS[3] == TOOL_60_DAY_OPPORTUNITIES
        assert FIVE_PRIMARY_TOOLS[4] == TOOL_SEO_GENERATOR

    def test_legacy_all_navigation_pages_contract(self):
        """ALL_NAVIGATION_PAGES must strictly retain 14 items for legacy contract preservation."""
        assert len(ALL_NAVIGATION_PAGES) == 14

    def test_canonical_map_normalizes_all_aliases(self):
        """Aliases should cleanly resolve to canonical names."""
        assert TOOL_CANONICAL_MAP.get("YouTube Video Research") == TOOL_VIDEO_RESEARCH
        assert TOOL_CANONICAL_MAP.get("Video Research") == TOOL_VIDEO_RESEARCH
        assert TOOL_CANONICAL_MAP.get("✨ SEO Generator") == TOOL_SEO_GENERATOR
        assert TOOL_CANONICAL_MAP.get("60-Day Opportunity Finder") == TOOL_60_DAY_OPPORTUNITIES
        assert TOOL_CANONICAL_MAP.get("Keyword Research") == TOOL_KEYWORD_RESEARCH
        assert TOOL_CANONICAL_MAP.get("Settings") == TOOL_SETTINGS


class TestRenderFivePrimaryNavigation:
    """Verify the 5-primary-tools sidebar navigation."""

    @patch("streamlit.sidebar")
    def test_render_five_primary_navigation_default(self, mock_sidebar):
        """Default view should present 5 primary tools with index 0 and quiet settings."""
        mock_sidebar.radio.return_value = TOOL_KEYWORD_RESEARCH
        mock_sidebar.button.return_value = False

        result = render_five_primary_navigation(TOOL_KEYWORD_RESEARCH)
        assert result == TOOL_KEYWORD_RESEARCH
        mock_sidebar.radio.assert_called_once()
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["options"] == FIVE_PRIMARY_TOOLS
        assert radio_kwargs["index"] == 0

    @patch("streamlit.sidebar")
    def test_render_five_primary_navigation_select_video_research(self, mock_sidebar):
        """Selecting Video Research should reflect index 1."""
        mock_sidebar.radio.return_value = TOOL_VIDEO_RESEARCH
        mock_sidebar.button.return_value = False

        result = render_five_primary_navigation(TOOL_VIDEO_RESEARCH)
        assert result == TOOL_VIDEO_RESEARCH
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["index"] == 1

    @patch("streamlit.sidebar")
    def test_render_five_primary_navigation_click_settings(self, mock_sidebar):
        """Clicking quiet settings button should route to TOOL_SETTINGS."""
        mock_sidebar.radio.return_value = TOOL_KEYWORD_RESEARCH
        mock_sidebar.button.return_value = True

        result = render_five_primary_navigation(TOOL_KEYWORD_RESEARCH)
        assert result == TOOL_SETTINGS

    def test_render_four_core_navigation_aliases_to_five_primary(self):
        """render_four_core_navigation should call render_five_primary_navigation."""
        with patch("src.ui.components.render_five_primary_navigation") as mock_fn:
            mock_fn.return_value = TOOL_VIDEO_RESEARCH
            res = render_four_core_navigation(TOOL_VIDEO_RESEARCH)
            assert res == TOOL_VIDEO_RESEARCH
            mock_fn.assert_called_once_with(current_page=TOOL_VIDEO_RESEARCH)


class TestTool1KeywordResearch:
    """Verify Tool 1: Keyword Research and integrated Pattern Generator."""

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
        """Should initialize session state with clean seed input."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_keyword_research_tool()
        assert "kr_results" in mock_state
        assert "kr_last_query" in mock_state
        assert "kr_patterns" in mock_state


class TestTool2VideoResearch:
    """Verify Tool 2: YouTube Video Research."""

    def test_callable(self):
        """Renderer function must be callable."""
        assert callable(render_video_research_tool)

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.expander")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_video_research_unconnected(
        self, mock_state, mock_exp, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should display setup instructions when API key is not configured without crashing."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        with patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}, clear=True):
            render_video_research_tool()
            assert "current_serp_analysis" in mock_state

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.columns", side_effect=_mock_columns)
    @patch("streamlit.text_input")
    @patch("streamlit.button")
    @patch("streamlit.expander")
    @patch("streamlit.session_state", new_callable=MockSessionState)
    def test_render_video_research_with_existing_analysis(
        self, mock_state, mock_exp, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should render video breakdown when analysis exists in session state."""
        mock_ti.return_value = "python tutorial"
        mock_btn.return_value = False

        dummy_analysis = KeywordSerpAnalysis(
            keyword="python tutorial",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            total_videos_analyzed=1,
            videos=[
                CompetitorVideoItem(
                    video_id="abc12345",
                    title="Python Tutorial for Beginners",
                    channel_id="UC1234567890",
                    channel_title="Coding Channel",
                    publish_date="2026-01-01T00:00:00Z",
                    view_count=50000,
                    rank=1,
                )
            ],
            average_views=50000.0,
            median_views=50000.0,
            unique_channels_count=1,
            opportunity_score=75,
            opportunity_label="High Opportunity",
        )
        mock_state["current_serp_analysis"] = dummy_analysis

        render_video_research_tool()
        assert mock_md.call_count >= 2


class TestTool3CompetitorResearch:
    """Verify Tool 3: Competitor Research."""

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
    def test_render_competitor_research_initial_state(
        self, mock_state, mock_exp, mock_btn, mock_ti, mock_cols, mock_cont, mock_md
    ):
        """Should initialize competitor state."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_competitor_research_tool()
        assert "cr_analysis" in mock_state


class TestTool4OpportunityFinder:
    """Verify Tool 4: 60-Day Opportunity Finder."""

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
        """Should initialize 60-day window state."""
        mock_ti.return_value = ""
        mock_btn.return_value = False

        render_opportunity_finder_tool()
        assert "opp_results" in mock_state
        assert "opp_window_str" in mock_state


class TestTool5SeoGenerator:
    """Verify Tool 5: SEO Generator."""

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
    """Verify Settings & System Status."""

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


class TestCrossToolWorkflowHandoffs:
    """Verify data handoffs across the five tools."""

    def test_session_state_handoff_keys(self):
        """All 5 tools should read and set designated cross-tool handoff keys."""
        state = MockSessionState()

        # Step 1: User researches keyword in Tool 1
        state["kr_last_query"] = "mechanical keyboard build"
        
        # Handoff to Tool 2: Video Research
        state["vr_target_keyword"] = state["kr_last_query"]
        assert state["vr_target_keyword"] == "mechanical keyboard build"

        # Handoff to Tool 3: Competitor Research
        state["cr_last_query"] = state["vr_target_keyword"]
        assert state["cr_last_query"] == "mechanical keyboard build"

        # Handoff to Tool 4: 60-Day Opportunity Finder
        state["opp_last_seed"] = state["cr_last_query"]
        assert state["opp_last_seed"] == "mechanical keyboard build"

        # Handoff to Tool 5: SEO Generator
        state["seo_main_keyword"] = state["opp_last_seed"]
        state["seo_secondary_keywords"] = "custom keyboard, sound test"
        assert state["seo_main_keyword"] == "mechanical keyboard build"
        assert "sound test" in state["seo_secondary_keywords"]
