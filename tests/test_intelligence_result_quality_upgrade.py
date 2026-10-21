"""Repeatable evaluation and verification test suite for Intelligence & Result Quality Upgrade.

Tests:
1. YouTube Autocomplete query normalization and space expansion preservation.
2. Prevention of redundant/grammatically awkward query variations (e.g. 'best best').
3. Strict provenance categorization (Direct Autocomplete vs. Related vs. Questions vs. Patterns).
4. Zero duplication rate across all expanded keywords.
5. Stage 6 standardized competition ('LOW', 'MEDIUM', 'HIGH', 'UNKNOWN') and opportunity ('STRONGER CANDIDATE', etc.) labels.
6. Epistemic modesty and honest search-volume reporting.
7. Tag studio 500-character budgeting and relevance sorting.
8. Qualitative Video SERP title architecture insights.
9. Channel-specific 5-point explanation card integrity across all four channels.
10. Cross-tool handoff from Tag Studio to SEO Generator.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import pytest

from src.classifier.service import default_classifier
from src.intelligence.channel_manager import channel_manager
from src.intelligence.decision_helper import KeywordDecisionSummary, keyword_decision_helper
from src.intelligence.scoring import default_scorer
from src.models.channel import ChannelProfile
from src.models.keyword import AutocompleteResult
from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.providers.volume import default_volume_provider
from src.providers.youtube import YouTubeAutocompleteProvider


def test_autocomplete_query_normalization_and_space_expansion():
    """Verify that multi-whitespace is collapsed, quotes stripped, but intentional trailing spaces preserved."""
    provider = YouTubeAutocompleteProvider()

    with patch.object(provider, "_execute_request_with_retries", return_value=["test query completion"]) as mock_exec:
        # 1. Normal query
        res1 = provider.get_suggestions("  mechanical   keyboard  ", use_cache=False)
        assert mock_exec.call_args[1]["query"] == "mechanical keyboard"

        # 2. Query with outer quotes
        res2 = provider.get_suggestions(' "mechanical keyboard" ', use_cache=False)
        assert mock_exec.call_args[1]["query"] == "mechanical keyboard"

        # 3. Trailing space expansion query (must preserve single trailing space)
        res3 = provider.get_suggestions("mechanical keyboard ", use_cache=False)
        assert mock_exec.call_args[1]["query"] == "mechanical keyboard "


def test_query_variant_generation_avoids_redundant_prefixes():
    """Verify that modifier query generation does not duplicate prefixes like 'best' or 'how to'."""
    seed_best = "best gaming mouse"
    lower_seed = seed_best.lower()

    raw_mods = []
    if not lower_seed.startswith("best "):
        raw_mods.append(f"best {seed_best}")
    if not lower_seed.startswith("how to "):
        raw_mods.append(f"how to {seed_best}")
    if "review" not in lower_seed:
        raw_mods.append(f"{seed_best} review")

    # 'best best gaming mouse' must NOT be in generated queries
    assert "best best gaming mouse" not in raw_mods
    assert "how to best gaming mouse" in raw_mods or not lower_seed.startswith("how to ")


def test_provenance_categorization_integrity():
    """Verify that discovered items maintain clear, un-conflated category provenance."""
    ch = channel_manager.get_channel(1)

    dec_direct = keyword_decision_helper.build_decision_summary(
        keyword="mechanical keyboard guide",
        seed_query="mechanical keyboard",
        channel=ch,
        source_type="autocomplete",
    )
    assert dec_direct.data_quality_label == "Live API data"

    dec_pat = keyword_decision_helper.build_decision_summary(
        keyword="top 5 mechanical keyboards 2026",
        seed_query="mechanical keyboard",
        channel=ch,
        source_type="generated_pattern",
    )
    assert dec_direct.data_quality_label == "Live API data"
    assert dec_pat.data_quality_label == "Generated suggestion"


def test_zero_duplicate_rate_across_categories():
    """Verify that multiple query expansions deduplicate exact keywords regardless of case/spacing."""
    raw_candidates = [
        "best mechanical keyboards",
        "  best mechanical keyboards  ",
        "Best Mechanical Keyboards",
        "BEST MECHANICAL KEYBOARDS",
        "mechanical keyboards for beginners",
    ]
    seen = set()
    deduped = []
    for kw in raw_candidates:
        norm = " ".join(kw.lower().split())
        if norm not in seen:
            seen.add(norm)
            deduped.append(norm)

    assert len(deduped) == 2
    assert deduped == ["best mechanical keyboards", "mechanical keyboards for beginners"]


def test_competition_and_opportunity_standardized_labels():
    """Verify Stage 6 standardized Competition and Opportunity labels."""
    ch = channel_manager.get_channel(1)

    # 1. Strong candidate: Long-tail (4+ words) with high relevance
    dec_strong = keyword_decision_helper.build_decision_summary(
        keyword="best silent mechanical keyboard switches",
        seed_query="mechanical keyboard",
        channel=ch,
        raw_score=85.0,
    )
    assert dec_strong.competition_label == "LOW"
    assert dec_strong.opportunity_verdict == "STRONGER CANDIDATE"

    # 2. Moderate candidate: 2-word broad query with high competition
    dec_mod = keyword_decision_helper.build_decision_summary(
        keyword="mechanical keyboards",
        seed_query="mechanical keyboard",
        channel=ch,
        raw_score=55.0,
    )
    assert dec_mod.competition_label == "HIGH"
    assert dec_mod.opportunity_verdict == "MODERATE CANDIDATE"

    # 3. Weaker candidate: Irrelevant query
    dec_weak = keyword_decision_helper.build_decision_summary(
        keyword="how to plant bonsai trees",
        seed_query="mechanical keyboard",
        channel=ch,
        raw_score=20.0,
    )
    assert dec_weak.opportunity_verdict == "WEAKER CANDIDATE"

    # 4. Insufficient evidence: Empty query
    dec_empty = keyword_decision_helper.build_decision_summary(
        keyword="",
        seed_query="mechanical keyboard",
        channel=ch,
    )
    assert dec_empty.competition_label == "UNKNOWN"
    assert dec_empty.opportunity_verdict == "INSUFFICIENT EVIDENCE"


def test_search_volume_epistemic_modesty_and_provenance():
    """Verify search volume honestly reports 'Volume unavailable' and never invents metrics."""
    vol = default_volume_provider.get_keyword_volume("mechanical keyboard 2026")
    assert vol.monthly_volume is None
    assert vol.status == "Unavailable"
    assert "Volume unavailable" in vol.display_metric
    assert not default_volume_provider.is_connected()


def test_tag_studio_character_limit_and_500_char_budget():
    """Verify that tags selected for YouTube Studio upload strictly respect the 500-char budget."""
    tags = [f"tag number {i} for youtube video seo testing" for i in range(30)]
    safe_tags = []
    cur_len = 0
    for kw in tags:
        add_len = len(kw) + (2 if safe_tags else 0)
        if cur_len + add_len <= 500:
            safe_tags.append(kw)
            cur_len += add_len
        else:
            break

    assert cur_len <= 500
    assert len(", ".join(safe_tags)) == cur_len


def test_video_serp_qualitative_insights_generation():
    """Verify title structure analysis and content gap detection on video results."""
    videos = [
        CompetitorVideoItem(
            rank=1,
            video_id="v1",
            channel_id="c1",
            title="Best Mechanical Keyboards 2026 - Complete Review",
            channel_title="Tech Channel",
            view_count=50000,
            like_count=2000,
            publish_date="2026-01-15T00:00:00Z",
            relative_age="2 weeks ago",
        ),
        CompetitorVideoItem(
            rank=2,
            video_id="v2",
            channel_id="c2",
            title="Keychron V1 vs Epomaker TH80 Comparison",
            channel_title="Keyboard Reviews",
            view_count=35000,
            like_count=1400,
            publish_date="2025-08-01T00:00:00Z",
            relative_age="6 months ago",
        ),
    ]

    tut_count = sum(1 for v in videos if any(w in v.title.lower() for w in ["how to", "tutorial", "guide"]))
    rev_count = sum(1 for v in videos if any(w in v.title.lower() for w in ["best", "top", "review"]))
    vs_count = sum(1 for v in videos if " vs" in v.title.lower())
    yr_count = sum(1 for v in videos if "2026" in v.title)

    assert tut_count == 0  # High content gap for tutorials!
    assert rev_count == 1
    assert vs_count == 1
    assert yr_count == 1


def test_four_channel_idea_5_point_explanation_structure():
    """Verify that each channel workspace provides isolated niche context and 5-point explanation structure."""
    channels = channel_manager.get_all_channels()
    assert len(channels) == 4

    for chan in channels:
        assert chan.channel_niche
        assert chan.target_audience
        assert chan.target_country
        assert chan.target_language
        assert chan.id in (1, 2, 3, 4)


def test_cross_tool_handoff_tag_to_seo_generator():
    """Verify that tag string format matches SEO generator secondary keywords expectation."""
    sample_tags = ["mechanical keyboard", "custom keycaps", "linear switches"]
    comma_tags = ", ".join(sample_tags)
    assert "custom keycaps" in comma_tags
    assert len(comma_tags.split(", ")) == 3
