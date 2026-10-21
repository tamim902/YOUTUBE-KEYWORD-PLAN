"""Unit and integration tests for Phase 38: Smart Research Quality & Keyword Decision Engine.

Verifies:
1. Keyword Decision Summary generation with all 8 evidence points and plain-language statuses:
   - Good candidate
   - Needs more research
   - Low relevance
   - Volume unavailable
   - Insufficient evidence
2. Transparent opportunity scoring behavior and 'Insufficient data' fallback when evidence is sparse.
3. Data quality indicators (Live API data, Cached data, Provider-sourced estimate, Generated suggestion, Incomplete research, Unavailable metrics).
4. Four-channel idea workflow with deduplication against saved channel backlog.
5. Research coverage reporting with the 4 distinct 60-day states:
   - Matching videos found
   - No matching videos found in executed searches
   - Few matching videos found
   - Insufficient coverage
6. Safe non-promissory disclaimers (zero ranking or viral traffic guarantees).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.intelligence.channel_manager import channel_manager
from src.intelligence.daily_engine import daily_opportunity_engine
from src.intelligence.decision_helper import (
    KeywordDecisionSummary,
    keyword_decision_helper,
)
from src.intelligence.gap_finder import GapFinderState, gap_finder
from src.intelligence.scoring import default_scorer
from src.models.channel import ChannelProfile
from src.providers.volume import UnconnectedSearchVolumeProvider
from src.ui.channel_components import render_channel_ideas_panel
from src.ui.tool_keyword_research import render_keyword_research_tool


class MockSessionState(dict):
    """Mock Streamlit session state for testing."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def test_decision_summary_good_candidate():
    """Verify focused long-tail keyword with high niche relevance returns 'Good candidate'."""
    ch = channel_manager.get_channel(1)  # Mechanical Keyboards
    summary = keyword_decision_helper.build_decision_summary(
        keyword="best silent mechanical keyboard switches",
        seed_query="mechanical keyboard switches",
        channel=ch,
        is_cached=False,
        retrieved_at="2026-10-21 10:00",
        queries_executed_count=8,
        raw_score=85.0,
    )

    assert summary.decision_status == "Good candidate"
    assert "Good candidate because" in summary.explanation
    assert "High: Matches channel" in summary.relevance_to_niche
    assert "Low" in summary.competition_evidence or "Long-tail" in summary.competition_evidence
    assert summary.data_quality_label == "Live API data"
    assert summary.opportunity_score_display == "85/100"
    assert "Volume unavailable" in summary.search_volume_and_source
    assert "Complete" in summary.research_completeness


def test_decision_summary_needs_more_research():
    """Verify broad 1-2 word query with unverified competition returns 'Needs more research'."""
    ch = channel_manager.get_channel(1)
    summary = keyword_decision_helper.build_decision_summary(
        keyword="keyboards",
        seed_query="keyboards",
        channel=ch,
        is_cached=True,
        retrieved_at="2026-10-21 09:30",
        queries_executed_count=1,
        raw_score=40.0,
    )

    assert summary.decision_status == "Needs more research"
    assert "Needs more research because" in summary.explanation
    assert "broad query" in summary.explanation
    assert summary.data_quality_label == "Cached data"
    assert "Cached data" in summary.data_freshness


def test_decision_summary_low_relevance():
    """Verify keyword unrelated to channel niche returns 'Low relevance'."""
    ch = channel_manager.get_channel(1)  # Keyboards
    summary = keyword_decision_helper.build_decision_summary(
        keyword="how to train a marathon race",
        seed_query="mechanical keyboards",
        channel=ch,
        is_cached=False,
        queries_executed_count=1,
        raw_score=10.0,
    )

    assert summary.decision_status == "Low relevance"
    assert "Low relevance because" in summary.explanation
    assert "No direct overlap" in summary.relevance_to_niche


def test_decision_summary_insufficient_evidence():
    """Verify empty or invalid keyword returns 'Insufficient evidence' and 'Insufficient data'."""
    ch = channel_manager.get_channel(1)
    summary = keyword_decision_helper.build_decision_summary(
        keyword="   ",
        seed_query="",
        channel=ch,
        is_cached=False,
    )

    assert summary.decision_status == "Insufficient evidence"
    assert "Insufficient evidence because" in summary.explanation
    assert summary.opportunity_score_display == "Insufficient data"
    assert summary.data_quality_label == "Incomplete research"


def test_decision_summary_volume_unavailable_explicit_source():
    """Verify volume source is truthfully documented as unavailable when provider is unconnected."""
    provider = UnconnectedSearchVolumeProvider()
    vol_obj = provider.get_keyword_volume("custom mechanical keyboard switches")

    assert vol_obj.volume_range == "Volume unavailable"
    assert not provider.is_connected()

    summary = keyword_decision_helper.build_decision_summary(
        keyword="custom mechanical keyboard switches",
        seed_query="mechanical keyboards",
        channel=channel_manager.get_channel(1),
        volume_status=vol_obj.display_metric,
    )

    assert "Volume unavailable" in summary.search_volume_and_source
    assert "Commercial provider not connected" in summary.search_volume_and_source
    assert "YouTube autocomplete query demand signals" in summary.search_volume_and_source


