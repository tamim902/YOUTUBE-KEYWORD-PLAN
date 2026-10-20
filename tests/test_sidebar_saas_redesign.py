"""Tests for Keyword Studio Premium SaaS Sidebar Redesign."""

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


class TestSidebarPreservationAndIntegrity:
    """Verify backward compatibility and navigation constants preservation."""

    def test_core_phase6_navigation_pages_preserved(self):
        """Core Phase 6 navigation pages must remain exactly 6 items."""
        assert len(NAVIGATION_PAGES) == 6
        assert NAVIGATION_PAGES == [
            PAGE_DASHBOARD,
            PAGE_NEW_RESEARCH,
            PAGE_RESULTS,
            PAGE_PATTERNS,
            PAGE_SAVED,
            PAGE_SETTINGS,
        ]

    def test_all_navigation_pages_count_and_order(self):
        """ALL_NAVIGATION_PAGES must have exactly 14 pages starting with PAGE_LANDING."""
        assert len(ALL_NAVIGATION_PAGES) == 14
        assert ALL_NAVIGATION_PAGES[0] == PAGE_LANDING
        assert ALL_NAVIGATION_PAGES[1] == PAGE_DASHBOARD
        assert ALL_NAVIGATION_PAGES[2] == PAGE_NEW_RESEARCH
        assert ALL_NAVIGATION_PAGES[3] == PAGE_RESULTS
        assert ALL_NAVIGATION_PAGES[4] == PAGE_PATTERNS
        assert ALL_NAVIGATION_PAGES[5] == PAGE_VIDEO_RESEARCH
        assert ALL_NAVIGATION_PAGES[6] == PAGE_CONTENT_OPPORTUNITIES
        assert ALL_NAVIGATION_PAGES[7] == PAGE_PRODUCT_OPPORTUNITIES
        assert ALL_NAVIGATION_PAGES[8] == PAGE_PRODUCT_PLANNER
        assert ALL_NAVIGATION_PAGES[9] == PAGE_RESEARCH_MONITOR
        assert ALL_NAVIGATION_PAGES[10] == PAGE_SAVED
        assert ALL_NAVIGATION_PAGES[11] == PAGE_USER_GUIDE
        assert ALL_NAVIGATION_PAGES[12] == PAGE_AUTH
        assert ALL_NAVIGATION_PAGES[13] == PAGE_SETTINGS
        assert PAGE_SERP == PAGE_VIDEO_RESEARCH


class TestSidebarCleanLabelsAndFormatting:
    """Verify human-readable emoji-free labels for clean SaaS typography."""

    def test_clean_label_mapping_completeness(self):
        """Every page in ALL_NAVIGATION_PAGES must have a clean SaaS label."""
        for page in ALL_NAVIGATION_PAGES:
            assert page in PAGE_LABEL_CLEAN_MAP
            clean_label = PAGE_LABEL_CLEAN_MAP[page]
            assert isinstance(clean_label, str)
            assert len(clean_label) > 0
            # Clean labels should not start with emoji
            assert not any(clean_label.startswith(char) for char in ["✨", "📊", "🔍", "📋", "🧩", "🎥", "💡", "📦", "🏷️", "📡", "💾", "📖", "🔐", "⚙️"])

    def test_format_nav_label_function(self):
        """format_nav_label converts raw constant to clean typography and handles unknown keys."""
        assert format_nav_label(PAGE_LANDING) == "Overview & Showcase"
        assert format_nav_label(PAGE_DASHBOARD) == "Dashboard"
        assert format_nav_label(PAGE_AUTH) == "Studio Profile & Auth"
        assert format_nav_label("UNKNOWN_PAGE") == "UNKNOWN_PAGE"


