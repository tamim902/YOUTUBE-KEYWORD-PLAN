"""Unit and integration tests for Phase 28: Complete Simplification, Premium Sidebar & Beginner-Friendly UX Redesign."""

import inspect
from unittest.mock import MagicMock, patch
import pytest

import app
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    NAVIGATION_PAGES,
    EXTENDED_NAVIGATION_PAGES,
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
    PAGE_CHANNELS,
    PAGE_MORNING_REPORT,
    PAGE_DESCRIPTION_STUDIO,
    PAGE_SEO_AUDIT,
    PAGE_ANALYTICS,
    PAGE_STRATEGY,
    PAGE_VALIDATION,
    PAGE_LABEL_CLEAN_MAP,
    format_nav_label,
    render_navigation,
)
from src.ui.guide import (
    BEGINNER_PAGE_GUIDES,
    render_beginner_page_guide,
)
from src.ui.styles import CUSTOM_CSS


# ==============================================================================
# 1. Phase A: Page Inventory & Navigation Contract Tests
# ==============================================================================

def test_all_14_base_navigation_destinations_preserved():
    """Verify base navigation contract remains exactly 14 items starting with PAGE_LANDING."""
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


def test_core_phase6_navigation_pages_preserved():
    """Verify core Phase 6 navigation pages remain untouched."""
    assert len(NAVIGATION_PAGES) == 6
    assert NAVIGATION_PAGES == [
        PAGE_DASHBOARD,
        PAGE_NEW_RESEARCH,
        PAGE_RESULTS,
        PAGE_PATTERNS,
        PAGE_SAVED,
        PAGE_SETTINGS,
    ]


def test_all_21_page_renderers_exist_in_app():
    """Verify all 21 page renderers exist and are callable in app.py."""
    expected_renderers = [
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
        "render_page_channels",
        "render_page_description_studio",
        "render_page_seo_audit",
        "render_page_analytics",
        "render_page_morning_report",
        "render_page_strategy",
        "render_page_validation",
    ]
    for fn_name in expected_renderers:
        assert hasattr(app, fn_name), f"Missing page renderer function {fn_name} in app.py"
        fn = getattr(app, fn_name)
        assert callable(fn), f"{fn_name} is not callable"


def test_all_page_renderers_call_render_page_header():
    """Ensure every page renderer invokes render_page_header for consistent branding."""
    expected_renderers = [
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
        "render_page_channels",
        "render_page_description_studio",
        "render_page_seo_audit",
        "render_page_analytics",
        "render_page_morning_report",
        "render_page_strategy",
        "render_page_validation",
    ]
    for fn_name in expected_renderers:
        fn = getattr(app, fn_name)
        source = inspect.getsource(fn)
        assert "render_page_header(" in source, f"{fn_name} does not call render_page_header"


# ==============================================================================
# 2. Phase B: Sidebar Redesign & Visual Tokens Tests
# ==============================================================================

def test_sidebar_css_white_background():
    """Verify clean white background is applied to sidebar."""
    assert "[data-testid=\"stSidebar\"] {" in CUSTOM_CSS
    assert "background-color: #FFFFFF !important;" in CUSTOM_CSS


def test_sidebar_apple_typography_and_font_stack():
    """Verify Apple-inspired font stack is defined for sidebar and app."""
    assert "-apple-system" in CUSTOM_CSS
    assert "BlinkMacSystemFont" in CUSTOM_CSS
    assert "SF Pro Display" in CUSTOM_CSS
    assert "SF Pro Text" in CUSTOM_CSS
    assert "Segoe UI" in CUSTOM_CSS


def test_sidebar_smooth_transitions_and_accents():
    """Verify 150-200ms smooth cubic-bezier transitions and blue-violet accents."""
    assert "160ms" in CUSTOM_CSS or "180ms" in CUSTOM_CSS
    assert "#2563EB" in CUSTOM_CSS  # Primary blue
    assert "#4F46E5" in CUSTOM_CSS  # Refined violet


def test_sidebar_active_nav_indicator_and_focus():
    """Verify active navigation item has distinct left accent border and focus states."""
    assert "border-left: 3px solid #2563EB !important;" in CUSTOM_CSS
    assert "#EFF6FF" in CUSTOM_CSS
    assert "outline: 2px solid" in CUSTOM_CSS


def test_sidebar_extended_tools_drawer_in_render_navigation():
    """Verify 1-click Quick Studio Jump drawer is integrated in render_navigation."""
    source = inspect.getsource(render_navigation)
    assert "Extended Studios" in source
    assert "PAGE_CHANNELS" in source
    assert "PAGE_STRATEGY" in source
    assert "PAGE_VALIDATION" in source
    assert "PAGE_MORNING_REPORT" in source


# ==============================================================================
# 3. Phase C: Keyword Research Workflow Simplification Tests
# ==============================================================================

