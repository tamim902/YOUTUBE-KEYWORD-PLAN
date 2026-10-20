"""
Streamlit UI Components for Phase 34: Personal SEO Research Memory & Smart Recommendations.

Provides:
1. In-context duplicate research detector banner for New Research and Wizard.
2. Channel research memory registry with search, filters, and safe deletion.
3. Smart Next Actions card with transparent evidence explanations and feedback controls.
4. Creator performance insights comparing selected vs published topics and self-reported ratings.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.channel_manager import channel_manager
from src.intelligence.research_memory import (
    FeedbackStatus,
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    ResearchMemoryEngine,
    SimilarityType,
    UserPerformanceRating,
)
from src.storage.database import db_manager


def _get_memory_engine() -> ResearchMemoryEngine:
    """Get or create singleton instance of ResearchMemoryEngine in session state."""
    if "research_memory_engine" not in st.session_state:
        st.session_state.research_memory_engine = ResearchMemoryEngine(
            database=db_manager,
            chan_mgr=channel_manager,
            stale_threshold_days=30,
        )
    return st.session_state.research_memory_engine


def render_duplicate_detection_banner(channel_id: int, query: str, context: str = "new_research") -> None:
    """Render an in-context duplicate research detection alert when query matches previous topics."""
    clean_q = query.strip()
    if not clean_q or len(clean_q) < 3:
        return

    engine = _get_memory_engine()
    match = engine.check_duplicate_research(channel_id=channel_id, query=clean_q)

    if not match.is_duplicate:
        return

    # Visual container for duplicate match
    badge_color = "#E0F2FE" if not match.is_stale else "#FEF3C7"
    badge_text_color = "#0369A1" if not match.is_stale else "#92400E"
    badge_label = f"Previously researched ({match.days_ago}d ago)" if not match.is_stale else f"Needs fresh research (Stale: {match.days_ago}d ago)"
    border_color = "#BAE6FD" if not match.is_stale else "#FDE68A"

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1.5px solid {border_color}; border-radius: 10px; padding: 1rem 1.25rem; margin-top: 0.75rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.1rem;">🧠</span>
                    <strong style="color: #0F172A; font-size: 0.95rem;">Research Memory: Similar Topic Found</strong>
                </div>
                <span style="background: {badge_color}; color: {badge_text_color}; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 9999px;">
                    {badge_label}
                </span>
            </div>
            <div style="color: #475569; font-size: 0.88rem; line-height: 1.45; margin-bottom: 0.6rem;">
                {match.explanation}
            </div>
            <div style="font-size: 0.82rem; color: #64748B;">
                Matched: <strong>"{match.matched_topic}"</strong> ({round(match.similarity_score * 100)}% similarity)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2, col_space = st.columns([1.5, 1.8, 2.5])
    with col_btn1:
        if st.button(
            "📂 Reopen Saved Findings",
            key=f"dup_btn_reopen_{context}_{channel_id}_{abs(hash(clean_q)) % 10000}",
            use_container_width=True,
            help="Review previously discovered queries, packages, and notes for this topic.",
        ):
            st.session_state.last_query = match.matched_topic
            st.session_state.active_seed_input = match.matched_topic
            st.session_state.current_page = "📋 Keyword Results"
            st.rerun()

    with col_btn2:
        st.caption("ℹ️ *A fresh search will never be blocked.*")


def render_research_memory_registry_tab(active_channel_id: int) -> None:
    """Render the full Research Memory registry table and search interface."""
    engine = _get_memory_engine()
    channel = channel_manager.get_channel(active_channel_id)
    c_name = channel.channel_name if channel else f"Channel {active_channel_id}"

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.4rem; margin-bottom: 1.15rem;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.25rem;">
                🧠 Research Memory: {c_name}
            </div>
            <div style="font-size: 0.88rem; color: #64748B; line-height: 1.45;">
                A centralized, channel-isolated memory of all previously researched seed keywords, saved topics,
                published videos, and rejection feedback. Never repeat duplicate work across your portfolio.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sync memory from existing searches and packages
    engine.db.sync_channel_research_memory(active_channel_id)

    # Controls Row: Search and Filters
    col_f1, col_f2, col_f3 = st.columns([2.5, 1.3, 1.2])
    with col_f1:
        search_mem = st.text_input(
            "Search Memory",
            placeholder="Search previously explored keywords or topics...",
            key=f"mem_search_input_{active_channel_id}",
        )
    with col_f2:
        filter_type = st.selectbox(
            "Filter Type",
            options=["All Types", "Seed Searches", "Saved Topics", "Content Packages", "Published Videos", "Rejected Ideas"],
            key=f"mem_filter_type_{active_channel_id}",
        )
    with col_f3:
        filter_status = st.selectbox(
            "Filter Status",
            options=["All Statuses", "Active", "Published", "Rejected", "Stale"],
            key=f"mem_filter_status_{active_channel_id}",
        )

    # Map filter strings to database values
    type_map = {
        "Seed Searches": "seed_search",
        "Saved Topics": "saved_topic",
        "Content Packages": "content_package",
        "Published Videos": "published_video",
        "Rejected Ideas": "rejected_idea",
    }
    status_map = {
        "Active": "active",
        "Published": "published",
        "Rejected": "rejected",
        "Stale": "stale",
    }

    db_type = type_map.get(filter_type)
    db_status = status_map.get(filter_status)

    records = engine.db.get_research_memory_records(
        channel_id=active_channel_id,
        memory_type=db_type,
        status=db_status,
        search_query=search_mem,
        limit=150,
    )

    if not records:
        st.info(f"No research memory entries found for {c_name} matching current filters.")
        return

    # Metrics Summary Row
    total_stored = len(records)
    published_cnt = sum(1 for r in records if r.get("status") == "published" or r.get("memory_type") == "published_video")
    packages_cnt = sum(1 for r in records if r.get("memory_type") == "content_package")
    stale_cnt = sum(1 for r in records if r.get("is_stale") or r.get("status") == "stale")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Topics in Memory", total_stored)
    with col_m2:
        st.metric("Packages Ready", packages_cnt)
    with col_m3:
        st.metric("Published Videos", published_cnt)
    with col_m4:
        st.metric("Stale Research (>30d)", stale_cnt)

    st.markdown("---")

    # Render Record Cards
    for rec in records:
        r_id = rec.get("id")
        topic = rec.get("topic_or_keyword", "")
        m_type = rec.get("memory_type", "seed_search")
        status = rec.get("status", "active")
        res_date = rec.get("research_date", "")[:10]
        evidence = rec.get("evidence_summary", {})
        rejection_reason = rec.get("rejection_reason", "")
        user_rating = rec.get("user_performance_rating", "")

        # Type Badge Styling
        type_badge = {
            "seed_search": ("🔍 Seed Search", "#F1F5F9", "#475569"),
            "saved_topic": ("💡 Saved Topic", "#E0F2FE", "#0284C7"),
            "content_package": ("📦 Content Package", "#EDE9FE", "#7C3AED"),
            "published_video": ("🎬 Published Video", "#DCFCE7", "#16A34A"),
            "rejected_idea": ("❌ Rejected Idea", "#FEE2E2", "#DC2626"),
        }.get(m_type, ("📄 Memory Record", "#F1F5F9", "#475569"))

        with st.container():
            col_info, col_actions = st.columns([3.5, 1.5])
            with col_info:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
                        <strong style="font-size: 1.02rem; color: #0F172A;">{topic}</strong>
                        <span style="background: {type_badge[1]}; color: {type_badge[2]}; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 9999px;">
                            {type_badge[0]}
                        </span>
                        <span style="background: #F8FAFC; color: #64748B; font-size: 0.72rem; padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid #E2E8F0;">
                            {res_date}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if rejection_reason:
                    st.caption(f"Reason for rejection: *{rejection_reason}*")
                elif user_rating:
                    st.caption(f"Creator Performance Rating: **{user_rating.replace('_', ' ').title()}**")
                elif evidence:
                    sample_details = ", ".join(f"{k}: {v}" for k, v in list(evidence.items())[:2])
                    st.caption(f"Evidence: {sample_details}")

            with col_actions:
                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    if st.button("🚀 Load", key=f"mem_btn_load_{r_id}", use_container_width=True, help="Load into New Keyword Research"):
                        st.session_state.active_seed_input = topic
                        st.session_state.current_page = "🔍 New Keyword Research"
                        st.rerun()

                with col_act2:
                    if st.button("🗑️", key=f"mem_btn_del_{r_id}", help="Delete this individual memory record"):
                        engine.clear_memory_record(record_id=r_id, channel_id=active_channel_id)
                        st.toast("Memory record deleted.")
                        st.rerun()

            st.markdown("<hr style='margin: 0.4rem 0; border: none; border-bottom: 1px solid #F1F5F9;'>", unsafe_allow_html=True)


def render_smart_recommendations_tab(active_channel_id: int) -> None:
    """Render smart recommendations with transparent explanations and feedback buttons."""
    engine = _get_memory_engine()
    channel = channel_manager.get_channel(active_channel_id)
    c_name = channel.channel_name if channel else f"Channel {active_channel_id}"

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.4rem; margin-bottom: 1.15rem;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.25rem;">
                💡 Smart Next Actions: {c_name}
            </div>
            <div style="font-size: 0.88rem; color: #64748B; line-height: 1.45;">
                Evidence-grounded next steps derived strictly from your channel's real saved research, unreviewed gap ideas,
                and content packages. Teach the system what is useful by giving feedback.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recs = engine.generate_smart_recommendations(channel_id=active_channel_id, max_recommendations=6)

    if not recs:
        st.info(f"No pending recommendations for {c_name}. All saved topics and packages are up to date.")
        return

    for idx, rec in enumerate(recs):
        r_key = rec.recommendation_key
        with st.container():
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 0.85rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 0.25rem;">
                        {rec.title}
                    </div>
                    <div style="font-size: 0.86rem; color: #334155; margin-bottom: 0.35rem;">
                        <strong>Why suggested:</strong> {rec.why_suggested}
                    </div>
                    <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.6rem;">
                        <strong>Supporting Evidence:</strong> {rec.supporting_evidence}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_action, col_fb1, col_fb2, col_fb3 = st.columns([2.5, 1, 1.2, 1.3])
            with col_action:
                if st.button(
                    f"👉 {rec.next_action_label}",
                    key=f"rec_action_btn_{r_key}_{idx}",
                    type="primary",
                    use_container_width=True,
                ):
                    if rec.target_page:
                        st.session_state.current_page = rec.target_page
                        if rec.target_params.get("topic"):
                            st.session_state.active_seed_input = rec.target_params["topic"]
                        st.rerun()

            with col_fb1:
                if st.button("👍 Useful", key=f"fb_useful_{r_key}_{idx}", use_container_width=True):
                    engine.record_recommendation_feedback(
                        channel_id=active_channel_id,
                        recommendation_key=r_key,
                        recommendation_type=rec.recommendation_type,
                        status=FeedbackStatus.USEFUL,
                    )
                    st.toast("Feedback recorded: Marked Useful.")
                    st.rerun()

            with col_fb2:
                if st.button("👎 Not relevant", key=f"fb_notrel_{r_key}_{idx}", use_container_width=True):
                    engine.record_recommendation_feedback(
                        channel_id=active_channel_id,
                        recommendation_key=r_key,
                        recommendation_type=rec.recommendation_type,
                        status=FeedbackStatus.NOT_RELEVANT,
                    )
                    st.toast("Dismissed: Recommendation removed from future suggestions.")
                    st.rerun()

            with col_fb3:
                if st.button("✅ Completed", key=f"fb_comp_{r_key}_{idx}", use_container_width=True):
                    engine.record_recommendation_feedback(
                        channel_id=active_channel_id,
                        recommendation_key=r_key,
                        recommendation_type=rec.recommendation_type,
                        status=FeedbackStatus.ALREADY_COMPLETED,
                    )
                    st.toast("Marked as Completed.")
                    st.rerun()

            st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)


def render_performance_insights_tab(active_channel_id: int) -> None:
    """Render performance tracking comparing selected vs published topics and self-reported ratings."""
    engine = _get_memory_engine()
    insights = engine.get_performance_insights(active_channel_id)

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.4rem; margin-bottom: 1.15rem;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.25rem;">
                📊 Performance Insights: {insights.channel_name}
            </div>
            <div style="font-size: 0.88rem; color: #64748B; line-height: 1.45;">
                {insights.analytics_explanation}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Topics Selected", insights.total_topics_selected)
    with col2:
        st.metric("Topics Published", insights.total_topics_published)
    with col3:
        st.metric("Video Packages", insights.total_packages_created)
    with col4:
        st.metric("Total Searches Run", insights.total_searches_run)

    st.markdown("---")

    col_v, col_r = st.columns(2)
    with col_v:
        st.markdown("#### 📈 Research Velocity Over Time")
        st.markdown(
            f"""
            - **Past 7 Days:** {insights.topics_over_time.get('past_7_days', 0)} topics researched or saved
            - **Past 30 Days:** {insights.topics_over_time.get('past_30_days', 0)} topics researched or saved
            - **All-Time Records:** {insights.topics_over_time.get('all_time', 0)} memory records
            """
        )

    with col_r:
        st.markdown("#### 🌟 Creator Self-Reported Performance Ratings")
        ratings = insights.user_ratings_breakdown
        st.markdown(
            f"""
            - **Exceeded Expectations:** {ratings.get('exceeded_expectations', 0)}
            - **Met Expectations:** {ratings.get('met_expectations', 0)}
            - **Underperformed:** {ratings.get('underperformed', 0)}
            - **Unrated:** {ratings.get('unrated', 0)}
            """
        )

    # Form to explicitly record a published video
    with st.expander("🎬 Record a Video as Published & Rate Performance"):
        with st.form(key=f"record_published_form_{active_channel_id}"):
            pub_topic = st.text_input("Published Video Topic", placeholder="e.g. Best Custom Mechanical Keyboards")
            pub_url = st.text_input("YouTube Video URL (Optional)", placeholder="https://youtube.com/watch?v=...")
            pub_rating = st.selectbox(
                "Creator Performance Rating",
                options=["met_expectations", "exceeded_expectations", "underperformed", "unrated"],
                format_func=lambda x: x.replace("_", " ").title(),
            )
            submit_pub = st.form_submit_button("✅ Record as Published")
            if submit_pub:
                if pub_topic.strip():
                    engine.record_topic_published(
                        channel_id=active_channel_id,
                        topic=pub_topic.strip(),
                        video_url=pub_url.strip(),
                        user_rating=pub_rating,
                    )
                    st.success(f"Recorded '{pub_topic.strip()}' as Published.")
                    st.rerun()
                else:
                    st.warning("Please enter a topic.")