class TestSidebarDesignSystemCSS:
    """Verify CSS selectors and Apple-inspired SaaS styling rules in CUSTOM_CSS."""

    def test_sidebar_brand_header_styles(self):
        """CUSTOM_CSS must include polished brand header styling."""
        assert ".ks-sidebar-header" in CUSTOM_CSS
        assert ".ks-brand-badge" in CUSTOM_CSS
        assert ".ks-brand-icon" in CUSTOM_CSS
        assert ".ks-brand-title" in CUSTOM_CSS
        assert ".ks-pro-tag" in CUSTOM_CSS
        assert ".ks-sidebar-divider" in CUSTOM_CSS

    def test_radio_to_saas_navigation_overhaul(self):
        """CUSTOM_CSS must hide native radio circles and style items as SaaS nav pills."""
        assert 'label[data-baseweb="radio"] > div:first-of-type' in CUSTOM_CSS
        assert 'label[data-baseweb="radio"]:has(input:checked)' in CUSTOM_CSS
        assert "#EFF6FF" in CUSTOM_CSS  # Light blue active background
        assert "#2563EB" in CUSTOM_CSS  # Primary blue accent
        assert "border-left: 3px solid #2563EB" in CUSTOM_CSS

    def test_four_navigation_group_headers_in_css(self):
        """CUSTOM_CSS must define the 4 section group headers via pseudo-elements."""
        assert "WORKSPACE" in CUSTOM_CSS
        assert "DISCOVERY & INTELLIGENCE" in CUSTOM_CSS
        assert "WORKFLOW & MANAGEMENT" in CUSTOM_CSS
        assert "STUDIO & CONFIGURATION" in CUSTOM_CSS

    def test_lucide_svg_masks_in_css(self):
        """CUSTOM_CSS must define SVG vector masks for icons across all 14 navigation items."""
        assert "-webkit-mask-image" in CUSTOM_CSS
        assert "mask-image" in CUSTOM_CSS
        # Verify specific Lucide icon references
        assert "data:image/svg+xml" in CUSTOM_CSS
        assert "viewBox='0 0 24 24'" in CUSTOM_CSS

    def test_bottom_workspace_card_styles(self):
        """CUSTOM_CSS must style the bottom workspace card and status indicators."""
        assert ".sidebar-workspace-card" in CUSTOM_CSS
        assert ".workspace-avatar" in CUSTOM_CSS
        assert ".workspace-name" in CUSTOM_CSS
        assert ".workspace-status-badge" in CUSTOM_CSS
        assert ".status-dot" in CUSTOM_CSS
        assert "SQLite WAL (Local)" in CUSTOM_CSS or ".workspace-detail-row" in CUSTOM_CSS


class TestRenderNavigationFunction:
    """Verify render_navigation execution, defaults, and routing."""

    @patch("streamlit.sidebar")
    def test_render_navigation_default(self, mock_sidebar):
        """render_navigation should render brand header, radio, and card."""
        mock_sidebar.radio.return_value = PAGE_DASHBOARD
        mock_sidebar.button.return_value = False

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_DASHBOARD
        assert mock_sidebar.markdown.call_count >= 2
        mock_sidebar.radio.assert_called_once()
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["options"] == ALL_NAVIGATION_PAGES
        assert radio_kwargs["index"] == 0
        assert radio_kwargs["format_func"] == format_nav_label

    @patch("streamlit.sidebar")
    def test_render_navigation_invalid_page_fallback(self, mock_sidebar):
        """Invalid current_page should gracefully fallback to PAGE_LANDING (index 0)."""
        mock_sidebar.radio.return_value = PAGE_LANDING
        mock_sidebar.button.return_value = False

        result = render_navigation("INVALID_PAGE_KEY")
        assert result == PAGE_LANDING
        radio_kwargs = mock_sidebar.radio.call_args[1]
        assert radio_kwargs["index"] == 0

    @patch("streamlit.sidebar")
    def test_render_navigation_profile_button_routing(self, mock_sidebar):
        """Clicking profile button in workspace card should route to PAGE_AUTH."""
        mock_sidebar.radio.return_value = PAGE_LANDING
        mock_sidebar.button.return_value = True  # User clicked profile button

        result = render_navigation(PAGE_LANDING)
        assert result == PAGE_AUTH
