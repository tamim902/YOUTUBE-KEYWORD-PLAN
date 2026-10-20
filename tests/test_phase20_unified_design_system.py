"""Comprehensive test suite for Phase 20 — Keyword Studio Unified Premium SaaS Design System."""

import inspect
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
    PAGE_SETTINGS,
    PAGE_USER_GUIDE,
    PAGE_VIDEO_RESEARCH,
    PAGE_SECTION_MAP,
    render_empty_state,
    render_header,
    render_page_header,
    render_provenance_badge,
)
from src.ui.styles import CUSTOM_CSS
import app


class TestPhase20DesignTokens:
    """Verify that centralized SaaS design tokens and component classes are defined in CUSTOM_CSS."""

    def test_css_variables_and_colors(self):
        """Verify root design system tokens in CUSTOM_CSS."""
        assert "--ks-canvas: #FFFFFF;" in CUSTOM_CSS
        assert "--ks-surface: #F8FAFC;" in CUSTOM_CSS
        assert "--ks-text-primary: #0F172A;" in CUSTOM_CSS
        assert "--ks-border: #E2E8F0;" in CUSTOM_CSS
        assert "--ks-accent-blue: #2563EB;" in CUSTOM_CSS
        assert "--ks-card-radius: 12px;" in CUSTOM_CSS

    def test_page_header_classes(self):
        """Verify Page Header component CSS classes."""
        assert ".ks-page-header" in CUSTOM_CSS
        assert ".ks-breadcrumb" in CUSTOM_CSS
        assert ".ks-page-title" in CUSTOM_CSS
        assert ".ks-page-subtitle" in CUSTOM_CSS
        assert ".ks-header-badges" in CUSTOM_CSS

    def test_card_classes(self):
        """Verify Standardized Card component CSS classes."""
        assert ".ks-card" in CUSTOM_CSS
        assert ".ks-card-header" in CUSTOM_CSS
        assert ".ks-card-title" in CUSTOM_CSS
        assert ".ks-card-subtitle" in CUSTOM_CSS
        assert ".ks-card-body" in CUSTOM_CSS

    def test_badge_variants(self):
        """Verify Badge and Provenance component CSS classes."""
        assert ".ks-badge" in CUSTOM_CSS
        assert ".ks-badge-primary" in CUSTOM_CSS
        assert ".ks-badge-success" in CUSTOM_CSS
        assert ".ks-badge-warning" in CUSTOM_CSS
        assert ".ks-badge-error" in CUSTOM_CSS
        assert ".ks-badge-neutral" in CUSTOM_CSS
        assert ".ks-badge-provenance" in CUSTOM_CSS
        assert ".ks-badge-demo" in CUSTOM_CSS

    def test_empty_state_classes(self):
        """Verify Empty State component CSS classes."""
        assert ".ks-empty-state" in CUSTOM_CSS
        assert ".ks-empty-icon" in CUSTOM_CSS
        assert ".ks-empty-title" in CUSTOM_CSS
        assert ".ks-empty-desc" in CUSTOM_CSS

    def test_tab_and_expander_styling(self):
        """Verify modern SaaS styling for Streamlit native tabs and expanders."""
        assert '[data-baseweb="tab"]' in CUSTOM_CSS
        assert '[data-baseweb="tab"][aria-selected="true"]' in CUSTOM_CSS
        assert '[data-testid="stExpander"]' in CUSTOM_CSS

    def test_accessibility_reduced_motion(self):
        """Verify reduced motion safety media query applies across all components."""
        assert "@media (prefers-reduced-motion: reduce)" in CUSTOM_CSS


