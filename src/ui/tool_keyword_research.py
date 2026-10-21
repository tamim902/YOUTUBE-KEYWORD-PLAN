"""Tool 1: Keyword Research — Easy, Powerful, Channel-Aware & vidIQ-Style Intelligence.

Provides a clean, fast, beginner-friendly interface for YouTube keyword discovery:
- Auto-detects active channel niche, language, and country preferences
- "Find for This Channel" action button with automated backlog deduplication
- Live YouTube Autocomplete with space expansion, question patterns, prepositions, and 2026 freshness
- vidIQ-style Overall Opportunity Scores (0-100) with color badges (Green >= 65, Yellow 45-64, Red < 45)
- Explainable Ranking Chance (Very High, High, Medium, Low) based on competition, niche relevance & intent
- Competition badges (🟢 Low / Easy to Rank, 🟡 Medium / Balanced, 🔴 High / Saturated)
- Search Volume Demand Index and connected third-party volume transparency
- Interactive vidIQ-Style YouTube Tag Studio with character count tracking (500-char YouTube upload limit)
- 1-Click Copy All Tags for YouTube Studio ready to paste into upload metadata
- Formula-safe CSV export for selected or all visible keywords
- 1-click cross-tool sending to Video Research, Competitor Research, and SEO Generator
"""

from __future__ import annotations

import io
import textwrap
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.classifier.service import default_classifier
from src.config import config
from src.intelligence.channel_manager import channel_manager
from src.intelligence.clustering import default_clusterer
from src.intelligence.decision_helper import KeywordDecisionSummary, keyword_decision_helper
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


def _render_html(html_str: str) -> None:
    """Render HTML cleanly without triggering Markdown indented code block parsing."""
    dedented = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(dedented)
    else:
        st.markdown(dedented, unsafe_allow_html=True)


