"""Personal YouTube SEO Coach & Daily Action Center UI (Phase 31).

Renders the "Your Next Best Steps" action center dashboard, 4-channel task queues,
5-section beginner SEO coaching guides, and the evidence-based Keyword Decision Helper.
"""

from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.action_center import ActionTask, TaskStatus, action_center_engine
from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.intelligence.daily_engine import daily_opportunity_engine
from src.intelligence.decision_helper import KeywordDecision, keyword_decision_helper
from src.models.channel import ChannelProfile


def render_action_center_dashboard(is_ready: bool) -> None:
    """Render the 'Your Next Best Steps' Daily Action Center & SEO Coach on Dashboard."""
    if not is_ready:
        st.warning("Database connection is initializing. Action Center will load once ready.")
        return

    channels = channel_manager.get_all_channels()
    if not channels:
        st.info("No channel profiles found. Initializing default channels...")
        channels = channel_manager.get_all_channels()

    # Active channel selection inside Action Center
    active_idx = int(st.session_state.get("active_channel_id", 1)) - 1
    if active_idx < 0 or active_idx >= len(channels):
        active_idx = 0

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%); border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                        <span style="font-size: 1.3rem;">🎯</span>
                        <h3 style="margin: 0; font-size: 1.28rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                            Your Next Best Steps
                        </h3>
                        <span style="background: rgba(79, 70, 229, 0.08); color: #4F46E5; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 6px;">
                            PERSONAL SEO COACH
                        </span>
                    </div>
                    <div style="font-size: 0.88rem; color: #64748B; line-height: 1.45;">
                        Evidence-based, prioritized action items tailored to your channels based on authentic application research and progress.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # 4-Channel Tabs
    # --------------------------------------------------------------------------
    channel_tab_names = [f"📺 {c.channel_name}" for c in channels]
    chan_tabs = st.tabs(channel_tab_names)

    for i, tab in enumerate(chan_tabs):
        chan = channels[i]
        with tab:
            render_channel_action_queue(chan)

    # --------------------------------------------------------------------------
    # Daily Research Automation & Scheduler Telemetry Drawer
    # --------------------------------------------------------------------------
    sched = action_center_engine.get_scheduler_status()
    with st.expander("⏰ Daily Morning Research & Automation Telemetry", expanded=False):
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Last Research Run", sched["last_run_display"].split(" at ")[0] if " at " in sched["last_run_display"] else sched["last_run_display"])
            st.caption(f"Status: **{sched['last_status']}**")
        with col_s2:
            st.metric("Next Run", "07:00 AM")
            st.caption(f"Timezone: **{sched['timezone']}**")
        with col_s3:
            st.metric("Unreviewed Ideas", sched["unreviewed_ideas_total"])
            st.caption("Across all 4 channels")
        with col_s4:
            st.metric("Failed Runs", sched["failed_reports_count"])
            st.caption("Zero errors detected" if sched["failed_reports_count"] == 0 else "Review logs")

        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.82rem; color: #475569; margin: 0.75rem 0;">
                ℹ️ <b>Local Execution Notice:</b> {sched['local_runner_notice']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("⚡ Run Daily Morning Research Now (All 4 Channels)", key="btn_dash_run_morning", use_container_width=True):
            with st.spinner("Executing independent 4-channel research pipelines..."):
                rep = daily_opportunity_engine.run_daily_morning_report()
                st.success(f"Generated {len(rep.ideas)} topic opportunities across {rep.total_channels_processed} channels!")
                st.rerun()


def render_channel_action_queue(channel: ChannelProfile) -> None:
    """Render the action items and progress summary for a specific channel."""
    c_id = channel.id or 1
    prog = action_center_engine.get_progress_summary(c_id)

    # Simple Real Progress Tracking Header
    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
    with col_p1:
        st.metric("Saved Projects", prog["saved_searches"])
    with col_p2:
        st.metric("Topics Awaiting Review", prog["topics_awaiting_review"])
    with col_p3:
        st.metric("Briefs Completed", prog["briefs_completed"])
    with col_p4:
        st.metric("Videos In Production", prog["videos_in_production"])
    with col_p5:
        st.metric("Audits Needing Fixes", prog["audits_requiring_attention"])

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Sync and retrieve real pending tasks for this channel
    tasks = action_center_engine.sync_tasks_for_channel(c_id)

    if not tasks:
        st.markdown(
            f"""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 1.25rem 1.5rem; text-align: center; margin: 1rem 0;">
                <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">🎉</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #166534; margin-bottom: 0.25rem;">
                    All Caught Up for {channel.channel_name}!
                </div>
                <div style="font-size: 0.86rem; color: #15803D; line-height: 1.45;">
                    No pending action items right now. Start a new keyword search or generate morning opportunities to discover fresh topics.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("🔍 Launch New Keyword Research", key=f"btn_empty_research_{c_id}", use_container_width=True):
                st.session_state["active_channel_id"] = c_id
                st.session_state["current_page"] = "🔍 New Keyword Research"
                st.rerun()
        with col_c2:
            if st.button("🌅 View Morning Idea Report", key=f"btn_empty_morning_{c_id}", use_container_width=True):
                st.session_state["active_channel_id"] = c_id
                st.session_state["current_page"] = "🌅 Daily Morning Idea Report"
                st.rerun()
        return

    # Render Task Cards
    for idx, task in enumerate(tasks):
        render_task_card(task, channel, idx)


def render_task_card(task: ActionTask, channel: ChannelProfile, index: int) -> None:
    """Render a single actionable SEO task card with structured coaching expander."""
    c_id = channel.id or 1
    unique_key = f"{task.task_key}_{c_id}_{index}"

    priority_bg = "rgba(220, 38, 38, 0.08)" if task.priority == "high" else "rgba(79, 70, 229, 0.08)"
    priority_color = "#DC2626" if task.priority == "high" else "#4F46E5"
    priority_label = "⚡ HIGH PRIORITY" if task.priority == "high" else "📌 ACTION ITEM"

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.35rem; margin-bottom: 0.95rem; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.5rem;">
                <span style="background: {priority_bg}; color: {priority_color}; font-size: 0.74rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 6px;">
                    {priority_label}
                </span>
                <span style="font-size: 0.78rem; color: #64748B;">Channel: <b>{task.channel_name}</b></span>
            </div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 0.25rem;">
                {task.title}
            </div>
            <div style="font-size: 0.86rem; color: #475569; line-height: 1.45; margin-bottom: 0.65rem;">
                {task.short_summary}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5-Section Beginner-Friendly SEO Coach Guidance Expander
    with st.expander(f"🧭 SEO Coach: How to Complete This Step", expanded=False):
        st.markdown(
            f"""
            <div style="font-size: 0.88rem; line-height: 1.55; color: #334155;">
                <div style="margin-bottom: 0.6rem;">
                    <b>🎯 WHAT TO DO:</b><br>
                    {task.what_to_do}
                </div>
                <div style="margin-bottom: 0.6rem;">
                    <b>💡 WHY IT MATTERS:</b><br>
                    {task.why_it_matters}
                </div>
                <div style="margin-bottom: 0.6rem;">
                    <b>🛠️ HOW TO DO IT:</b>
                    <ul style="margin: 0.25rem 0 0.5rem 1.25rem; padding: 0;">
                        {''.join(f'<li>{step}</li>' for step in task.how_to_do_it)}
                    </ul>
                </div>
                <div style="margin-bottom: 0.6rem;">
                    <b>✅ WHAT TO CHECK (Creator Manual Checklist):</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Interactive manual checklist items
        for c_idx, check_item in enumerate(task.what_to_check):
            st.checkbox(check_item, key=f"chk_{unique_key}_{c_idx}")

        st.markdown(
            f"""
            <div style="font-size: 0.88rem; line-height: 1.55; color: #334155; margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px dashed #E2E8F0;">
                <b>⏭️ WHAT COMES NEXT:</b> {task.what_comes_next}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Action Buttons Row
    col_b1, col_b2, col_b3 = st.columns([2.5, 1.2, 0.9])
    with col_b1:
        if st.button(
            f"👉 Open in {task.target_page} →",
            key=f"btn_open_{unique_key}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["active_channel_id"] = task.channel_id
            st.session_state["current_page"] = task.target_page
            if "keyword" in task.context_data:
                st.session_state["active_seed_input"] = task.context_data["keyword"]
                st.session_state["last_query"] = task.context_data["keyword"]
            st.rerun()

    with col_b2:
        if st.button(
            "✅ Mark as Done",
            key=f"btn_done_{unique_key}",
            use_container_width=True,
        ):
            action_center_engine.mark_task_completed(task.task_key)
            st.toast(f"Task marked complete: '{task.title}'")
            st.rerun()

    with col_b3:
        if st.button(
            "✕ Dismiss",
            key=f"btn_dismiss_{unique_key}",
            use_container_width=True,
            help="Dismiss this recommendation. It will not be re-suggested.",
        ):
            action_center_engine.dismiss_task(task.task_key)
            st.toast("Recommendation dismissed.")
            st.rerun()

    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)


def render_keyword_decision_helper(
    candidate_keywords: List[str],
    channel: ChannelProfile,
    limit: int = 4,
) -> None:
    """Render the Keyword Decision Helper comparing candidates with honest evidence."""
    if not candidate_keywords:
        return

    decisions = keyword_decision_helper.evaluate_candidates(
        candidate_keywords,
        channel,
        limit=limit,
    )
    if not decisions:
        return

    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.35rem; margin: 1.25rem 0 0.85rem 0; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                <span style="font-size: 1.25rem;">⚖️</span>
                <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A;">
                    Keyword Decision Helper
                </div>
                <span style="background: rgba(37, 99, 235, 0.08); color: #1D4ED8; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 5px;">
                    TRANSPARENT EVIDENCE
                </span>
            </div>
            <div style="font-size: 0.85rem; color: #64748B; line-height: 1.45;">
                Compare candidate phrases against your channel's established niche, search intent, and existing video catalog.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, dec in enumerate(decisions):
        with st.container():
            st.markdown(
                f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; flex-wrap: wrap; gap: 0.5rem;">
                        <span style="font-size: 0.98rem; font-weight: 700; color: #1E293B;">
                            <code>{dec.keyword}</code>
                        </span>
                        <div style="display: flex; gap: 0.4rem; align-items: center;">
                            <span style="font-size: 0.78rem; font-weight: 700; color: #0F172A;">
                                {dec.verdict}
                            </span>
                            <span style="font-size: 0.72rem; color: #64748B; background: #FFFFFF; border: 1px solid #CBD5E1; padding: 0.1rem 0.45rem; border-radius: 4px;">
                                {dec.confidence}
                            </span>
                        </div>
                    </div>
                    <div style="font-size: 0.84rem; color: #475569; line-height: 1.5; margin-bottom: 0.5rem;">
                        <div>• <b>Relevance:</b> {dec.relevance_reason}</div>
                        <div>• <b>Intent & Format:</b> {dec.intent_fit}</div>
                        <div>• <b>Tail Length:</b> {dec.tail_length_fit}</div>
                        <div>• <b>Catalog Overlap:</b> {dec.cannibalization_risk}</div>
                        <div>• <b>Competitor Evidence:</b> {dec.competitor_evidence}</div>
                        <div>• <b>Source:</b> {dec.coverage_source}</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.82rem; color: #334155;">
                        <b>👉 Recommended Next Step:</b> {dec.recommended_action}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.caption(f"ℹ️ {decisions[0].disclaimer}")
