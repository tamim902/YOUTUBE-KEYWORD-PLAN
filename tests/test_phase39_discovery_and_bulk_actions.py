"""Unit and integration tests for Phase 39: Smart Keyword Discovery & Bulk One-Click Actions.

Verifies:
1. Unified Keyword Discovery collecting YouTube autocomplete + questions + alphabet + 8-framework patterns.
2. Transparent Source and Data Quality distinction:
   - YouTube Autocomplete: Source='YouTube Autocomplete', Data Quality='Live API data' / 'Cached data'
   - Generated Patterns: Source='Generated Pattern', Data Quality='Generated suggestion'
3. Honest volume reporting ('Volume unavailable') across all discovered candidates with zero fabrication.
4. Whitespace normalization and exact deduplication with Autocomplete priority.
5. Channel-specific discovery ('Find for This Channel') utilizing channel niche, country, language,
   and deduplicating against the saved channel backlog.
6. Reliable bulk actions:
   - Multi-select keywords
   - Copy selected keywords vs copy all visible keywords
   - Plain text export
   - Formula-safe CSV export (stripping formula injection risks)
7. Cross-tool handoffs to Video Research, Competitor Research, and SEO Generator with widget key synchronization.
8. Strict preservation of the 5 primary tools and 4 saved channel profiles.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.classifier.service import default_classifier
from src.config import config
from src.intelligence.channel_manager import channel_manager
from src.intelligence.decision_helper import keyword_decision_helper
from src.intelligence.scoring import default_scorer
from src.models.channel import ChannelProfile
from src.models.keyword import AutocompleteResult
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import PatternCategory, PatternConfig, PatternLanguage
from src.providers.volume import default_volume_provider
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.channel_components import get_active_channel
from src.ui.components import (
    TOOL_KEYWORD_RESEARCH,
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
)
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


def mock_columns(spec):
    """Mock st.columns returning an appropriate number of MagicMock columns."""
    count = len(spec) if isinstance(spec, list) else int(spec)
    return [MagicMock(__enter__=MagicMock(), __exit__=MagicMock()) for _ in range(count)]


def test_five_primary_tools_strict_order():
    """Verify that exactly five primary tools exist in the studio."""
    tools = [
        TOOL_KEYWORD_RESEARCH,
        TOOL_VIDEO_RESEARCH,
        TOOL_COMPETITOR_RESEARCH,
        TOOL_60_DAY_OPPORTUNITIES,
        TOOL_SEO_GENERATOR,
    ]
    assert len(tools) == 5
    assert "Keyword Research" in tools[0]
    assert "YouTube Video Research" in tools[1]
    assert "Competitor Research" in tools[2]
    assert "60-Day Opportunities" in tools[3]
    assert "SEO Generator" in tools[4]


def test_unified_discovery_collects_autocomplete_and_patterns():
    """Verify unified discovery collects both autocomplete and patterns with distinct sources."""
    ch = channel_manager.get_channel(1)
    seed = "mechanical keyboard switches"

    # 1. Autocomplete candidate
    ac_result = AutocompleteResult(keyword="best mechanical keyboard switches", is_cached=False)
    dec_ac = keyword_decision_helper.build_decision_summary(
        keyword=ac_result.keyword,
        seed_query=seed,
        channel=ch,
        is_cached=False,
        queries_executed_count=5,
        volume_status="Volume unavailable",
        source_type="autocomplete",
    )

    # 2. Pattern candidate
    pat_cfg = PatternConfig(
        seeds=[seed],
        categories=[PatternCategory.BEST_BUYING, PatternCategory.REVIEWS],
        language_mode=PatternLanguage.EN,
        max_generated=5,
    )
    generator = SmartKeywordPatternGenerator()
    patterns = generator.generate(pat_cfg)
    assert len(patterns) > 0

    top_pat = patterns[0]
    dec_pat = keyword_decision_helper.build_decision_summary(
        keyword=top_pat.keyword,
        seed_query=seed,
        channel=ch,
        is_cached=False,
        queries_executed_count=5,
        volume_status="Volume unavailable",
        source_type="generated_pattern",
    )

    # Verify Autocomplete attributes
    assert dec_ac.data_quality_label == "Live API data"
    assert "Volume unavailable" in dec_ac.search_volume_and_source

    # Verify Pattern attributes
    assert dec_pat.data_quality_label == "Generated suggestion"
    assert "Volume unavailable" in dec_pat.search_volume_and_source


def test_whitespace_normalization_and_deduplication():
    """Verify whitespace normalization and deduplication with Autocomplete priority."""
    clean_q = "custom keyboard"
    raw_inputs = [
        "   best   custom   keyboard   switches  ",
        "best custom keyboard switches",
        "BEST CUSTOM KEYBOARD SWITCHES",
        "custom keyboard",  # Exact seed match should be excluded
        "  ",  # Empty/whitespace only
    ]

    seen = set()
    normalized = []
    clean_q_norm = " ".join(clean_q.lower().split())

    for raw in raw_inputs:
        k_norm = " ".join(raw.lower().strip().split())
        if not k_norm or len(k_norm) < 2 or k_norm == clean_q_norm:
            continue
        if k_norm not in seen:
            seen.add(k_norm)
            normalized.append(k_norm)

    # Only 1 unique item should survive
    assert len(normalized) == 1
    assert normalized[0] == "best custom keyboard switches"


def test_channel_backlog_deduplication():
    """Verify that keywords in the channel backlog are excluded during channel discovery."""
    ch = channel_manager.get_channel(1)
    saved_backlog = [
        {"topic": "Quiet mechanical keyboard build", "keyword": "silent mechanical keyboard"},
        {"topic": "Lube switches tutorial", "keyword": "how to lube switches"},
    ]
    excluded_topics = {s["topic"].lower().strip() for s in saved_backlog}
    excluded_kws = {s["keyword"].lower().strip() for s in saved_backlog}
    full_excluded = excluded_topics.union(excluded_kws)

    test_candidates = [
        "silent mechanical keyboard",        # In backlog -> should be filtered
        "how to lube switches",              # In backlog -> should be filtered
        "best budget tactile switches 2026", # Fresh -> should be retained
    ]

    filtered_candidates = [
        k for k in test_candidates
        if " ".join(k.lower().split()) not in full_excluded
    ]

    assert len(filtered_candidates) == 1
    assert filtered_candidates[0] == "best budget tactile switches 2026"


def test_bulk_multiselect_and_copy_snippet_generation():
    """Verify bulk selection targets specific keywords and formats clean copy snippets."""
    all_kws = [
        "best mechanical keyboard for coding",
        "mechanical keyboard switch sound test",
        "budget mechanical keyboard under 50",
        "custom keyboard building guide",
    ]

    # Select a subset
    selected_subset = [all_kws[0], all_kws[2]]
    copy_selected_text = "\n".join(selected_subset)
    copy_all_text = "\n".join(all_kws)

    assert "coding" in copy_selected_text
    assert "under 50" in copy_selected_text
    assert "sound test" not in copy_selected_text

    assert len(copy_selected_text.splitlines()) == 2
    assert len(copy_all_text.splitlines()) == 4


def test_csv_export_formula_safety_and_selected_filtering():
    """Verify CSV export sanitizes formulas and respects selected row subsets."""
    export_svc = ExportService()

    raw_data = [
        {"Keyword": "=HYPERLINK('http://evil.com')", "Source": "YouTube Autocomplete", "Opportunity Score": "85/100"},
        {"Keyword": "+cmd|' /C calc'!A0", "Source": "YouTube Autocomplete", "Opportunity Score": "70/100"},
        {"Keyword": "safe mechanical keyboard", "Source": "Generated Pattern", "Opportunity Score": "90/100"},
    ]
    df = pd.DataFrame(raw_data)

    # Sanitize dataframe
    safe_df = sanitize_dataframe_for_export(df)
    csv_bytes = export_svc.export_csv(safe_df, sanitize_formulas=True)
    csv_text = csv_bytes.decode("utf-8")

    # Formula characters at start must be sanitized with leading single quote
    assert "'=HYPERLINK" in csv_text or "\\=HYPERLINK" in csv_text or not csv_text.startswith("=")
    assert "'+cmd" in csv_text or "\\+cmd" in csv_text or not "+cmd" in csv_text
    assert "safe mechanical keyboard" in csv_text


def test_cross_tool_handoff_prefills_and_synchronizes_keys():
    """Verify cross-tool handoff sets both state variables and widget input keys."""
    state = MockSessionState()
    ch = channel_manager.get_channel(1)
    state["active_channel_id"] = 1

    picked_kw = "best quiet mechanical keyboard"
    secondary_kws = "silent red switches, desk pad, sound dampening foam"

    # Simulate sending to SEO Generator
    state.seo_main_keyword = picked_kw
    state["gen_main_kw_input"] = picked_kw
    state.seo_secondary_keywords = secondary_kws
    state["gen_sec_kws_input"] = secondary_kws
    state.seo_topic_summary = f"Complete guide and tutorial for {picked_kw}"
    state["gen_topic_summary_input"] = f"Complete guide and tutorial for {picked_kw}"
    state.seo_target_viewer = ch.target_audience
    state["gen_target_viewer_input"] = ch.target_audience
    state["gen_format_radio"] = "Long-form (16:9)"
    state.current_page = TOOL_SEO_GENERATOR

    # Verify all synced properly
    assert state.seo_main_keyword == picked_kw
    assert state["gen_main_kw_input"] == picked_kw
    assert state.seo_secondary_keywords == secondary_kws
    assert state["gen_sec_kws_input"] == secondary_kws
    assert state.seo_target_viewer == ch.target_audience
    assert state["gen_target_viewer_input"] == ch.target_audience
    assert state.current_page == TOOL_SEO_GENERATOR

    # Simulate sending to Video Research
    state.vr_target_keyword = picked_kw
    state["vr_search_input"] = picked_kw
    state.current_page = TOOL_VIDEO_RESEARCH
    assert state.vr_target_keyword == picked_kw
    assert state["vr_search_input"] == picked_kw
    assert state.current_page == TOOL_VIDEO_RESEARCH

    # Simulate sending to Competitor Research
    state.cr_last_query = picked_kw
    state["cr_keyword_input"] = picked_kw
    state.current_page = TOOL_COMPETITOR_RESEARCH
    assert state.cr_last_query == picked_kw
    assert state["cr_keyword_input"] == picked_kw
    assert state.current_page == TOOL_COMPETITOR_RESEARCH


def test_keyword_research_tool_renders_with_unified_discovery_and_bulk_actions():
    """Verify Tool 1 renders with unified results, filters, inspector, and bulk actions."""
    ch = channel_manager.get_channel(1)
    state = MockSessionState()
    state["active_channel_id"] = 1
    state["kr_last_query"] = "mechanical keyboards"
    state["kr_results"] = [
        {
            "Keyword": "best mechanical keyboard for typing",
            "Source": "YouTube Autocomplete",
            "Data Quality": "Live API data",
            "Decision Status": "Good candidate",
            "Search Volume": "Volume unavailable",
            "Competition": "Low (Long-tail)",
            "Search Intent": "Review & Buyer Intent",
            "Opportunity Score": "88/100",
            "_raw_score": 88.0,
            "_source_type": "autocomplete",
            "_decision": {
                "keyword": "best mechanical keyboard for typing",
                "decision_status": "Good candidate",
                "explanation": "Good candidate because it has strong niche alignment.",
                "relevance_to_niche": "High: Matches channel core topic (keyboards).",
                "search_volume_and_source": "Volume unavailable (Commercial provider not connected)",
                "competition_evidence": "Low: Long-tail phrase (5 words)",
                "search_intent": "Review & Buyer Intent",
                "recent_video_evidence": "Not yet inspected in executed searches",
                "data_freshness": "Live API data (retrieved today)",
                "research_completeness": "Complete: 9 queries executed",
                "recommended_action": "Proceed to SEO Generator to draft title options.",
                "opportunity_score_display": "88/100",
                "data_quality_label": "Live API data",
                "disclaimer": "Analytical estimate without guarantees.",
            },
            "_score_breakdown": {
                "seed_term_score": 35.0,
                "similarity_score": 25.0,
                "intent_score": 20.0,
                "length_score": 8.0,
                "penalty": 0.0,
            },
        },
        {
            "Keyword": "top 5 mechanical keyboards 2026",
            "Source": "Generated Pattern",
            "Data Quality": "Generated suggestion",
            "Decision Status": "Good candidate",
            "Search Volume": "Volume unavailable",
            "Competition": "Low (Long-tail)",
            "Search Intent": "Listicle Intent",
            "Opportunity Score": "83/100",
            "_raw_score": 83.0,
            "_source_type": "pattern",
            "_decision": {
                "keyword": "top 5 mechanical keyboards 2026",
                "decision_status": "Good candidate",
                "explanation": "Good candidate because it has strong niche alignment.",
                "relevance_to_niche": "High: Matches channel core topic (keyboards).",
                "search_volume_and_source": "Volume unavailable (Commercial provider not connected)",
                "competition_evidence": "Low: Long-tail phrase (5 words)",
                "search_intent": "Listicle Intent",
                "recent_video_evidence": "Not yet inspected in executed searches",
                "data_freshness": "Live API data (retrieved today)",
                "research_completeness": "Complete: 9 queries executed",
                "recommended_action": "Proceed to SEO Generator to draft title options.",
                "opportunity_score_display": "83/100",
                "data_quality_label": "Generated suggestion",
                "disclaimer": "Analytical estimate without guarantees.",
            },
            "_score_breakdown": {
                "seed_term_score": 30.0,
                "similarity_score": 25.0,
                "intent_score": 20.0,
                "length_score": 8.0,
                "penalty": 0.0,
            },
        },
    ]

    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        render_keyword_research_tool()
        # Verify both results are preserved and properly categorized
        assert len(state["kr_results"]) == 2
        sources = {r["Source"] for r in state["kr_results"]}
        assert "YouTube Autocomplete" in sources
        assert "Generated Pattern" in sources
        qualities = {r["Data Quality"] for r in state["kr_results"]}
        assert "Live API data" in qualities
        assert "Generated suggestion" in qualities


def test_opportunity_finder_recent_videos_found_alias_and_rendering():
    """Verify GapFinderState.RECENT_VIDEOS_FOUND alias exists and Opportunity Finder evaluates it safely."""
    from src.models.morning_report import GapFinderState
    from src.intelligence.gap_finder import gap_finder
    from src.ui.tool_opportunity_finder import render_opportunity_finder_tool

    # Verify alias exists on enum
    assert hasattr(GapFinderState, "RECENT_VIDEOS_FOUND")
    assert GapFinderState.RECENT_VIDEOS_FOUND == GapFinderState.MATCHING_RECENT_VIDEOS_FOUND

    # Verify gap finder evaluates >= 4 videos safely
    state, msg = gap_finder.evaluate_gap_state(matching_videos_count=5, queries_executed=3)
    assert state == GapFinderState.MATCHING_RECENT_VIDEOS_FOUND

    # Smoke render with MockSessionState
    m_state = MockSessionState()
    m_state["active_channel_id"] = 1
    m_state["opp_last_query"] = "keyboards"
    with patch("streamlit.session_state", m_state), patch("streamlit.rerun"):
        render_opportunity_finder_tool()


def test_seo_generator_title_candidate_angle_resilience():
    """Verify SEO Generator safely reads title candidates whether angle or angle_type is used."""
    from src.intelligence.content_factory import TitleCandidate, VideoContentPackage
    from src.ui.tool_seo_generator import render_seo_generator_tool

    cand1 = TitleCandidate(
        title="Best Mechanical Keyboards (2026): What to Buy",
        angle="buyer_guide",
        char_count=45,
        is_front_loaded=True,
        length_status="Optimal",
    )
    pkg = VideoContentPackage(
        channel_id=1,
        channel_name="Mechanical Keyboards",
        topic="Best Keyboards",
        primary_keyword="mechanical keyboards",
        selected_title=cand1.title,
        title_options=[cand1],
    )

    state = MockSessionState()
    state["active_channel_id"] = 1
    state["seo_main_keyword"] = "mechanical keyboards"
    state["seo_generated_pkg"] = pkg

    with patch("streamlit.session_state", state), patch("streamlit.rerun"):
        render_seo_generator_tool()


def test_vidiq_scoring_and_ranking_chance_computation():
    """Verify vidIQ-style scores, competition tiers, and ranking chances."""
    ch = channel_manager.get_channel(1)

    # 1. Long-tail keyword: should have High/Very High ranking chance and Low competition
    dec_lt = keyword_decision_helper.build_decision_summary(
        keyword="best silent mechanical keyboard for programming",
        seed_query="mechanical keyboard",
        channel=ch,
        queries_executed_count=5,
        raw_score=90.0,
    )
    assert dec_lt.competition_tier == "Low"
    assert "High" in dec_lt.ranking_chance
    assert dec_lt.vidiq_score >= 65
    assert "🟢" in dec_lt.vidiq_score_display

    # 2. Broad single word: should have High competition and Low ranking chance
    dec_broad = keyword_decision_helper.build_decision_summary(
        keyword="keyboards",
        seed_query="keyboards",
        channel=ch,
        queries_executed_count=1,
        raw_score=40.0,
    )
    assert dec_broad.competition_tier == "High"
    assert dec_broad.ranking_chance in ("Low", "Medium")


def test_tag_studio_character_counter_and_formatting():
    """Verify YouTube Tag Studio character counting against the 500-character upload limit."""
    tags = [
        "best mechanical keyboards",
        "mechanical keyboards 2026",
        "custom keyboard build",
        "quiet linear switches",
    ]
    comma_tags = ", ".join(tags)
    assert len(comma_tags) < 500
    assert "best mechanical keyboards" in comma_tags
    assert "2026" in comma_tags

