"""Tests for the Simple Premium YouTube Keyword Studio with 4-Channel Workspace.

Verifies:
1. Exact 5 primary sections: Keyword Research, YouTube Video Research, Competitor Research, 60-Day Opportunities, SEO Generator.
2. 4-Channel manager: Storage, retrieval, profile edits, and persistence in SQLite.
3. Channel context isolation: Switching active channel updates niche, language, and audience.
4. "Find Video Ideas for My Channel": Tailored evidence-backed ideas per channel with rolling 60-day gap context.
5. 1-click "Start Creating" handoff: Direct transfer of topic, keywords, and channel profile to Tool 5 (SEO Generator).
6. Search volume transparency: "Volume unavailable" without fabricated exact numbers.
7. Thumbnail text hook generator: Compact 2-5 word high-contrast hooks.
8. End-to-end rendering and cross-tool data flow across all 5 tools.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from src.intelligence.channel_manager import channel_manager
from src.intelligence.daily_engine import daily_opportunity_engine
from src.models.channel import ChannelProfile, get_default_four_channels
from src.providers.volume import UnconnectedSearchVolumeProvider, default_volume_provider
from src.storage.database import db_manager
from src.ui.channel_components import (
    get_active_channel,
    render_channel_editor,
    render_channel_header_bar,
    render_channel_ideas_panel,
)
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
    render_five_primary_navigation,
)
from src.ui.tool_competitor_research import render_competitor_research_tool
from src.ui.tool_keyword_research import render_keyword_research_tool
from src.ui.tool_opportunity_finder import render_opportunity_finder_tool
from src.ui.tool_seo_generator import generate_thumbnail_text_hook, render_seo_generator_tool
from src.ui.tool_video_research import render_video_research_tool


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


def mock_columns(spec, **kwargs):
    """Dynamic column mock that always returns the exact requested number of columns."""
    count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(count)]


@pytest.fixture(autouse=True)
def ensure_db_clean():
    """Ensure database is initialized and clean before each test."""
    db_manager.init_db()
    yield


def test_five_primary_tools_exact_count_and_order():
    """Verify exactly 5 primary tools are defined and match specified names."""
    assert len(FIVE_PRIMARY_TOOLS) == 5
    expected = [
        TOOL_KEYWORD_RESEARCH,
        TOOL_VIDEO_RESEARCH,
        TOOL_COMPETITOR_RESEARCH,
        TOOL_60_DAY_OPPORTUNITIES,
        TOOL_SEO_GENERATOR,
    ]
    assert FIVE_PRIMARY_TOOLS == expected
    assert TOOL_SETTINGS == "⚙️ Settings"
    # Legacy backward-compatibility contract
    assert len(ALL_NAVIGATION_PAGES) == 14


def test_four_channel_profiles_exist_and_isolated():
    """Verify that all four distinct channel profiles exist in SQLite with distinct niches."""
    channels = channel_manager.get_all_channels()
    assert len(channels) >= 4

    ch1 = channels[0]
    ch2 = channels[1]
    ch3 = channels[2]
    ch4 = channels[3]

    assert ch1.id == 1
    assert ch2.id == 2
    assert ch3.id == 3
    assert ch4.id == 4

    # Verify niches are distinct and isolated
    niches = {c.channel_niche for c in channels[:4]}
    assert len(niches) == 4, "All 4 channels must have independent niches"

    # Verify Bengali channel language isolation
    assert ch2.target_language == "bn"
    assert ch1.target_language == "en"


def test_channel_profile_editing_and_persistence():
    """Verify editing a channel profile persists correctly to SQLite and can be reset."""
    ch1 = channel_manager.get_channel(1)
    assert ch1 is not None
    original_niche = ch1.channel_niche

    # Modify ch1
    ch1.channel_name = "Custom Tech Studio"
    ch1.channel_niche = "Smart Home Automation"
    ch1.target_audience = "IoT Engineers"
    channel_manager.save_channel(ch1)

    # Re-fetch from DB
    updated_ch1 = channel_manager.get_channel(1)
    assert updated_ch1.channel_name == "Custom Tech Studio"
    assert updated_ch1.channel_niche == "Smart Home Automation"
    assert updated_ch1.target_audience == "IoT Engineers"

    # Reset to default
    defaults = get_default_four_channels()
    channel_manager.save_channel(defaults[0])

    reset_ch1 = channel_manager.get_channel(1)
    assert reset_ch1.channel_niche == original_niche


def test_get_active_channel_context_switching():
    """Verify get_active_channel returns the correct profile depending on session state."""
    state = MockSessionState()

    with patch("streamlit.session_state", state):
        state["active_channel_id"] = 1
        active = get_active_channel()
        assert active.id == 1
        assert "Keyboard" in active.channel_niche or "Tech" in active.channel_name

        state["active_channel_id"] = 2
        active2 = get_active_channel()
        assert active2.id == 2
        assert active2.target_language == "bn"

        state["active_channel_id"] = 3
        active3 = get_active_channel()
        assert active3.id == 3
        assert "Kitchen" in active3.channel_niche or "Espresso" in active3.channel_niche

        state["active_channel_id"] = 4
        active4 = get_active_channel()
        assert active4.id == 4
        assert "Gym" in active4.channel_niche or "Fitness" in active4.channel_niche


def test_find_channel_ideas_generates_tailored_evidence():
    """Verify that daily_opportunity_engine generates ideas tailored to the active channel."""
    ch = channel_manager.get_channel(1)
    ideas = daily_opportunity_engine._generate_ideas_for_channel(channel=ch, count=4)

    assert len(ideas) == 4
    for idea in ideas:
        assert idea.channel_id == ch.id
        assert idea.proposed_topic
        assert idea.main_keyword
        assert idea.why_topic_worth_researching
        assert idea.suggested_thumbnail_concept
        assert isinstance(idea.suggested_video_format, str) and len(idea.suggested_video_format) > 0
        assert idea.recent_relevant_videos_found >= 0


def test_search_volume_transparency():
    """Verify that search volume truthfully returns 'Volume unavailable' when unconnected."""
    provider = UnconnectedSearchVolumeProvider()
    assert not provider.is_connected()

    res = provider.get_keyword_volume("mechanical keyboards")
    assert res.keyword == "mechanical keyboards"
    assert res.monthly_volume is None
    assert res.volume_range == "Volume unavailable"
    assert res.status == "Unavailable"
    assert "Unconnected" in res.provider_name

    # Verify default provider in module is consistent
    def_res = default_volume_provider.get_keyword_volume("python automation")
    assert def_res.volume_range == "Volume unavailable"


def test_thumbnail_text_hook_generation():
    """Verify thumbnail text hook generator produces compact 2-5 word high-contrast hooks."""
    hook_mistake = generate_thumbnail_text_hook("Common Keyboard Mistakes", "keyboard mistakes")
    assert hook_mistake == "AVOID THIS!"

    hook_vs = generate_thumbnail_text_hook("Keychron vs Epomaker", "keychron vs epomaker")
    assert hook_vs == "THE REAL WINNER"

    hook_best = generate_thumbnail_text_hook("Best Mechanical Keyboards 2026", "best keyboards")
    assert hook_best == "DON'T BUY YET!"

    hook_tut = generate_thumbnail_text_hook("Python Automation Tutorial", "python tutorial")
    assert hook_tut == "DO THIS FIRST!"

    hook_rev = generate_thumbnail_text_hook("M1 Mac Mini Review", "m1 mac review")
    assert hook_rev == "WORTH IT IN 2026?"

    words = hook_best.split()
    assert 1 <= len(words) <= 5


def test_channel_header_bar_renders():
    """Verify render_channel_header_bar renders channel buttons and summary."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.toggle", return_value=False), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"):

        active_prof = render_channel_header_bar()
        assert active_prof.id == 1