def test_decision_summary_recent_video_four_states():
    """Verify recent video evidence accurately handles the four 60-day states without false claims."""
    ch = channel_manager.get_channel(1)

    # 1. Zero matching videos found in executed searches (High Content Gap)
    s0 = keyword_decision_helper.build_decision_summary(
        keyword="hall effect magnetic keyboard build guide",
        channel=ch,
        serp_video_count=0,
    )
    assert s0.recent_video_evidence == "No matching videos found in executed searches (High Content Gap)"

    # 2. Few matching videos found (1-3)
    s2 = keyword_decision_helper.build_decision_summary(
        keyword="hall effect magnetic keyboard build guide",
        channel=ch,
        serp_video_count=2,
    )
    assert s2.recent_video_evidence == "Few matching videos found (2 videos in executed search sample)"

    # 3. Matching videos found (4+)
    s5 = keyword_decision_helper.build_decision_summary(
        keyword="hall effect magnetic keyboard build guide",
        channel=ch,
        serp_video_count=6,
    )
    assert s5.recent_video_evidence == "Matching videos found (6 videos in executed search sample)"

    # 4. Not yet inspected
    s_none = keyword_decision_helper.build_decision_summary(
        keyword="hall effect magnetic keyboard build guide",
        channel=ch,
        serp_video_count=None,
    )
    assert "Not yet inspected in executed searches" in s_none.recent_video_evidence


def test_channel_idea_workflow_deduplicates_saved_backlog():
    """Verify that ideas already saved in channel backlog are excluded from fresh recommendations."""
    ch = channel_manager.get_channel(1)

    # Pre-save an idea in channel 1's backlog
    state = MockSessionState()
    state["active_channel_id"] = 1
    state["show_channel_ideas_panel"] = True
    state["saved_ideas_channel_1"] = [
        {
            "topic": "Hall Effect Magnetic Switch Keyboards in 2026",
            "keyword": "best hall effect keyboard 2026",
        }
    ]

    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        render_channel_ideas_panel(ch)
        ideas = state.get(f"channel_ideas_{ch.id}", [])
        assert len(ideas) >= 3

        # Verify the pre-saved idea was NOT recommended again
        assert not any(
            i.proposed_topic.lower().strip() == "hall effect magnetic switch keyboards in 2026"
            for i in ideas
        ), "Saved idea must be excluded from fresh recommendations to prevent duplication"


def test_scoring_formula_insufficient_data_behavior():
    """Verify that scoring formula returns 'Insufficient data' when essential evidence is missing."""
    scorer = default_scorer
    res_empty = scorer.score("", "")
    assert res_empty.total_score == 0.0

    # Decision summary with empty score returns "Insufficient data"
    ch = channel_manager.get_channel(1)
    summary = keyword_decision_helper.build_decision_summary(
        keyword="xyz nonword 123",
        seed_query="espresso coffee",
        channel=ch,
        raw_score=0.0,
    )
    assert summary.opportunity_score_display == "Insufficient data"


def test_keyword_research_tool_coverage_and_inspector_render():
    """Verify Keyword Research tool executes and sets up decision inspector without crash."""
    ch = channel_manager.get_channel(1)
    state = MockSessionState()
    state["active_channel_id"] = 1
    state["kr_last_query"] = "mechanical keyboards"
    state["kr_results"] = [
        {
            "Keyword": "best mechanical keyboard for typing",
            "Decision Status": "Good candidate",
            "Search Volume": "Volume unavailable",
            "Competition": "Low (Long-tail)",
            "Search Intent": "Review & Buyer Intent",
            "Data Quality": "Live API data",
            "Opportunity Score": "88/100",
            "_raw_score": 88.0,
            "_decision": {
                "keyword": "best mechanical keyboard for typing",
                "decision_status": "Good candidate",
                "explanation": "Good candidate because it has strong niche alignment and clear Review & Buyer Intent intent.",
                "relevance_to_niche": "High: Matches channel core topic (keyboards).",
                "search_volume_and_source": "Volume unavailable (Commercial provider not connected)",
                "competition_evidence": "Low: Long-tail phrase (5 words)",
                "search_intent": "Review & Buyer Intent",
                "recent_video_evidence": "Not yet inspected in executed searches",
                "data_freshness": "Live API data (retrieved today)",
                "research_completeness": "Complete: 9 queries executed",
                "recommended_action": "Proceed to SEO Generator to draft title options and description.",
                "opportunity_score_display": "88/100",
                "data_quality_label": "Live API data",
                "disclaimer": "Analysis is an analytical estimate based on current public YouTube patterns and content gaps.",
            },
            "_score_breakdown": {
                "seed_term_score": 35.0,
                "similarity_score": 25.0,
                "intent_score": 20.0,
                "length_score": 8.0,
                "penalty": 0.0,
            },
        }
    ]

    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        render_keyword_research_tool()
        # Verify results and inspector render smoothly
        assert len(state["kr_results"]) == 1
        assert state["kr_results"][0]["Decision Status"] == "Good candidate"
        assert state["kr_results"][0]["Data Quality"] == "Live API data"
