"""Tool 2: YouTube Video Research — Restored & Upgraded Core Workflow.

Provides dedicated YouTube Video SERP and competitor video research using the official
YouTube Data API v3 when configured:
- Target keyword query with date range, language, region, and sort order filters
- Real public video data: Title, Channel, Video URL, Published Date, View Count, Likes, Comments, Duration, Thumbnails
- Search metadata: Query, Retrieval Time, Result Count, Date Range, Cache Status (0 quota units)
- Video details panel / expandable metadata
- Grounded actions: Open video, Copy title, Send to Competitor Research, Send to SEO Generator, Export to CSV
- Strict epistemic modesty: Zero fabricated views, zero private analytics claims (no fake CTR or revenue)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time
from typing import Any, Dict, List, Optional
import streamlit as st

from src.config import config
from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.providers.serp import YouTubeDataApiSerpProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, generate_export_filename
from src.ui.channel_components import get_active_channel
from src.ui.components import (
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
    TOOL_SETTINGS,
)


def render_video_research_tool() -> None:
    """Render the restored Tool 2: YouTube Video Research."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                🎥 YouTube Video Research
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Review top-ranking YouTube videos, view counts, upload dates, and engagement to identify proven video topics and content gaps.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Epistemic Modesty Notice
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; 
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.85rem; color: #475569;">
            🔒 <b>Public Data & Empirical Policy:</b> Video research retrieves only publicly viewable YouTube video metadata 
            (titles, channels, publish dates, public view counts, likes, and comments). Keyword Studio never fakes view counts 
            or search rankings, and does not claim access to private YouTube Studio analytics such as click-through rate (CTR), 
            subscriber conversions, or channel revenue.
        </div>
        """,
        unsafe_allow_html=True,
    )

    serp_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
    is_connected = serp_provider.is_connected()

    # Session State
    if "current_serp_analysis" not in st.session_state:
        st.session_state.current_serp_analysis = None
    if "vr_last_query" not in st.session_state:
        st.session_state.vr_last_query = ""
    if "vr_target_keyword" not in st.session_state:
        st.session_state.vr_target_keyword = ""

    # Channel Context
    active_chan = get_active_channel()

    # Prefill from cross-tool handoff or active channel if present
    initial_keyword = (
        st.session_state.vr_target_keyword
        or st.session_state.vr_last_query
        or st.session_state.get("kr_last_query", "")
        or (active_chan.channel_niche.split("&")[0].strip() if active_chan else "")
        or ""
    )

    # Connection Status Header
    if is_connected:
        daily_used = db_manager.get_daily_quota_used() if hasattr(db_manager, "get_daily_quota_used") else 0
        c_status1, c_status2 = st.columns([3.5, 1.5])
        with c_status1:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; color: #15803D;">
                    <span style="font-size: 1rem;">🟢</span> 
                    <b>Connected to YouTube Data API v3</b> &middot; Batch-optimized (101 quota units/search, 0 units cached)
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_status2:
            st.markdown(
                f"""
                <div style="text-align: right; font-size: 0.84rem; color: #64748B;">
                    API Quota: <b>{daily_used:,}</b> / 10,000 units/day
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.write("")
    else:
        st.markdown(
            """
            <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px;">
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <span style="font-size: 1.3rem;">ℹ️</span>
                    <div>
                        <div style="font-weight: 700; color: #92400E; font-size: 0.95rem; margin-bottom: 4px;">
                            YouTube Data API v3 Key Required for Live Video SERP Inspection
                        </div>
                        <div style="font-size: 0.86rem; color: #B45309; line-height: 1.45;">
                            Under our <b>zero fabricated metrics guarantee</b>, Keyword Studio does not invent fake YouTube video views, 
                            publish dates, or competitor tags when unconnected. To inspect live ranking competitor videos, 
                            configure your free Google YouTube Data API key in <b>Settings</b>.
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Search Form
    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            search_query = st.text_input(
                "Enter Video Topic or Search Keyword",
                value=initial_keyword,
                placeholder="e.g. best mechanical keyboards 2026, python tutorial, sourdough bread",
                key="vr_search_input",
                help="Type a target query to inspect currently ranking YouTube videos and competitor performance.",
            )
        with c_in2:
            st.write("")
            st.write("")
            btn_run_vr = st.button("🚀 Inspect Videos", type="primary", use_container_width=True, key="vr_submit_btn")

        # Filters Expander
        with st.expander("⚙️ Video Search & Region Filters (Optional)", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                date_filter = st.selectbox(
                    "Published Date Range",
                    ["Any Time", "Last 7 Days", "Last 30 Days", "Last 60 Days", "Last 90 Days", "Last 365 Days"],
                    index=0,
                    key="vr_date_select",
                )
            with col_f2:
                sort_order = st.selectbox(
                    "Sort Competitor Results By",
                    [
                        "Relevance (Default)",
                        "Upload Date (Newest First)",
                        "View Count (Most Popular)",
                        "Rating (Highest Rated)",
                    ],
                    index=0,
                    key="vr_sort_select",
                )
            with col_f3:
                max_vids = st.selectbox(
                    "Number of Videos to Retrieve",
                    [5, 10, 15, 20, 50],
                    index=1,
                    key="vr_max_videos_select",
                )

            col_f4, col_f5, col_f6 = st.columns(3)
            with col_f4:
                country_opts = list(config.supported_countries.keys())
                chan_country = active_chan.target_country.upper() if active_chan else "US"
                def_country_idx = country_opts.index(chan_country) if chan_country in country_opts else (country_opts.index("US") if "US" in country_opts else 0)
                selected_country = st.selectbox(
                    "Region / Country Code",
                    options=country_opts,
                    format_func=lambda c: f"{config.supported_countries.get(c, c)} ({c})",
                    index=def_country_idx,
                    key="vr_country_select",
                )
            with col_f5:
                lang_opts = list(config.supported_languages.keys())
                chan_lang = active_chan.target_language.lower() if active_chan else "en"
                def_lang_idx = lang_opts.index(chan_lang) if chan_lang in lang_opts else (lang_opts.index("en") if "en" in lang_opts else 0)
                selected_lang = st.selectbox(
                    "Search Language",
                    options=lang_opts,
                    format_func=lambda l: f"{config.supported_languages.get(l, l)} ({l})",
                    index=def_lang_idx,
                    key="vr_lang_select",
                )
            with col_f6:
                use_cache = st.checkbox(
                    "Use 24h Local Cache (0 quota units)",
                    value=True,
                    help="When enabled, identical searches within 24 hours return from local disk without using Google API quota.",
                    key="vr_cache_checkbox",
                )

    # Handle Search Submission
    if btn_run_vr and search_query.strip():
        clean_kw = search_query.strip()
        st.session_state.vr_last_query = clean_kw
        st.session_state.vr_target_keyword = clean_kw

        if not is_connected:
            st.error(
                "❌ YouTube Data API v3 key is not configured. "
                "Please configure a key in Settings to inspect live ranking videos."
            )
            col_btn1, _ = st.columns([2, 3])
            with col_btn1:
                if st.button("⚙️ Open Settings to Add API Key", key="vr_goto_settings_btn"):
                    st.session_state.current_page = TOOL_SETTINGS
                    st.rerun()
        else:
            with st.spinner(f"Retrieving top ranking videos and competitor data for '{clean_kw}'..."):
                t0 = time.time()

                # Calculate published_after ISO string
                published_after_val: Optional[str] = None
                now_utc = datetime.now(timezone.utc)
                if date_filter == "Last 7 Days":
                    published_after_val = (now_utc - timedelta(days=7)).isoformat()
                elif date_filter == "Last 30 Days":
                    published_after_val = (now_utc - timedelta(days=30)).isoformat()
                elif date_filter == "Last 60 Days":
                    published_after_val = (now_utc - timedelta(days=60)).isoformat()
                elif date_filter == "Last 90 Days":
                    published_after_val = (now_utc - timedelta(days=90)).isoformat()
                elif date_filter == "Last 365 Days":
                    published_after_val = (now_utc - timedelta(days=365)).isoformat()

                order_map = {
                    "Relevance (Default)": "relevance",
                    "Upload Date (Newest First)": "date",
                    "View Count (Most Popular)": "viewCount",
                    "Rating (Highest Rated)": "rating",
                }
                order_api = order_map.get(sort_order, "relevance")

                try:
                    analysis = serp_provider.analyze_keyword(
                        keyword=clean_kw,
                        language=selected_lang,
                        country=selected_country,
                        max_results=max_vids,
                        order=order_api,
                        published_after=published_after_val,
                        use_cache=use_cache,
                    )
                    st.session_state.current_serp_analysis = analysis
                except Exception as exc:
                    st.error(f"❌ Failed to retrieve YouTube video data: {str(exc)}")
                st.rerun()

    # Results Display
    analysis: Optional[KeywordSerpAnalysis] = st.session_state.get("current_serp_analysis")
    if analysis:
        st.markdown("---")

        if analysis.total_videos_analyzed == 0:
            st.warning(
                f"No ranking videos returned for '{analysis.keyword}'. "
                f"{analysis.status_message} Try loosening the date filter or searching a broader topic."
            )
        else:
            # Metadata & Top Cards
            c_hdr1, c_hdr2 = st.columns([3.5, 1.5])
            with c_hdr1:
                st.markdown(f"### Research Results for: `{analysis.keyword}`")
                cache_badge = "💾 Local Cache (0 quota units)" if analysis.is_cached else "⚡ Live YouTube Data API v3 (101 units)"
                fetch_time = analysis.fetched_at[:19].replace("T", " ") if analysis.fetched_at else "Recently"
                st.caption(f"{cache_badge} &middot; Fetched at: {fetch_time} &middot; Total videos: **{analysis.total_videos_analyzed}**")
            with c_hdr2:
                opp_col = "#10B981" if analysis.opportunity_score >= 60 else "#3B82F6" if analysis.opportunity_score >= 40 else "#F59E0B"
                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid {opp_col}; 
                                border-radius: 6px; padding: 8px 12px; text-align: center;">
                        <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Opportunity Score</div>
                        <div style="font-size: 1.35rem; font-weight: 800; color: {opp_col};">{analysis.opportunity_score}/100</div>
                        <div style="font-size: 0.72rem; color: #64748B;">{analysis.opportunity_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.write("")

            # Top Metrics
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.metric("Videos Analyzed", f"{analysis.total_videos_analyzed}")
            with m2:
                st.metric("Median Views", f"{int(analysis.median_views):,}")
            with m3:
                st.metric("Average Views", f"{int(analysis.average_views):,}")
            with m4:
                st.metric("Unique Creators", f"{analysis.unique_channels_count}")
            with m5:
                st.metric("Median Video Age", f"{int(analysis.median_video_age_days)} days")

            # Common recurring competitor tags
            tags_sample = getattr(analysis, "top_tags", [])
            if tags_sample:
                st.markdown("##### 🏷️ Frequent Competitor Tags")
                tag_names = [t[0] if isinstance(t, (tuple, list)) else str(t) for t in tags_sample[:8]]
                p_badges = " ".join([f"`{kw}`" for kw in tag_names])
                st.markdown(f"Top tags observed across ranking videos: {p_badges}")

            st.write("")
            st.markdown("##### 🏆 Ranking Videos Breakdown")

            for v in analysis.videos:
                with st.container():
                    col_thumb, col_details = st.columns([1, 4])
                    with col_thumb:
                        if v.thumbnail_url:
                            st.image(v.thumbnail_url, use_container_width=True)
                        else:
                            st.markdown(
                                """
                                <div style="width: 100%; height: 90px; background: #F1F5F9; border-radius: 6px; 
                                            display: flex; align-items: center; justify-content: center; color: #94A3B8; font-size: 1.5rem;">
                                    📹
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    with col_details:
                        st.markdown(f"**#{v.rank} [{v.title}]({v.video_url})**")
                        channel_str = f"[{v.channel_title}]({v.channel_url})" if v.channel_url else v.channel_title
                        st.caption(
                            f"Channel: **{channel_str}** &middot; Published: **{v.relative_age}** ({v.publish_date[:10]}) &middot; "
                            f"Duration: **{v.duration or 'N/A'}**"
                        )
                        likes_text = f"{v.like_count:,} likes" if v.like_count is not None else "Likes hidden"
                        comments_text = f"{v.comment_count:,} comments" if v.comment_count is not None else "Comments disabled"
                        st.markdown(
                            f"👁️ **{v.view_count:,} views** &nbsp;|&nbsp; "
                            f"⚡ **{int(v.daily_views):,} daily views** &nbsp;|&nbsp; "
                            f"👍 {likes_text} &nbsp;|&nbsp; 💬 {comments_text}"
                        )

                        # Video-level actions
                        with st.expander("🛠️ Video Actions & Metadata", expanded=False):
                            col_cp1, col_cp2 = st.columns(2)
                            with col_cp1:
                                st.text_input("📋 Video Title (Click to Copy)", value=v.title, key=f"copy_t_{v.video_id}", help="Click inside and Ctrl+C to copy title")
                            with col_cp2:
                                st.text_input("🔗 Video URL (Click to Copy)", value=v.video_url, key=f"copy_u_{v.video_id}", help="Click inside and Ctrl+C to copy URL")

                            if v.tags:
                                st.caption(f"Tags: {', '.join(v.tags[:10])}")
                            if v.description:
                                st.caption(f"Description excerpt: {v.description[:220]}...")

                            btn_row1, btn_row2, btn_row3 = st.columns([1.5, 1.5, 1.5])
                            with btn_row1:
                                if st.button(f"🎯 Send to Competitor Research", key=f"vr_send_cr_{v.video_id}", use_container_width=True):
                                    st.session_state.cr_last_query = v.title
                                    st.session_state.current_page = TOOL_COMPETITOR_RESEARCH
                                    st.rerun()
                            with btn_row2:
                                if st.button(f"✨ Send to SEO Generator", key=f"vr_send_seo_{v.video_id}", use_container_width=True):
                                    st.session_state.seo_main_keyword = v.title
                                    st.session_state.seo_secondary_keywords = analysis.keyword
                                    st.session_state.current_page = TOOL_SEO_GENERATOR
                                    st.rerun()
                            with btn_row3:
                                if st.button(f"⚡ Send to 60-Day Gap Finder", key=f"vr_send_opp_{v.video_id}", use_container_width=True):
                                    st.session_state.opp_last_seed = analysis.keyword
                                    st.session_state.current_page = TOOL_60_DAY_OPPORTUNITIES
                                    st.rerun()

                    st.markdown("<div style='margin: 8px 0; border-top: 1px solid #F1F5F9;'></div>", unsafe_allow_html=True)

            # Global Actions & Exports
            st.markdown("#### 🛠️ Research Actions & CSV Export")
            c_act1, c_act2, c_act3 = st.columns([2, 2, 2])

            with c_act1:
                # Formula-safe CSV export
                csv_bytes = ExportService.export_serp_csv(analysis)
                csv_filename = generate_export_filename(analysis.keyword, scope="serp", extension="csv")
                st.download_button(
                    label="📥 Export Videos CSV",
                    data=csv_bytes,
                    file_name=csv_filename,
                    mime="text/csv",
                    use_container_width=True,
                    key="vr_dl_csv_btn",
                )

            with c_act2:
                # Save research session to database
                if st.button("💾 Save Research Session", use_container_width=True, key="vr_save_session_btn"):
                    try:
                        sess_id = db_manager.save_video_research_session(
                            analysis=analysis,
                            provider="YouTube Data API v3",
                            associated_keywords=[analysis.keyword],
                        )
                        st.success(f"✅ Session #{sess_id} saved to SQLite database successfully!")
                    except Exception as ex:
                        st.error(f"Failed to save session: {str(ex)}")

            with c_act3:
                # Send keyword to SEO generator
                if st.button(f"✨ Send Keyword to SEO Generator", type="primary", use_container_width=True, key="vr_send_top_seo_btn"):
                    st.session_state.seo_main_keyword = analysis.keyword
                    sec_kws = [t[0] if isinstance(t, (tuple, list)) else str(t) for t in getattr(analysis, "top_tags", [])[:4]]
                    st.session_state.seo_secondary_keywords = ", ".join(sec_kws) if sec_kws else analysis.keyword
                    st.session_state.current_page = TOOL_SEO_GENERATOR
                    st.rerun()

    elif not analysis and not search_query.strip():
        st.info("👆 Enter a target keyword or video topic above to inspect top-ranking YouTube videos.")
