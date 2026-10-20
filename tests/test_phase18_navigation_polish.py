"""Unit and integration tests for Phase 18 — Keyword Studio Premium Navigation & Interaction Polish."""

from unittest.mock import MagicMock, patch
import pytest

from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    NAVIGATION_PAGES,
    PAGE_AUTH,
    PAGE_DASHBOARD,
    PAGE_LANDING,
    PAGE_PRODUCT_OPPORTUNITIES,
    PAGE_PRODUCT_PLANNER,
    PAGE_VIDEO_RESEARCH,
    PAGE_LABEL_CLEAN_MAP,
    format_nav_label,
    render_navigation,
)
from src.ui.styles import CUSTOM_CSS


class TestPhase18DesignTokensAndCSS:
    """Verify Phase 18 design tokens, search controls, and interaction styling."""

    def test_navigation_design_tokens_present(self):
        """CUSTOM_CSS must include explicit Phase 18 design token variables."""
        assert "--ks-sidebar-bg" in CUSTOM_CSS
        assert "--ks-nav-pill-active" in CUSTOM_CSS
        assert "--ks-nav-border-active" in CUSTOM_CSS
        assert "--ks-nav-text-active" in CUSTOM_CSS
        assert "--ks-nav-transition" in CUSTOM_CSS

    def test_command_search_styles_present(self):
        """CUSTOM_CSS must include search input, empty state, and result label styles."""
        assert "nav-search-results-label" in CUSTOM_CSS
        assert "nav-empty-state" in CUSTOM_CSS
        assert '[data-testid="stSidebar"] div[data-testid="stTextInput"]' in CUSTOM_CSS

    def test_sidebar_toggle_styles_present(self):
        """CUSTOM_CSS must include styles for the sidebar compact view toggle."""
        assert '[data-testid="stSidebar"] div[data-testid="stToggle"]' in CUSTOM_CSS


class TestPhase18CommandStyleNavigationSearch:
    """Verify command-style destination search and filtering behavior."""

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_search_filtering_returns_real_matching_destinations(self, mock_sidebar):
        """Search query filters to actual matching destinations without fake results."""
        mock_sidebar.text_input.return_value = "video"
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False
        mock_sidebar.radio.return_value = PAGE_VIDEO_RESEARCH

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_VIDEO_RESEARCH

        # Verify radio was called with filtered options
        radio_calls = [c for c in mock_sidebar.radio.call_args_list if c[0][0] == "Matching Pages"]
        assert len(radio_calls) == 1
        filtered_options = radio_calls[0][1]["options"]
        assert PAGE_VIDEO_RESEARCH in filtered_options
        assert all(p in ALL_NAVIGATION_PAGES for p in filtered_options)

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_search_filtering_multiple_matches(self, mock_sidebar):
        """Search for 'product' returns product opportunity finder and planner."""
        mock_sidebar.text_input.return_value = "product"
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False
        mock_sidebar.radio.return_value = PAGE_PRODUCT_OPPORTUNITIES

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_PRODUCT_OPPORTUNITIES

        radio_calls = [c for c in mock_sidebar.radio.call_args_list if c[0][0] == "Matching Pages"]
        assert len(radio_calls) == 1
        filtered_options = radio_calls[0][1]["options"]
        assert PAGE_PRODUCT_OPPORTUNITIES in filtered_options
        assert PAGE_PRODUCT_PLANNER in filtered_options

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_search_empty_state_retains_current_page(self, mock_sidebar):
        """When no destination matches the search, current page is retained."""
        mock_sidebar.text_input.return_value = "nonexistent_query_xyz"
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False

        result = render_navigation(PAGE_DASHBOARD)
        # Retains current page
        assert result == PAGE_DASHBOARD

        # Empty state markdown rendered
        markdown_contents = [c[0][0] for c in mock_sidebar.markdown.call_args_list if isinstance(c[0][0], str)]
        assert any("nav-empty-state" in m for m in markdown_contents)


class TestPhase18CollapsibleSidebarMode:
    """Verify collapsible / compact sidebar mode and state preservation."""

    @patch("streamlit.sidebar")
    def test_compact_mode_injects_compact_styles(self, mock_sidebar):
        """When compact mode is active in session state, compact CSS is injected."""
        with patch("streamlit.session_state", {"sidebar_compact_mode": True}):
            mock_sidebar.text_input.return_value = ""
            mock_sidebar.toggle.return_value = True
            mock_sidebar.button.return_value = False
            mock_sidebar.radio.return_value = PAGE_LANDING

            result = render_navigation(PAGE_LANDING)
            assert result == PAGE_LANDING

            markdown_contents = [c[0][0] for c in mock_sidebar.markdown.call_args_list if isinstance(c[0][0], str)]
            assert any("min-width: 80px" in m for m in markdown_contents)

    @patch("streamlit.sidebar")
    def test_expanded_mode_no_compact_override(self, mock_sidebar):
        """When compact mode is False, compact override CSS is not injected."""
        with patch("streamlit.session_state", {"sidebar_compact_mode": False}):
            mock_sidebar.text_input.return_value = ""
            mock_sidebar.toggle.return_value = False
            mock_sidebar.button.return_value = False
            mock_sidebar.radio.return_value = PAGE_LANDING

            result = render_navigation(PAGE_LANDING)
            assert result == PAGE_LANDING

            markdown_contents = [c[0][0] for c in mock_sidebar.markdown.call_args_list if isinstance(c[0][0], str)]
            assert not any("min-width: 80px" in m for m in markdown_contents)


class TestPhase18WorkspaceProfileRefinement:
    """Verify workspace profile card disclosures and profile navigation."""

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_workspace_card_disclosures(self, mock_sidebar):
        """Workspace profile card must disclose SQLite WAL and Opt-in APIs accurately."""
        mock_sidebar.text_input.return_value = ""
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False
        mock_sidebar.radio.return_value = PAGE_LANDING

        render_navigation(PAGE_LANDING)

        markdown_contents = [c[0][0] for c in mock_sidebar.markdown.call_args_list if isinstance(c[0][0], str)]
        workspace_card_html = next(m for m in markdown_contents if "sidebar-workspace-card" in m)

        assert "Local Pro Studio" in workspace_card_html
        assert "SQLite WAL (Local)" in workspace_card_html
        assert "Opt-in APIs" in workspace_card_html

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_workspace_card_profile_route(self, mock_sidebar):
        """Clicking Studio Profile & Auth button routes to PAGE_AUTH."""
        mock_sidebar.text_input.return_value = ""
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = True  # Profile button clicked
        mock_sidebar.radio.return_value = PAGE_LANDING

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_AUTH
