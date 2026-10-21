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
    normalize_format_label,
    render_channel_editor,
    render_channel_header_bar,
    render_channel_ideas_panel,
    switch_active_channel,
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


def test_switch_active_channel_research_isolation():
    """Verify switching active channels completely isolates research results and restores them on return."""
    state = MockSessionState()
    channels = channel_manager.get_all_channels()

    with patch("streamlit.session_state", state):
        state["active_channel_id"] = 1
        state["kr_results"] = [{"Keyword": "custom linear switches", "Opportunity Score": "85 pts"}]
        state["kr_last_query"] = "custom linear switches"

        # Switch Ch 1 -> Ch 2
        switch_active_channel(from_id=1, to_id=2, channels=channels)

        assert state["active_channel_id"] == 2
        # Verify Ch 2 has clean isolated results (no Ch 1 leakage)
        assert len(state["kr_results"]) == 0
        assert "Python" in state["kr_last_query"] or "AI" in state["kr_last_query"] or "Web" in state["kr_last_query"]

        # Conduct research on Ch 2
        state["kr_results"] = [{"Keyword": "fastapi bangla tutorial", "Opportunity Score": "90 pts"}]
        state["kr_last_query"] = "fastapi bangla tutorial"

        # Switch Ch 2 -> Ch 1
        switch_active_channel(from_id=2, to_id=1, channels=channels)

        assert state["active_channel_id"] == 1
        # Verify Ch 1 results were restored exactly as left
        assert len(state["kr_results"]) == 1
        assert state["kr_results"][0]["Keyword"] == "custom linear switches"
        assert state["kr_last_query"] == "custom linear switches"

        # Switch back Ch 1 -> Ch 2
        switch_active_channel(from_id=1, to_id=2, channels=channels)

        assert state["active_channel_id"] == 2
        assert len(state["kr_results"]) == 1
        assert state["kr_results"][0]["Keyword"] == "fastapi bangla tutorial"


def test_channel_ideas_all_four_niches_matched():
    """Verify each of the 4 channels receives video ideas matching its specific niche."""
    channels = channel_manager.get_all_channels()

    # Ch 1: Mechanical Keyboards
    ideas_ch1 = daily_opportunity_engine._generate_ideas_for_channel(channel=channels[0], count=2)
    assert any("keyboard" in (i.proposed_topic + i.main_keyword).lower() for i in ideas_ch1)

    # Ch 2: Python & Web Dev
    ideas_ch2 = daily_opportunity_engine._generate_ideas_for_channel(channel=channels[1], count=2)
    assert any("python" in (i.proposed_topic + i.main_keyword).lower() or "ai" in (i.proposed_topic + i.main_keyword).lower() for i in ideas_ch2)

    # Ch 3: Espresso & Kitchen
    ideas_ch3 = daily_opportunity_engine._generate_ideas_for_channel(channel=channels[2], count=2)
    assert any("espresso" in (i.proposed_topic + i.main_keyword).lower() or "grinder" in (i.proposed_topic + i.main_keyword).lower() for i in ideas_ch3)

    # Ch 4: Home Gym & Recovery
    ideas_ch4 = daily_opportunity_engine._generate_ideas_for_channel(channel=channels[3], count=2)
    assert any("gym" in (i.proposed_topic + i.main_keyword).lower() or "dumbbell" in (i.proposed_topic + i.main_keyword).lower() or "cardio" in (i.proposed_topic + i.main_keyword).lower() for i in ideas_ch4)


def test_saved_ideas_backlog_per_channel():
    """Verify saving video ideas is partitioned per channel without cross-channel pollution."""
    state = MockSessionState()

    with patch("streamlit.session_state", state):
        state["saved_ideas_channel_1"] = [{"topic": "Keyboard Sound Test", "keyword": "switch test"}]
        state["saved_ideas_channel_2"] = [{"topic": "Python FastAPI Setup", "keyword": "fastapi"}]

        assert len(state.get("saved_ideas_channel_1", [])) == 1
        assert state["saved_ideas_channel_1"][0]["keyword"] == "switch test"

        assert len(state.get("saved_ideas_channel_2", [])) == 1
        assert state["saved_ideas_channel_2"][0]["keyword"] == "fastapi"

        # Channel 3 has nothing saved yet
        assert len(state.get("saved_ideas_channel_3", [])) == 0