def render_keyword_research_tool() -> None:
    """Render the upgraded Tool 1: Keyword Research with vidIQ-style intelligence."""
    active_channel = get_active_channel()

    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                🔍 YouTube Keyword Research & Tag Studio
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Discover real YouTube autocomplete search suggestions with vidIQ-style opportunity scores, competition badges, ranking chances, and ready-to-copy YouTube Studio tags.
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
            💡 <b>Data Transparency Notice:</b> Results represent real viewer queries actively suggested by YouTube's autocomplete engine, 
            along with structural pattern hypotheses across 8 creator frameworks. YouTube does not provide official public monthly search volume; 
            where third-party volume is not connected, search demand is honestly labeled based on live YouTube autocomplete ranking signals. 
            Relevance and ranking scores evaluate competition and topic alignment, not guaranteed algorithm traffic.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Session State Initialization
    if "kr_results" not in st.session_state:
        st.session_state.kr_results = []
    if "kr_last_query" not in st.session_state:
        st.session_state.kr_last_query = active_channel.channel_niche.split("&")[0].strip()
    if "kr_execution_time" not in st.session_state:
        st.session_state.kr_execution_time = 0.0
    if "kr_patterns" not in st.session_state:
        st.session_state.kr_patterns = []

    # Main Input Form
    with st.container():
        c_in1, c_in2, c_in3 = st.columns([3.2, 1.3, 1.5])
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
        with c_in3:
            st.write("")
            st.write("")
            btn_find_channel = st.button(
                "🎯 Find for This Channel",
                type="secondary",
                use_container_width=True,
                key="kr_chan_search_btn",
                help=f"Auto-research keywords for {active_channel.channel_name} ({active_channel.channel_niche}) excluding saved backlog.",
            )

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
                    help="Automatically queries high-converting intent prefixes (how to, best, tutorial, review, vs, 2026).",
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
    should_run_search = False
    is_channel_discovery = False
    clean_q = ""

    if btn_find_channel:
        clean_q = active_channel.channel_niche.split("&")[0].strip()
        st.session_state["kr_seed_input"] = clean_q
        st.session_state.kr_last_query = clean_q
        is_channel_discovery = True
        should_run_search = True
    elif btn_search and query.strip():
        clean_q = " ".join(query.strip().split())
        st.session_state.kr_last_query = clean_q
        is_channel_discovery = False
        should_run_search = True

    if should_run_search and clean_q:
        spinner_msg = (
            f"🎯 Auto-discovering keywords & tags tailored to {active_channel.channel_name} ({clean_q})..."
            if is_channel_discovery
            else f"Querying YouTube autocomplete & analyzing ranking chances for '{clean_q}'..."
        )
        with st.spinner(spinner_msg):
            t0 = time.time()
            provider = YouTubeAutocompleteProvider(database_manager=db_manager)
            all_suggestions: List[AutocompleteResult] = []
            executed_queries: List[str] = [clean_q]

            # 1. Core direct autocomplete
            direct_suggs = provider.get_suggestions(
                clean_q,
                language=selected_lang,
                country=selected_country,
                use_cache=True,
            )
            all_suggestions.extend(direct_suggs)

            # 2. Space-expanded autocomplete (top immediate completions)
            space_suggs = provider.get_suggestions(
                f"{clean_q} ",
                language=selected_lang,
                country=selected_country,
                use_cache=True,
            )
            all_suggestions.extend(space_suggs)

            # 3. Question, intent & year variations
            if enable_questions:
                modifier_prefixes = [
                    f"best {clean_q}",
                    f"how to {clean_q}",
                    f"{clean_q} tutorial",
                    f"{clean_q} review",
                    f"{clean_q} for beginners",
                    f"{clean_q} vs",
                    f"why {clean_q}",
                    f"{clean_q} 2026",
                    f"{clean_q} for",
                    f"{clean_q} with",
                    f"{clean_q} under",
                ]
                for mod_query in modifier_prefixes:
                    executed_queries.append(mod_query)
                    q_suggs = provider.get_suggestions(
                        mod_query,
                        language=selected_lang,
                        country=selected_country,
                        use_cache=True,
                    )
                    all_suggestions.extend(q_suggs[:3])

            # 4. Alphabet expansion if selected
            if enable_alphabet:
                letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "m", "s", "t", "w"]
                for char in letters:
                    char_query = f"{clean_q} {char}"
                    executed_queries.append(char_query)
                    char_suggs = provider.get_suggestions(
                        char_query,
                        language=selected_lang,
                        country=selected_country,
                        use_cache=True,
                    )
                    all_suggestions.extend(char_suggs[:2])

            # 5. Relevant creator keyword patterns across 8 frameworks
            pat_cfg = PatternConfig(
                seeds=[clean_q],
                categories=list(PatternCategory),
                language_mode=PatternLanguage.EN,
                alternatives=None,
                include_current_year=True,
                max_generated=25,
            )
            pat_generator = SmartKeywordPatternGenerator()
            generated_patterns = pat_generator.generate(pat_cfg)

            # Load channel backlog if channel discovery
            saved_list = st.session_state.get(f"saved_ideas_channel_{active_channel.id}", [])
            saved_topics = {s.get("topic", "").lower().strip() for s in saved_list if isinstance(s, dict) and s.get("topic")}
            saved_kws = {s.get("keyword", "").lower().strip() for s in saved_list if isinstance(s, dict) and s.get("keyword")}
            excluded_channel_backlog = saved_topics.union(saved_kws).union({t.lower().strip() for t in active_channel.existing_video_topics})

            dt = time.time() - t0
            st.session_state.kr_execution_time = dt
            st.session_state["kr_executed_queries"] = executed_queries

            # Filter unwanted foreign country artifacts if target is general/US
            foreign_country_noise = ["in pakistan", "in india", "in bangladesh", "in nigeria", "in kenya", "in hindi", "in urdu", "in tamil", "in telugu"]

            seen = set()
            unique_results = []
            clean_q_norm = " ".join(clean_q.lower().split())

            # 1. Process Autocomplete suggestions first (empirical viewer demand)
            for s_idx, s in enumerate(all_suggestions):
                k_norm = " ".join(s.keyword.lower().strip().split())
                if not k_norm or len(k_norm) < 2 or k_norm == clean_q_norm:
                    continue
                # Filter out foreign location noise if country is Western/US
                if selected_country.upper() in ("US", "GB", "CA", "AU"):
                    if any(noise in k_norm for noise in foreign_country_noise):
                        continue
                if is_channel_discovery and (k_norm in excluded_channel_backlog or any(b in k_norm for b in excluded_channel_backlog if len(b) > 5)):
                    continue
                if k_norm not in seen:
                    seen.add(k_norm)
                    cls = default_classifier.classify(s.keyword)
                    score_res = default_scorer.score(s.keyword, clean_q, cls)
                    words_count = len(s.keyword.split())
                    
                    vol_obj = default_volume_provider.get_keyword_volume(s.keyword, country=selected_country)

                    dec_summary = keyword_decision_helper.build_decision_summary(
                        keyword=s.keyword,
                        seed_query=clean_q,
                        channel=active_channel,
                        is_cached=getattr(s, "is_cached", False),
                        retrieved_at=getattr(s, "retrieved_at", None),
                        queries_executed_count=len(executed_queries),
                        volume_status=vol_obj.display_metric,
                        raw_score=score_res.total_score,
                        source_type="cached" if getattr(s, "is_cached", False) else "autocomplete",
                    )

                    # vidIQ-style Competition Badge
                    if dec_summary.competition_tier == "Low":
                        comp_badge = "🟢 Low"
                        comp_label = "Low (Long-tail)"
                    elif dec_summary.competition_tier == "Medium":
                        comp_badge = "🟡 Medium"
                        comp_label = "Moderate"
                    else:
                        comp_badge = "🔴 High"
                        comp_label = "High (Broad)"

                    unique_results.append({
                        "Keyword": s.keyword,
                        "Tag": f"🏷️ {s.keyword}",
                        "vidIQ Score": dec_summary.vidiq_score_display,
                        "Ranking Chance": dec_summary.ranking_chance_display,
                        "Competition": comp_badge,
                        "Search Volume": dec_summary.search_volume_badge,
                        "Search Intent": cls.primary_intent.value,
                        "Source": "YouTube Autocomplete",
                        "Data Quality": dec_summary.data_quality_label,
                        "Decision Status": dec_summary.decision_status,
                        "Opportunity Score": dec_summary.opportunity_score_display,
                        "_score_num": dec_summary.vidiq_score,
                        "_ranking_chance": dec_summary.ranking_chance,
                        "_competition_tier": dec_summary.competition_tier,
                        "_comp_label": comp_label,
                        "_source_type": "autocomplete",
                        "_raw_score": float(dec_summary.vidiq_score) if dec_summary.decision_status != "Low relevance" else 0.0,
                        "_decision": dec_summary.to_dict(),
                        "_score_breakdown": score_res.to_dict(),
                    })

            # 2. Process Generated Patterns next
            for p in generated_patterns:
                p_kw = getattr(p, "keyword", str(p)) if not isinstance(p, dict) else p.get("keyword", str(p))
                k_norm = " ".join(p_kw.lower().strip().split())
                if not k_norm or len(k_norm) < 2 or k_norm == clean_q_norm:
                    continue
                if selected_country.upper() in ("US", "GB", "CA", "AU"):
                    if any(noise in k_norm for noise in foreign_country_noise):
                        continue
                if is_channel_discovery and (k_norm in excluded_channel_backlog or any(b in k_norm for b in excluded_channel_backlog if len(b) > 5)):
                    continue
                if k_norm not in seen:
                    seen.add(k_norm)
                    cls = default_classifier.classify(p_kw)
                    score_res = default_scorer.score(p_kw, clean_q, cls)
                    words_count = len(p_kw.split())
                    vol_obj = default_volume_provider.get_keyword_volume(p_kw, country=selected_country)

                    raw_intent = getattr(p, "intent", None) or (p.get("intent") if isinstance(p, dict) else None) or cls.primary_intent
                    intent_val = raw_intent.value if hasattr(raw_intent, "value") else str(raw_intent)

                    dec_summary = keyword_decision_helper.build_decision_summary(
                        keyword=p_kw,
                        seed_query=clean_q,
                        channel=active_channel,
                        is_cached=False,
                        retrieved_at=None,
                        queries_executed_count=len(executed_queries),
                        volume_status=vol_obj.display_metric,
                        raw_score=score_res.total_score,
                        source_type="generated_pattern",
                    )

                    if dec_summary.competition_tier == "Low":
                        comp_badge = "🟢 Low"
                        comp_label = "Low (Long-tail)"
                    elif dec_summary.competition_tier == "Medium":
                        comp_badge = "🟡 Medium"
                        comp_label = "Moderate"
                    else:
                        comp_badge = "🔴 High"
                        comp_label = "High (Broad)"

                    unique_results.append({
                        "Keyword": p_kw,
                        "Tag": f"🏷️ {p_kw}",
                        "vidIQ Score": dec_summary.vidiq_score_display,
                        "Ranking Chance": dec_summary.ranking_chance_display,
                        "Competition": comp_badge,
                        "Search Volume": dec_summary.search_volume_badge,
                        "Search Intent": intent_val,
                        "Source": "Generated Pattern",
                        "Data Quality": "Generated suggestion",
                        "Decision Status": dec_summary.decision_status,
                        "Opportunity Score": dec_summary.opportunity_score_display,
                        "_score_num": dec_summary.vidiq_score,
                        "_ranking_chance": dec_summary.ranking_chance,
                        "_competition_tier": dec_summary.competition_tier,
                        "_comp_label": comp_label,
                        "_source_type": "pattern",
                        "_raw_score": float(dec_summary.vidiq_score - 3) if dec_summary.decision_status != "Low relevance" else 0.0,
                        "_decision": dec_summary.to_dict(),
                        "_score_breakdown": score_res.to_dict(),
                    })

            # Sort by vidIQ overall score descending
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
        
        ac_count = sum(1 for r in results if r.get("Source", "YouTube Autocomplete") == "YouTube Autocomplete")
        pat_count = sum(1 for r in results if r.get("Source") == "Generated Pattern")
        high_rank_count = sum(1 for r in results if "High" in str(r.get("Ranking Chance", "")))
        executed_list = st.session_state.get("kr_executed_queries", [st.session_state.kr_last_query])

        # Research Coverage Reporting Banner
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; font-size: 0.84rem; color: #475569;">
                📊 <b>Research Coverage:</b> Executed <b>{len(executed_list)}</b> queries in {st.session_state.kr_execution_time:.2f}s &middot; 
                <b>Discovered:</b> {len(results)} keywords ({ac_count} Autocomplete queries + {pat_count} Generated Patterns) &middot; 
                <b>High Ranking Potential:</b> <span style="color: #15803D; font-weight: 700;">{high_rank_count} Keywords</span> &middot; 
                <b>Channel Context:</b> Aligned with <b>{active_channel.channel_name}</b> ({active_channel.channel_niche})
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Metric Tiles (vidIQ Style KPI Header)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Keywords Discovered", len(results), help=f"{ac_count} from YouTube Autocomplete, {pat_count} from Generated Patterns")
        with m2:
            st.metric("Top Ranking Candidates", f"{high_rank_count} Keywords", help="Keywords with High or Very High ranking chance based on long-tail specificity and low competition.")
        with m3:
            top_score = max((r.get("_score_num", 75) for r in results), default=80)
            st.metric("Best vidIQ Score", f"{top_score}/100", help="Highest opportunity score discovered in this keyword batch.")
        with m4:
            st.metric("Retrieval Speed", f"{st.session_state.kr_execution_time:.2f}s")

        # Filters & Search Controls (4 columns)
        c_f1, c_f2, c_f3, c_f4 = st.columns([2, 1.4, 1.3, 1.3])
        with c_f1:
            table_search = st.text_input("🔍 Filter keywords", placeholder="Type to filter results...", key="kr_table_search")
        with c_f2:
            rank_chances = ["All Ranking Chances", "🟢 Very High", "🟢 High", "🟡 Medium", "🔴 Low"]
            selected_rank_chance = st.selectbox("Filter Ranking Chance", rank_chances, key="kr_rank_chance_filter")
        with c_f3:
            comp_options = ["All Competitions", "🟢 Low", "🟡 Medium", "🔴 High"]
            selected_comp = st.selectbox("Filter Competition", comp_options, key="kr_comp_filter")
        with c_f4:
            sources = ["All Sources", "YouTube Autocomplete", "Generated Pattern"]
            selected_source = st.selectbox("Filter Source", sources, key="kr_source_filter")

        # Apply filtering
        filtered_results = list(results)
        if table_search.strip():
            filtered_results = [r for r in filtered_results if table_search.lower().strip() in r["Keyword"].lower()]
        if selected_rank_chance != "All Ranking Chances":
            clean_rc = selected_rank_chance.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
            filtered_results = [r for r in filtered_results if clean_rc in str(r.get("Ranking Chance", ""))]
        if selected_comp != "All Competitions":
            clean_cp = selected_comp.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
            filtered_results = [r for r in filtered_results if clean_cp in str(r.get("Competition", ""))]
        if selected_source != "All Sources":
            filtered_results = [r for r in filtered_results if r.get("Source", "YouTube Autocomplete") == selected_source]

        # Results Table with vidIQ Columns
        st.caption(f"Showing **{len(filtered_results)}** of {len(results)} discovered keywords with vidIQ-style scoring:")
        df_display = pd.DataFrame(filtered_results)
        
        display_cols = [
            c for c in ["Keyword", "vidIQ Score", "Ranking Chance", "Competition", "Search Volume", "Search Intent", "Source", "Data Quality"]
            if c in df_display.columns
        ]

        st.dataframe(
            df_display[display_cols],
            column_config={
                "Keyword": st.column_config.TextColumn("Keyword Phrase", width="large"),
                "vidIQ Score": st.column_config.TextColumn("Overall Score", width="small", help="vidIQ-style overall score (0-100). Higher is better!"),
                "Ranking Chance": st.column_config.TextColumn("Ranking Chance", width="medium", help="Probability of ranking based on competition, channel niche, and intent specificity."),
                "Competition": st.column_config.TextColumn("Competition", width="small", help="Search competition level: Low (Green), Medium (Yellow), High (Red)."),
                "Search Volume": st.column_config.TextColumn("Search Volume", width="medium", help="Viewer search demand signal observed on YouTube."),
                "Search Intent": st.column_config.TextColumn("Search Intent", width="medium"),
                "Source": st.column_config.TextColumn("Source", width="medium"),
                "Data Quality": st.column_config.TextColumn("Data Quality", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # ==============================================================================
        # 🏷️ VIDIQ-STYLE YOUTUBE TAG STUDIO & EXPORTER
        # ==============================================================================
        st.markdown("### 🏷️ YouTube Tag Studio (vidIQ-Style Tags with Scores)")
        st.caption("Review individual tags with scores, monitor character count limits, and copy ready-to-paste tags for YouTube Studio:")

        raw_tag_list = [r["Keyword"] for r in filtered_results]
        comma_separated_tags = ", ".join(raw_tag_list)
        char_count = len(comma_separated_tags)

        # YouTube Studio 500-Character Counter Badge
        if char_count <= 480:
            char_badge = f"""<span style="background: #DCFCE7; color: #15803D; font-weight: 700; padding: 4px 12px; border-radius: 12px; font-size: 0.82rem;">🟢 {char_count} / 500 Characters (Optimal for YouTube Upload)</span>"""
        elif char_count <= 500:
            char_badge = f"""<span style="background: #FEF3C7; color: #B45309; font-weight: 700; padding: 4px 12px; border-radius: 12px; font-size: 0.82rem;">🟡 {char_count} / 500 Characters (Near Upload Limit)</span>"""
        else:
            char_badge = f"""<span style="background: #FEE2E2; color: #B91C1C; font-weight: 700; padding: 4px 12px; border-radius: 12px; font-size: 0.82rem;">🔴 {char_count} / 500 Characters (Use Top 10 to fit limit)</span>"""

        # Render visual vidIQ Tag Pills with individual score badges
        pills_html = []
        for r in filtered_results[:25]:
            score_num = r.get("_score_num", 75)
            pill_color = "#15803D" if score_num >= 65 else ("#B45309" if score_num >= 45 else "#B91C1C")
            pill_bg = "#DCFCE7" if score_num >= 65 else ("#FEF3C7" if score_num >= 45 else "#FEE2E2")
            pills_html.append(
                f"""<span style="background: #F8FAFC; border: 1px solid #CBD5E1; color: #1E293B; padding: 4px 10px; border-radius: 16px; margin: 3px; font-size: 0.84rem; display: inline-flex; align-items: center; gap: 6px;">🏷️ {r['Keyword']} <b style="background: {pill_bg}; color: {pill_color}; padding: 1px 6px; border-radius: 10px; font-size: 0.74rem;">{score_num}</b></span>"""
            )

        tag_studio_html = f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A;">
                    🏷️ Discovered YouTube Video Tags ({len(filtered_results)} Tags)
                </div>
                <div>
                    {char_badge}
                </div>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px;">
                {''.join(pills_html)}
            </div>
        </div>
        """
        _render_html(tag_studio_html)

        # 1-Click Copy Tag Buttons Row
        c_tag1, c_tag2, c_tag3 = st.columns([2.5, 2, 1.5])
        with c_tag1:
            safe_tags = []
            cur_len = 0
            for kw in raw_tag_list:
                add_len = len(kw) + (2 if safe_tags else 0)
                if cur_len + add_len <= 500:
                    safe_tags.append(kw)
                    cur_len += add_len
                else:
                    break
            safe_tags_str = ", ".join(safe_tags)

            with st.popover(f"📋 Copy YouTube Studio Tags ({len(safe_tags)} tags &middot; {cur_len} chars)"):
                st.markdown("**Comma-separated tags ready to paste into YouTube Studio's tag box:**")
                st.code(safe_tags_str, language=None)
                st.caption(f"Formatted specifically for YouTube upload metadata: {cur_len} / 500 characters used.")

        with c_tag2:
            top_10_tags = raw_tag_list[:10]
            top_10_str = ", ".join(top_10_tags)
            with st.popover(f"⭐ Copy Top 10 High-Ranking Tags"):
                st.markdown("**Top 10 highest-scoring tags for maximum SEO relevance:**")
                st.code(top_10_str, language=None)
                st.caption(f"{len(top_10_str)} characters used. Paste these at the beginning of your tag box.")

        with c_tag3:
            st.download_button(
                label="📥 Export Tags (.txt)",
                data=comma_separated_tags,
                file_name=f"youtube_tags_{st.session_state.kr_last_query.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_dl_tags_btn",
                help="Download all discovered tags formatted with commas.",
            )

        # ==============================================================================
        # KEYWORD DECISION SUMMARY & EVIDENCE INSPECTOR
        # ==============================================================================
        st.markdown("### 📋 Keyword Decision Summary & Evidence Inspector")
        st.caption("Select any discovered keyword to inspect its full 8-point evidence summary, data quality indicators, and scoring formula:")

        kw_names = [r["Keyword"] for r in filtered_results]
        if kw_names:
            sel_kw = st.selectbox("Select Keyword to Inspect", kw_names, key="kr_inspect_select")
            sel_rec = next((r for r in filtered_results if r["Keyword"] == sel_kw), None)

            if sel_rec and "_decision" in sel_rec:
                dec = sel_rec["_decision"]
                source_badge_color = "#2563EB" if sel_rec.get("Source") == "YouTube Autocomplete" else "#7C3AED"
                source_badge_bg = "#EFF6FF" if sel_rec.get("Source") == "YouTube Autocomplete" else "#F5F3FF"
                
                vidiq_score_str = sel_rec.get("vidIQ Score", dec.get("vidiq_score_display", "🟢 80/100"))
                ranking_chance_str = sel_rec.get("Ranking Chance", dec.get("ranking_chance_display", "🟢 High"))
                comp_badge_str = sel_rec.get("Competition", "🟢 Low")
                volume_str = sel_rec.get("Search Volume", "🟢 High Demand")

                inspector_html = f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 18px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <div>
                            <h4 style="margin: 0 0 4px 0; font-size: 1.25rem; color: #0F172A; font-weight: 700;">
                                {dec.get('keyword', sel_kw)}
                            </h4>
                            <div style="font-size: 0.85rem; color: #64748B;">
                                Tag format: <code>{dec.get('keyword', sel_kw)}</code> &middot; Length: {len(dec.get('keyword', sel_kw))} chars
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="background: {source_badge_bg}; color: {source_badge_color}; font-weight: 700; font-size: 0.80rem; padding: 4px 10px; border-radius: 12px;">
                                {sel_rec.get('Source', 'Autocomplete')}
                            </span>
                            <span style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 0.80rem; padding: 4px 12px; border-radius: 12px;">
                                {dec.get('decision_status', 'Good candidate')}
                            </span>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px;">
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; text-align: center;">
                            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Overall Score</div>
                            <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-top: 2px;">{vidiq_score_str}</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; text-align: center;">
                            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Ranking Chance</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-top: 2px;">{ranking_chance_str}</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; text-align: center;">
                            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Competition</div>
                            <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-top: 2px;">{comp_badge_str}</div>
                        </div>
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; text-align: center;">
                            <div style="font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Search Demand</div>
                            <div style="font-size: 1.00rem; font-weight: 700; color: #0F172A; margin-top: 2px;">{volume_str}</div>
                        </div>
                    </div>

                    <div style="background: #EFF6FF; border-left: 4px solid #3B82F6; border-radius: 4px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.90rem; color: #1E3A8A;">
                        💡 <b>Strategy Recommendation:</b> {dec.get('explanation', '')}
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; font-size: 0.85rem; color: #334155; line-height: 1.5;">
                        <div>• <b>Relevance to Niche:</b> {dec.get('relevance_to_niche', '')}</div>
                        <div>• <b>Search Volume & Source:</b> {dec.get('search_volume_and_source', '')}</div>
                        <div>• <b>Competition Evidence:</b> {dec.get('competition_evidence', '')}</div>
                        <div>• <b>Search Intent:</b> {dec.get('search_intent', '')}</div>
                        <div>• <b>Recent Video Evidence:</b> {dec.get('recent_video_evidence', '')}</div>
                        <div>• <b>Data Freshness:</b> {dec.get('data_freshness', '')}</div>
                        <div>• <b>Research Completeness:</b> {dec.get('research_completeness', '')}</div>
                        <div>• <b>Recommended Action:</b> {dec.get('recommended_action', '')}</div>
                    </div>
                </div>
                """
                _render_html(inspector_html)

                # Collapsible Scoring Formula Expander
                with st.expander("📐 Transparent Scoring Formula & Evidence Contribution", expanded=False):
                    st.markdown(
                        """
                        **Transparent vidIQ-Style Heuristic Relevance & Ranking Formula:**
                        $$\\text{Overall Score} = (\\text{Relevance Score} \\times 0.55) + (\\text{Ranking Chance Score} \\times 0.45)$$
                        $$\\text{Relevance Score} = (\\text{Seed Overlap} \\times 0.40) + (\\text{Sequence Similarity} \\times 0.30) + (\\text{Intent Clarity} \\times 0.20) + (\\text{Length Quality} \\times 0.10)$$
                        """
                    )
                    sb = sel_rec.get("_score_breakdown", {})
                    st.markdown(
                        f"""
                        - **Seed Overlap (0–40 pts):** {sb.get('seed_term_score', 0):.1f} pts (Token overlap with seed/niche)
                        - **Sequence Similarity (0–30 pts):** {sb.get('similarity_score', 0):.1f} pts (Character and token sequence alignment)
                        - **Intent Clarity (0–20 pts):** {sb.get('intent_score', 0):.1f} pts (Structured intent clarity e.g. How-to, Review, Buyer)
                        - **Length Quality (0–10 pts):** {sb.get('length_score', 0):.1f} pts (Optimal 2–6 word sweet spot for video queries)
                        - **Duplicate Repetition Penalty:** -{sb.get('penalty', 0):.0f} pts
                        - **vidIQ Overall Score:** `{vidiq_score_str}`
                        - **Ranking Probability:** `{ranking_chance_str}`
                        """
                    )
                    st.caption(f"ℹ️ {dec.get('disclaimer', '')}")

                # 1-Click Copy snippet for this keyword decision
                dec_copy_snippet = f"Keyword: {dec.get('keyword', sel_kw)}\nTag: {dec.get('keyword', sel_kw)}\nScore: {vidiq_score_str}\nRanking Chance: {ranking_chance_str}\nCompetition: {comp_badge_str}\nDemand: {volume_str}\nRecommendation: {dec.get('recommended_action', '')}"
                st.code(dec_copy_snippet, language="text")

        # ==============================================================================
        # BULK KEYWORD ACTIONS & CROSS-TOOL HANDOFF
        # ==============================================================================
        st.markdown("### 📋 Bulk Keyword Actions & Cross-Tool Handoff")
        st.caption("Perform one-click bulk operations on discovered keywords or hand them off directly to other tools:")

        # Multi-select widget
        all_filtered_kw_names = [r["Keyword"] for r in filtered_results]
        selected_kws = st.multiselect(
            "Select Keywords for Bulk Action (Optional — leave empty to target all visible):",
            options=all_filtered_kw_names,
            default=[],
            key="kr_bulk_multiselect",
            help="Select one or more keywords to copy, export, or send to other tools.",
        )

        targeted_kws = selected_kws if selected_kws else all_filtered_kw_names
        target_label = f"Selected ({len(selected_kws)})" if selected_kws else f"All Visible ({len(all_filtered_kw_names)})"

        c_act1, c_act2, c_act3, c_act4 = st.columns([1.5, 1.5, 1.5, 1.5])

        with c_act1:
            with st.popover(f"📋 Copy {target_label}"):
                st.markdown(f"**Copy {len(targeted_kws)} Keywords:**")
                copy_text = "\n".join(targeted_kws)
                st.code(copy_text, language=None)
                st.caption("Click the clipboard icon in the top-right of the code box above to copy.")

        with c_act2:
            copy_text = "\n".join(targeted_kws)
            st.download_button(
                label=f"📄 Download Text ({len(targeted_kws)})",
                data=copy_text,
                file_name=f"keywords_{st.session_state.kr_last_query.replace(' ', '_')}_{len(targeted_kws)}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_dl_txt_btn",
                help="Download targeted keywords as a clean line-by-line text file.",
            )

        with c_act3:
            export_svc = ExportService()
            targeted_rows = [r for r in filtered_results if r["Keyword"] in targeted_kws]
            clean_df = pd.DataFrame(targeted_rows).drop(columns=["_raw_score", "_source_type", "_score_num"], errors="ignore")
            csv_bytes = export_svc.export_csv(clean_df, sanitize_formulas=True)
            st.download_button(
                label=f"📥 Export CSV ({len(targeted_rows)})",
                data=csv_bytes,
                file_name=f"keywords_{st.session_state.kr_last_query.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="kr_dl_csv_btn",
                help="Download targeted keyword records as a formula-safe CSV spreadsheet.",
            )

        with c_act4:
            if st.button("🔄 Reset Research", use_container_width=True, key="kr_reset_btn"):
                st.session_state.kr_results = []
                st.session_state.kr_patterns = []
                st.rerun()

        # Cross-Tool Handoff Row
        st.markdown("#### 🚀 Send Keyword to Other Tools")
        st.caption("Seamlessly pass your selected keyword and supporting phrases into downstream tools:")

        c_pick, c_btn_vr, c_btn_cr, c_btn_seo = st.columns([2.5, 1.5, 1.5, 1.5])
        with c_pick:
            default_handoff_idx = 0
            if selected_kws and selected_kws[0] in all_filtered_kw_names:
                default_handoff_idx = all_filtered_kw_names.index(selected_kws[0])
            
            picked_handoff_kw = st.selectbox(
                "Keyword for Cross-Tool Handoff:",
                options=all_filtered_kw_names,
                index=default_handoff_idx,
                key="kr_handoff_kw_select",
            )

        with c_btn_vr:
            st.write("")
            st.write("")
            if st.button("🎥 Video Research", use_container_width=True, key="kr_send_vr_btn", help="Inspect ranking videos and view counts for this keyword."):
                st.session_state.vr_target_keyword = picked_handoff_kw
                st.session_state["vr_search_input"] = picked_handoff_kw
                st.session_state.current_page = TOOL_VIDEO_RESEARCH
                st.rerun()

        with c_btn_cr:
            st.write("")
            st.write("")
            if st.button("🎯 Competitor Research", use_container_width=True, key="kr_send_cr_btn", help="Analyze competitor channels and video angles for this topic."):
                st.session_state.cr_last_query = picked_handoff_kw
                st.session_state["cr_keyword_input"] = picked_handoff_kw
                st.session_state.current_page = TOOL_COMPETITOR_RESEARCH
                st.rerun()

        with c_btn_seo:
            st.write("")
            st.write("")
            if st.button("✨ SEO Generator", type="primary", use_container_width=True, key="kr_send_seo_btn", help="Draft optimized YouTube titles, description, and tags for this keyword."):
                other_kws = [k for k in targeted_kws if k != picked_handoff_kw][:5]
                sec_kw_str = ", ".join(other_kws) if other_kws else picked_handoff_kw
                
                st.session_state.seo_main_keyword = picked_handoff_kw
                st.session_state["gen_main_kw_input"] = picked_handoff_kw
                st.session_state.seo_secondary_keywords = sec_kw_str
                st.session_state["gen_sec_kws_input"] = sec_kw_str
                st.session_state.seo_topic_summary = f"Complete guide and tutorial for {picked_handoff_kw}"
                st.session_state["gen_topic_summary_input"] = f"Complete guide and tutorial for {picked_handoff_kw}"
                st.session_state.seo_target_viewer = active_channel.target_audience
                st.session_state["gen_target_viewer_input"] = active_channel.target_audience
                st.session_state["gen_format_radio"] = "Long-form (16:9)"
                st.session_state.current_page = TOOL_SEO_GENERATOR
                st.rerun()

    elif not results and st.session_state.kr_last_query:
        st.warning(f"No suggestions found for '{st.session_state.kr_last_query}'. Try a shorter or broader seed phrase.")
    else:
        st.info(f"👆 Enter a seed keyword or click 'Find for This Channel' to start discovering high-intent search queries and vidIQ-style tags for {active_channel.channel_name}.")

    st.write("")
    st.markdown("---")

    # ==============================================================================
    # RESTORED KEYWORD PATTERN GENERATOR (INTEGRATED INTO KEYWORD RESEARCH)
    # ==============================================================================
    st.markdown("### 🧩 Custom Keyword Pattern Generator (Advanced Creator Frameworks)")
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

    with st.expander("🛠️ Configure & Generate Custom Patterns", expanded=(len(st.session_state.kr_patterns) == 0)):
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

        if st.button("✨ Generate Custom Keyword Patterns", type="primary", use_container_width=True, key="kr_pat_gen_btn"):
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

    # Display Generated Custom Patterns
    patterns = st.session_state.kr_patterns
    if patterns:
        st.markdown(f"##### 📋 Generated Custom Pattern Candidates ({len(patterns)})")
        st.caption("Select any pattern to run empirical Autocomplete research or send to SEO Generator:")

        pat_rows = []
        for p in patterns:
            p_kw = getattr(p, "keyword", str(p)) if not isinstance(p, dict) else p.get("keyword", str(p))
            raw_cat = (
                getattr(p, "pattern_category", None)
                or (p.get("pattern_category") if isinstance(p, dict) else None)
                or "Custom Pattern"
            )
            if hasattr(raw_cat, "value"):
                raw_cat = raw_cat.value
            cat_str = str(raw_cat).replace("_", " ").title()

            raw_intent = (
                getattr(p, "intent", None)
                or (p.get("intent") if isinstance(p, dict) else None)
                or "Informational"
            )
            if hasattr(raw_intent, "value"):
                raw_intent = raw_intent.value
            intent_str = str(raw_intent)

            pat_rows.append({
                "Pattern Candidate": p_kw,
                "Category": cat_str,
                "Intent": intent_str,
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
            all_pat_text = "\n".join(
                getattr(p, "keyword", str(p)) if not isinstance(p, dict) else p.get("keyword", str(p))
                for p in patterns
            )
            st.download_button(
                label="📋 Copy / Export All Patterns",
                data=all_pat_text,
                file_name=f"patterns_{pat_seed.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="kr_pat_dl_btn",
            )
        with c_pact2:
            top_pattern = getattr(patterns[0], "keyword", str(patterns[0])) if not isinstance(patterns[0], dict) else patterns[0].get("keyword", str(patterns[0]))
            if st.button(f"🔍 Run '{top_pattern[:20]}...' in Autocomplete", use_container_width=True, key="kr_pat_run_ac_btn"):
                st.session_state.kr_last_query = top_pattern
                st.rerun()
        with c_pact3:
            top_pattern = getattr(patterns[0], "keyword", str(patterns[0])) if not isinstance(patterns[0], dict) else patterns[0].get("keyword", str(patterns[0]))
            if st.button(f"✨ Send Top Pattern to SEO Generator", type="primary", use_container_width=True, key="kr_pat_send_seo_btn"):
                sec_list = [
                    getattr(p, "keyword", str(p)) if not isinstance(p, dict) else p.get("keyword", str(p))
                    for p in patterns[1:5]
                ]
                st.session_state.seo_main_keyword = top_pattern
                st.session_state["gen_main_kw_input"] = top_pattern
                st.session_state.seo_secondary_keywords = ", ".join(sec_list)
                st.session_state["gen_sec_kws_input"] = ", ".join(sec_list)
                st.session_state.current_page = TOOL_SEO_GENERATOR
                st.rerun()
