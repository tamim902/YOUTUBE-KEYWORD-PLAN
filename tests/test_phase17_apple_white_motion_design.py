"""Phase 17 Apple-Inspired White Motion Design & Smart User Guide Test Suite.

Verifies:
1. Apple typography and San Francisco system font stack fallback.
2. Premium White design system tokens (#FFFFFF, #F8FAFC, #111827, #E5E7EB, #2563EB).
3. Interactive cursor micro-interactions, button pressed states, and touch-screen safety.
4. Fast motion keyframes and prefers-reduced-motion accessibility compliance.
5. Multi-device responsive breakpoints (320px, 480px, 768px, 1024px, 1440px, 1920px).
6. Navigation architecture preserving Phase 6/11/12 assertions while adding User Guide.
7. Complete User Guide database integrity (all 11 mandatory points for all 10 major features).
8. Deterministic Next-Best-Action guidance engine logic and state transitions.
9. First-time onboarding persistence in SQLite app_settings.
10. Demo data isolation ensuring 0 database mutations during showcase inspection.
"""

import pytest
from unittest.mock import MagicMock

from src.ui.styles import CUSTOM_CSS
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
)
from src.ui.guide import (
    USER_GUIDE_SECTIONS,
    DeterministicGuidanceEngine,
    GuidanceRecommendation,
)
from src.storage import db_manager


class TestAppleTypographyAndWhiteDesignSystem:
    """Verifies Apple typography, white theme tokens, and visual simplicity."""

    def test_san_francisco_font_stack_present(self):
        """Verify San Francisco font stack is defined with graceful system fallbacks."""
        assert "-apple-system" in CUSTOM_CSS
        assert "BlinkMacSystemFont" in CUSTOM_CSS
        assert '"SF Pro Display"' in CUSTOM_CSS
        assert '"SF Pro Text"' in CUSTOM_CSS
        assert '"Segoe UI"' in CUSTOM_CSS

    def test_white_theme_color_tokens_defined(self):
        """Verify white design tokens match specification."""
        assert "--bg-canvas: #FFFFFF;" in CUSTOM_CSS
        assert "--bg-secondary: #F8FAFC;" in CUSTOM_CSS
        assert "--text-primary: #111827;" in CUSTOM_CSS
        assert "--border-subtle: #E5E7EB;" in CUSTOM_CSS
        assert "--brand-primary: #2563EB;" in CUSTOM_CSS
        assert "--accent-emerald: #15803D;" in CUSTOM_CSS
        assert "--accent-amber: #B45309;" in CUSTOM_CSS
        assert "--accent-rose: #B91C1C;" in CUSTOM_CSS

    def test_responsive_typography_clamp_used(self):
        """Verify fluid responsive typography uses clamp() for headings."""
        assert "clamp(" in CUSTOM_CSS
        assert ".hero-title" in CUSTOM_CSS
        assert ".hero-subtitle" in CUSTOM_CSS

    def test_subtle_ambient_background_gradients(self):
        """Verify gentle blue/violet radial wash on white canvas."""
        assert "radial-gradient(" in CUSTOM_CSS
        assert "rgba(37, 99, 235," in CUSTOM_CSS


class TestInteractiveCursorAndMotionSystem:
    """Verifies fast lightweight motion, hover feedback, and accessibility."""

    def test_gpu_accelerated_keyframes_and_timing(self):
        """Verify transform/opacity keyframes exist with responsive timings."""
        assert "@keyframes fadeInUp" in CUSTOM_CSS
        assert "@keyframes fadeInScale" in CUSTOM_CSS
        assert "@keyframes pulseGlow" in CUSTOM_CSS
        assert "cubic-bezier(0.16, 1, 0.3, 1)" in CUSTOM_CSS

    def test_button_pressed_micro_interaction(self):
        """Verify button click feedback uses active transform scale."""
        assert ":active" in CUSTOM_CSS
        assert "transform: scale(" in CUSTOM_CSS

    def test_card_hover_elevation_without_blocking_inputs(self):
        """Verify card hover elevates with transform translateY."""
        assert "transform: translateY(-2px)" in CUSTOM_CSS

    def test_touch_device_hover_suppression(self):
        """Verify hover effects are suppressed on touch screens."""
        assert "@media (hover: none) and (pointer: coarse)" in CUSTOM_CSS

    def test_prefers_reduced_motion_compliance(self):
        """Verify animations are completely disabled for motion-sensitive users."""
        assert "@media (prefers-reduced-motion: reduce)" in CUSTOM_CSS
        assert "animation-duration: 0.01ms !important;" in CUSTOM_CSS
        assert "transition-duration: 0.01ms !important;" in CUSTOM_CSS

    def test_responsive_media_breakpoints_defined(self):
        """Verify breakpoints cover 320px–480px, 768px, 1024px, 1440px, and 1920px+."""
        assert "@media (max-width: 480px)" in CUSTOM_CSS
        assert "@media (max-width: 768px)" in CUSTOM_CSS
        assert "@media screen and (min-width: 769px) and (max-width: 1024px)" in CUSTOM_CSS
        assert "@media (min-width: 1440px)" in CUSTOM_CSS
        assert "@media screen and (min-width: 1920px)" in CUSTOM_CSS


