"""Phase 17 Smart Onboarding, Interactive Guided Tours & Guided Workflows Test Suite.

Verifies:
1. 7-Goal First-Run Onboarding Engine with tailored starting workflows and persistence.
2. Interactive Guided Tours for all 6 major sections (Next/Back/Skip/Finish controls and element callouts).
3. 3 Structured Smart Workflow Plans (Keyword 7-step, Niche 9-step, Competitor 6-step) with real-condition tracking.
4. Deterministic Next-Best-Action guidance engine covering all context scenarios (empty seed, SERP, quota, coverage, etc.).
5. Guidance preferences reset safety ensuring 0 deletion of searches, keywords, or configurations.
6. Complete User Guide playbook integrity covering all required points across all 10 major sections.
"""

import pytest
from unittest.mock import MagicMock

from src.storage import db_manager
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    NAVIGATION_PAGES,
    PAGE_AUTH,
    PAGE_CONTENT_OPPORTUNITIES,
    PAGE_DASHBOARD,
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
    INTERACTIVE_TOURS,
    ONBOARDING_GOALS,
    USER_GUIDE_SECTIONS,
    WORKFLOW_PLANS,
    DeterministicGuidanceEngine,
    GuidanceRecommendation,
    reset_guidance_preferences,
)


class TestFirstRunOnboarding:
    """Verifies 7-Goal First-Run Onboarding Engine."""

    EXPECTED_GOALS = [
        "keywords",
        "niche",
        "product_gaps",
        "competitor_serp",
        "video_topics",
        "content_brief",
        "export_reports",
    ]

    def test_all_seven_goals_defined_with_required_metadata(self):
        """Verify all 7 distinct user goals are present with complete metadata."""
        assert len(ONBOARDING_GOALS) == 7
        for goal_key in self.EXPECTED_GOALS:
            assert goal_key in ONBOARDING_GOALS, f"Missing goal '{goal_key}'"
            goal = ONBOARDING_GOALS[goal_key]
            assert goal.get("title"), f"Goal '{goal_key}' missing title"
            assert goal.get("icon"), f"Goal '{goal_key}' missing icon"
            assert goal.get("description"), f"Goal '{goal_key}' missing description"
            assert goal.get("target_page"), f"Goal '{goal_key}' missing target_page"
            assert goal.get("workflow_key"), f"Goal '{goal_key}' missing workflow_key"
            assert goal.get("badge"), f"Goal '{goal_key}' missing badge"
            assert len(goal.get("steps", [])) >= 4, f"Goal '{goal_key}' must have >= 4 steps"

    def test_onboarding_target_pages_are_valid(self):
        """Verify all target pages resolve to existing registered application pages."""
        for goal_key, goal in ONBOARDING_GOALS.items():
            target = goal["target_page"]
            assert target in ALL_NAVIGATION_PAGES, f"Target page '{target}' for goal '{goal_key}' is not in ALL_NAVIGATION_PAGES"

    def test_onboarding_persistence_in_app_settings(self):
        """Verify onboarding goal and completion persist in SQLite app_settings."""
        db_manager.set_setting("selected_onboarding_goal", "product_gaps")
        db_manager.set_setting("user_onboarded_v17", "true")

        assert db_manager.get_setting("selected_onboarding_goal") == "product_gaps"
        assert db_manager.get_setting("user_onboarded_v17") == "true"


class TestInteractiveGuidedTours:
    """Verifies Contextual Guided Tours for all 6 major sections."""

    EXPECTED_TOURS = [
        "keyword_studio",
        "video_serp",
        "product_opportunities",
        "content_opportunities",
        "product_planner",
        "research_monitor",
    ]

    REQUIRED_STEP_FIELDS = [
        "step_num",
        "element_title",
        "selector_ref",
        "what_it_does",
        "when_to_use",
        "recommended_choice",
        "what_happens_after",
        "what_to_do_next",
    ]

    def test_all_six_section_tours_defined(self):
        """Verify all 6 major application sections have interactive tours."""
        assert len(INTERACTIVE_TOURS) == 6
        for tour_id in self.EXPECTED_TOURS:
            assert tour_id in INTERACTIVE_TOURS, f"Tour '{tour_id}' missing from INTERACTIVE_TOURS"

    def test_every_tour_has_at_least_four_instructional_steps(self):
        """Verify every tour has at least 4 detailed walkthrough steps."""
        for tour_id, tour in INTERACTIVE_TOURS.items():
            steps = tour.get("steps", [])
            assert len(steps) >= 4, f"Tour '{tour_id}' has {len(steps)} steps; expected >= 4"

    def test_each_tour_step_contains_all_required_guidance_fields(self):
        """Verify each step provides element explanations, recommended options, and next actions."""
        for tour_id, tour in INTERACTIVE_TOURS.items():
            for idx, step in enumerate(tour["steps"], 1):
                for field in self.REQUIRED_STEP_FIELDS:
                    assert field in step, f"Tour '{tour_id}' step {idx} missing field '{field}'"
                    assert step[field], f"Tour '{tour_id}' step {idx} field '{field}' cannot be empty"

    def test_tour_completion_state_persistence(self):
        """Verify tour completion state is stored and retrieved in SQLite settings."""
        test_tour = "keyword_studio"
        key = f"tour_completed_{test_tour}"
        db_manager.set_setting(key, "true")
        assert db_manager.get_setting(key) == "true"


