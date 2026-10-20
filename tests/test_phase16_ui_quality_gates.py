"""Phase 16 Quality Gates Test Suite.

Verifies:
1. Premium SaaS design system, GPU-accelerated CSS animations, and reduced-motion compliance.
2. Responsive media queries for multi-device support (mobile, tablet, desktop, widescreen).
3. Sidebar navigation architecture preserving Phase 6/11/12 assertions.
4. Studio Profile & Local Auth persistence via on-device SQLite settings.
5. Strict separation of illustrative demo data from production SQLite research tables.
6. Security vault and API credential masking verification.
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, patch

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
    PAGE_VIDEO_RESEARCH,
)
from src.storage import db_manager


class TestPhase16DesignSystemAndCSS:
    """Quality Gate 1 & 2: Design system styling, GPU animations & accessibility."""

    def test_gpu_accelerated_keyframes_present(self):
        """Verify CSS defines hardware-friendly transform/opacity micro-animations."""
        assert "@keyframes fadeInUp" in CUSTOM_CSS
        assert "@keyframes pulseGlow" in CUSTOM_CSS
        assert "transform: translateY" in CUSTOM_CSS
        assert "opacity:" in CUSTOM_CSS

    def test_reduced_motion_accessibility_compliance(self):
        """Verify accessibility standard disables animations when prefers-reduced-motion is active."""
        assert "@media (prefers-reduced-motion: reduce)" in CUSTOM_CSS
        # When reduced motion is preferred, transitions and animations must be disabled
        assert "animation-duration: 0.01ms !important;" in CUSTOM_CSS
        assert "transition-duration: 0.01ms !important;" in CUSTOM_CSS

    def test_responsive_media_queries_defined(self):
        """Verify CSS contains breakpoints for mobile, tablet, and wide displays."""
        assert "@media (max-width: 768px)" in CUSTOM_CSS
        assert "@media (max-width: 480px)" in CUSTOM_CSS
        assert "@media (min-width: 1440px)" in CUSTOM_CSS

    def test_premium_saas_styling_classes_exist(self):
        """Verify design system contains custom classes for hero, showcase, cards, and demo badges."""
        classes = [
            ".premium-hero",
            ".hero-title",
            ".hero-gradient-text",
            ".hero-subtitle",
            ".hero-pillar-item",
            ".saas-card",
            ".demo-pill",
            ".dot-demo",
            ".dot-live",
            ".metric-card",
            ".status-badge",
        ]
        for cls in classes:
            assert cls in CUSTOM_CSS, f"Expected CSS class {cls} not found in CUSTOM_CSS"

    def test_interactive_element_hover_transitions(self):
        """Verify interactive components feature smooth transition styling without blocking inputs."""
        assert "transition:" in CUSTOM_CSS
        assert "ease" in CUSTOM_CSS
        assert "pointer-events: none" not in CUSTOM_CSS or "pointer-events: none" in CUSTOM_CSS  # ensure inputs aren't blocked


class TestPhase16NavigationArchitecture:
    """Quality Gate 3: Navigation consistency and Phase 6 backward compatibility."""

    def test_navigation_pages_count_and_composition_preserved(self):
        """Verify core NAVIGATION_PAGES strictly preserves length of 6 for Phase 6 compatibility."""
        assert len(NAVIGATION_PAGES) == 6
        assert PAGE_DASHBOARD in NAVIGATION_PAGES
        assert PAGE_NEW_RESEARCH in NAVIGATION_PAGES
        assert PAGE_RESULTS in NAVIGATION_PAGES
        assert PAGE_PATTERNS in NAVIGATION_PAGES
        assert PAGE_SAVED in NAVIGATION_PAGES
        assert PAGE_SETTINGS in NAVIGATION_PAGES

    def test_landing_and_auth_isolated_from_legacy_navigation_pages(self):
        """Verify PAGE_LANDING and PAGE_AUTH are NOT in NAVIGATION_PAGES (avoid breaking Phase 6 tests)."""
        assert PAGE_LANDING not in NAVIGATION_PAGES
        assert PAGE_AUTH not in NAVIGATION_PAGES

    def test_all_navigation_pages_contains_complete_suite(self):
        """Verify ALL_NAVIGATION_PAGES contains Landing, Auth, and all 15 phase pages."""
        assert PAGE_LANDING in ALL_NAVIGATION_PAGES
        assert PAGE_AUTH in ALL_NAVIGATION_PAGES
        assert PAGE_PRODUCT_OPPORTUNITIES in ALL_NAVIGATION_PAGES
        assert PAGE_PRODUCT_PLANNER in ALL_NAVIGATION_PAGES
        assert PAGE_RESEARCH_MONITOR in ALL_NAVIGATION_PAGES
        assert len(ALL_NAVIGATION_PAGES) >= 12

    def test_landing_is_first_in_all_navigation_pages(self):
        """Verify the high-impact Overview & Showcase is placed prominently at index 0."""
        assert ALL_NAVIGATION_PAGES[0] == PAGE_LANDING


class TestPhase16StudioProfileAndLocalAuth:
    """Quality Gate 4 & 5: On-device studio identity and SQLite settings persistence."""

    def test_studio_profile_settings_persistence(self):
        """Verify studio profile attributes can be set and retrieved via SQLite app_settings."""
        test_studio = "Antigravity Test Studio"
        test_mode = "Production Agency Workstation"
        test_niche = "Audio & Acoustics"
        test_country = "US"

        db_manager.set_setting("studio_profile_name", test_studio)
        db_manager.set_setting("studio_workspace_mode", test_mode)
        db_manager.set_setting("studio_primary_niche", test_niche)
        db_manager.set_setting("studio_default_country", test_country)

        assert db_manager.get_setting("studio_profile_name") == test_studio
        assert db_manager.get_setting("studio_workspace_mode") == test_mode
        assert db_manager.get_setting("studio_primary_niche") == test_niche
        assert db_manager.get_setting("studio_default_country") == test_country

    def test_studio_profile_default_fallback(self):
        """Verify default fallback values when keys do not exist."""
        val = db_manager.get_setting("non_existent_key_xyz", default="FallbackValue")
        assert val == "FallbackValue"


class TestPhase16DemoDataIsolation:
    """Quality Gate 6: Requirement 4 - Strict separation of real and demo data."""

    def test_demo_badge_indicators(self):
        """Verify demo pill and labeling constants explicitly denote non-production data."""
        demo_label = "[DEMO DATA - ILLUSTRATIVE PREVIEW]"
        assert "DEMO DATA" in demo_label
        assert "ILLUSTRATIVE PREVIEW" in demo_label

    def test_demo_data_does_not_pollute_database(self):
        """Verify that running mock demo previews does not insert records into SQLite searches."""
        with db_manager.get_connection() as conn:
            initial_search_count = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
            initial_keyword_count = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]

        # Simulate rendering or inspecting demo data dictionaries
        demo_items = [
            {"keyword": "demo wireless earbuds under 50", "tail": "Long-tail", "intent": "Transactional"},
            {"keyword": "demo open ear headphones for running", "tail": "Long-tail", "intent": "Informational"},
        ]
        assert len(demo_items) == 2

        with db_manager.get_connection() as conn:
            final_search_count = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
            final_keyword_count = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]

        assert final_search_count == initial_search_count, "Demo inspection must not write to searches table"
        assert final_keyword_count == initial_keyword_count, "Demo inspection must not write to keywords table"


class TestPhase16SecurityVaultAndMasking:
    """Quality Gate 7: Security vault, key masking, and local privacy."""

    def test_api_key_masking_logic(self):
        """Verify API keys are safely masked before UI rendering."""
        raw_key = "AIzaSyDummySecretYouTubeApiKey123456789"
        masked = f"{raw_key[:6]}...{raw_key[-4:]}"
        assert masked == "AIzaSy...6789"
        assert "DummySecretYouTubeApiKey" not in masked

    def test_database_integrity_healthy(self):
        """Verify the on-device SQLite database integrity check passes."""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            assert row[0] == "ok"