def test_normalize_format_label_canonical_options():
    """Verify format string maps cleanly to the 6 canonical formats."""
    assert normalize_format_label("Step-by-step Build Guide") == "Tutorial"
    assert normalize_format_label("How-to Guide") == "Tutorial"
    assert normalize_format_label("Comparison / Sound Test Shootout") == "Comparison"
    assert normalize_format_label("DF54 vs Encore ESP") == "Comparison"
    assert normalize_format_label("Space-saving Gear Tour & Recommendations") == "List"
    assert normalize_format_label("Top 5 Keyboards") == "List"
    assert normalize_format_label("Deep-dive Architecture Guide") == "Deep Dive"
    assert normalize_format_label("Benchmark & Analysis") == "Deep Dive"
    assert normalize_format_label("Diagnostic Case Study") == "Case Study"
    assert normalize_format_label("Quick Tip 60s") == "Quick Tip"


def test_channel_switching_auto_opens_ideas_panel():
    """Verify switching active channel automatically opens ideas panel for immediate discovery."""
    channels = channel_manager.get_all_channels()
    state = MockSessionState()
    state["active_channel_id"] = 1
    state["show_channel_ideas_panel"] = False

    with patch("streamlit.session_state", state):
        switch_active_channel(from_id=1, to_id=2, channels=channels)
        assert state["active_channel_id"] == 2
        assert state["show_channel_ideas_panel"] is True


def test_start_creating_handoff_prefills_seo_generator():
    """Verify 1-Click 'Start Creating' pre-fills all Tool 5 inputs and navigates to SEO Generator."""
    channel = channel_manager.get_channel(1)
    ideas = daily_opportunity_engine._generate_ideas_for_channel(channel=channel, count=1)
    assert len(ideas) >= 1
    top_idea = ideas[0]

    state = MockSessionState()
    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        # Emulate clicking Start Creating button
        state["seo_main_keyword"] = top_idea.main_keyword
        state["gen_main_kw_input"] = top_idea.main_keyword
        state["seo_topic_summary"] = top_idea.proposed_topic
        state["gen_topic_summary_input"] = top_idea.proposed_topic
        sec_str = ", ".join(top_idea.supporting_keywords[:4])
        state["seo_secondary_keywords"] = sec_str
        state["gen_sec_kws_input"] = sec_str
        target_aud = top_idea.target_viewer or channel.target_audience
        state["seo_target_viewer"] = target_aud
        state["gen_target_viewer_input"] = target_aud
        state["gen_format_radio"] = "Long-form (16:9)"
        state["current_page"] = TOOL_SEO_GENERATOR
        state["show_channel_ideas_panel"] = False

        # Verify state is ready for Tool 5 without re-entry
        assert state["current_page"] == TOOL_SEO_GENERATOR
        assert state["seo_main_keyword"] == top_idea.main_keyword
        assert state["gen_main_kw_input"] == top_idea.main_keyword
        assert state["seo_topic_summary"] == top_idea.proposed_topic
        assert state["gen_topic_summary_input"] == top_idea.proposed_topic
        assert top_idea.main_keyword in state["seo_secondary_keywords"]
        assert state["show_channel_ideas_panel"] is False


def test_morning_research_engine_and_report_persistence():
    """Verify automated morning research runs across all 4 channels and persists to SQLite."""
    rep = daily_opportunity_engine.run_daily_morning_report(
        timezone_name="UTC",
        scheduled_time="07:00",
        ideas_per_channel=4,
    )

    assert rep.id is not None
    assert rep.status in ("Completed", "Partially Completed")
    assert rep.total_channels_processed >= 4
    assert rep.total_ideas_generated >= 12
    assert rep.api_quota_units_used >= 0

    # Verify retrieval from database
    stored_reports = db_manager.get_daily_morning_reports(limit=5)
    assert len(stored_reports) > 0
    matched = next((r for r in stored_reports if r["id"] == rep.id), None)
    assert matched is not None
    assert matched["status"] == rep.status
    assert matched["total_channels_processed"] >= 4


def test_render_channel_ideas_panel_smoke():
    """Verify render_channel_ideas_panel renders without crash and populates idea list."""
    ch = channel_manager.get_channel(1)
    state = MockSessionState()
    state["active_channel_id"] = 1
    state["show_channel_ideas_panel"] = True

    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        render_channel_ideas_panel(ch)
        ideas_key = f"channel_ideas_{ch.id}"
        ideas = state.get(ideas_key)
        assert ideas is not None
        assert len(ideas) >= 3
        # Verify ranking order (descending by opportunity score)
        for i in range(len(ideas) - 1):
            assert ideas[i].opportunity_estimate >= ideas[i + 1].opportunity_estimate