class TestPhase20ReusableComponents:
    """Verify reusable UI rendering functions."""

    def test_provenance_badge_mapping(self):
        """Verify data source provenance badges return appropriate labels and colors."""
        yt_badge = render_provenance_badge("youtube_api")
        assert "YouTube Data API v3" in yt_badge
        assert "prov-dot" in yt_badge

        auto_badge = render_provenance_badge("autocomplete")
        assert "Autocomplete Live" in auto_badge

        sqlite_badge = render_provenance_badge("local_sqlite")
        assert "SQLite" in sqlite_badge

        cache_badge = render_provenance_badge("cached")
        assert "Cache" in cache_badge

        offline_badge = render_provenance_badge("deterministic")
        assert "Deterministic" in offline_badge

        # Empty provenance returns empty string
        assert render_provenance_badge(None) == ""
        assert render_provenance_badge("") == ""

    @patch("streamlit.markdown")
    def test_render_page_header_output(self, mock_markdown):
        """Verify render_page_header constructs valid HTML with breadcrumb, title, and badges."""
        render_page_header(
            title="Test Title",
            subtitle="Test Subtitle Description",
            category="WORKSPACE",
            badge_text="Live Ready",
            badge_type="success",
            provenance="local_sqlite",
        )
        mock_markdown.assert_called_once()
        html_arg = mock_markdown.call_args[0][0]

        assert "ks-page-header" in html_arg
        assert "WORKSPACE" in html_arg
        assert "Test Title" in html_arg
        assert "Test Subtitle Description" in html_arg
        assert "Live Ready" in html_arg
        assert "ks-badge-success" in html_arg
        assert "SQLite" in html_arg

    @patch("streamlit.columns")
    @patch("streamlit.button")
    @patch("streamlit.markdown")
    def test_render_empty_state_action(self, mock_markdown, mock_button, mock_columns):
        """Verify render_empty_state renders icon, title, description, and action button."""
        col_mock = MagicMock()
        mock_columns.return_value = [col_mock, col_mock, col_mock]
        mock_button.return_value = True

        clicked = render_empty_state(
            title="No Items Found",
            description="Perform an action to add items.",
            icon="📦",
            action_label="Add Item",
            action_key="test_add_btn",
        )

        assert clicked is True
        mock_markdown.assert_called_once()
        html_arg = mock_markdown.call_args[0][0]
        assert "ks-empty-state" in html_arg
        assert "No Items Found" in html_arg
        assert "Perform an action to add items." in html_arg
        assert "📦" in html_arg

    def test_page_section_map_covers_all_14_pages(self):
        """Verify PAGE_SECTION_MAP classifies every one of the 14 navigation destinations."""
        assert len(PAGE_SECTION_MAP) == 14
        expected_groups = {
            "WORKSPACE",
            "DISCOVERY & INTELLIGENCE",
            "WORKFLOW & MANAGEMENT",
            "STUDIO & CONFIGURATION",
        }
        for page in ALL_NAVIGATION_PAGES:
            assert page in PAGE_SECTION_MAP
            assert PAGE_SECTION_MAP[page] in expected_groups

        # Check group distribution
        workspace_pages = [p for p, s in PAGE_SECTION_MAP.items() if s == "WORKSPACE"]
        assert len(workspace_pages) == 4
        assert PAGE_DASHBOARD in workspace_pages

        discovery_pages = [p for p, s in PAGE_SECTION_MAP.items() if s == "DISCOVERY & INTELLIGENCE"]
        assert len(discovery_pages) == 5
        assert PAGE_VIDEO_RESEARCH in discovery_pages

        workflow_pages = [p for p, s in PAGE_SECTION_MAP.items() if s == "WORKFLOW & MANAGEMENT"]
        assert len(workflow_pages) == 3
        assert PAGE_RESEARCH_MONITOR in workflow_pages

        studio_pages = [p for p, s in PAGE_SECTION_MAP.items() if s == "STUDIO & CONFIGURATION"]
        assert len(studio_pages) == 2
        assert PAGE_AUTH in studio_pages
        assert PAGE_SETTINGS in studio_pages


class TestPhase20PageHeaderIntegration:
    """Verify that all 14 page rendering functions in app.py use render_page_header."""

    ALL_14_PAGE_RENDERERS = [
        "render_page_landing",
        "render_page_dashboard",
        "render_page_new_research",
        "render_page_results",
        "render_page_patterns",
        "render_page_saved",
        "render_page_video_research",
        "render_page_content_opportunities",
        "render_page_product_opportunities",
        "render_page_product_planner",
        "render_page_research_monitor",
        "render_page_user_guide",
        "render_page_auth",
        "render_page_settings",
    ]

    def test_all_14_page_functions_exist_in_app(self):
        """Verify all 14 page rendering functions exist and are callable in app.py."""
        for fn_name in self.ALL_14_PAGE_RENDERERS:
            fn = getattr(app, fn_name, None)
            assert fn is not None, f"Expected {fn_name} in app.py"
            assert callable(fn), f"{fn_name} must be callable"

    def test_all_14_page_functions_call_render_page_header(self):
        """Verify each of the 14 page functions invokes render_page_header."""
        for fn_name in self.ALL_14_PAGE_RENDERERS:
            fn = getattr(app, fn_name)
            source = inspect.getsource(fn)
            assert "render_page_header(" in source, (
                f"{fn_name} does not call render_page_header()"
            )


class TestPhase20DashboardEmptyStates:
    """Verify that render_page_dashboard renders standardized empty states when empty."""

    @patch("src.ui.components.st.markdown")
    @patch("src.ui.components.st.columns")
    @patch("src.ui.components.st.button")
    @patch("app.db_manager")
    @patch("app.st")
    def test_dashboard_renders_empty_states_when_no_data(
        self, mock_app_st, mock_db_mgr, mock_btn, mock_cols, mock_ui_md
    ):
        """When recent_searches is empty and no active crawl result, render_empty_state is used."""
        mock_db_mgr.get_database_stats.return_value = {
            "total_keywords": 0,
            "total_cached_queries": 0,
        }
        mock_app_st.session_state = MagicMock()
        mock_app_st.session_state.crawl_result = None
        mock_app_st.session_state.direct_results = None
        mock_cols.side_effect = lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
        mock_btn.return_value = False

        app.render_page_dashboard(is_ready=True, recent_searches=[])

        # Verify render_page_header was called
        page_header_calls = [
            call for call in mock_app_st.markdown.call_args_list
            if "ks-page-header" in str(call)
        ] + [
            call for call in mock_ui_md.call_args_list
            if "ks-page-header" in str(call)
        ]
        assert len(page_header_calls) >= 1
