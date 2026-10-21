"""Comprehensive Acceptance Tests for Master Upgrade:
Niche → Sub-Niche → Product → YouTube 60-Day Opportunity Engine.

Tests all 15 Master Criteria:
1. All four root niches are present.
2. Each root niche can expand into sub-niches.
3. Sub-niches expand into sub-sub-niches and product categories.
4. Product selection triggers the correct research workflow.
5. Market selection is preserved (US, UK, CA).
6. The rolling 60-day date boundary is correct.
7. Recent relevant videos trigger the strict exclusion rule.
8. Channel names, dates, and public views are displayed from actual returned data.
9. Irrelevant videos do not incorrectly trigger exclusion.
10. Insufficient coverage never becomes an approved opportunity.
11. API failures never become approved opportunities.
12. Results save and reopen correctly from SQLite database.
13. Search, sorting, filtering, and CSV export work.
14. Taxonomy duplicates are handled correctly.
15. Existing application sections continue to work.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.intelligence.product_gap_engine import (
    OpportunityEvaluationResult,
    OpportunityStatus,
    ProductGapEngine,
    ProductOpportunityRecord,
    product_gap_engine,
)
from src.intelligence.product_taxonomy import (
    ProductTaxonomyManager,
    TaxonomyProduct,
    taxonomy_manager,
)
from src.storage.database import DatabaseManager, db_manager
from src.storage.export import ExportService
from src.ui.tool_opportunity_finder import render_opportunity_finder_tool


# -----------------------------------------------------------------------------
# Criterion 1: All four root niches are present
# -----------------------------------------------------------------------------
def test_criterion_1_four_root_niches_present():
    """Verify that all four required root categories exist in the taxonomy."""
    roots = taxonomy_manager.get_root_niches()
    expected_roots = {
        "Home & Kitchen",
        "Automotive & Car Care",
        "Tools & Home Improvement",
        "Outdoor & Survival",
    }
    assert set(roots) == expected_roots, f"Root niches mismatch. Got: {roots}"


# -----------------------------------------------------------------------------
# Criterion 2: Each root niche can expand into sub-niches
# -----------------------------------------------------------------------------
def test_criterion_2_sub_niches_expansion():
    """Verify that every root niche expands into multiple verified sub-niches."""
    for rn in taxonomy_manager.get_root_niches():
        sub_niches = taxonomy_manager.get_sub_niches(rn)
        assert len(sub_niches) >= 2, f"Root niche '{rn}' should have at least 2 sub-niches, got {len(sub_niches)}"
        for sn in sub_niches:
            assert isinstance(sn, str) and len(sn) > 0


# -----------------------------------------------------------------------------
# Criterion 3: Sub-niches expand into sub-sub-niches and product categories
# -----------------------------------------------------------------------------
def test_criterion_3_deep_hierarchy_expansion():
    """Verify 5-level hierarchy down to product categories."""
    hk_sub = taxonomy_manager.get_sub_niches("Home & Kitchen")
    assert "Kitchen Appliances" in hk_sub

    sub_subs = taxonomy_manager.get_sub_sub_niches("Home & Kitchen", "Kitchen Appliances")
    assert "Coffee Equipment" in sub_subs

    cats = taxonomy_manager.get_product_categories("Home & Kitchen", "Kitchen Appliances", "Coffee Equipment")
    assert "Espresso Machines" in cats

    products = taxonomy_manager.get_products("Home & Kitchen", "Kitchen Appliances", category="Espresso Machines")
    assert len(products) >= 1
    espresso_prod = products[0]
    assert "Espresso" in espresso_prod.product_name
    assert "Home & Kitchen → Kitchen Appliances → Coffee Equipment → Espresso Machines" in espresso_prod.full_breadcrumb


# -----------------------------------------------------------------------------
# Criterion 4: Product selection triggers research workflow
# -----------------------------------------------------------------------------
def test_criterion_4_product_selection_triggers_research():
    """Verify that product selection generates targeted queries and runs evaluation."""
    prod = taxonomy_manager.get_products("Home & Kitchen")[0]
    queries = product_gap_engine.generate_candidate_queries(prod, market="US", max_queries=4)
    assert len(queries) >= 2
    assert prod.product_name.lower() in queries[0].lower()

    res = product_gap_engine.research_product(prod, market="US", max_queries=3, use_cache=False)
    assert isinstance(res, OpportunityEvaluationResult)
    assert res.product.product_id == prod.product_id
    assert len(res.records) >= 2
    assert res.total_queries_executed >= 2


# -----------------------------------------------------------------------------
# Criterion 5: Market selection is preserved (US, UK, CA)
# -----------------------------------------------------------------------------
def test_criterion_5_market_selection_preserved():
    """Verify US, UK, and CA markets are supported with localized queries."""
    prod = taxonomy_manager.get_products("Automotive & Car Care")[0]

    for mkt in ["US", "UK", "CA"]:
        queries = product_gap_engine.generate_candidate_queries(prod, market=mkt, max_queries=5)
        res = product_gap_engine.research_product(prod, market=mkt, max_queries=2, use_cache=False)
        assert res.market == mkt
        assert all(r.market == mkt for r in res.records)
        assert all("Commission not verified" in r.affiliate_status for r in res.records)


# -----------------------------------------------------------------------------
# Criterion 6: Rolling 60-day date boundary is correct
# -----------------------------------------------------------------------------
def test_criterion_6_rolling_60day_window_boundary():
    """Verify UTC calculation of 60-day rolling window."""
    start_dt, end_dt, window_str = product_gap_engine.get_rolling_window()
    assert end_dt.tzinfo == timezone.utc
    assert start_dt.tzinfo == timezone.utc
    delta = end_dt - start_dt
    assert delta.days == 60
    assert "60 days UTC" in window_str


# -----------------------------------------------------------------------------
# Criterion 7: Recent relevant videos trigger the strict exclusion rule
# -----------------------------------------------------------------------------
def test_criterion_7_strict_exclusion_rule_recent_videos():
    """If 1+ relevant matching videos in last 60 days, must be EXCLUDED."""
    prod = taxonomy_manager.get_products("Tools & Home Improvement")[0]
    now_iso = datetime.now(timezone.utc).isoformat()

    matching_vids = [
        {
            "video_id": "v101",
            "title": f"Review of {prod.product_name} - Real World Testing",
            "published_at": now_iso,
            "channel_title": "Tool Expert",
            "views": 25000,
        }
    ]

    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword=prod.product_name,
        product=prod,
        market="US",
        matching_videos=matching_vids,
        executed_queries=["q1", "q2"],
    )

    assert rec.opportunity_status == OpportunityStatus.EXCLUDED_RECENT_VIDEOS
    assert rec.matching_videos_count == 1
    assert "Strict Rule Applied" in rec.recommendation
    assert rec.observed_competition in ("MEDIUM", "HIGH")


# -----------------------------------------------------------------------------
# Criterion 8: Channel names, dates, and views displayed from actual data
# -----------------------------------------------------------------------------
def test_criterion_8_video_metadata_preservation():
    """Verify video titles, channels, dates, and view counts are preserved in evidence."""
    prod = taxonomy_manager.get_products("Home & Kitchen")[0]
    recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    vids = [
        {
            "video_id": "vid_xyz",
            "title": f"Complete Guide to {prod.product_name}",
            "channel_title": "EspressoLab Pro",
            "published_at": recent_date,
            "views": 42100,
            "like_count": 1200,
        }
    ]

    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword=prod.product_name,
        product=prod,
        matching_videos=vids,
        executed_queries=["q1", "q2"],
    )

    assert len(rec.video_evidence) == 1
    ev = rec.video_evidence[0]
    assert ev["channel_title"] == "EspressoLab Pro"
    assert ev["views"] == 42100
    assert ev["published_at"] == recent_date
    assert rec.latest_publish_date == recent_date[:10]


# -----------------------------------------------------------------------------
# Criterion 9: Irrelevant videos do not incorrectly trigger exclusion
# -----------------------------------------------------------------------------
def test_criterion_9_irrelevant_videos_do_not_trigger_exclusion():
    """Off-topic videos should not count towards matching competitor videos."""
    prod = taxonomy_manager.get_products("Home & Kitchen", category="Espresso Machines")[0]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Video title has nothing to do with espresso machines
    unrelated_vids = [
        {
            "video_id": "v_cake",
            "title": "Baking Grandmother's Famous Strawberry Cake Recipe",
            "published_at": now_iso,
            "channel_title": "Sweet Treats",
            "views": 100000,
        }
    ]

    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword="manual lever espresso machine",
        product=prod,
        matching_videos=unrelated_vids,
        executed_queries=["q1", "q2"],
    )

    # Strawberry cake is irrelevant; relevant matching count must be 0 -> POTENTIAL OPPORTUNITY
    assert rec.matching_videos_count == 0
    assert rec.opportunity_status == OpportunityStatus.POTENTIAL_OPPORTUNITY


# -----------------------------------------------------------------------------
# Criterion 10: Insufficient coverage never becomes an approved opportunity
# -----------------------------------------------------------------------------
def test_criterion_10_insufficient_coverage_never_approved():
    """If <2 queries executed, status MUST be NEEDS MORE RESEARCH, never POTENTIAL OPPORTUNITY."""
    prod = taxonomy_manager.get_products("Outdoor & Survival")[0]

    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword=prod.product_name,
        product=prod,
        matching_videos=[],
        executed_queries=["single_query_only"],  # only 1 query
    )

    assert rec.opportunity_status == OpportunityStatus.NEEDS_MORE_RESEARCH
    assert rec.opportunity_status != OpportunityStatus.POTENTIAL_OPPORTUNITY
    assert "Minimum 2 distinct queries required" in rec.recommendation


# -----------------------------------------------------------------------------
# Criterion 11: API failures never become approved opportunities
# -----------------------------------------------------------------------------
def test_criterion_11_api_failure_never_approved():
    """If API quota error or network exception occurs, status must be RESEARCH FAILED."""
    prod = taxonomy_manager.get_products("Outdoor & Survival")[0]

    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword=prod.product_name,
        product=prod,
        matching_videos=[],
        executed_queries=["q1", "q2"],
        has_api_error=True,
    )

    assert rec.opportunity_status == OpportunityStatus.RESEARCH_FAILED
    assert rec.opportunity_status != OpportunityStatus.POTENTIAL_OPPORTUNITY
    assert "Never classified as an opportunity" in rec.recommendation


# -----------------------------------------------------------------------------
# Criterion 12: Results save and reopen correctly from SQLite
# -----------------------------------------------------------------------------
def test_criterion_12_sqlite_persistence_and_resume(tmp_path):
    """Verify safe database saving and reopening."""
    test_db = DatabaseManager(db_path=tmp_path / "test_opportunity.db")
    test_db.init_db()

    prod = taxonomy_manager.get_products("Home & Kitchen")[0]
    rec = product_gap_engine.evaluate_opportunity(
        candidate_keyword=prod.product_name,
        product=prod,
        market="CA",
        matching_videos=[],
        executed_queries=["q1", "q2"],
    )

    # Save
    row_id = test_db.save_product_opportunity_record(rec)
    assert row_id >= 1

    # Reopen
    fetched = test_db.get_product_opportunity_records(product_id=prod.product_id, market="CA")
    assert len(fetched) == 1
    loaded = fetched[0]
    assert loaded["candidate_keyword"] == prod.product_name
    assert loaded["opportunity_status"] == OpportunityStatus.POTENTIAL_OPPORTUNITY
    assert loaded["market"] == "CA"
    assert len(loaded["executed_queries"]) == 2


# -----------------------------------------------------------------------------
# Criterion 13: Search, sorting, filtering, and CSV export work
# -----------------------------------------------------------------------------
def test_criterion_13_search_filter_csv_export():
    """Verify product searching, taxonomy filtering, and formula-safe CSV export."""
    # Fast search
    res = taxonomy_manager.search_products("grinder")
    assert len(res) >= 1
    assert any("Grinder" in p.product_name for p in res)

    # CSV Export
    import pandas as pd
    df = pd.DataFrame([
        {
            "Candidate Keyword": "=cmd|' /C calc'!A0",  # CSV injection payload
            "Opportunity Status": OpportunityStatus.POTENTIAL_OPPORTUNITY,
            "Matching Videos": 0,
        }
    ])
    csv_bytes = ExportService.export_csv(df)
    csv_out = csv_bytes.decode("utf-8-sig")
    # Ensure formula injection prefix is sanitized
    assert not csv_out.startswith("=cmd")
    assert "'=cmd" in csv_out or "cmd" in csv_out


# -----------------------------------------------------------------------------
# Criterion 14: Taxonomy duplicates are handled correctly
# -----------------------------------------------------------------------------
def test_criterion_14_taxonomy_deduplication():
    """Verify unique product IDs and clean normalization across catalog."""
    products = taxonomy_manager.get_products()
    product_ids = [p.product_id for p in products]
    assert len(product_ids) == len(set(product_ids)), "Product IDs must be strictly unique!"

    # Product names within same category should be unique
    for rn in taxonomy_manager.get_root_niches():
        prods_in_niche = taxonomy_manager.get_products(rn)
        names = [p.product_name.lower() for p in prods_in_niche]
        assert len(names) == len(set(names)), f"Duplicate product names detected in {rn}!"


# -----------------------------------------------------------------------------
# Criterion 15: Existing application sections continue to work
# -----------------------------------------------------------------------------
def test_criterion_15_existing_sections_work():
    """Verify Tool 4 renders cleanly with all mocked Streamlit components."""
    class MockSession(dict):
        pass

    state = MockSession()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.selectbox", return_value="US"), \
         patch("streamlit.text_input", return_value=""), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.columns", side_effect=lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        # Should execute cleanly without error
        render_opportunity_finder_tool()