class TestSmartWorkflowPlansAndRealConditionTracking:
    """Verifies 3 Structured Smart Workflow Plans and condition evaluators."""

    def test_three_workflow_plans_defined_with_exact_step_counts(self):
        """Verify Keyword (7 steps), Niche (9 steps), and Competitor (6 steps) workflows exist."""
        assert "keywords" in WORKFLOW_PLANS
        assert "niche_products" in WORKFLOW_PLANS
        assert "competitors" in WORKFLOW_PLANS

        assert len(WORKFLOW_PLANS["keywords"]["steps"]) == 7, "Keyword workflow must have exactly 7 steps"
        assert len(WORKFLOW_PLANS["niche_products"]["steps"]) == 9, "Niche product workflow must have exactly 9 steps"
        assert len(WORKFLOW_PLANS["competitors"]["steps"]) == 6, "Competitor workflow must have exactly 6 steps"

    def test_workflow_steps_have_complete_instructional_playbooks(self):
        """Verify each step contains prerequisites, recommended settings, expected outputs, and mistakes."""
        required_keys = [
            "id",
            "title",
            "description",
            "prerequisites",
            "recommended_defaults",
            "expected_output",
            "common_mistakes",
            "target_page",
            "evaluator",
        ]
        for wf_key, plan in WORKFLOW_PLANS.items():
            for step in plan["steps"]:
                for rk in required_keys:
                    assert rk in step, f"Workflow '{wf_key}' step '{step.get('id')}' missing key '{rk}'"
                assert callable(step["evaluator"]), f"Workflow '{wf_key}' step '{step['id']}' evaluator must be callable"

    def test_workflow_evaluator_evaluates_actual_data_not_page_visits(self):
        """Verify that steps are only completed when actual data conditions are met, never on page views."""
        mock_state = MagicMock()
        mock_state.last_query = ""
        mock_state.direct_results = []
        mock_state.crawl_result = None
        mock_state.current_serp_analysis = None

        mock_db = MagicMock()
        mock_db.get_recent_searches.return_value = []

        step_seed = WORKFLOW_PLANS["keywords"]["steps"][0]
        step_expand = WORKFLOW_PLANS["keywords"]["steps"][1]
        step_serp = WORKFLOW_PLANS["keywords"]["steps"][3]

        # 1. Initially all False
        assert step_seed["evaluator"](mock_state, mock_db, ready=True) is False
        assert step_expand["evaluator"](mock_state, mock_db, ready=True) is False
        assert step_serp["evaluator"](mock_state, mock_db, ready=True) is False

        # 2. Add real query -> Seed step turns True
        mock_state.last_query = "mechanical keyboard"
        assert step_seed["evaluator"](mock_state, mock_db, ready=True) is True
        assert step_expand["evaluator"](mock_state, mock_db, ready=True) is False

        # 3. Add autocomplete results -> Expand step turns True
        kw_mock = MagicMock()
        kw_mock.tail_length = "Long-tail"
        mock_state.direct_results = [kw_mock]
        assert step_expand["evaluator"](mock_state, mock_db, ready=True) is True

        # 4. Add SERP analysis -> SERP step turns True
        mock_state.current_serp_analysis = MagicMock()
        assert step_serp["evaluator"](mock_state, mock_db, ready=True) is True


