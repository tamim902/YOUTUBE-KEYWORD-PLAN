"""Tool 3: Competitor Research — Upgraded Core Workflow.

Analyzes public competitor videos and channels using official YouTube Data API v3 when configured:
- Accepts a target keyword or competitor channel name
- Grounded competitor insights: Common title structures, recurring topics and formats, publishing frequency
- View counts, video age distribution, and repeated keyword phrases
- Explains every insight using the actual videos or evidence supporting it
- Unconnected state: Actionable setup instructions without fake metrics
- Cross-tool handoffs to Video Research and SEO Generator
- Formula-safe CSV export
- Strict epistemic modesty: Discloses sample boundaries, no private analytics claims
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import re
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.providers.serp import UnconnectedSerpMetricsProvider, YouTubeDataApiSerpProvider
from src.storage.database import db_manager
from src.storage.export import ExportService, sanitize_dataframe_for_export
from src.ui.channel_components import get_active_channel
from src.ui.components import (
    TOOL_VIDEO_RESEARCH,
    TOOL_SEO_GENERATOR,
    TOOL_SETTINGS,
)


def render_competitor_research_tool() -> None:
    """Render the upgraded Tool 3: Competitor Research."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                🎯 YouTube Competitor Research
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Analyze publicly ranking competitor videos or channel topics to uncover recurring title hooks, formats, and underserved angles.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Epistemic Modesty Notice
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #8B5CF6; 
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.85rem; color: #475569;">
            🔒 <b>Privacy & Public Data Guarantee:</b> Analysis uses only publicly viewable YouTube video metadata (titles, channel names, 
            publish dates, public view counts). Keyword Studio does not claim to know private competitor metrics such as click-through rates (CTR), 
            subscriber conversion, or YouTube Studio revenue. Observed results represent a sample of ranking videos, not every video published.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Session State
    if "cr_analysis" not in st.session_state:
        st.session_state.cr_analysis = None
    if "cr_last_query" not in st.session_state:
        st.session_state.cr_last_query = ""

    # Check API status
    has_api_key = bool(
        os.getenv("YOUTUBE_API_KEY")
        or (db_manager.get_setting("youtube_api_key") if hasattr(db_manager, "get_setting") else None)
    )

    active_chan = get_active_channel()
    initial_query = (
        st.session_state.cr_last_query
        or st.session_state.get("vr_last_query", "")
        or st.session_state.get("kr_last_query", "")
        or (active_chan.channel_niche.split("&")[0].strip() if active_chan else "")
        or ""
    )

    # Search Form
    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            comp_query = st.text_input(
                "Enter Target Keyword or Competitor Channel Topic",
                value=initial_query,
                placeholder="e.g. best mechanical keyboards, Ali Abdaal study tips, python automation",
                key="cr_keyword_input",
                help="Type a target search topic or creator niche to analyze competitor video patterns.",
            )
        with c_in2:
            st.write("")
            st.write("")
            btn_comp_search = st.button("🎯 Research Competitors", type="primary", use_container_width=True, key="cr_submit_btn")

        # Filters Expander
        with st.expander("⚙️ Competitor Search Filters (Optional)", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                date_filter = st.selectbox(
                    "Published Date Range",
                    ["Any Time", "Last 7 Days", "Last 30 Days", "Last 60 Days", "Last Year"],
                    index=0,
                    key="cr_date_filter",
                )
            with col_f2:
                sort_order = st.selectbox(
                    "Sort Competitor Results By",
                    ["Relevance to Query", "Highest Public View Count", "Most Recently Published"],
                    index=0,
                    key="cr_sort_order",
                )
            with col_f3:
                max_competitors = st.selectbox(
                    "Competitors to Analyze",
                    [10, 15, 25, 50],
                    index=0,
                    key="cr_max_comp",
                )

    # Unconfigured Banner (Actionable guidance)
    if not has_api_key:
        st.markdown(
            """
            <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 14px 16px; margin: 15px 0;">
                <div style="display: flex; align-items: flex-start; gap: 10px;">
                    <span style="font-size: 1.3rem;">ℹ️</span>
                    <div>
                        <div style="font-weight: 700; color: #92400E; margin-bottom: 4px; font-size: 0.95rem;">
                            Live YouTube Data API Key Not Configured
                        </div>
                        <div style="font-size: 0.85rem; color: #78350F; line-height: 1.5;">
                            To fetch live public view counts and top ranking competitor videos directly from YouTube's API:
                            <ol style="margin: 6px 0 6px 18px; padding: 0;">
                                <li>Get a free YouTube Data API v3 key from Google Cloud Console.</li>
                                <li>Add your key in <b>Settings</b> below.</li>
                            </ol>
                            <em>Keyword Studio never fabricates fake competitor view counts or imaginary competitor rankings when credentials are unconfigured.</em>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Handle Search Submission
    if btn_comp_search and comp_query.strip():
        clean_q = comp_query.strip()
        st.session_state.cr_last_query = clean_q

        if not has_api_key:
            unconnected = UnconnectedSerpMetricsProvider()
            metrics = unconnected.get_metrics(clean_q)
            st.session_state.cr_analysis = {
                "keyword": clean_q,
                "is_connected": False,
                "status_message": metrics.status_message,
                "videos": [],
                "queried_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
            st.rerun()
        else:
            with st.spinner(f"Analyzing top ranking videos for '{clean_q}'..."):
                try:
                    serp_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
                    pub_after = None
                    now = datetime.now(timezone.utc)
                    if date_filter == "Last 7 Days":
                        pub_after = (now - timedelta(days=7)).isoformat()
                    elif date_filter == "Last 30 Days":
                        pub_after = (now - timedelta(days=30)).isoformat()
                    elif date_filter == "Last 60 Days":
                        pub_after = (now - timedelta(days=60)).isoformat()
                    elif date_filter == "Last Year":
                        pub_after = (now - timedelta(days=365)).isoformat()

                    order_map = {
                        "Relevance to Query": "relevance",
                        "Highest Public View Count": "viewCount",
                        "Most Recently Published": "date",
                    }

                    analysis = serp_provider.analyze_keyword(
                        keyword=clean_q,
                        max_results=max_competitors,
                        order=order_map.get(sort_order, "relevance"),
                        published_after=pub_after,
                        use_cache=True,
                    )

                    st.session_state.cr_analysis = {
                        "keyword": clean_q,
                        "is_connected": True,
                        "status_message": "Success",
                        "videos": [
                            {
                                "title": v.title,
                                "channel": v.channel_title,
                                "published_at": v.publish_date[:10] if v.publish_date else "Unknown",
                                "views": v.view_count if v.view_count is not None else 0,
                                "daily_views": int(v.daily_views) if v.daily_views is not None else 0,
                                "url": f"https://youtube.com/watch?v={v.video_id}" if v.video_id else "",
                                "has_year": bool(re.search(r"\b202[0-9]\b", v.title)),
                                "has_brackets": bool(re.search(r"[\[\(\{].*?[\]\)\}]", v.title)),
                            }
                            for v in analysis.videos
                        ],
                        "total_analyzed": len(analysis.videos),
                        "avg_views": analysis.average_views,
                        "median_views": analysis.median_views,
                        "common_phrases": analysis.common_keywords,
                        "queried_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    }
                except Exception as exc:
                    st.error(f"Error querying YouTube Data API: {exc}")
                    st.session_state.cr_analysis = None
            st.rerun()

    # Results Section
    analysis_data = st.session_state.cr_analysis
    if analysis_data:
        st.markdown("---")
        if not analysis_data.get("is_connected", False):
            st.info(
                f"**Competitor Research Status for '{analysis_data.get('keyword')}':**\n\n"
                f"• {analysis_data.get('status_message')}\n"
                f"• Retrieval Timestamp: {analysis_data.get('queried_at')}\n\n"
                f"To inspect live competitor video counts and title formats, configure your `YOUTUBE_API_KEY`."
            )
        else:
            videos = analysis_data.get("videos", [])
            st.markdown(f"### 📊 Competitor Landscape for *\"{analysis_data.get('keyword')}\"*")
            st.caption(f"Retrieved {len(videos)} top ranking public videos from YouTube Data API at {analysis_data.get('queried_at')}:")

            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Videos Analyzed", len(videos))
            with m2:
                avg_v = analysis_data.get("avg_views", 0)
                st.metric("Average Views", f"{int(avg_v):,}" if avg_v else "N/A")
            with m3:
                med_v = analysis_data.get("median_views", 0)
                st.metric("Median Views", f"{int(med_v):,}" if med_v else "N/A")
            with m4:
                unique_creators = len(set(v.get("channel") for v in videos if v.get("channel")))
                st.metric("Unique Creators", unique_creators)

            # Grounded Competitor Analysis Section
            if videos:
                st.markdown("#### 💡 Grounded Competitor Insights & Patterns")
                c_an1, c_an2 = st.columns(2)
                with c_an1:
                    year_count = sum(1 for v in videos if v.get("has_year"))
                    bracket_count = sum(1 for v in videos if v.get("has_brackets"))
                    how_to_count = sum(1 for v in videos if "how" in v.get("title", "").lower())
                    review_count = sum(1 for v in videos if "review" in v.get("title", "").lower())
                    vs_count = sum(1 for v in videos if "vs" in v.get("title", "").lower())
                    st.markdown(
                        f"""
                        **Common Structural Hooks in Ranking Titles:**
                        - Contains Current Year (e.g. 2026): **{year_count} of {len(videos)}** titles
                        - Uses Hook Brackets/Parentheses `[..]`: **{bracket_count} of {len(videos)}** titles
                        - How-To / Tutorial Format: **{how_to_count} of {len(videos)}** titles
                        - In-Depth Reviews: **{review_count} of {len(videos)}** titles
                        - Direct Comparisons (VS): **{vs_count} of {len(videos)}** titles
                        """
                    )
                with c_an2:
                    common_kws = analysis_data.get("common_phrases", [])
                    phrases_html = " ".join([f"`{p}`" for p in common_kws[:6]]) if common_kws else "N/A"
                    st.markdown(
                        f"""
                        **Recurring Keyword Themes in Sample:**
                        {phrases_html}

                        **Content Gap Opportunity:**
                        - Many ranking videos are general overviews. Address specific beginner pain points or long-term durability tests not covered in the top 3 videos.
                        """
                    )

                # Video Table
                st.markdown("#### 📹 Ranking Competitor Videos Evidence")
                df_vids = pd.DataFrame(videos)
                st.dataframe(
                    df_vids[["title", "channel", "published_at", "views", "daily_views", "url"]],
                    column_config={
                        "title": st.column_config.TextColumn("Video Title", width="large"),
                        "channel": st.column_config.TextColumn("Channel", width="medium"),
                        "published_at": st.column_config.TextColumn("Published", width="small"),
                        "views": st.column_config.NumberColumn("Total Views", format="%d"),
                        "daily_views": st.column_config.NumberColumn("Daily Velocity", format="%d"),
                        "url": st.column_config.LinkColumn("Watch on YouTube", width="small"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                # Action Buttons
                c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 2])
                with c_act1:
                    export_svc = ExportService()
                    csv_bytes = export_svc.export_csv(df_vids, sanitize_formulas=True)
                    st.download_button(
                        label="📥 Export Competitor Data CSV",
                        data=csv_bytes,
                        file_name=f"competitors_{analysis_data.get('keyword', '').replace(' ', '_')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="cr_export_csv_btn",
                    )
                with c_act2:
                    if st.button("🎥 Open in Video Research", use_container_width=True, key="cr_open_vr_btn"):
                        st.session_state.vr_target_keyword = analysis_data.get("keyword", "")
                        st.session_state.current_page = TOOL_VIDEO_RESEARCH
                        st.rerun()
                with c_act3:
                    if st.button(f"✨ Send Topic to SEO Generator", type="primary", use_container_width=True, key="cr_send_seo_btn"):
                        st.session_state.seo_main_keyword = analysis_data.get("keyword", "")
                        if videos:
                            st.session_state.seo_secondary_keywords = videos[0].get("title", "")
                        st.session_state.current_page = TOOL_SEO_GENERATOR
                        st.rerun()
    else:
        st.info("👆 Enter a target keyword or competitor channel topic above to inspect top competing YouTube videos.")
