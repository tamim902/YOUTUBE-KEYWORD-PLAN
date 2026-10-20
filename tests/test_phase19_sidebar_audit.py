"""Comprehensive QA audit tests for Phase 19 — Keyword Studio Sidebar Final Audit & Visual QA."""

from unittest.mock import MagicMock, patch
import pytest

from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    NAVIGATION_PAGES,
    PAGE_AUTH,
    PAGE_CONTENT_OPPORTUNITIES,
    PAGE_DASHBOARD,
    PAGE_LANDING,
    PAGE_NEW_RESEARCH,
    PAGE_PATTERNS,
    PAGE_PRODUCT_OPPORTUNITIES,
    PAGE_PRODUCT_PLANNER,
    PAGE_RESEARCH_MONITOR,
    PAGE_RESULTS,
    PAGE_SAVED,
    PAGE_SERP,
    PAGE_SETTINGS,
    PAGE_USER_GUIDE,
    PAGE_VIDEO_RESEARCH,
    PAGE_LABEL_CLEAN_MAP,
    format_nav_label,
    render_navigation,
)
from src.ui.styles import CUSTOM_CSS


class TestPhase19NavigationDestinationAudit:
    """Audit all 14 navigation destinations for existence, uniqueness, and routing."""

    EXPECTED_14_PAGES = [
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
        PAGE_USER_GUIDE,
        PAGE_AUTH,
        PAGE_SETTINGS,
    ]

    def test_all_14_destinations_defined_and_unique(self):
        """All 14 navigation pages must be unique, non-empty, and match ALL_NAVIGATION_PAGES."""
        assert len(self.EXPECTED_14_PAGES) == 14
        assert len(set(self.EXPECTED_14_PAGES)) == 14
        assert ALL_NAVIGATION_PAGES == self.EXPECTED_14_PAGES
        assert PAGE_SERP == PAGE_VIDEO_RESEARCH

    def test_clean_label_coverage_and_typography(self):
        """Every page must have an emoji-free clean label in PAGE_LABEL_CLEAN_MAP."""
        for page in ALL_NAVIGATION_PAGES:
            clean_title = format_nav_label(page)
            assert isinstance(clean_title, str)
            assert len(clean_title) >= 3
            # Check typography has no emoji
            assert not any(ord(c) > 0x2000 for c in clean_title[:2])

    def test_phase6_core_compatibility_preserved(self):
        """Core Phase 6 navigation pages must remain exactly 6 items."""
        assert len(NAVIGATION_PAGES) == 6
        assert set(NAVIGATION_PAGES).issubset(set(ALL_NAVIGATION_PAGES))


class TestPhase19VisualQACSSAudit:
    """Audit CSS selectors, design tokens, contrast colors, and typography rules."""

    def test_section_group_headers_scoped_to_main_nav(self):
        """Group headers must be scoped to aria-label='Go to page' to prevent leaking into search."""
        assert 'aria-label="Go to page"] > label:nth-of-type(1)' in CUSTOM_CSS
        assert 'aria-label="Go to page"] > label:nth-of-type(5)' in CUSTOM_CSS
        assert 'aria-label="Go to page"] > label:nth-of-type(10)' in CUSTOM_CSS
        assert 'aria-label="Go to page"] > label:nth-of-type(13)' in CUSTOM_CSS

    def test_lucide_icon_masks_bound_to_values(self):
        """Lucide SVG masks must be bound to input values for search persistence."""
        assert ':has(input[value*="Overview"]) p::before' in CUSTOM_CSS
        assert ':has(input[value*="Dashboard"]) p::before' in CUSTOM_CSS
        assert ':has(input[value*="New Keyword"]) p::before' in CUSTOM_CSS
        assert ':has(input[value*="YouTube Video"]) p::before' in CUSTOM_CSS
        assert ':has(input[value*="Studio Profile"]) p::before' in CUSTOM_CSS

    def test_active_and_focus_state_design_tokens(self):
        """CUSTOM_CSS must include active state and accessibility focus ring tokens."""
        assert "--ks-nav-pill-active: #EFF6FF" in CUSTOM_CSS
        assert "--ks-nav-border-active: #2563EB" in CUSTOM_CSS
        assert "border-left: 3px solid #2563EB" in CUSTOM_CSS
        assert "outline: 2px solid #93C5FD" in CUSTOM_CSS or "*:focus-visible" in CUSTOM_CSS

    def test_reduced_motion_compliance(self):
        """Prefers-reduced-motion media query must suppress all sidebar animations."""
        assert "@media (prefers-reduced-motion: reduce)" in CUSTOM_CSS
        assert "animation-duration: 0.01ms" in CUSTOM_CSS or "transition: none" in CUSTOM_CSS


class TestPhase19FunctionalInteractionAudit:
    """Audit collapse mode toggling, search input filtering, and profile button routing."""

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_every_destination_selectable_via_navigation(self, mock_sidebar):
        """Verifying all 14 destinations can be returned by render_navigation without error."""
        mock_sidebar.text_input.return_value = ""
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False

        for target_page in ALL_NAVIGATION_PAGES:
            mock_sidebar.radio.return_value = target_page
            result = render_navigation(target_page)
            assert result == target_page

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_search_filtering_and_clear_action(self, mock_sidebar):
        """Search query filters destinations, and clear button is available."""
        mock_sidebar.text_input.return_value = "Monitor"
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False
        mock_sidebar.radio.return_value = PAGE_RESEARCH_MONITOR

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_RESEARCH_MONITOR

        # Verify clear button was rendered
        button_keys = [c[1].get("key") for c in mock_sidebar.button.call_args_list if "key" in c[1]]
        assert "clear_nav_search_btn" in button_keys

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {})
    def test_empty_search_reset_action(self, mock_sidebar):
        """Empty search query shows reset button and preserves page."""
        mock_sidebar.text_input.return_value = "unmatched_search_phrase"
        mock_sidebar.toggle.return_value = False
        mock_sidebar.button.return_value = False

        result = render_navigation(PAGE_RESULTS)
        assert result == PAGE_RESULTS

        button_keys = [c[1].get("key") for c in mock_sidebar.button.call_args_list if "key" in c[1]]
        assert "clear_empty_nav_search_btn" in button_keys

    @patch("streamlit.sidebar")
    @patch("streamlit.session_state", {"sidebar_compact_mode": True})
    def test_compact_mode_persists_selection(self, mock_sidebar):
        """Compact mode retains current page selection and injects compact layout CSS."""
        mock_sidebar.text_input.return_value = ""
        mock_sidebar.toggle.return_value = True
        mock_sidebar.button.return_value = False
        mock_sidebar.radio.return_value = PAGE_PRODUCT_PLANNER

        result = render_navigation(PAGE_PRODUCT_PLANNER)
        assert result == PAGE_PRODUCT_PLANNER

        # Verify compact styling was emitted
        markdown_contents = [c[0][0] for c in mock_sidebar.markdown.call_args_list if isinstance(c[0][0], str)]
        assert any("min-width: 80px" in m for m in markdown_contents)
