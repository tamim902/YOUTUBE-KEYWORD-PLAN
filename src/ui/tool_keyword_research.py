"""Tool 1: Keyword Research — Easy, Powerful & Channel-Aware.

Provides a clean, fast, beginner-friendly interface for YouTube keyword discovery:
- Auto-detects active channel niche, language, and country preferences
- Live YouTube Autocomplete with question patterns and preposition variations
- Alphabet-based expansion (A-Z)
- Genuine search volume status via volume provider architecture
- Clean results table: Keyword | Search Volume | Competition | Search Intent | Source | Opportunity Score
- One-click copy for every keyword, multi-select copy, and "Copy All Suggestions"
- Formula-safe CSV export
- Integrated Pattern Generator for candidate video angles across 8 frameworks
- 1-click cross-tool sending to Video Research, Competitor Research, and SEO Generator
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.classifier.service import default_classifier
from src.config import config
from src.intelligence.channel_manager import channel_manager
from src.intelligence.clustering import default_clusterer
from src.intelligence.scoring import default_scorer
from src.models.keyword import AutocompleteResult, KeywordItem
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import PatternCategory, PatternConfig, PatternLanguage
from src.providers.volume import default_volume_provider
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.channel_components import get_active_channel
from src.ui.components import (
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
)


def render_keyword_research_tool() -> None:
    """Render the upgraded Tool 1: Keyword Research."""
    active_channel = get_active_channel()

    st.markdown(
        """
        <div style="margin-bottom: 16px;">
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
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 16px; font-size: 0.85rem; color: #475569;">
            💡 <b>Data Transparency Notice:</b> Results represent real viewer queries actively suggested by YouTube's autocomplete engine. 
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
        # Default to active channel's niche if available
        st.session_state.kr_last_query = active_channel.channel_niche.split("&")[0].strip()
    if "kr_execution_time" not in st.session_state:
        st.session_state.kr_execution_time = 0.0
    if "kr_patterns" not in st.session_state:
        st.session_state.kr_patterns = []

    # Main Input Form
    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            query = st.text_input(
                "Enter Seed Keyword or Topic",
                value=st.session_state.kr_last_query,
                placeholder=f"e.g. {active_channel.channel_niche.split('&')[0].strip()}",
                key="kr_seed_input",
                help="Type a core keyword or niche topic to explore live YouTube autocomplete suggestions.",
            )
        with c_in2:
            st.write("")  # Spacing
            st.write("")
            btn_search = st.button("🔍 Find Keywords", type="primary", use_container_width=True, key="kr_submit_btn")

        # Compact Settings Expander (Pre-filled from active channel)
        with st.expander("⚙️ Advanced Research Settings (Optional)", expanded=False):
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            with col_s1:
                country_opts = list(config.supported_countries.keys())
                chan_country = active_channel.target_country.upper()
                def_country_idx = country_opts.index(chan_country) if chan_country in country_opts else 0
                selected_country = st.selectbox(
                    "Target Country",
                    options=country_opts,
                    format_func=lambda c: f"{config.supported_countries.get(c, c)} ({c})",
                    index=def_country_idx,
                    key="kr_country_select",
                )
            with col_s2:
                lang_opts = list(config.supported_languages.keys())
                chan_lang = active_channel.target_language.lower()
                def_lang_idx = lang_opts.index(chan_lang) if chan_lang in lang_opts else 0
                selected_lang = st.selectbox(
                    "Target Language",
                    options=lang_opts,
                    format_func=lambda l: f"{config.supported_languages.get(l, l)} ({l})",
                    index=def_lang_idx,
                    key="kr_lang_select",
                )
            with col_s3:
                enable_questions = st.checkbox(
                    "Include Question & Preposition Variations",
                    value=True,
                    help="Automatically queries question prefixes (how, why, what, best, for, vs) to expand search intent.",
                    key="kr_questions_check",
                )
            with col_s4:
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

            # 2. Question & Preposition Variations
            if enable_questions:
                modifier_prefixes = [
                    f"how to {clean_q}",
                    f"best {clean_q}",
                    f"why {clean_q}",
                    f"what is {clean_q}",
                    f"{clean_q} for beginners",
                    f"{clean_q} tutorial",
                    f"{clean_q} review",
                    f"{clean_q} vs",
                ]
                for mod_query in modifier_prefixes:
                    q_suggs = provider.get_suggestions(
                        mod_query,
                        language=selected_lang,
                        country=selected_country,
                        use_cache=True,
                    )
                    all_suggestions.extend(q_suggs[:3])

            # 3. Alphabet expansion if selected
            if enable_alphabet:
                letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "m", "p", "s", "t", "w"]
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
                    words_count = len(s.keyword.split())
                    comp_label = "Low (Long-tail)" if words_count >= 4 else "Moderate" if words_count == 3 else "High (Broad)"
                    
                    # Search volume via provider
                    vol_obj = default_volume_provider.get_keyword_volume(s.keyword, country=selected_country)

                    unique_results.append({
                        "Keyword": s.keyword,
                        "Search Volume": vol_obj.display_metric,
                        "Competition": comp_label,
                        "Search Intent": cls.primary_intent.value,
                        "Source": "YouTube Autocomplete",
                        "Opportunity Score": f"{int(score_res.total_score)} pts",
                        "_raw_score": score_res.total_score,
                    })

            # Sort by raw score descending
            unique_results.sort(key=lambda x: x["_raw_score"], reverse=True)
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
                        project_name=f"{active_channel.channel_name}: {clean_q}",
                    )
                    kw_items = [
                        KeywordItem(
                            keyword=r["Keyword"],
                            seed_keyword=clean_q,
                            source=r["Source"],
                            language=selected_lang,
                            country=selected_country,
                        )
                        for r in unique_results
                    ]
                    db_manager.save_keywords(search_id, kw_items)
                except Exception:
                    pass

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
            top_intent = results[0]["Search Intent"] if results else "N/A"
            st.metric("Top Search Intent", top_intent)
        with m3:
            st.metric("Search Volume Data", "Volume unavailable", help="Official YouTube search volumes are not public. Real autocomplete query signals are shown.")
        with m4:
            st.metric("Retrieval Speed", f"{st.session_state.kr_execution_time:.2f}s")

        # Filters & Search Controls
        c_f1, c_f2 = st.columns([2.5, 1.5])
        with c_f1:
            table_search = st.text_input("🔍 Filter keywords", placeholder="Type to filter results...", key="kr_table_search")
        with c_f2:
            intents = ["All Intents"] + sorted(list(set(r["Search Intent"] for r in results)))
            selected_intent = st.selectbox("Filter Intent", intents, key="kr_intent_filter")

        # Apply filtering
        filtered_results = list(results)
        if table_search.strip():
            filtered_results = [r for r in filtered_results if table_search.lower().strip() in r["Keyword"].lower()]
        if selected_intent != "All Intents":
            filtered_results = [r for r in filtered_results if r["Search Intent"] == selected_intent]

        # Results Table exactly matching Keyword | Search Volume | Competition | Search Intent | Source | Opportunity Score
        st.caption(f"Showing **{len(filtered_results)}** of {len(results)} discovered keywords:")
        df_display = pd.DataFrame(filtered_results)
        
        st.dataframe(
            df_display[[
                "Keyword", "Search Volume", "Competition", "Search Intent", "Source", "Opportunity Score"
            ]],
            column_config={
                "Keyword": st.column_config.TextColumn("Keyword", width="large"),
                "Search Volume": st.column_config.TextColumn("Search Volume", width="medium"),
                "Competition": st.column_config.TextColumn("Competition", width="medium"),
                "Search Intent": st.column_config.TextColumn("Search Intent", width="medium"),
                "Source": st.column_config.TextColumn("Source", width="medium"),
                "Opportunity Score": st.column_config.TextColumn("Opportunity Score", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Bulk & Multi-Select Copy Actions
        st.markdown("#### 📋 Copy & Export Actions")
        c_cp1, c_cp2, c_cp3, c_cp4 = st.columns([1.5, 1.5, 1.5, 1.5])

        with c_cp1:
            all_kw_text = "\n".join(r["Keyword"] for r in filtered_results)
            st.download_button(
                label=f"📋 Download All ({len(filtered_results)})",
                data=all_kw_text,
                file_name=f"all_keywords_{st.session_state.kr_last_query.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_dl_all_btn",
                help="Download or copy all discovered keywords formatted as plain text.",
            )

        with c_cp2:
            export_svc = ExportService()
            clean_df = pd.DataFrame(filtered_results).drop(columns=["_raw_score"], errors="ignore")
            csv_bytes = export_svc.export_csv(clean_df, sanitize_formulas=True)
            st.download_button(
                label="📥 Export CSV",
                data=csv_bytes,
                file_name=f"keywords_{st.session_state.kr_last_query.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="kr_dl_csv_btn",
            )

        with c_cp3:
            # Multi-keyword selection to copy together
            with st.popover("📋 1-Click Copy"):
                st.caption("1-Click Copy Selected or All Keywords:")
                with st.expander("Copy All Keywords", expanded=False):
                    st.code(all_kw_text, language=None)
                kw_options = [r["Keyword"] for r in filtered_results]
                selected_multi = st.multiselect("Pick specific keywords to copy:", options=kw_options, key="kr_multi_select")
                if selected_multi:
                    multi_text = "\n".join(selected_multi)
                    st.code(multi_text, language=None)
                    st.success(f"✅ {len(selected_multi)} keywords ready to copy above!")

        with c_cp4:
            if st.button("🔄 Retry Research", use_container_width=True, key="kr_retry_btn"):
                st.session_state.kr_results = []
                st.rerun()

        # Per-Keyword Quick Actions
        st.markdown("#### 🚀 Send Keyword to Other Tools")
        if filtered_results:
            top_kw = filtered_results[0]["Keyword"]
            
            c_sel_col, c_btn_vr, c_btn_cr, c_btn_seo = st.columns([2, 1.5, 1.5, 1.5])
            with c_sel_col:
                picked_kw = st.selectbox(
                    "Selected Keyword for Handoff",
                    options=[r["Keyword"] for r in filtered_results],
                    index=0,
                    key="kr_picked_handoff_select",
                )
            with c_btn_vr:
                st.write("")
                st.write("")
                if st.button("🎥 Video Research", use_container_width=True, key="kr_send_vr_btn"):
                    st.session_state.vr_target_keyword = picked_kw
                    st.session_state.current_page = TOOL_VIDEO_RESEARCH
                    st.rerun()
            with c_btn_cr:
                st.write("")
                st.write("")
                if st.button("🎯 Competitor Research", use_container_width=True, key="kr_send_cr_btn"):
                    st.session_state.cr_last_query = picked_kw
                    st.session_state.current_page = TOOL_COMPETITOR_RESEARCH
                    st.rerun()
            with c_btn_seo:
                st.write("")
                st.write("")
                if st.button("✨ SEO Generator", type="primary", use_container_width=True, key="kr_send_seo_btn"):
                    st.session_state.seo_main_keyword = picked_kw
                    st.session_state.seo_secondary_keywords = ", ".join(r["Keyword"] for r in filtered_results[1:5])
                    st.session_state.current_page = TOOL_SEO_GENERATOR
                    st.rerun()

    elif not results and st.session_state.kr_last_query:
        st.warning(f"No autocomplete suggestions found for '{st.session_state.kr_last_query}'. Try a shorter or broader seed phrase.")
    else:
        st.info(f"👆 Enter a seed keyword above to start discovering high-intent search queries for {active_channel.channel_name}.")

    st.write("")
    st.markdown("---")

    # ==============================================================================
    # RESTORED KEYWORD PATTERN GENERATOR (INTEGRATED INTO KEYWORD RESEARCH)
    # ==============================================================================
    st.markdown("### 🧩 Keyword Pattern Generator (Candidate Video Ideas)")
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #7C3AED; 
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 16px; font-size: 0.85rem; color: #475569;">
            💡 <b>Candidate Suggestions Notice:</b> Generated patterns are candidate keyword ideas produced across 8 proven creator frameworks 
            (Listicles, Best & Buying, Reviews, How-To, Comparisons, Questions, Audience, Time Modifiers). 
            They are structural hypotheses for content planning, <b>not</b> verified historical search volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    pat_seed_default = st.session_state.kr_last_query or active_channel.channel_niche.split("&")[0].strip()

    with st.expander("🛠️ Configure & Generate Keyword Patterns", expanded=(len(st.session_state.kr_patterns) == 0)):
        c_pat1, c_pat2 = st.columns(2)
        with c_pat1:
            pat_seed = st.text_input(
                "Seed Topic for Patterns",
                value=pat_seed_default,
                placeholder=f"e.g. {pat_seed_default}",
                key="kr_pat_seed_input",
                help="The core topic or noun to plug into creator framework patterns.",
            )
            pat_alternatives = st.text_input(
                "Comparison Alternatives / Competitors (Optional)",
                placeholder="e.g. keychron, epomaker, ducky",
                key="kr_pat_alts_input",
                help="Optional competitor brands or alternatives for head-to-head comparison patterns.",
            )
        with c_pat2:
            cat_display_names = {
                PatternCategory.BEST_BUYING: "Best & Buying Intent (Best [kw], Top [kw])",
                PatternCategory.REVIEWS: "Reviews & Feedback ([kw] review, Is [kw] worth it?)",
                PatternCategory.HOW_TO: "How-To & Tutorials (How to [kw], [kw] tutorial)",
                PatternCategory.COMPARISON: "Comparison ([kw] vs [alt], [kw] alternatives)",
                PatternCategory.QUESTIONS: "Questions ([kw] questions, problems and solutions)",
                PatternCategory.LISTICLES: "Listicles & Rankings (Top 5 [kw], Best [kw])",
                PatternCategory.AUDIENCE: "Audience & Use-Case ([kw] for beginners, for pros)",
                PatternCategory.TIME_MODIFIERS: "Time Modifiers (Current Year [kw])",
            }
            selected_categories = st.multiselect(
                "Pattern Framework Categories",
                options=list(cat_display_names.keys()),
                default=list(cat_display_names.keys()),
                format_func=lambda c: cat_display_names[c],
                key="kr_pat_cats_select",
            )
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                include_current_year = st.checkbox("Include Current Year", value=True, key="kr_pat_year_check")
            with col_opt2:
                max_patterns = st.slider("Max Patterns Limit", min_value=10, max_value=100, value=30, step=10, key="kr_pat_limit_slider")

        if st.button("✨ Generate Keyword Patterns", type="primary", use_container_width=True, key="kr_pat_gen_btn"):
            if not pat_seed.strip():
                st.warning("Please provide a seed topic for patterns.")
            elif not selected_categories:
                st.warning("Please select at least one pattern category.")
            else:
                alts = [a.strip() for a in pat_alternatives.split(",") if a.strip()] if pat_alternatives else None
                pat_cfg = PatternConfig(
                    seeds=[pat_seed.strip()],
                    categories=selected_categories,
                    language_mode=PatternLanguage.EN,
                    alternatives=alts,
                    include_current_year=include_current_year,
                    max_generated=max_patterns,
                )
                pat_generator = SmartKeywordPatternGenerator()
                generated_list = pat_generator.generate(pat_cfg)
                st.session_state.kr_patterns = generated_list
                st.rerun()

    # Display Generated Patterns
    patterns = st.session_state.kr_patterns
    if patterns:
        st.markdown(f"##### 📋 Generated Pattern Candidates ({len(patterns)})")
        st.caption("Select any pattern to run empirical Autocomplete research or send to SEO Generator:")

        pat_rows = []
        for p in patterns:
            pat_rows.append({
                "Pattern Candidate": p.keyword,
                "Category": p.pattern_category.replace("_", " ").title(),
                "Intent": p.intent.value if hasattr(p.intent, "value") else str(p.intent),
                "Framework": "Template-Generated Idea",
            })

        df_pat = pd.DataFrame(pat_rows)
        st.dataframe(
            df_pat,
            column_config={
                "Pattern Candidate": st.column_config.TextColumn("Candidate Pattern", width="large"),
                "Category": st.column_config.TextColumn("Framework Category", width="medium"),
                "Intent": st.column_config.TextColumn("Hypothesized Intent", width="medium"),
                "Framework": st.column_config.TextColumn("Type", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

        c_pact1, c_pact2, c_pact3 = st.columns([2, 2, 2])
        with c_pact1:
            all_pat_text = "\n".join(p.keyword for p in patterns)
            st.download_button(
                label="📋 Copy / Export All Patterns",
                data=all_pat_text,
                file_name=f"patterns_{pat_seed.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_pat_dl_btn",
            )
        with c_pact2:
            top_pattern = patterns[0].keyword
            if st.button(f"🔍 Run '{top_pattern[:20]}...' in Autocomplete", use_container_width=True, key="kr_pat_run_ac_btn"):
                st.session_state.kr_last_query = top_pattern
                st.rerun()
        with c_pact3:
            if st.button(f"✨ Send Top Pattern to SEO Generator", type="primary", use_container_width=True, key="kr_pat_send_seo_btn"):
                st.session_state.seo_main_keyword = patterns[0].keyword
                st.session_state.seo_secondary_keywords = ", ".join(p.keyword for p in patterns[1:5])
                st.session_state.current_page = TOOL_SEO_GENERATOR
                st.rerun()
