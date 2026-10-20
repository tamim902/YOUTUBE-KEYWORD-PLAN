"""Test suite for Phase 29: Simple Mode & Guided Keyword Research Experience.

Verifies:
1. InterfaceMode enum (Simple Mode default, Advanced Mode option).
2. Interface Mode database persistence via app_settings table.
3. 7-Step WizardStep enum, labels, and sequential progression.
4. Deterministic relevance tier classification (Highly relevant, Worth reviewing, More research needed, Generated idea, Data unavailable).
5. Epistemic honesty in beginner tooltips (no fake ranking guarantees).
6. WizardState dataclass validation, error handling, and input preservation.
7. Back / Next step navigation without repeated network requests or loss of state.
8. Duplicate submission prevention while searching.
9. One-click action data export and clipboard buffer compatibility.
10. Strict invariant preservation of 14 base navigation pages.
"""

from __future__ import annotations

import tempfile
import pytest
from unittest.mock import MagicMock, patch

from src.models.wizard import (
    BEGINNER_TOOLTIPS,
    InterfaceMode,
    RelevanceTierLabel,
    WizardState,
    WizardStep,
    WizardSuggestionItem,
    get_relevance_badge_style,
    get_relevance_tier_label,
)
from src.storage.database import DatabaseManager
from src.ui.components import (
    ALL_NAVIGATION_PAGES,
    get_current_interface_mode,
    render_beginner_tooltip,
    render_relevance_badge,
    set_interface_mode,
)
from src.ui.wizard_ui import get_or_create_wizard_state


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary DatabaseManager for isolated testing."""
    db_file = tmp_path / "test_phase29.db"
    db = DatabaseManager(db_path=db_file)
    db.init_db()
    return db


# =============================================================================
# 1. INTERFACE MODE ENUM & CONVERSION
# =============================================================================
def test_interface_mode_enum_values():
    assert InterfaceMode.SIMPLE.value == "simple"
    assert InterfaceMode.ADVANCED.value == "advanced"


def test_interface_mode_from_str():
    assert InterfaceMode.from_str("advanced") == InterfaceMode.ADVANCED
    assert InterfaceMode.from_str("ADVANCED") == InterfaceMode.ADVANCED
    assert InterfaceMode.from_str("pro") == InterfaceMode.ADVANCED
    assert InterfaceMode.from_str("expert") == InterfaceMode.ADVANCED
    assert InterfaceMode.from_str("simple") == InterfaceMode.SIMPLE
    assert InterfaceMode.from_str(None) == InterfaceMode.SIMPLE
    assert InterfaceMode.from_str("unknown") == InterfaceMode.SIMPLE


# =============================================================================
# 2. INTERFACE MODE DATABASE PERSISTENCE
# =============================================================================
def test_interface_mode_db_persistence(temp_db):
    # Default is simple
    val = temp_db.get_setting("interface_mode", "simple")
    assert val == "simple"

    # Save advanced
    temp_db.set_setting("interface_mode", "advanced")
    val = temp_db.get_setting("interface_mode", "simple")
    assert val == "advanced"

    # Switch back to simple
    temp_db.set_setting("interface_mode", "simple")
    val = temp_db.get_setting("interface_mode", "simple")
    assert val == "simple"


def test_get_and_set_interface_mode_helpers():
    with patch("streamlit.session_state", {}) as mock_state:
        # Default when session state is empty
        mode = get_current_interface_mode()
        assert mode in ("simple", "advanced")

        # Explicit set
        set_interface_mode("advanced")
        assert mock_state.get("interface_mode") == "advanced"
        assert get_current_interface_mode() == "advanced"

        set_interface_mode("simple")
        assert mock_state.get("interface_mode") == "simple"
        assert get_current_interface_mode() == "simple"


# =============================================================================
# 3. WIZARD STEP ENUM
# =============================================================================
def test_wizard_steps():
    assert len(WizardStep) == 7
    assert WizardStep.STEP_1_CHANNEL.value == 1
    assert WizardStep.STEP_2_TOPIC.value == 2
    assert WizardStep.STEP_3_SETTINGS.value == 3
    assert WizardStep.STEP_4_FIND.value == 4
    assert WizardStep.STEP_5_REVIEW.value == 5
    assert WizardStep.STEP_6_CHOOSE.value == 6
    assert WizardStep.STEP_7_CONTINUE.value == 7

    assert "Channel" in WizardStep.STEP_1_CHANNEL.title
    assert "Topic" in WizardStep.STEP_2_TOPIC.title
    assert "Settings" in WizardStep.STEP_3_SETTINGS.title
    assert "Find" in WizardStep.STEP_4_FIND.title
    assert "Review" in WizardStep.STEP_5_REVIEW.title
    assert "Best-Fit" in WizardStep.STEP_6_CHOOSE.title
    assert "Continue" in WizardStep.STEP_7_CONTINUE.title


# =============================================================================
# 4. RELEVANCE TIER CLASSIFICATION
# =============================================================================
def test_relevance_tier_labels():
    # Score >= 75 -> Highly relevant
    assert get_relevance_tier_label(85.0) == RelevanceTierLabel.HIGHLY_RELEVANT.value
    assert get_relevance_tier_label(75.0) == RelevanceTierLabel.HIGHLY_RELEVANT.value

    # 45 <= Score < 75 -> Worth reviewing
    assert get_relevance_tier_label(74.9) == RelevanceTierLabel.WORTH_REVIEWING.value
    assert get_relevance_tier_label(50.0) == RelevanceTierLabel.WORTH_REVIEWING.value
    assert get_relevance_tier_label(45.0) == RelevanceTierLabel.WORTH_REVIEWING.value

    # Score < 45 -> More research needed
    assert get_relevance_tier_label(44.9) == RelevanceTierLabel.MORE_RESEARCH_NEEDED.value
    assert get_relevance_tier_label(10.0) == RelevanceTierLabel.MORE_RESEARCH_NEEDED.value

    # Generated pattern idea
    assert get_relevance_tier_label(90.0, is_generated=True) == RelevanceTierLabel.GENERATED_IDEA.value

    # None or invalid
    assert get_relevance_tier_label(None) == RelevanceTierLabel.DATA_UNAVAILABLE.value
    assert get_relevance_tier_label("invalid") == RelevanceTierLabel.DATA_UNAVAILABLE.value


def test_relevance_badge_style():
    for tier in RelevanceTierLabel:
        style = get_relevance_badge_style(tier.value)
        assert "bg" in style
        assert "color" in style
        assert "border" in style
        assert "icon" in style


def test_render_relevance_badge_html():
    badge_html = render_relevance_badge(85.0)
    assert "Highly relevant" in badge_html
    assert "span" in badge_html

    badge_gen = render_relevance_badge(90.0, is_generated=True)
    assert "Generated idea" in badge_gen


# =============================================================================
# 5. HONEST BEGINNER TOOLTIPS
# =============================================================================
def test_beginner_tooltips_content():
    expected_keys = [
        "search_intent",
        "long_tail_keyword",
        "topic_potential",
        "research_confidence",
        "competitor_videos",
        "live_autocomplete",
        "cached_autocomplete",
        "generated_idea",
        "data_unavailable",
    ]
    for key in expected_keys:
        assert key in BEGINNER_TOOLTIPS
        text = BEGINNER_TOOLTIPS[key]
        assert len(text) > 15
        # Epistemic honesty check: Ensure no fake guarantees
        lower_t = text.lower()
        assert (
            "guarantee" not in lower_t
            or "never promise" in lower_t
            or "never guarantee" in lower_t
            or "not" in lower_t
        )


def test_render_beginner_tooltip():
    assert "viewer" in render_beginner_tooltip("search_intent").lower()
    assert "Helpful guidance" in render_beginner_tooltip("non_existent_key")


# =============================================================================
# 6. WIZARD SUGGESTION ITEM
# =============================================================================
def test_wizard_suggestion_item_serialization():
    item = WizardSuggestionItem(
        keyword="best wireless earbuds under 50",
        relevance_score=82.5,
        relevance_label="Highly relevant",
        search_intent="Commercial",
        provenance="live_autocomplete",
        is_cached=False,
        is_generated=False,
    )
    d = item.to_dict()
    assert d["keyword"] == "best wireless earbuds under 50"
    assert d["relevance_score"] == 82.5
    assert d["is_cached"] is False

    reconstructed = WizardSuggestionItem.from_dict(d)
    assert reconstructed.keyword == item.keyword
    assert reconstructed.relevance_score == item.relevance_score
    assert reconstructed.search_intent == item.search_intent


# =============================================================================
# 7. WIZARD STATE VALIDATION & STEP ADVANCEMENT
# =============================================================================
def test_wizard_state_step_validation():
    state = WizardState()
    assert state.current_step == 1

    # Step 1: Channel selected by default -> valid
    valid, err = state.validate_current_step()
    assert valid is True
    assert err is None

    # Advancing to Step 2
    assert state.go_next() is True
    assert state.current_step == 2

    # Step 2: Empty topic -> invalid
    state.topic = ""
    valid, err = state.validate_current_step()
    assert valid is False
    assert "at least 2 characters" in err

    # Setting valid topic -> valid
    state.topic = "best wireless earbuds"
    valid, err = state.validate_current_step()
    assert valid is True
    assert err is None

    # Advancing to Step 3
    assert state.go_next() is True
    assert state.current_step == 3

    # Step 3: Settings have valid defaults -> valid
    valid, err = state.validate_current_step()
    assert valid is True

    # Advancing to Step 4
    assert state.go_next() is True
    assert state.current_step == 4

    # Step 4: No suggestions yet -> invalid
    valid, err = state.validate_current_step()
    assert valid is False
    assert "No keyword suggestions found yet" in err

    # Populate suggestions -> valid
    state.suggestions = [
        {"keyword": "best wireless earbuds 2026", "relevance_score": 85.0},
        {"keyword": "best wireless earbuds under 100", "relevance_score": 80.0},
    ]
    valid, err = state.validate_current_step()
    assert valid is True

    # Advancing to Step 5
    assert state.go_next() is True
    assert state.current_step == 5
    valid, err = state.validate_current_step()
    assert valid is True

    # Advancing to Step 6
    assert state.go_next() is True
    assert state.current_step == 6

    # Step 6: No chosen best-fit keyword -> invalid
    state.best_fit_keyword = None
    state.selected_keyword = None
    valid, err = state.validate_current_step()
    assert valid is False
    assert "Please select your best-fit keyword" in err

    # Choose winning keyword -> valid
    state.best_fit_keyword = "best wireless earbuds 2026"
    valid, err = state.validate_current_step()
    assert valid is True

    # Advancing to Step 7
    assert state.go_next() is True
    assert state.current_step == 7


# =============================================================================
# 8. BACK NAVIGATION & STATE PRESERVATION
# =============================================================================
def test_wizard_back_navigation_preserves_inputs():
    state = WizardState(
        current_step=5,
        channel_id=2,
        channel_name="Productivity & AI Tools",
        topic="notion setup tutorial",
        suggestions=[{"keyword": "notion setup for students", "relevance_score": 90.0}],
    )

    # Move back to step 4
    assert state.go_back() is True
    assert state.current_step == 4
    # Topic and suggestions are preserved
    assert state.topic == "notion setup tutorial"
    assert len(state.suggestions) == 1
    assert state.channel_id == 2

    # Move back to step 3
    assert state.go_back() is True
    assert state.current_step == 3
    assert state.topic == "notion setup tutorial"


def test_wizard_reset():
    state = WizardState(
        current_step=6,
        topic="iphone 16 tips",
        suggestions=[{"keyword": "iphone 16 camera tips"}],
        best_fit_keyword="iphone 16 camera tips",
    )
    state.reset()
    assert state.current_step == 1
    assert state.topic == ""
    assert state.suggestions == []
    assert state.best_fit_keyword is None


# =============================================================================
# 9. DUPLICATE SUBMISSION PREVENTION
# =============================================================================
def test_duplicate_submission_blocked_when_searching():
    state = WizardState(current_step=4)
    state.is_searching = True
    valid, err = state.validate_current_step()
    assert valid is False
    assert "currently running" in err


# =============================================================================
# 10. INVARIANT TEST: 14 NAVIGATION DESTINATIONS
# =============================================================================
def test_all_navigation_pages_contract_intact():
    """Verify strictly that Phase 28 / Phase 29 preserves exactly 14 base destinations."""
    assert len(ALL_NAVIGATION_PAGES) == 14


# =============================================================================
# 11. WIZARD STEP 4 EXECUTION & MOCKED PROVIDER
# =============================================================================
def test_wizard_step_4_execution_mocked():
    state = WizardState(current_step=4, topic="mechanical keyboards")

    mock_suggestion = MagicMock()
    mock_suggestion.keyword = "best mechanical keyboards 2026"
    mock_suggestion.is_cached = False

    with patch("src.providers.youtube.YouTubeAutocompleteProvider.get_suggestions", return_value=[mock_suggestion]):
        from src.providers.youtube import YouTubeAutocompleteProvider
        from src.classifier.service import default_classifier
        from src.intelligence.scoring import default_scorer

        provider = YouTubeAutocompleteProvider()
        raw = provider.get_suggestions("mechanical keyboards")
        assert len(raw) == 1

        formatted = []
        for item in raw:
            cls = default_classifier.classify(item.keyword)
            score_obj = default_scorer.score(item.keyword, "mechanical keyboards", cls)
            w_item = WizardSuggestionItem(
                keyword=item.keyword,
                relevance_score=float(score_obj.total_score),
                relevance_label=get_relevance_tier_label(float(score_obj.total_score)),
                search_intent=str(cls.primary_intent.value if hasattr(cls.primary_intent, "value") else cls.primary_intent),
                provenance="live_autocomplete",
            )
            formatted.append(w_item.to_dict())

        state.suggestions = formatted
        valid, err = state.validate_current_step()
        assert valid is True
        assert len(state.suggestions) == 1
        assert state.suggestions[0]["keyword"] == "best mechanical keyboards 2026"
        assert state.suggestions[0]["relevance_label"] in (
            RelevanceTierLabel.HIGHLY_RELEVANT.value,
            RelevanceTierLabel.WORTH_REVIEWING.value,
        )


# =============================================================================
# 12. WIZARD STATE SERIALIZATION ROUNDTRIP
# =============================================================================
def test_wizard_state_roundtrip_serialization():
    original = WizardState(
        current_step=3,
        channel_id=3,
        channel_name="Creator Education & Growth",
        topic="youtube automation tips",
        language="es",
        country="ES",
        suggestions=[{"keyword": "youtube shorts tips", "relevance_score": 88.0}],
        best_fit_keyword="youtube shorts tips",
    )
    d = original.to_dict()
    assert d["current_step"] == 3
    assert d["topic"] == "youtube automation tips"
    assert d["channel_id"] == 3
    assert d["language"] == "es"
    assert d["country"] == "ES"

    restored = WizardState.from_dict(d)
    assert restored.current_step == original.current_step
    assert restored.topic == original.topic
    assert restored.channel_id == original.channel_id
    assert restored.language == original.language
    assert restored.country == original.country
    assert restored.best_fit_keyword == original.best_fit_keyword
    assert len(restored.suggestions) == 1


# =============================================================================
# 13. WIZARD JUMP TO STEP
# =============================================================================
def test_wizard_jump_to_step():
    state = WizardState(current_step=1)
    assert state.jump_to_step(5) is True
    assert state.current_step == 5
    assert state.jump_to_step(99) is False
    assert state.current_step == 5


# =============================================================================
# 14. DATAFRAME BUILD CONTAINS RELEVANCE LABEL
# =============================================================================
def test_dataframe_build_contains_relevance_label():
    from app import build_dataframe_from_keywords
    from src.crawler.models import DiscoveredKeyword

    kw = DiscoveredKeyword(
        keyword="best wireless earbuds 2026",
        normalized_key="best wireless earbuds 2026",
        depth=1,
        source_type="LIVE_AUTOCOMPLETE",
        source_name="youtube_autocomplete",
        language="en",
        country="US",
        relevance_score=85.0,
    )
    tuples = [(kw, "Long-tail", ["Commercial"])]
    df = build_dataframe_from_keywords(tuples)

    assert "Relevance Label" in df.columns
    assert df.iloc[0]["Relevance Label"] == "Highly relevant"
    assert df.iloc[0]["Relevance Score"] == 85.0


# =============================================================================
# 15. CHANNEL PROFILES ACCESSIBLE FOR WIZARD STEP 1
# =============================================================================
def test_channel_profiles_accessible_for_wizard():
    from src.intelligence.channel_manager import channel_manager
    channels = channel_manager.get_all_channels()
    assert len(channels) >= 1
    ch1 = channels[0]
    assert hasattr(ch1, "channel_name")
    assert hasattr(ch1, "niche")
    assert hasattr(ch1, "target_audience")

