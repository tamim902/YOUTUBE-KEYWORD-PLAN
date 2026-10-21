"""Tool 4: 60-Day Opportunity Finder & Niche Product Discovery Engine.

Features:
- Complete 5-Level Niche Explorer (Home & Kitchen, Automotive & Car Care, Tools & Home Improvement, Outdoor & Survival)
- Interactive breadcrumb navigation, modal/popup drill-down, and global product fast search
- Multi-market research: US, UK, CA (with honest affiliate disclaimer: 'Commission not verified')
- Rolling 60-day UTC window with exact start and end timestamps
- Strict Personal Exclusion Rule:
  * 1+ relevant matching videos in last 60 days → EXCLUDED — RECENT VIDEOS FOUND
  * 0 matching videos across >=2 executed queries → POTENTIAL OPPORTUNITY
  * <2 queries executed → NEEDS MORE RESEARCH
  * API failure or quota exhausted → RESEARCH FAILED
- Filterable, sortable, formula-safe CSV exportable Product Opportunity Matrix
- Transparent 'Recommended Keywords to Pursue' section strictly excluding candidates with recent videos
- Video Evidence Inspector and Taxonomy Coverage & Provenance Reporting
- Safe SQLite persistence and seamless cross-tool handoffs to Video Research, Competitor Research, and SEO Generator
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import textwrap
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.classifier.service import default_classifier
from src.intelligence.gap_finder import GapFinder, GapFinderState, gap_finder
from src.intelligence.product_gap_engine import (
    OpportunityEvaluationResult,
    OpportunityStatus,
    ProductGapEngine,
    ProductOpportunityRecord,
    product_gap_engine,
)
from src.intelligence.product_taxonomy import TaxonomyProduct, taxonomy_manager
from src.providers.serp import YouTubeDataApiSerpProvider
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.channel_components import get_active_channel
from src.ui.components import (
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_SEO_GENERATOR,
)


def _render_html(html_str: str) -> None:
    """Render clean, unindented HTML without markdown code block formatting artifacts."""
    clean_html = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


def _render_status_badge(status: str) -> str:
    """Generate compact HTML badge for opportunity statuses."""
    if status == OpportunityStatus.POTENTIAL_OPPORTUNITY or "POTENTIAL" in status:
        bg = "#DCFCE7"
        fg = "#166534"
        border = "#BBF7D0"
        icon = "⭐"
    elif status == OpportunityStatus.EXCLUDED_RECENT_VIDEOS or "EXCLUDED" in status:
        bg = "#FEE2E2"
        fg = "#991B1B"
        border = "#FECACA"
        icon = "🚫"
    elif status == OpportunityStatus.NEEDS_MORE_RESEARCH or "NEEDS" in status:
        bg = "#FEF3C7"
        fg = "#92400E"
        border = "#FDE68A"
        icon = "⚠️"
    else:
        bg = "#F1F5F9"
        fg = "#475569"
        border = "#CBD5E1"
        icon = "🛑"

    return f"""<span style="background-color: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 4px; padding: 2px 7px; font-size: 0.76rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;">{icon} {status}</span>"""


def render_opportunity_finder_tool() -> None:
    """Render Tool 4: 60-Day Opportunity Finder & Niche Product Discovery Engine."""
    # Header Banner
    _render_html(
        """
        <div style="margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.7rem;">⚡</span>
                <h2 style="font-size: 1.55rem; font-weight: 700; color: #1E293B; margin: 0;">
                    60-Day Opportunity Finder & Product Research Engine
                </h2>
            </div>
            <p style="font-size: 0.92rem; color: #64748B; margin: 4px 0 0 0;">
                Systematically explore <b>4 Main Niches → Sub-Niches → Specific Products</b> and discover verified YouTube content gaps with zero competitor uploads in the rolling 60-day window.
            </p>
        </div>
        """
    )

    # Rolling window computation
    start_dt, end_dt, window_str = product_gap_engine.get_rolling_window()

    # Epistemic Modesty & Strict Rule Notice
    _render_html(
        f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #10B981; border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.84rem; color: #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    ⚖️ <b>Strict 60-Day Exclusion Rule:</b> If <b>1 or more</b> relevant videos were published within the last 60 days, candidate is strictly <b>EXCLUDED</b>. 
                    Candidates with <b>0 matching videos</b> across &ge;2 executed searches are classified as <b>POTENTIAL OPPORTUNITIES</b>.
                </div>
                <div style="font-size: 0.8rem; background: #E2E8F0; padding: 2px 8px; border-radius: 4px; font-weight: 600; color: #1E293B;">
                    📅 Window: {window_str}
                </div>
            </div>
        </div>
        """
    )

    # Session State Initialization
    if "opp_results" not in st.session_state:
        st.session_state.opp_results = []
    if "opp_last_seed" not in st.session_state:
        st.session_state.opp_last_seed = ""
    if "opp_window_str" not in st.session_state:
        st.session_state.opp_window_str = window_str
    if "opp_market" not in st.session_state:
        st.session_state.opp_market = "US"
    if "tax_selected_niche" not in st.session_state:
        st.session_state.tax_selected_niche = None
    if "tax_selected_sub" not in st.session_state:
        st.session_state.tax_selected_sub = None
    if "tax_selected_category" not in st.session_state:
        st.session_state.tax_selected_category = None
    if "tax_selected_product_id" not in st.session_state:
        st.session_state.tax_selected_product_id = None
    if "opp_recommended_list" not in st.session_state:
        st.session_state.opp_recommended_list = []
    if "opp_video_evidence" not in st.session_state:
        st.session_state.opp_video_evidence = []

    # Controls Bar: Market Selector & Channel Context
    c_m1, c_m2 = st.columns([1.5, 3.5])
    with c_m1:
        selected_market = st.selectbox(
            "🌍 Research Market",
            options=["US", "UK", "CA"],
            index=["US", "UK", "CA"].index(st.session_state.opp_market),
            key="opp_market_select",
            help="Select geographic market for localized YouTube search and product relevance.",
        )
        if selected_market != st.session_state.opp_market:
            st.session_state.opp_market = selected_market

    with c_m2:
        active_chan = get_active_channel()
        chan_label = f"Channel: **{active_chan.channel_name}** ({active_chan.channel_niche})" if active_chan else "Global Mode (All Niches)"
        _render_html(
            f"""
            <div style="background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 6px; padding: 7px 12px; margin-top: 24px; font-size: 0.82rem; color: #475569; display: flex; justify-content: space-between; align-items: center;">
                <span>🎯 {chan_label}</span>
                <span style="color: #64748B; font-style: italic;">Affiliate: <b>Commission not verified</b></span>
            </div>
            """
        )

    st.markdown("---")

    # =========================================================================
    # SECTION 1: 5-LEVEL NICHE & PRODUCT TAXONOMY EXPLORER
    # =========================================================================
    st.markdown("### 🗂️ 1. Interactive Niche & Product Explorer")
    st.caption("Drill down through the 5-level hierarchy: Root Niche → Sub-Niche → Sub-Sub-Niche → Product Category → Product.")

    # Global Product Fast Search
    all_products = taxonomy_manager.get_products()
    search_q = st.text_input(
        "🔍 Fast Product Search across All 4 Niches",
        placeholder="Type any product or alias (e.g. espresso, dash cam, multimeter, water filter, air fryer)...",
        key="tax_fast_search",
        help="Quickly locate products in any branch of the taxonomy without manual clicking.",
    )

    if search_q.strip():
        search_results = taxonomy_manager.search_products(search_q.strip(), limit=8)
        if search_results:
            st.caption(f"Found {len(search_results)} matching products:")
            cols = st.columns(min(len(search_results), 3))
            for idx, p in enumerate(search_results):
                with cols[idx % len(cols)]:
                    _render_html(
                        f"""
                        <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                            <div style="font-weight: 700; font-size: 0.88rem; color: #1E293B;">{p.product_name}</div>
                            <div style="font-size: 0.74rem; color: #64748B; margin: 2px 0;">{p.full_breadcrumb}</div>
                            <div style="font-size: 0.74rem; color: #0284C7;">Price Tier: {p.price_tier} &middot; Type: {p.product_type}</div>
                        </div>
                        """
                    )
                    if st.button(f"⚡ Research '{p.product_name[:20]}'", key=f"btn_search_prod_{p.product_id}", use_container_width=True):
                        st.session_state.tax_selected_product_id = p.product_id
                        _run_product_research(p, st.session_state.opp_market)
                        st.rerun()
        else:
            st.info(f"No catalog products matched '{search_q}'. You can still research it as a custom seed topic below.")

    # Breadcrumb Bar
    curr_niche = st.session_state.tax_selected_niche
    curr_sub = st.session_state.tax_selected_sub
    curr_cat = st.session_state.tax_selected_category

    bc_parts = ["Home"]
    if curr_niche:
        bc_parts.append(curr_niche)
    if curr_sub:
        bc_parts.append(curr_sub)
    if curr_cat:
        bc_parts.append(curr_cat)

    bc_str = " → ".join(bc_parts)
    b_col1, b_col2 = st.columns([4, 1])
    with b_col1:
        _render_html(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 12px; margin-bottom: 12px; font-size: 0.84rem; color: #334155; font-weight: 600;">
                📍 Path: <span style="color: #2563EB;">{bc_str}</span>
            </div>
            """
        )
    with b_col2:
        if curr_niche:
            if st.button("⬅️ Up / Reset", use_container_width=True, key="btn_tax_reset"):
                st.session_state.tax_selected_niche = None
                st.session_state.tax_selected_sub = None
                st.session_state.tax_selected_category = None
                st.session_state.tax_selected_product_id = None
                st.rerun()

    # Niche Explorer Navigation Levels
    root_niches = taxonomy_manager.get_root_niches()

    if not curr_niche:
        # Level 1: Root Niches Selection Cards
        st.markdown("##### Select a Root Niche to Explore:")
        n_cols = st.columns(4)
        niche_icons = {
            "Home & Kitchen": "🏠",
            "Automotive & Car Care": "🚗",
            "Tools & Home Improvement": "🛠️",
            "Outdoor & Survival": "🏕️",
        }
        for idx, rn in enumerate(root_niches):
            with n_cols[idx]:
                icon = niche_icons.get(rn, "📦")
                prod_count = len(taxonomy_manager.get_products(rn))
                sub_count = len(taxonomy_manager.get_sub_niches(rn))
                _render_html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid #3B82F6; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 8px;">
                        <div style="font-size: 2rem; margin-bottom: 4px;">{icon}</div>
                        <div style="font-weight: 700; font-size: 0.95rem; color: #1E293B;">{rn}</div>
                        <div style="font-size: 0.78rem; color: #64748B; margin-top: 4px;">{sub_count} Sub-Niches &middot; {prod_count} Products</div>
                    </div>
                    """
                )
                if st.button(f"Explore {rn}", key=f"btn_rn_{idx}", use_container_width=True, type="primary" if idx == 0 else "secondary"):
                    st.session_state.tax_selected_niche = rn
                    st.session_state.tax_selected_sub = None
                    st.session_state.tax_selected_category = None
                    st.rerun()

    elif curr_niche and not curr_sub:
        # Level 2: Sub-Niches in selected Root Niche
        sub_niches = taxonomy_manager.get_sub_niches(curr_niche)
        st.markdown(f"##### Sub-Niches in *{curr_niche}*:")
        sub_cols = st.columns(min(len(sub_niches), 4))
        for idx, sn in enumerate(sub_niches):
            with sub_cols[idx % len(sub_cols)]:
                p_in_sub = taxonomy_manager.get_products(curr_niche, sub_niche=sn)
                _render_html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                        <div style="font-weight: 700; font-size: 0.88rem; color: #1E293B;">📂 {sn}</div>
                        <div style="font-size: 0.75rem; color: #64748B;">{len(p_in_sub)} Catalog Products</div>
                    </div>
                    """
                )
                if st.button(f"View {sn}", key=f"btn_sub_{idx}", use_container_width=True):
                    st.session_state.tax_selected_sub = sn
                    st.session_state.tax_selected_category = None
                    st.rerun()

    elif curr_niche and curr_sub and not curr_cat:
        # Level 3: Product Categories in selected Sub-Niche
        categories = taxonomy_manager.get_product_categories(curr_niche, curr_sub)
        st.markdown(f"##### Categories in *{curr_niche} → {curr_sub}*:")
        cat_cols = st.columns(min(len(categories), 3))
        for idx, cat in enumerate(categories):
            with cat_cols[idx % len(cat_cols)]:
                p_in_cat = taxonomy_manager.get_products(curr_niche, sub_niche=curr_sub, category=cat)
                _render_html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; margin-bottom: 8px;">
                        <div style="font-weight: 700; font-size: 0.88rem; color: #1E293B;">🏷️ {cat}</div>
                        <div style="font-size: 0.75rem; color: #64748B;">{len(p_in_cat)} Products</div>
                    </div>
                    """
                )
                if st.button(f"Inspect {cat}", key=f"btn_cat_{idx}", use_container_width=True):
                    st.session_state.tax_selected_category = cat
                    st.rerun()

    else:
        # Level 4 & 5: Specific Products in selected Category
        products = taxonomy_manager.get_products(curr_niche, sub_niche=curr_sub, category=curr_cat)
        st.markdown(f"##### Products in *{curr_cat}*:")
        for idx, p in enumerate(products):
            p_c1, p_c2 = st.columns([3.5, 1.5])
            with p_c1:
                _render_html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #2563EB; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px;">
                        <div style="font-weight: 700; font-size: 0.92rem; color: #1E293B;">📦 {p.product_name}</div>
                        <div style="font-size: 0.78rem; color: #64748B;">Aliases: {', '.join(p.aliases[:3]) if p.aliases else 'None registered'}</div>
                        <div style="font-size: 0.74rem; color: #0284C7; margin-top: 2px;">
                            Price Tier: <b>{p.price_tier}</b> &middot; Candidate Queries: <b>{len(p.candidate_keywords)}</b> &middot; Market: <b>{', '.join(p.market_suitability)}</b>
                        </div>
                    </div>
                    """
                )
            with p_c2:
                st.write("")
                if st.button(f"⚡ Research 60-Day Gaps", key=f"btn_run_prod_{p.product_id}", type="primary", use_container_width=True):
                    st.session_state.tax_selected_product_id = p.product_id
                    _run_product_research(p, st.session_state.opp_market)
                    st.rerun()

    st.markdown("---")

    # =========================================================================
    # SECTION 2: DIRECT SEED / TOPIC INPUT (Preserved Classic Workflow)
    # =========================================================================
    st.markdown("### ✍️ 2. Custom Seed Topic or Keyword")
    st.caption("Alternatively, analyze any custom seed topic or phrase directly using YouTube Autocomplete and SERP competition.")

    initial_seed = (
        st.session_state.opp_last_seed
        or st.session_state.get("kr_last_query", "")
        or (active_chan.channel_niche.split("&")[0].strip() if active_chan else "")
        or ""
    )

    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            niche_seed = st.text_input(
                "Enter Seed Topic or Keyword",
                value=initial_seed,
                placeholder="e.g. mechanical keyboards, sourdough baking, cordless drill",
                key="opp_seed_input",
                help="Type any topic to run multi-query competition analysis within the rolling 60-day window.",
            )
        with c_in2:
            st.write("")
            st.write("")
            btn_find_gaps = st.button("⚡ Find 60-Day Gaps", type="primary", use_container_width=True, key="opp_submit_btn")

    if btn_find_gaps and niche_seed.strip():
        _run_seed_topic_research(niche_seed.strip(), st.session_state.opp_market)
        st.rerun()

    # =========================================================================
    # SECTION 3: RESULTS DISPLAY & 60-DAY OPPORTUNITY MATRIX
    # =========================================================================
    results = st.session_state.opp_results
    if results:
        st.markdown("---")

        # Metrics Banner
        total_cand = len(results)
        pot_opps = sum(1 for r in results if r["Opportunity Status"] == OpportunityStatus.POTENTIAL_OPPORTUNITY)
        excluded_cnt = sum(1 for r in results if r["Opportunity Status"] == OpportunityStatus.EXCLUDED_RECENT_VIDEOS)
        needs_cnt = sum(1 for r in results if r["Opportunity Status"] == OpportunityStatus.NEEDS_MORE_RESEARCH)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Candidates", total_cand)
        with m2:
            st.metric("⭐ Approved Opportunities", pot_opps, help="0 matching videos across >=2 queries within last 60 days.")
        with m3:
            st.metric("🚫 Excluded by Rule", excluded_cnt, help="1+ recent videos found in rolling 60-day window.")
        with m4:
            st.metric("Market & Window", f"{st.session_state.opp_market} (60d)", help="Rolling 60 days UTC.")

        # =====================================================================
        # ⭐ RECOMMENDED KEYWORDS TO PURSUE (Strict Exclusion Enforced)
        # =====================================================================
        st.markdown("### ⭐ Recommended Keywords to Pursue")
        st.caption("Strictly filtered according to your rule: Only candidates with **zero matching competitor videos** in the rolling 60-day window are approved.")

        recommended_items = [r for r in results if r["Opportunity Status"] == OpportunityStatus.POTENTIAL_OPPORTUNITY]

        if recommended_items:
            for idx, item in enumerate(recommended_items[:5]):
                rec_c1, rec_c2 = st.columns([3.8, 1.2])
                with rec_c1:
                    _render_html(
                        f"""
                        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 700; font-size: 1rem; color: #166534;">🎯 {item['Candidate Keyword']}</span>
                                {_render_status_badge(item['Opportunity Status'])}
                            </div>
                            <div style="font-size: 0.82rem; color: #374151; margin-bottom: 4px;">
                                <b>Why Selected:</b> {item['Explanation']}
                            </div>
                            <div style="font-size: 0.8rem; color: #4B5563;">
                                <b>Search Evidence:</b> {item['Search Coverage']} &middot; <b>Recent Videos (60d):</b> 0 &middot; <b>Market:</b> {item.get('Market', 'US')}
                            </div>
                            <div style="font-size: 0.8rem; color: #15803D; margin-top: 4px;">
                                <b>Suggested Video Title:</b> <em>"{item.get('Suggested Title', item['Suggested Angle'])}"</em>
                            </div>
                            <div style="font-size: 0.76rem; color: #6B7280; margin-top: 2px;">
                                ⚠️ <em>Missing Evidence: Search volume data not connected (epistemic modesty: volume unverified).</em>
                            </div>
                        </div>
                        """
                    )
                with rec_c2:
                    st.write("")
                    cand_kw = item["Candidate Keyword"]
                    if st.button("🚀 Send to SEO", key=f"btn_rec_seo_{idx}", type="primary", use_container_width=True):
                        st.session_state.seo_main_keyword = cand_kw
                        st.session_state.seo_topic_summary = item["Suggested Angle"]
                        st.session_state.seo_secondary_keywords = f"{cand_kw} review, best {cand_kw}, how to use {cand_kw}"
                        st.session_state.current_page = TOOL_SEO_GENERATOR
                        st.rerun()

                    if st.button("🔍 Video SERP", key=f"btn_rec_vr_{idx}", use_container_width=True):
                        st.session_state.vr_target_keyword = cand_kw
                        st.session_state.current_page = TOOL_VIDEO_RESEARCH
                        st.rerun()
        else:
            st.info("No candidates qualified as approved opportunities under the strict 0-recent-video rule. All analyzed queries either had recent competitor uploads or insufficient queries.")

        st.markdown("---")

        # =====================================================================
        # PRODUCT OPPORTUNITY MATRIX TABLE
        # =====================================================================
        st.markdown(f"### 🎯 Product Opportunity Matrix for *\"{st.session_state.opp_last_seed}\"*")
        st.caption(f"Evaluated across rolling 60-day window: **{st.session_state.opp_window_str}**")

        # Filter Controls
        f_c1, f_c2 = st.columns([2, 2])
        with f_c1:
            status_filter = st.selectbox(
                "Filter by Opportunity Status",
                options=["ALL", OpportunityStatus.POTENTIAL_OPPORTUNITY, OpportunityStatus.EXCLUDED_RECENT_VIDEOS, OpportunityStatus.NEEDS_MORE_RESEARCH, OpportunityStatus.RESEARCH_FAILED],
                index=0,
                key="opp_filter_status",
            )
        with f_c2:
            sort_by = st.selectbox(
                "Sort Table By",
                options=["Matching Videos (Ascending - Best First)", "Matching Videos (Descending)", "Candidate Keyword"],
                index=0,
                key="opp_sort_by",
            )

        filtered_results = list(results)
        if status_filter != "ALL":
            filtered_results = [r for r in filtered_results if r["Opportunity Status"] == status_filter]

        if "Ascending" in sort_by:
            filtered_results.sort(key=lambda x: int(x["Matching Videos"]))
        elif "Descending" in sort_by:
            filtered_results.sort(key=lambda x: int(x["Matching Videos"]), reverse=True)
        else:
            filtered_results.sort(key=lambda x: x["Candidate Keyword"])

        df_opp = pd.DataFrame(filtered_results)
        table_cols = [
            "Candidate Keyword",
            "Opportunity Status",
            "Matching Videos",
            "Latest Publish Date",
            "Observed Competition",
            "Search Coverage",
            "Explanation",
            "Suggested Angle",
        ]
        available_cols = [c for c in table_cols if c in df_opp.columns]

        st.dataframe(
            df_opp[available_cols],
            column_config={
                "Candidate Keyword": st.column_config.TextColumn("Candidate Keyword", width="medium"),
                "Opportunity Status": st.column_config.TextColumn("Opportunity Status", width="medium"),
                "Matching Videos": st.column_config.NumberColumn("Recent Videos (60d)", format="%d"),
                "Latest Publish Date": st.column_config.TextColumn("Latest Observed Date", width="small"),
                "Observed Competition": st.column_config.TextColumn("Observed Competition", width="small"),
                "Search Coverage": st.column_config.TextColumn("Search Coverage", width="medium"),
                "Explanation": st.column_config.TextColumn("Opportunity Explanation", width="large"),
                "Suggested Angle": st.column_config.TextColumn("Suggested Content Angle", width="large"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Action Buttons Row
        c_act1, c_act2, c_act3 = st.columns(3)
        with c_act1:
            csv_data = ExportService.export_csv(df_opp[available_cols])
            st.download_button(
                label="📥 Download Opportunities (CSV)",
                data=csv_data,
                file_name=f"60day_opportunities_{st.session_state.opp_last_seed.replace(' ', '_')}_{st.session_state.opp_market}.csv",
                mime="text/csv",
                use_container_width=True,
                key="opp_dl_csv_btn",
            )

        with c_act2:
            if st.button("🔄 Refresh Gap Analysis", use_container_width=True, key="opp_refresh_btn"):
                st.session_state.opp_results = []
                st.rerun()

        with c_act3:
            best_cand = recommended_items[0]["Candidate Keyword"] if recommended_items else (results[0]["Candidate Keyword"] if results else "")
            if best_cand:
                if st.button(f"🚀 Send Top Candidate to SEO", type="primary", use_container_width=True, key="opp_send_seo_btn"):
                    st.session_state.seo_main_keyword = best_cand
                    st.session_state.seo_topic_summary = f"Complete video walkthrough for {best_cand}"
                    st.session_state.current_page = TOOL_SEO_GENERATOR
                    st.rerun()

        # =====================================================================
        # VIDEO EVIDENCE INSPECTOR
        # =====================================================================
        evidence_list = st.session_state.get("opp_video_evidence", [])
        if evidence_list:
            with st.expander(f"🔎 Video Evidence Inspector ({len(evidence_list)} Competitor Videos Examined)"):
                st.caption("Examine actual video titles, channels, dates, view counts, and semantic relevance tags:")
                df_ev = pd.DataFrame(evidence_list)
                st.dataframe(
                    df_ev,
                    column_config={
                        "title": st.column_config.TextColumn("Video Title", width="large"),
                        "channel_title": st.column_config.TextColumn("Channel Name", width="medium"),
                        "published_at": st.column_config.TextColumn("Publish Date", width="small"),
                        "views": st.column_config.NumberColumn("Public Views", format="%d"),
                        "relevance_status": st.column_config.TextColumn("Relevance Status", width="medium"),
                        "query": st.column_config.TextColumn("Trigger Query", width="medium"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

    else:
        st.info("💡 Select a product from the Niche Explorer above or enter a seed topic to uncover underserved 60-day YouTube content gaps.")

    # =========================================================================
    # TAXONOMY COVERAGE & PROVENANCE REPORT
    # =========================================================================
    with st.expander("📊 Product Taxonomy Coverage & Provenance Report"):
        cov = taxonomy_manager.get_coverage_report()
        st.markdown(f"**Total Catalog Products:** {cov['total_catalog_products']} across **{cov['total_root_niches']}** root categories.")
        st.caption(f"Markets Supported: {', '.join(cov['markets_supported'])} &middot; Sources: Verified Retailer Taxonomy & Manufacturer Catalogs.")

        for n_name, n_data in cov["niches"].items():
            st.markdown(
                f"- **{n_name}**: {n_data['sub_niches_count']} sub-niches, {n_data['product_categories_count']} categories, {n_data['products_count']} verified products."
            )
        st.info(f"⚖️ **Epistemic Notice:** {cov['epistemic_notice']}")


def _run_product_research(product: TaxonomyProduct, market: str) -> None:
    """Execute live or simulated 60-day YouTube research for a taxonomy product."""
    st.session_state.opp_last_seed = product.product_name
    progress_bar = st.progress(0, text=f"Expanding keyword queries for '{product.product_name}'...")
    time.sleep(0.1)

    serp_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
    progress_bar.progress(30, text=f"Searching YouTube Data API for {market} competitor uploads (Rolling 60 Days)...")

    eval_res: OpportunityEvaluationResult = product_gap_engine.research_product(
        product=product,
        market=market,
        serp_provider=serp_provider,
        max_queries=5,
        use_cache=True,
    )
    progress_bar.progress(70, text="Filtering dates and verifying video semantic relevance...")

    gap_rows = []
    all_evidence = []
    for rec in eval_res.records:
        # Save to database
        try:
            db_manager.save_product_opportunity_record(rec)
        except Exception:
            pass

        all_evidence.extend(rec.video_evidence)
        gap_rows.append({
            "Candidate Keyword": rec.candidate_keyword,
            "Related Topic": rec.product_name,
            "Main Niche": rec.main_niche,
            "Sub-Niche": rec.sub_niche,
            "Product Category": rec.product_category,
            "Product": rec.product_name,
            "Market": rec.market,
            "Matching Videos": rec.matching_videos_count,
            "Latest Publish Date": rec.latest_publish_date,
            "Observed Competition": rec.observed_competition,
            "Search Coverage": rec.search_coverage,
            "Opportunity Status": rec.opportunity_status,
            "Explanation": rec.recommendation,
            "Suggested Angle": rec.suggested_angle,
            "Suggested Title": rec.suggested_title,
        })

    progress_bar.progress(100, text="Research complete!")
    time.sleep(0.1)
    progress_bar.empty()

    st.session_state.opp_results = gap_rows
    st.session_state.opp_recommended_list = eval_res.recommended_candidates
    st.session_state.opp_video_evidence = all_evidence
    st.session_state.opp_window_str = eval_res.research_window_str


def _run_seed_topic_research(clean_seed: str, market: str) -> None:
    """Execute 60-day YouTube research for an arbitrary seed topic."""
    st.session_state.opp_last_seed = clean_seed
    provider = YouTubeAutocompleteProvider(database_manager=db_manager)

    # 1. Expand seed into niche subtopics
    subtopic_queries = [
        f"{clean_seed} tutorial",
        f"{clean_seed} review",
        f"{clean_seed} mistakes",
        f"best {clean_seed}",
        f"{clean_seed} for beginners",
        f"how to use {clean_seed}",
        f"{clean_seed} guide",
        f"{clean_seed} comparison",
    ]

    expanded_ideas = []
    seen_topics = set()
    for sq in subtopic_queries:
        suggestions = provider.get_suggestions(sq, language="en", country=market, use_cache=True)
        for s in suggestions[:2]:
            kw = s.keyword.strip()
            if kw.lower() not in seen_topics and len(kw.split()) >= 2:
                seen_topics.add(kw.lower())
                expanded_ideas.append(kw)

    if not expanded_ideas:
        expanded_ideas = [
            f"{clean_seed} setup guide",
            f"{clean_seed} common mistakes",
            f"{clean_seed} long-term review",
            f"budget {clean_seed} alternatives",
        ]

    # Create temporary TaxonomyProduct proxy for evaluation
    proxy_prod = TaxonomyProduct(
        product_id=f"custom_{abs(hash(clean_seed))}",
        product_name=clean_seed.title(),
        main_niche="Custom / Seed Topic",
        sub_niche="User Inquiries",
        sub_sub_niche="Dynamic Research",
        product_category=clean_seed.title(),
        aliases=[clean_seed],
        candidate_keywords=expanded_ideas[:6],
    )

    serp_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
    eval_res = product_gap_engine.research_product(
        product=proxy_prod,
        market=market,
        serp_provider=serp_provider,
        max_queries=6,
        use_cache=True,
    )

    gap_rows = []
    all_evidence = []
    for rec in eval_res.records:
        try:
            db_manager.save_product_opportunity_record(rec)
        except Exception:
            pass

        all_evidence.extend(rec.video_evidence)
        gap_rows.append({
            "Candidate Keyword": rec.candidate_keyword,
            "Related Topic": rec.product_name,
            "Main Niche": rec.main_niche,
            "Sub-Niche": rec.sub_niche,
            "Product Category": rec.product_category,
            "Product": rec.product_name,
            "Market": rec.market,
            "Matching Videos": rec.matching_videos_count,
            "Latest Publish Date": rec.latest_publish_date,
            "Observed Competition": rec.observed_competition,
            "Search Coverage": rec.search_coverage,
            "Opportunity Status": rec.opportunity_status,
            "Explanation": rec.recommendation,
            "Suggested Angle": rec.suggested_angle,
            "Suggested Title": rec.suggested_title,
        })

    st.session_state.opp_results = gap_rows
    st.session_state.opp_recommended_list = eval_res.recommended_candidates
    st.session_state.opp_video_evidence = all_evidence
    st.session_state.opp_window_str = eval_res.research_window_str