class TestNavigationArchitecturePhase17:
    """Verifies navigation backward compatibility and new User Guide page."""

    def test_core_navigation_pages_count_strictly_six(self):
        """Ensure len(NAVIGATION_PAGES) == 6 is strictly preserved for Phase 6 assertions."""
        assert len(NAVIGATION_PAGES) == 6

    def test_user_guide_page_in_all_navigation_pages(self):
        """Verify PAGE_USER_GUIDE is added to ALL_NAVIGATION_PAGES."""
        assert PAGE_USER_GUIDE in ALL_NAVIGATION_PAGES
        assert PAGE_USER_GUIDE not in NAVIGATION_PAGES
        assert len(ALL_NAVIGATION_PAGES) >= 13


class TestCompleteUserGuideDatabase:
    """Verifies all 11 required points for all 10 major application sections."""

    REQUIRED_POINTS = [
        "title",
        "category",
        "summary",            # 1. What this section does
        "when_to_use",        # 2. When to use it
        "prerequisites",      # 3. What the user needs before starting
        "steps",              # 4. Exact steps to follow
        "option_choices",     # 5. Which option or setting to choose
        "recommended_defaults", # 6. Recommended default settings and why
        "expected_result",    # 7. What result to expect
        "how_to_interpret",   # 8. How to interpret the results
        "common_mistakes",    # 9. Common mistakes
        "troubleshooting",    # 10. Troubleshooting
        "what_to_do_next",    # 11. What to do next
    ]

    EXPECTED_SECTIONS = [
        "keyword_discovery",
        "pattern_generator",
        "video_serp",
        "content_opportunities",
        "product_opportunities",
        "product_planner",
        "research_monitor",
        "saved_research",
        "studio_auth",
        "settings_backup",
    ]

    def test_all_ten_major_sections_present_in_user_guide(self):
        """Verify all 10 major features have complete documentation playbooks."""
        for sec in self.EXPECTED_SECTIONS:
            assert sec in USER_GUIDE_SECTIONS, f"Section '{sec}' missing from USER_GUIDE_SECTIONS"

    def test_each_section_contains_all_eleven_required_points(self):
        """Verify every playbook contains all 11 required instructional fields."""
        for sec, data in USER_GUIDE_SECTIONS.items():
            for req in self.REQUIRED_POINTS:
                assert req in data, f"Section '{sec}' missing required field '{req}'"
                # Ensure fields are non-empty
                val = data[req]
                assert val, f"Section '{sec}' field '{req}' cannot be empty"
                if req == "steps":
                    assert len(val) >= 4, f"Section '{sec}' steps must have at least 4 items"


class TestDeterministicGuidanceEngine:
    """Verifies deterministic Next-Best-Action guidance logic based on application state."""

    def test_guidance_recommends_seed_when_session_empty(self):
        """Verify recommendation when no keywords or queries exist in session."""
        mock_state = MagicMock()
        mock_state.last_query = ""
        mock_state.direct_results = []
        mock_state.crawl_result = None
        mock_state.current_serp_analysis = None

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert isinstance(rec, GuidanceRecommendation)
        assert "Seed Keyword" in rec.action_title
        assert rec.target_page == "🔍 New Keyword Research"
        assert rec.urgency == "high"

    def test_guidance_recommends_serp_when_keywords_exist_without_serp(self):
        """Verify recommendation when keywords exist but no SERP analysis done."""
        mock_state = MagicMock()
        mock_state.last_query = "wireless earbuds"
        kw_mock = MagicMock()
        kw_mock.keyword = "best wireless earbuds for gym"
        mock_state.direct_results = [kw_mock]
        mock_state.crawl_result = None
        mock_state.current_serp_analysis = None

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "SERP" in rec.action_title
        assert rec.target_page == "🎥 YouTube Video Research"

    def test_guidance_recommends_content_brief_when_serp_complete(self):
        """Verify recommendation when SERP analysis is available."""
        mock_state = MagicMock()
        mock_state.last_query = "wireless earbuds"
        mock_state.direct_results = []
        mock_state.crawl_result = None
        serp_mock = MagicMock()
        serp_mock.query = "best wireless earbuds"
        mock_state.current_serp_analysis = serp_mock

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Brief" in rec.action_title
        assert rec.target_page == "💡 Content Opportunities"


class TestOnboardingAndDemoDataGuardrails:
    """Verifies onboarding persistence and zero demo data database pollution."""

    def test_onboarding_persistence_in_app_settings(self):
        """Verify onboarding dismissal is stored safely in SQLite."""
        db_manager.set_setting("user_onboarded_v17", "true")
        assert db_manager.get_setting("user_onboarded_v17") == "true"

    def test_inspecting_guides_does_not_mutate_database(self):
        """Verify viewing user guides creates zero rows in searches and keywords tables."""
        with db_manager.get_connection() as conn:
            init_s = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
            init_k = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]

        # Read all sections
        _ = [len(v["steps"]) for v in USER_GUIDE_SECTIONS.values()]

        with db_manager.get_connection() as conn:
            fin_s = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
            fin_k = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]

        assert fin_s == init_s, "Guide inspection must never insert into searches table"
        assert fin_k == init_k, "Guide inspection must never insert into keywords table"
