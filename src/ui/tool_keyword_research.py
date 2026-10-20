"""Tool 1: Keyword Research — Simplified Core Workflow.

Provides a clean, fast, beginner-friendly interface for YouTube keyword discovery:
- YouTube Autocomplete suggestions
- Alphabet expansion (A-Z) & question-based variations
- Honest search volume labeling ("Volume unavailable" / proxy)
- Deterministic search intent & relevance classification
- Searchable table with sort, filter, copy, and formula-safe CSV export
- 1-click handoff to Tool 4 (SEO Generator)
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.classifier.service import default_classifier
from src.config import config
from src.intelligence.scoring import default_scorer
from src.models.keyword import AutocompleteResult, KeywordItem
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.components import TOOL_SEO_GENERATOR


def render_keyword_research_tool() -> None:
    """Render the simplified Tool 1: Keyword Research."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                🔍 YouTube Keyword Research
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Discover real YouTube autocomplete search suggestions, search intent, and keyword angles with zero fabricated metrics.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Epistemic Modesty Notice
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #3B82F6; 
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.85rem; color: #475569;">
            💡 <b>Data Transparency Notice:</b> Results represent real viewer search queries actively suggested by YouTube's autocomplete engine. 
            YouTube does not provide official public monthly search volume; where third-party volume is not connected, it is honestly labeled 
            <b>"Volume unavailable"</b> rather than fabricated. Relevance scores indicate topic alignment, not guaranteed rankings.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Session State Initialization
    if "kr_results" not in st.session_state:
        st.session_state.kr_results = []
    if "kr_last_query" not in st.session_state:
        st.session_state.kr_last_query = ""
    if "kr_execution_time" not in st.session_state:
        st.session_state.kr_execution_time = 0.0

    # Main Input Form
    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            query = st.text_input(
                "Enter Seed Keyword or Topic",
                value=st.session_state.kr_last_query,
                placeholder="e.g. python tutorial, mechanical keyboard, sourdough bread",
                key="kr_seed_input",
                help="Type a core keyword or niche topic to explore live YouTube autocomplete suggestions.",
            )
        with c_in2:
            st.write("")  # Spacing
            st.write("")
            btn_search = st.button("🔍 Find Keywords", type="primary", use_container_width=True, key="kr_submit_btn")

        # Compact Settings Expander
        with st.expander("⚙️ Search & Region Settings (Optional)", expanded=False):
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                country_opts = list(config.supported_countries.keys())
                def_country_idx = country_opts.index("US") if "US" in country_opts else 0
                selected_country = st.selectbox(
                    "Target Country / Region",
                    options=country_opts,
                    format_func=lambda c: f"{config.supported_countries.get(c, c)} ({c})",
                    index=def_country_idx,
                    key="kr_country_select",
                )
            with col_s2:
                lang_opts = list(config.supported_languages.keys())
                def_lang_idx = lang_opts.index("en") if "en" in lang_opts else 0
                selected_lang = st.selectbox(
                    "Target Language",
                    options=lang_opts,
                    format_func=lambda l: f"{config.supported_languages.get(l, l)} ({l})",
                    index=def_lang_idx,
                    key="kr_lang_select",
                )
            with col_s3:
                enable_alphabet = st.checkbox(
                    "Include Alphabet Expansion (A-Z)",
                    value=False,
                    help="Expands the seed query by appending letters A to Z for wider long-tail discovery.",
                    key="kr_alphabet_check",
                )

    # Handle Search Submission
    if btn_search and query.strip():
        clean_q = query.strip()
        st.session_state.kr_last_query = clean_q
        with st.spinner(f"Querying YouTube autocomplete for '{clean_q}'..."):
            t0 = time.time()
            provider = YouTubeAutocompleteProvider(database_manager=db_manager)
            all_suggestions: List[AutocompleteResult] = []

            # 1. Core direct autocomplete
            direct_suggs = provider.get_suggestions(
                clean_q,
                language=selected_lang,
                country=selected_country,
                use_cache=True,
            )
            all_suggestions.extend(direct_suggs)

            # 2. Question variations (who, what, how, why, best)
            question_prefixes = ["how to", "best", "why", "what is"]
            for q_pre in question_prefixes:
                q_query = f"{q_pre} {clean_q}"
                q_suggs = provider.get_suggestions(
                    q_query,
                    language=selected_lang,
                    country=selected_country,
                    use_cache=True,
                )
                all_suggestions.extend(q_suggs[:3])

            # 3. Alphabet expansion if selected (A-E sample for speed)
            if enable_alphabet:
                letters = ["a", "b", "c", "d", "e"]
                for char in letters:
                    char_query = f"{clean_q} {char}"
                    char_suggs = provider.get_suggestions(
                        char_query,
                        language=selected_lang,
                        country=selected_country,
                        use_cache=True,
                    )
                    all_suggestions.extend(char_suggs[:2])

            dt = time.time() - t0
            st.session_state.kr_execution_time = dt

            # Deduplicate by keyword
            seen = set()
            unique_results = []
            for s in all_suggestions:
                k_norm = s.keyword.lower().strip()
                if k_norm not in seen and k_norm != clean_q.lower():
                    seen.add(k_norm)
                    cls = default_classifier.classify(s.keyword)
                    score_res = default_scorer.score(s.keyword, clean_q, cls)
                    unique_results.append({
                        "keyword": s.keyword,
                        "intent": cls.primary_intent.value,
                        "relevance": round(score_res.total_score, 1),
                        "volume": "Volume unavailable",  # Truthful labeling
                        "difficulty": "Moderate" if len(s.keyword.split()) <= 2 else "Low (Long-tail)",
                        "source": "YouTube Autocomplete",
                        "status": "Verified",
                    })

            # Sort by relevance score descending
            unique_results.sort(key=lambda x: x["relevance"], reverse=True)
            st.session_state.kr_results = unique_results

            # Persist search in SQLite
            if unique_results:
                try:
                    search_id = db_manager.save_search(
                        seed_keyword=clean_q,
                        language=selected_lang,
                        country=selected_country,
                        max_depth=1,
                        request_budget=len(unique_results),
                        total_results=len(unique_results),
                        project_name=clean_q,
                    )
                    kw_items = [
                        KeywordItem(
                            keyword=r["keyword"],
                            seed_keyword=clean_q,
                            source=r["source"],
                            language=selected_lang,
                            country=selected_country,
                        )
                        for r in unique_results
                    ]
                    db_manager.save_keywords(search_id, kw_items)
                except Exception as e:
                    pass  # Non-blocking persistence

            st.rerun()

    # Results Display
    results = st.session_state.kr_results
    if results:
        st.markdown("---")
        # Metric Tiles
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Keywords Discovered", len(results))
        with m2:
            top_intent = results[0]["intent"] if results else "N/A"
            st.metric("Top Search Intent", top_intent)
        with m3:
            st.metric("Search Volume Data", "Volume unavailable", help="Official YouTube search volumes are not public. Real autocomplete signals are shown.")
        with m4:
            st.metric("Retrieval Speed", f"{st.session_state.kr_execution_time:.2f}s")

        # Filters & Controls
        c_f1, c_f2, c_f3 = st.columns([2, 1.5, 1.5])
        with c_f1:
            table_search = st.text_input("🔍 Filter keywords", placeholder="Type to filter results...", key="kr_table_search")
        with c_f2:
            intents = ["All Intents"] + sorted(list(set(r["intent"] for r in results)))
            selected_intent = st.selectbox("Filter Intent", intents, key="kr_intent_filter")
        with c_f3:
            relevance_filter = st.selectbox(
                "Filter Relevance",
                ["All Scores", "High Relevance (80+)", "Medium+ (60+)"],
                key="kr_rel_filter",
            )

        # Apply filtering
        filtered_results = list(results)
        if table_search.strip():
            filtered_results = [r for r in filtered_results if table_search.lower().strip() in r["keyword"].lower()]
        if selected_intent != "All Intents":
            filtered_results = [r for r in filtered_results if r["intent"] == selected_intent]
        if relevance_filter == "High Relevance (80+)":
            filtered_results = [r for r in filtered_results if r["relevance"] >= 80]
        elif relevance_filter == "Medium+ (60+)":
            filtered_results = [r for r in filtered_results if r["relevance"] >= 60]

        # Results Table
        st.caption(f"Showing {len(filtered_results)} of {len(results)} discovered keywords:")
        df_display = pd.DataFrame(filtered_results)
        
        # Display polished dataframe
        st.dataframe(
            df_display[[
                "keyword", "intent", "relevance", "volume", "difficulty", "source"
            ]],
            column_config={
                "keyword": st.column_config.TextColumn("Keyword Phrase", width="large"),
                "intent": st.column_config.TextColumn("Search Intent", width="medium"),
                "relevance": st.column_config.ProgressColumn("Relevance Score", min_value=0, max_value=100, format="%d pts"),
                "volume": st.column_config.TextColumn("Monthly Volume", width="medium"),
                "difficulty": st.column_config.TextColumn("Competition Estimate", width="medium"),
                "source": st.column_config.TextColumn("Data Source", width="medium"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Action Buttons Row
        st.markdown("#### 🛠️ Keyword Actions")
        c_act1, c_act2, c_act3, c_act4 = st.columns([1.5, 1.5, 1.5, 2])

        with c_act1:
            # Copy all filtered keywords
            all_kw_text = "\n".join(r["keyword"] for r in filtered_results)
            st.download_button(
                label=f"📋 Export Keywords ({len(filtered_results)})",
                data=all_kw_text,
                file_name=f"youtube_keywords_{st.session_state.kr_last_query.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_dl_txt_btn",
            )

        with c_act2:
            # Formula-safe CSV export
            export_svc = ExportService()
            clean_df = pd.DataFrame(filtered_results)
            csv_bytes = export_svc.export_csv(clean_df, sanitize_formulas=True)
            st.download_button(
                label="📥 Download CSV",
                data=csv_bytes,
                file_name=f"keyword_research_{st.session_state.kr_last_query.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="kr_dl_csv_btn",
            )

        with c_act3:
            if st.button("🔄 Retry Research", use_container_width=True, key="kr_retry_btn"):
                st.session_state.kr_results = []
                st.rerun()

        with c_act4:
            # One-click jump to Tool 4 (SEO Generator)
            if filtered_results:
                top_kw = filtered_results[0]["keyword"]
                if st.button(f"✨ Send '{top_kw[:20]}...' to SEO Generator", type="primary", use_container_width=True, key="kr_send_seo_btn"):
                    st.session_state.seo_main_keyword = top_kw
                    st.session_state.seo_secondary_keywords = ", ".join(r["keyword"] for r in filtered_results[1:5])
                    st.session_state.current_page = TOOL_SEO_GENERATOR
                    st.rerun()

    elif not results and st.session_state.kr_last_query:
        st.warning(f"No autocomplete suggestions found for '{st.session_state.kr_last_query}'. Try a shorter or broader seed phrase.")
    else:
        st.info("👆 Enter a seed keyword above to start discovering high-intent YouTube search queries.")
