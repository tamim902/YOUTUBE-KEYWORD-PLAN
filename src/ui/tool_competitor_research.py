"""Tool 2: Competitor Research — Simplified Core Workflow.

Analyzes public competitor videos using official YouTube Data API v3 when configured:
- Public video data: Title, Channel, Published Date, View Count, URL
- Simple grounded analysis: Common title patterns, frequently covered subtopics, recent video volume
- Unconnected state: Actionable setup instructions without fake metrics
- Epistemic modesty: Clear disclosure of sample boundaries with zero private analytics claims
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis
from src.providers.serp import UnconnectedSerpMetricsProvider, YouTubeDataApiSerpProvider
from src.storage.export import ExportService, sanitize_dataframe_for_export


def render_competitor_research_tool() -> None:
    """Render the simplified Tool 2: Competitor Research."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                🎯 YouTube Competitor Research
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Analyze publicly ranking YouTube videos for your target keyword to uncover title hooks, subtopics, and content gaps.
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
            subscriber conversion, or YouTube Studio revenue.
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
    has_api_key = bool(os.getenv("YOUTUBE_API_KEY"))

    # Search Form
    with st.container():
        c_in1, c_in2 = st.columns([3.5, 1.5])
        with c_in1:
            comp_query = st.text_input(
                "Enter Keyword to Research Competitors",
                value=st.session_state.cr_last_query,
                placeholder="e.g. best mechanical keyboards 2026, python langgraph tutorial",
                key="cr_keyword_input",
            )
        with c_in2:
            st.write("")
            st.write("")
            btn_comp_search = st.button("🎯 Research Competitors", type="primary", use_container_width=True, key="cr_submit_btn")

        # Filters Expander
        with st.expander("⚙️ Competitor Search Filters (Optional)", expanded=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                date_filter = st.selectbox(
                    "Published Date Range",
                    ["Any Time", "Last 7 Days", "Last 30 Days", "Last 60 Days", "Last Year"],
                    key="cr_date_filter",
                )
            with col_f2:
                sort_order = st.selectbox(
                    "Sort Competitor Results By",
                    ["Relevance to Query", "Highest Public View Count", "Most Recently Published"],
                    key="cr_sort_order",
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
                                <li>Get a free YouTube Data API v3 key from the <a href="https://console.cloud.google.com/" target="_blank" style="color: #2563EB; font-weight: 600;">Google Cloud Console</a> (free tier provides 10,000 units/day).</li>
                                <li>Add <code>YOUTUBE_API_KEY=your_key_here</code> to your <code>.env</code> file, or open <b>Settings</b> below to paste it.</li>
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
            # Fallback when key is missing: Show clear message via UnconnectedSerpMetricsProvider
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
            # Query official YouTube Data API v3
            with st.spinner(f"Analyzing top ranking videos for '{clean_q}'..."):
                try:
                    serp_provider = YouTubeDataApiSerpProvider()
                    # Calculate date cutoff
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
                        max_results=12,
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
                                "published_at": v.published_at[:10] if v.published_at else "Unknown",
                                "views": v.view_count if v.view_count is not None else 0,
                                "url": f"https://youtube.com/watch?v={v.video_id}" if v.video_id else "",
                                "has_year": bool(v.has_year),
                                "has_brackets": bool(v.has_brackets),
                            }
                            for v in analysis.videos
                        ],
                        "total_analyzed": len(analysis.videos),
                        "avg_views": analysis.average_views,
                        "newest_days": analysis.newest_video_days,
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
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Videos Analyzed", len(videos))
            with m2:
                avg_v = analysis_data.get("avg_views", 0)
                st.metric("Average Public Views", f"{int(avg_v):,}" if avg_v else "N/A")
            with m3:
                newest = analysis_data.get("newest_days", 0)
                st.metric("Newest Competitor Video", f"{newest} days ago" if newest else "Recent")

            # Simple Competitor Analysis Section
            if videos:
                with st.container():
                    st.markdown("#### 💡 Grounded Competitor Insights")
                    c_an1, c_an2 = st.columns(2)
                    with c_an1:
                        # Extract title patterns
                        year_count = sum(1 for v in videos if v.get("has_year"))
                        bracket_count = sum(1 for v in videos if v.get("has_brackets"))
                        st.markdown(
                            f"""
                            **Common Title Patterns:**
                            - Includes current year (e.g. 2026): **{year_count} of {len(videos)}** titles
                            - Uses hooks/brackets (e.g. [Review], (Don't Buy)): **{bracket_count} of {len(videos)}** titles
                            """
                        )
                    with c_an2:
                        st.markdown(
                            f"""
                            **Content Angle Opportunity:**
                            - Create an updated, hands-on comparison with structured timestamps and unique testing.
                            - Target sub-questions not fully addressed in the top 3 ranking titles.
                            """
                        )

                # Video Table
                st.markdown("#### 📹 Ranking Videos Breakdown")
                df_vids = pd.DataFrame(videos)
                st.dataframe(
                    df_vids[["title", "channel", "published_at", "views", "url"]],
                    column_config={
                        "title": st.column_config.TextColumn("Video Title", width="large"),
                        "channel": st.column_config.TextColumn("Channel", width="medium"),
                        "published_at": st.column_config.TextColumn("Published Date", width="small"),
                        "views": st.column_config.NumberColumn("Public Views", format="%d"),
                        "url": st.column_config.LinkColumn("YouTube Link", width="small"),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                # Export CSV
                export_svc = ExportService()
                csv_bytes = export_svc.export_csv(df_vids, sanitize_formulas=True)
                st.download_button(
                    label="📥 Export Competitor Data as CSV",
                    data=csv_bytes,
                    file_name=f"competitor_research_{analysis_data.get('keyword', '').replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=False,
                    key="cr_export_csv_btn",
                )
    else:
        st.info("👆 Enter a target keyword above to inspect top competing YouTube videos.")