class TestDeterministicGuidanceEngineContextAware:
    """Verifies Deterministic Next-Best-Action guidance engine under multiple session scenarios."""

    def test_guidance_recommends_seed_for_empty_session(self):
        """Verify seed recommendation when session is empty."""
        mock_state = MagicMock()
        mock_state.last_query = ""
        mock_state.direct_results = []
        mock_state.crawl_result = None
        mock_state.current_serp_analysis = None
        mock_state.provider_quota_exhausted = False
        mock_state.unverified_products_count = 0
        mock_state.research_coverage_pct = 100
        mock_state.planner_shortlist_count = 0

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Seed Keyword" in rec.action_title
        assert rec.target_page == PAGE_NEW_RESEARCH
        assert rec.urgency == "high"

    def test_guidance_recommends_quota_fallback_when_quota_exhausted(self):
        """Verify public scraper recommendation when provider quota is exhausted."""
        mock_state = MagicMock()
        mock_state.last_query = "wireless earbuds"
        mock_state.direct_results = [MagicMock()]
        mock_state.current_serp_analysis = None
        mock_state.provider_quota_exhausted = True
        mock_state.unverified_products_count = 0
        mock_state.research_coverage_pct = 100
        mock_state.planner_shortlist_count = 0

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Public Scraper Fallback" in rec.action_title
        assert rec.target_page == PAGE_SETTINGS
        assert rec.urgency == "high"

    def test_guidance_recommends_serp_when_keywords_exist_without_serp(self):
        """Verify SERP inspection recommendation when keywords exist."""
        mock_state = MagicMock()
        mock_state.last_query = "wireless earbuds"
        kw = MagicMock()
        kw.keyword = "best wireless earbuds for gym"
        mock_state.direct_results = [kw]
        mock_state.crawl_result = None
        mock_state.current_serp_analysis = None
        mock_state.provider_quota_exhausted = False
        mock_state.unverified_products_count = 0
        mock_state.research_coverage_pct = 100
        mock_state.planner_shortlist_count = 0

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "SERP" in rec.action_title
        assert rec.target_page == PAGE_VIDEO_RESEARCH
        assert rec.urgency == "high"

    def test_guidance_recommends_product_verification_when_unverified_items_exist(self):
        """Verify identity verification recommendation when products are unverified."""
        mock_state = MagicMock()
        mock_state.last_query = "mechanical keyboard"
        mock_state.direct_results = [MagicMock()]
        mock_state.current_serp_analysis = MagicMock()
        mock_state.provider_quota_exhausted = False
        mock_state.unverified_products_count = 4
        mock_state.research_coverage_pct = 100
        mock_state.planner_shortlist_count = 0

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Verify Extracted Product Identities" in rec.action_title
        assert rec.target_page == PAGE_PRODUCT_OPPORTUNITIES
        assert rec.urgency == "high"

    def test_guidance_recommends_coverage_expansion_when_coverage_low(self):
        """Verify coverage expansion recommendation when query coverage is below 30%."""
        mock_state = MagicMock()
        mock_state.last_query = "espresso machine"
        mock_state.direct_results = [MagicMock()]
        mock_state.current_serp_analysis = MagicMock()
        mock_state.provider_quota_exhausted = False
        mock_state.unverified_products_count = 0
        mock_state.research_coverage_pct = 20
        mock_state.planner_shortlist_count = 0

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Expand Query Budget" in rec.action_title
        assert rec.target_page == PAGE_PRODUCT_OPPORTUNITIES

    def test_guidance_recommends_affiliate_planner_when_shortlist_ready(self):
        """Verify affiliate planner recommendation when shortlist products exist."""
        mock_state = MagicMock()
        mock_state.last_query = "espresso machine"
        mock_state.direct_results = [MagicMock()]
        mock_state.current_serp_analysis = MagicMock()
        mock_state.provider_quota_exhausted = False
        mock_state.unverified_products_count = 0
        mock_state.research_coverage_pct = 100
        mock_state.planner_shortlist_count = 3

        rec = DeterministicGuidanceEngine.evaluate_state(mock_state, is_ready=True)
        assert "Affiliate Rates" in rec.action_title
        assert rec.target_page == PAGE_PRODUCT_PLANNER


class TestGuidancePreferencesResetSafety:
    """Verifies that reset_guidance_preferences cleans tour preferences while preserving research data."""

    def test_reset_guidance_preferences_clears_tours_and_onboarding(self):
        """Verify resetting guidance clears tour flags and onboarding state."""
        db_manager.set_setting("tour_completed_keyword_studio", "true")
        db_manager.set_setting("tour_completed_video_serp", "true")
        db_manager.set_setting("user_onboarded_v17", "true")
        db_manager.set_setting("selected_onboarding_goal", "keywords")

        res = reset_guidance_preferences()
        assert res["status"] == "success"

        assert db_manager.get_setting("tour_completed_keyword_studio") is None
        assert db_manager.get_setting("tour_completed_video_serp") is None
        assert db_manager.get_setting("user_onboarded_v17") is None
        assert db_manager.get_setting("selected_onboarding_goal") is None

    def test_reset_guidance_preserves_searches_and_historical_data(self):
        """Verify resetting guidance leaves search queries and database records 100% untouched."""
        # Insert test search
        search_id = db_manager.save_search(
            seed_keyword="keyboard switches guide",
            language="en",
            country="US",
            max_depth=1,
            request_budget=10,
            total_results=12,
        )
        assert search_id is not None

        # Reset guidance preferences
        reset_guidance_preferences()

        # Verify search record is still intact
        recent = db_manager.get_recent_searches(limit=10)
        found = any(s.get("seed_keyword") == "keyboard switches guide" for s in recent)
        assert found, "Resetting guidance must never delete user search history!"


class TestUserGuidePlaybookThoroughness:
    """Verifies extended documentation fields across all 10 major feature playbooks."""

    def test_all_ten_sections_contain_extended_instructional_points(self):
        """Verify metric_explanations, interpreting_zero_results, and export_and_saving."""
        for sec_key, sec in USER_GUIDE_SECTIONS.items():
            assert "metric_explanations" in sec, f"Section '{sec_key}' missing metric_explanations"
            assert isinstance(sec["metric_explanations"], dict), f"Section '{sec_key}' metric_explanations must be dict"
            assert "interpreting_zero_results" in sec, f"Section '{sec_key}' missing interpreting_zero_results"
            assert sec["interpreting_zero_results"], f"Section '{sec_key}' interpreting_zero_results cannot be empty"
            assert "export_and_saving" in sec, f"Section '{sec_key}' missing export_and_saving"
            assert sec["export_and_saving"], f"Section '{sec_key}' export_and_saving cannot be empty"