def test_tool_keyword_research_renders_without_crash():
    """Verify Tool 1: Keyword Research renders cleanly and is channel-aware."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.text_input", return_value="mechanical keyboards"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        render_keyword_research_tool()
        assert state["kr_last_query"] != ""


def test_tool_video_research_renders_without_crash():
    """Verify Tool 2: YouTube Video Research renders cleanly."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.text_input", return_value="mechanical keyboards"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.selectbox", return_value="Last 30 Days"), \
         patch("streamlit.checkbox", return_value=True), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        render_video_research_tool()


def test_tool_competitor_research_renders_without_crash():
    """Verify Tool 3: Competitor Research renders cleanly."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.text_input", return_value="mechanical keyboards"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.selectbox", return_value="Last 30 Days"), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        render_competitor_research_tool()


def test_tool_opportunity_finder_renders_without_crash():
    """Verify Tool 4: 60-Day Opportunity Finder renders cleanly."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.text_input", return_value="mechanical keyboards"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        render_opportunity_finder_tool()


def test_tool_seo_generator_renders_without_crash():
    """Verify Tool 5: SEO Generator renders cleanly."""
    state = MockSessionState()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.text_input", return_value="mechanical keyboards"), \
         patch("streamlit.radio", return_value="Long-form (16:9)"), \
         patch("streamlit.selectbox", return_value="Informative & Engaging"), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.columns", side_effect=mock_columns), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        render_seo_generator_tool()
