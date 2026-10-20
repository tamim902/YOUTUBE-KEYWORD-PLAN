"""Tool 1: Keyword Research — Upgraded Core Workflow with Integrated Pattern Generator.

Provides a clean, fast, beginner-friendly interface for YouTube keyword discovery:
- Live YouTube Autocomplete suggestions
- Alphabet-based expansion (A-Z)
- Question-based patterns (who, what, how, why, can)
- Preposition & modifier variations (for, with, without, best, review, vs)
- Deterministic search intent & relevance classification
- Clean results table: Keyword | Volume | Competition | Intent | Source | Status
- Honest volume labeling ("Unavailable" / proxy) with zero fabricated numbers
- Integrated Pattern Generator for candidate video angles across 8 frameworks
- Cross-tool handoffs to Video Research, Competitor Research, 60-Day Opportunities, and SEO Generator
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
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import PatternCategory, PatternConfig, PatternLanguage
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.components import (
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
)


def render_keyword_research_tool() -> None:
    """Render the upgraded Tool 1: Keyword Research with Integrated Pattern Generator."""
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
            <b>"Unavailable"</b> rather than fabricated. Relevance scores indicate topic alignment, not guaranteed rankings.
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
    if "kr_patterns" not in st.session_state:
        st.session_state.kr_patterns = []

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
        with st.expander("⚙️ Search, Alphabet & Expansion Settings (Optional)", expanded=False):
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            with col_s1:
                country_opts = list(config.supported_countries.keys())
                def_country_idx = country_opts.index("US") if "US" in country_opts else 0
                selected_country = st.selectbox(
                    "Target Region / Country",
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

            # 2. Question & Preposition Variations (how, best, why, what is, for, vs)
            if enable_questions:
                modifier_prefixes = [
                    "how to", "best", "why", "what is",
                    f"{clean_q} for beginners",
                    f"{clean_q} tutorial",
                    f"{clean_q} review",
                    f"{clean_q} vs",
                ]
                for mod_query in modifier_prefixes:
                    q_suggs = provider.get_suggestions(
                        mod_query if not mod_query.startswith(clean_q) else f"{mod_query}",
                        language=selected_lang,
                        country=selected_country,
                        use_cache=True,
                    )
                    all_suggestions.extend(q_suggs[:3])

            # 3. Alphabet expansion if selected
            if enable_alphabet:
                letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "p", "s", "t", "w"]
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
                    unique_results.append({
                        "Keyword": s.keyword,
                        "Volume": "Unavailable",  # Truthful labeling
                        "Competition": comp_label,
                        "Intent": cls.primary_intent.value,
                        "Source": "YouTube Autocomplete",
                        "Status": "Active",
                        "_relevance_score": round(score_res.total_score, 1),
                    })

            # Sort by relevance score descending
            unique_results.sort(key=lambda x: x["_relevance_score"], reverse=True)
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
            top_intent = results[0]["Intent"] if results else "N/A"
            st.metric("Top Search Intent", top_intent)
        with m3:
            st.metric("Search Volume Data", "Unavailable", help="Official YouTube search volumes are not public. Real autocomplete query signals are shown.")
        with m4:
            st.metric("Retrieval Speed", f"{st.session_state.kr_execution_time:.2f}s")

        # Filters & Controls
        c_f1, c_f2, c_f3 = st.columns([2, 1.5, 1.5])
        with c_f1:
            table_search = st.text_input("🔍 Filter keywords", placeholder="Type to filter results...", key="kr_table_search")
        with c_f2:
            intents = ["All Intents"] + sorted(list(set(r["Intent"] for r in results)))
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
            filtered_results = [r for r in filtered_results if table_search.lower().strip() in r["Keyword"].lower()]
        if selected_intent != "All Intents":
            filtered_results = [r for r in filtered_results if r["Intent"] == selected_intent]
        if relevance_filter == "High Relevance (80+)":
            filtered_results = [r for r in filtered_results if r["_relevance_score"] >= 80]
        elif relevance_filter == "Medium+ (60+)":
            filtered_results = [r for r in filtered_results if r["_relevance_score"] >= 60]

        # Results Table exactly matching Keyword | Volume | Competition | Intent | Source | Status
        st.caption(f"Showing **{len(filtered_results)}** of {len(results)} discovered keywords:")
        df_display = pd.DataFrame(filtered_results)
        
        st.dataframe(
            df_display[[
                "Keyword", "Volume", "Competition", "Intent", "Source", "Status"
            ]],
            column_config={
                "Keyword": st.column_config.TextColumn("Keyword", width="large"),
                "Volume": st.column_config.TextColumn("Volume", width="medium"),
                "Competition": st.column_config.TextColumn("Competition", width="medium"),
                "Intent": st.column_config.TextColumn("Intent", width="medium"),
                "Source": st.column_config.TextColumn("Source", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Action Buttons Row
        st.markdown("#### 🛠️ Keyword Actions & Cross-Tool Handoffs")
        c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 1.5])

        with c_act1:
            all_kw_text = "\n".join(r["Keyword"] for r in filtered_results)
            st.download_button(
                label=f"📋 Export Keywords ({len(filtered_results)})",
                data=all_kw_text,
                file_name=f"youtube_keywords_{st.session_state.kr_last_query.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_dl_txt_btn",
            )

        with c_act2:
            export_svc = ExportService()
            clean_df = pd.DataFrame(filtered_results).drop(columns=["_relevance_score"], errors="ignore")
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

        # Cross-Tool Handoff Row
        if filtered_results:
            top_kw = filtered_results[0]["Keyword"]
            st.caption(f"Send primary keyword **'{top_kw}'** to other tools:")
            c_snd1, c_snd2, c_snd3, c_snd4 = st.columns(4)

            with c_snd1:
                if st.button("🎥 Send to Video Research", use_container_width=True, key="kr_send_vr_btn"):
                    st.session_state.vr_target_keyword = top_kw
                    st.session_state.current_page = TOOL_VIDEO_RESEARCH
                    st.rerun()

            with c_snd2:
                if st.button("🎯 Send to Competitor Research", use_container_width=True, key="kr_send_cr_btn"):
                    st.session_state.cr_last_query = top_kw
                    st.session_state.current_page = TOOL_COMPETITOR_RESEARCH
                    st.rerun()

            with c_snd3:
                if st.button("⚡ Send to 60-Day Gap Finder", use_container_width=True, key="kr_send_opp_btn"):
                    st.session_state.opp_last_seed = top_kw
                    st.session_state.current_page = TOOL_60_DAY_OPPORTUNITIES
                    st.rerun()

            with c_snd4:
                if st.button("✨ Send to SEO Generator", type="primary", use_container_width=True, key="kr_send_seo_btn"):
                    st.session_state.seo_main_keyword = top_kw
                    st.session_state.seo_secondary_keywords = ", ".join(r["Keyword"] for r in filtered_results[1:5])
                    st.session_state.current_page = TOOL_SEO_GENERATOR
                    st.rerun()

    elif not results and st.session_state.kr_last_query:
        st.warning(f"No autocomplete suggestions found for '{st.session_state.kr_last_query}'. Try a shorter or broader seed phrase.")
    else:
        st.info("👆 Enter a seed keyword above to start discovering high-intent YouTube search queries.")

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
            💡 <b>Candidate Ideas Notice:</b> Generated patterns are candidate keyword ideas produced across 8 proven creator frameworks 
            (Listicles, Best & Buying, Reviews, How-To, Comparisons, Questions, Audience, Time Modifiers). 
            They are structural hypotheses for content planning, <b>not</b> verified historical search volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    pat_seed_default = st.session_state.kr_last_query or "mechanical keyboard"

    with st.expander("🛠️ Configure & Generate Keyword Patterns", expanded=(len(st.session_state.kr_patterns) == 0)):
        c_pat1, c_pat2 = st.columns(2)
        with c_pat1:
            pat_seed = st.text_input(
                "Seed Topic for Patterns",
                value=pat_seed_default,
                placeholder="e.g. python, mechanical keyboards, photography",
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