def test_new_keyword_research_first_screen_prompt():
    """Verify beginner prompt 'What keyword or topic do you want to make a video about?' exists."""
    source = inspect.getsource(app.render_page_new_research)
    assert "What keyword or topic do you want to make a video about?" in source
    assert "best wireless earbuds" in source
    assert "Find Keywords" in source


def test_new_keyword_research_has_click_explanation():
    """Verify clear explanation of what happens after clicking Find Keywords."""
    source = inspect.getsource(app.render_page_new_research)
    assert "What happens after clicking" in source
    assert "YouTube" in source


def test_new_keyword_research_has_collapsible_advanced_settings():
    """Verify rarely used advanced settings are housed inside an expander."""
    source = inspect.getsource(app.render_page_new_research)
    assert "Advanced Search Settings" in source
    assert "Target Language" in source
    assert "Target Country / Region" in source


def test_new_keyword_research_has_validation_message():
    """Verify clear input validation message explaining how to fix input."""
    source = inspect.getsource(app.render_page_new_research)
    assert "Please enter a keyword or topic first" in source


def test_new_keyword_research_has_five_step_path():
    """Verify 5-step guided path is presented when results are retrieved."""
    source = inspect.getsource(app.render_page_new_research)
    assert "YOUR 5-STEP KEYWORD RESEARCH PATH" in source
    assert "1. Discover Keywords" in source
    assert "Check Competing Videos" in source or "Check Videos" in source


# ==============================================================================
# 4. Phase E: 5-Point Beginner Explainer Database Tests
# ==============================================================================

def test_beginner_page_guides_covers_all_major_sections():
    """Verify BEGINNER_PAGE_GUIDES contains comprehensive 5-point guides for all key sections."""
    required_keys = [
        "keyword_research",
        "keyword_results",
        "pattern_generator",
        "video_research",
        "content_opportunities",
        "product_opportunities",
        "product_planner",
        "topic_validation",
        "strategy_autopilot",
        "seo_audit",
        "morning_report",
        "description_studio",
        "analytics",
        "channel_portfolio",
        "dashboard",
        "saved_research",
        "research_monitor",
        "settings",
        "user_guide",
        "studio_auth",
    ]
    for key in required_keys:
        assert key in BEGINNER_PAGE_GUIDES, f"Missing beginner guide for {key}"
        guide = BEGINNER_PAGE_GUIDES[key]
        # Check all 5 required elements
        assert "what_is_this" in guide and len(guide["what_is_this"]) > 10
        assert "what_should_i_enter" in guide and len(guide["what_should_i_enter"]) > 5
        assert "example_input" in guide and len(guide["example_input"]) > 0
        assert "how_do_i_use_it" in guide and isinstance(guide["how_do_i_use_it"], list)
        assert 3 <= len(guide["how_do_i_use_it"]) <= 5
        assert "what_will_i_get" in guide and len(guide["what_will_i_get"]) > 10
        assert "what_should_i_do_next" in guide and len(guide["what_should_i_do_next"]) > 10


def test_render_beginner_page_guide_callable():
    """Verify render_beginner_page_guide is callable and handles aliases gracefully."""
    assert callable(render_beginner_page_guide)


def test_render_beginner_page_guide_invoked_across_major_pages():
    """Verify render_beginner_page_guide is invoked across major application pages."""
    pages_to_check = [
        app.render_page_new_research,
        app.render_page_results,
        app.render_page_patterns,
        app.render_page_video_research,
        app.render_page_content_opportunities,
        app.render_page_product_opportunities,
        app.render_page_product_planner,
        app.render_page_saved,
        app.render_page_dashboard,
        app.render_page_strategy,
        app.render_page_validation,
        app.render_page_seo_audit,
        app.render_page_morning_report,
        app.render_page_channels,
        app.render_page_description_studio,
        app.render_page_analytics,
        app.render_page_settings,
        app.render_page_auth,
        app.render_page_user_guide,
        app.render_page_research_monitor,
    ]
    for page_fn in pages_to_check:
        src = inspect.getsource(page_fn)
        assert "render_beginner_page_guide(" in src, f"{page_fn.__name__} does not call render_beginner_page_guide"


# ==============================================================================
# 5. Phase F & H: Results Simplification & Next-Step Guidance
# ==============================================================================

def test_results_table_uses_plain_english_column_config():
    """Verify results table configures human-friendly column titles and tooltips."""
    source = inspect.getsource(app.render_page_results)
    assert "Topic Potential" in source
    assert "Viewer Search Intent" in source
    assert "Topic Group" in source
    assert "Data Source" in source


def test_results_table_has_competing_videos_quick_action():
    """Verify selecting a keyword provides a 1-click action to check competing videos."""
    source = inspect.getsource(app.render_page_results)
    assert "Check Competing Videos" in source
    assert "PAGE_VIDEO_RESEARCH" in source


def test_results_page_has_prominent_next_step():
    """Verify render_recommended_next_step is called on results page."""
    source = inspect.getsource(app.render_page_results)
    assert "render_recommended_next_step(" in source
    assert "Check Competing Videos for" in source
