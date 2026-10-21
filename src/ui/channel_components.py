"""Channel Workspace Components: Compact Selector, Profile Manager & Video Ideas.

Provides:
- Compact 4-channel switcher in the top header
- Active channel context (niche, language, audience, format, exclusions)
- Channel Profile Editor (CRUD operations persisted to SQLite)
- Channel-Wise Video Ideas Generator ("Find Video Ideas for My Channel")
- 1-click "Start Creating" handoff directly to SEO Generator
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.intelligence.daily_engine import daily_opportunity_engine
from src.models.channel import ChannelProfile, get_default_four_channels
from src.models.morning_report import DailyIdeaItem, IdeaReviewStatus
from src.storage.database import db_manager
from src.ui.components import TOOL_SEO_GENERATOR


def get_active_channel() -> ChannelProfile:
    """Retrieve the currently active ChannelProfile from session state and database."""
    chan_id = int(st.session_state.get("active_channel_id", 1))
    profile = channel_manager.get_channel(chan_id)
    if not profile:
        profile = channel_manager.get_all_channels()[0]
        st.session_state["active_channel_id"] = profile.id or 1
    return profile


def switch_active_channel(from_id: int, to_id: int, channels: List[ChannelProfile]) -> None:
    """Safely switch active channel with complete isolation of research results and queries."""
    if from_id == to_id:
        return

    # 1. Snapshot outgoing channel state
    st.session_state[f"chan_state_{from_id}"] = {
        "kr_results": list(st.session_state.get("kr_results", [])),
        "kr_last_query": st.session_state.get("kr_last_query", ""),
        "kr_patterns": list(st.session_state.get("kr_patterns", [])),
        "current_serp_analysis": st.session_state.get("current_serp_analysis", None),
        "vr_last_query": st.session_state.get("vr_last_query", ""),
        "vr_target_keyword": st.session_state.get("vr_target_keyword", ""),
        "cr_analysis": st.session_state.get("cr_analysis", None),
        "cr_last_query": st.session_state.get("cr_last_query", ""),
        "opp_results": list(st.session_state.get("opp_results", [])),
        "opp_last_seed": st.session_state.get("opp_last_seed", ""),
        "seo_generated_pkg": st.session_state.get("seo_generated_pkg", None),
        "seo_main_keyword": st.session_state.get("seo_main_keyword", ""),
        "seo_secondary_keywords": st.session_state.get("seo_secondary_keywords", ""),
        "seo_topic_summary": st.session_state.get("seo_topic_summary", ""),
        "seo_target_viewer": st.session_state.get("seo_target_viewer", ""),
    }

    # 2. Update active channel id
    st.session_state["active_channel_id"] = to_id
    st.session_state["show_channel_ideas_panel"] = True

    # 3. Find incoming channel profile
    target_chan = next((c for c in channels if c.id == to_id), None)
    default_seed = target_chan.channel_niche.split("&")[0].strip() if target_chan else ""
    target_viewer = target_chan.target_audience if target_chan else "General Audience"

    # 4. Restore incoming channel state or initialize clean isolated state
    incoming_state = st.session_state.get(f"chan_state_{to_id}")
    if incoming_state:
        for k, v in incoming_state.items():
            st.session_state[k] = v
    else:
        st.session_state["kr_results"] = []
        st.session_state["kr_last_query"] = default_seed
        st.session_state["kr_patterns"] = []
        st.session_state["current_serp_analysis"] = None
        st.session_state["vr_last_query"] = default_seed
        st.session_state["vr_target_keyword"] = default_seed
        st.session_state["cr_analysis"] = None
        st.session_state["cr_last_query"] = default_seed
        st.session_state["opp_results"] = []
        st.session_state["opp_last_seed"] = default_seed
        st.session_state["seo_generated_pkg"] = None
        st.session_state["seo_main_keyword"] = default_seed
        st.session_state["seo_secondary_keywords"] = ""
        st.session_state["seo_topic_summary"] = ""
        st.session_state["seo_target_viewer"] = target_viewer


def render_channel_header_bar() -> ChannelProfile:
    """Render compact 4-channel switcher, active channel badge, and quick actions."""
    channels = channel_manager.get_all_channels()
    current_chan = get_active_channel()
    curr_id = current_chan.id or 1

    # Main Channel Header Card
    st.markdown(
        """
        <style>
            .ks-chan-bar {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 10px 14px;
                margin-bottom: 14px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 4 Channel Pills Row
    c_pills = st.columns([1, 1, 1, 1, 1.2])
    for idx, chan in enumerate(channels[:4]):
        c_id = chan.id or (idx + 1)
        is_active = (c_id == curr_id)
        btn_type = "primary" if is_active else "secondary"
        clean_name = chan.channel_name[:16]
        label = f"{'★ ' if is_active else ''}Ch {c_id}: {clean_name}"

        with c_pills[idx]:
            if st.button(label, key=f"hdr_chan_pill_{c_id}", type=btn_type, use_container_width=True):
                if c_id != curr_id:
                    switch_active_channel(curr_id, c_id, channels)
                st.rerun()

    with c_pills[4]:
        # Quick Ideas Action Button (Defaults to open on startup or channel selection)
        if "show_channel_ideas_panel" not in st.session_state:
            st.session_state["show_channel_ideas_panel"] = True
        is_open = bool(st.session_state.get("show_channel_ideas_panel", True))
        btn_type = "primary" if is_open else "secondary"
        show_ideas_btn = st.button("💡 Video Ideas", type=btn_type, use_container_width=True, key="hdr_find_ideas_btn")
        if show_ideas_btn:
            st.session_state["show_channel_ideas_panel"] = not is_open
            st.rerun()

    # Active Channel Summary Banner
    format_label = "Shorts & Long-form" if current_chan.content_format == "both" else current_chan.content_format.replace("_", " ").title()
    subs_str = f" &middot; Subtopics: {', '.join(current_chan.sub_niches[:3])}" if current_chan.sub_niches else ""
    
    col_info, col_manage = st.columns([4, 1])
    with col_info:
        st.markdown(
            f"""
            <div style="font-size: 0.82rem; color: #475569; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 12px; margin-bottom: 12px;">
                📺 <b>Active Profile:</b> <span style="color: #0F172A; font-weight: 700;">{current_chan.channel_name}</span> &nbsp;|&nbsp; 
                <b>Niche:</b> <span style="color: #2563EB; font-weight: 600;">{current_chan.channel_niche}</span> &nbsp;|&nbsp; 
                <b>Lang:</b> <code>{current_chan.target_language.upper()}</code> &nbsp;|&nbsp; 
                <b>Audience:</b> {current_chan.target_audience} &nbsp;|&nbsp; 
                <b>Format:</b> {format_label}
                {subs_str}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_manage:
        # Toggle Manage Profiles
        is_managing = st.toggle("⚙️ Edit Profile", value=bool(st.session_state.get("show_channel_editor", False)), key="hdr_toggle_manage_profile")
        if is_managing != bool(st.session_state.get("show_channel_editor", False)):
            st.session_state["show_channel_editor"] = is_managing
            st.rerun()

    # Inline Channel Profile Editor (When toggled)
    if st.session_state.get("show_channel_editor", False):
        render_channel_editor(current_chan)

    # Inline Channel Ideas Panel (When triggered)
    if st.session_state.get("show_channel_ideas_panel", False):
        render_channel_ideas_panel(current_chan)

    return current_chan


def render_channel_editor(profile: ChannelProfile) -> None:
    """Render a clean, minimal channel profile editor with SQLite persistence."""
    with st.expander(f"📝 Edit Channel Profile: {profile.channel_name} (Channel {profile.id})", expanded=True):
        st.caption("Customize your channel niche, language, and audience to automatically guide research across all five tools.")
        
        c_ed1, c_ed2 = st.columns(2)
        with c_ed1:
            chan_name = st.text_input("Channel Name", value=profile.channel_name, key=f"edit_ch_name_{profile.id}")
            chan_url = st.text_input("Channel URL or ID (Optional)", value=profile.channel_url, placeholder="e.g. https://youtube.com/@TechGearPulse", key=f"edit_ch_url_{profile.id}")
            chan_niche = st.text_input("Main Niche / Core Topic", value=profile.channel_niche, placeholder="e.g. Mechanical Keyboards, Python Automation", key=f"edit_ch_niche_{profile.id}")
            sub_niches_val = ", ".join(profile.sub_niches) if profile.sub_niches else ""
            chan_subniches = st.text_input("Related Subtopics (comma-separated)", value=sub_niches_val, placeholder="e.g. Keycaps, Switch Sound Tests, Desk Setup", key=f"edit_ch_subs_{profile.id}")

        with c_ed2:
            chan_aud = st.text_input("Target Audience", value=profile.target_audience, placeholder="e.g. Beginners, Software Engineers, Typists", key=f"edit_ch_aud_{profile.id}")
            
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                chan_lang = st.text_input("Content Language Code", value=profile.target_language, max_chars=5, help="e.g. en, bn, es, hi, de", key=f"edit_ch_lang_{profile.id}")
            with c_l2:
                chan_country = st.text_input("Target Country Code", value=profile.target_country, max_chars=5, help="e.g. US, BD, GB, IN, CA", key=f"edit_ch_country_{profile.id}")

            fmt_opts = ["both", "long_form", "shorts"]
            fmt_idx = fmt_opts.index(profile.content_format) if profile.content_format in fmt_opts else 0
            chan_fmt = st.selectbox("Preferred Video Format", fmt_opts, index=fmt_idx, format_func=lambda f: "Shorts & Long-form" if f == "both" else f.replace("_", " ").title(), key=f"edit_ch_fmt_{profile.id}")

            excl_val = ", ".join(profile.excluded_topics) if profile.excluded_topics else ""
            chan_excl = st.text_input("Exclusions / Topics to Avoid (comma-separated)", value=excl_val, placeholder="e.g. gaming, membrane keyboards, unboxing", key=f"edit_ch_excl_{profile.id}")

        c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 3])
        with c_btn1:
            if st.button("💾 Save Profile", type="primary", use_container_width=True, key=f"btn_save_chan_{profile.id}"):
                profile.channel_name = chan_name.strip() or f"Channel {profile.id}"
                profile.channel_url = chan_url.strip()
                profile.channel_niche = chan_niche.strip() or "General"
                profile.sub_niches = [s.strip() for s in chan_subniches.split(",") if s.strip()]
                profile.target_audience = chan_aud.strip() or "General Audience"
                profile.target_language = chan_lang.strip().lower() or "en"
                profile.target_country = chan_country.strip().upper() or "US"
                profile.content_format = chan_fmt
                profile.excluded_topics = [e.strip() for e in chan_excl.split(",") if e.strip()]

                try:
                    channel_manager.save_channel(profile)
                    st.success("✅ Channel profile saved successfully!")
                    st.session_state["show_channel_editor"] = False
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Failed to save profile: {str(ex)}")

        with c_btn2:
            if st.button("🔄 Reset to Default Profile", use_container_width=True, key=f"btn_reset_chan_{profile.id}"):
                defaults = get_default_four_channels()
                def_profile = defaults[(profile.id or 1) - 1]
                channel_manager.save_channel(def_profile)
                st.info("ℹ️ Profile reset to default template.")
                st.rerun()


def normalize_format_label(raw_format: str) -> str:
    """Map format string to one of the 6 canonical formats: Tutorial, Comparison, List, Deep Dive, Case Study, Quick Tip."""
    rf = (raw_format or "").lower()
    if any(k in rf for k in ["list", "best-of", "listicle", "top", "essential", "tour", "recommendations"]):
        return "List"
    elif any(k in rf for k in ["vs", "comparison", "shootout", "versus", "compare"]):
        return "Comparison"
    elif any(k in rf for k in ["case study", "experiment", "breakdown"]):
        return "Case Study"
    elif any(k in rf for k in ["quick tip", "tip", "hack", "short", "minute"]):
        return "Quick Tip"
    elif any(k in rf for k in ["deep dive", "deep-dive", "architecture", "benchmark", "analysis", "in-depth"]):
        return "Deep Dive"
    elif any(k in rf for k in ["how-to", "tutorial", "guide", "walkthrough", "step-by-step", "build"]):
        return "Tutorial"
    return "Tutorial"


def render_channel_ideas_panel(profile: ChannelProfile) -> None:
    """Render research-backed video ideas tailored specifically to the active channel."""
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; 
                    border-radius: 8px; padding: 14px 18px; margin: 12px 0 16px 0;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0 0 4px 0; font-size: 1.25rem; font-weight: 700; color: #0F172A;">
                        💡 Video Ideas for Your Channel
                    </h3>
                    <p style="margin: 0; font-size: 0.88rem; color: #64748B;">
                        Tailored to <b>{profile.channel_name}</b> &middot; Niche: <b>{profile.channel_niche}</b> &middot; Target Audience: <i>{profile.target_audience}</i> &middot; Rolling 60-day gap evidence
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Action Bar: Primary "Research New Ideas" button + Settings toggle
    col_act_left, col_act_right = st.columns([3.5, 1.5])
    with col_act_left:
        if st.button("🔄 Research New Ideas", type="primary", use_container_width=False, key=f"btn_res_new_ideas_{profile.id}"):
            st.session_state[f"channel_ideas_{profile.id}"] = None
            st.session_state[f"ideas_seed_{profile.id}"] = st.session_state.get(f"ideas_seed_{profile.id}", 0) + 1
            st.rerun()
    with col_act_right:
        if st.button("✕ Close Ideas Panel", use_container_width=True, key=f"btn_close_ideas_{profile.id}"):
            st.session_state["show_channel_ideas_panel"] = False
            st.rerun()

    # Expander: Optional Automated Morning Research Settings
    with st.expander("⚙️ Automated Morning Research Settings & Local Scheduling", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.86rem; color: #334155; margin-bottom: 8px;">
                Configure automated daily morning research runs across all 4 saved channels. Generated ideas are saved locally to SQLite so fresh ideas are ready without waiting.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("ℹ️ **Notice:** Scheduled automated runs require your computer and the Keyword Studio server to remain running at the scheduled time.")

        # Settings Form
        s_en = db_manager.get_setting("morning_research_enabled", "false") == "true"
        s_time = db_manager.get_setting("morning_research_time", "07:00")
        s_tz = db_manager.get_setting("morning_research_timezone", "UTC")

        c_s1, c_s2, c_s3 = st.columns([1.5, 1.5, 2])
        with c_s1:
            cfg_enabled = st.toggle("Enable Daily Research", value=s_en, key="toggle_morning_enabled")
        with c_s2:
            cfg_time = st.text_input("Scheduled Time (HH:MM)", value=s_time, max_chars=5, key="input_morning_time")
        with c_s3:
            cfg_tz = st.selectbox("Local Timezone", ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Dhaka", "Asia/Kolkata", "Asia/Tokyo"], index=0, key="sel_morning_tz")

        if st.button("💾 Save Schedule Settings", key="btn_save_morning_cfg"):
            db_manager.save_setting("morning_research_enabled", "true" if cfg_enabled else "false")
            db_manager.save_setting("morning_research_time", cfg_time.strip() or "07:00")
            db_manager.save_setting("morning_research_timezone", cfg_tz)
            st.success("✅ Morning research schedule settings saved!")

        st.divider()

        # Trigger Run Now & Display Last Successful Run
        latest_reports = db_manager.get_daily_morning_reports(limit=1)
        last_rep = latest_reports[0] if latest_reports else None

        c_run1, c_run2 = st.columns([3, 2])
        with c_run1:
            if last_rep:
                st.caption(
                    f"🕒 **Last Successful Run:** {last_rep.get('run_date')} &middot; "
                    f"Status: **{last_rep.get('status')}** &middot; "
                    f"{last_rep.get('total_ideas_generated', 0)} ideas generated across {last_rep.get('total_channels_processed', 0)} channels"
                )
            else:
                st.caption("🕒 **Last Successful Run:** No reports recorded yet.")

        with c_run2:
            force_run = st.checkbox("Force Re-run (Bypass duplicate check)", value=False, key="chk_force_morning_run")
            if st.button("🚀 Run Morning Research Now", type="secondary", use_container_width=True, key="btn_trigger_morning_now"):
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                is_duplicate = (last_rep and last_rep.get("run_date") == today_str and last_rep.get("status") == "Completed")

                if is_duplicate and not force_run:
                    st.warning(f"ℹ️ Morning research has already run today ({today_str}). To refresh anyway, check 'Force Re-run'.")
                else:
                    with st.spinner("Executing morning research across all 4 channels (respecting quotas & channel isolation)..."):
                        try:
                            rep = daily_opportunity_engine.run_daily_morning_report(
                                timezone_name=cfg_tz,
                                scheduled_time=cfg_time,
                                ideas_per_channel=4,
                            )
                            db_manager.save_setting("morning_research_last_run", datetime.now(timezone.utc).isoformat())
                            st.session_state[f"channel_ideas_{profile.id}"] = None
                            st.success(f"✅ Morning research completed! Generated {rep.total_ideas_generated} ideas across {rep.total_channels_processed} channels.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Morning research failed: {str(ex)}")

    # Transparent Ranking Disclaimer
    st.markdown(
        """
        <div style="font-size: 0.78rem; color: #64748B; margin-top: 4px; margin-bottom: 14px;">
            ℹ️ <i>Ranking is an analytical estimate based on current public YouTube search patterns and content gaps. It does not predict algorithm behavior or guarantee views.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fetch / Generate Tailored Ideas (Excluding saved backlog to prevent duplicates)
    saved_list = st.session_state.get(f"saved_ideas_channel_{profile.id}", [])
    saved_topics = {s.get("topic", "").lower().strip() for s in saved_list if isinstance(s, dict) and s.get("topic")}
    saved_kws = {s.get("keyword", "").lower().strip() for s in saved_list if isinstance(s, dict) and s.get("keyword")}
    excluded_existing = saved_topics.union(saved_kws).union({t.lower().strip() for t in profile.existing_video_topics})

    ideas_key = f"channel_ideas_{profile.id}"
    ideas = st.session_state.get(ideas_key)
    if not ideas:
        with st.spinner(f"Analyzing YouTube search patterns and 60-day competitor gaps for '{profile.channel_name}'..."):
            ideas = daily_opportunity_engine._generate_ideas_for_channel(
                channel=profile,
                count=5,
                existing_topics=set(excluded_existing),
            )
            # Rank ideas by transparent, explainable opportunity score descending
            ideas = sorted(ideas, key=lambda x: getattr(x, "opportunity_estimate", 0), reverse=True)
            st.session_state[ideas_key] = ideas

    if not ideas:
        st.warning("No fresh ideas generated for this niche. Try updating your niche and subtopics in the profile editor.")
        return

    # Render each idea as a clean, actionable card
    for idx, idea in enumerate(ideas):
        norm_fmt = normalize_format_label(idea.suggested_video_format)
        score_val = getattr(idea, "opportunity_estimate", 0.0)
        is_sparse = (
            getattr(idea, "review_label", "") == IdeaReviewStatus.NEEDS_MORE_RESEARCH.value
            or getattr(idea, "confidence_level", "") == "Sparse"
            or score_val < 55.0
            or (idea.recent_relevant_videos_found == 0 and len(idea.supporting_keywords) < 2)
        )

        with st.container():
            # Rank #1 Rationale Callout
            if idx == 0:
                gap_note = "zero competing videos (high content gap)" if idea.recent_relevant_videos_found == 0 else f"{idea.recent_relevant_videos_found} recent matching videos"
                st.markdown(
                    f"""
                    <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #2563EB; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.88rem; color: #1E3A8A;">
                        🏆 <b>Ranked #1 Rationale:</b> Grounded in active channel niche (<b>{profile.channel_niche}</b>) with {gap_note} and clear <b>{idea.search_intent}</b> viewer intent in rolling 60-day window.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Idea Card Box
            suggested_title = idea.seo_focused_title_options[0] if idea.seo_focused_title_options else idea.proposed_topic
            status_badge = (
                """<span style="background: #FEF3C7; color: #92400E; font-weight: 700; font-size: 0.76rem; padding: 3px 10px; border-radius: 12px;">⚠️ Needs More Research</span>"""
                if is_sparse else
                f"""<span style="background: #DCFCE7; color: #166534; font-weight: 700; font-size: 0.76rem; padding: 3px 10px; border-radius: 12px;">Score: {score_val:.0f}/100 &middot; High Opportunity</span>"""
            )
            recent_vids_text = "No recent matching videos found (High Content Gap!)" if idea.recent_relevant_videos_found == 0 else f"{idea.recent_relevant_videos_found} recent matching videos found in rolling 60-day window"

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <span style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 0.78rem; padding: 3px 10px; border-radius: 12px; text-transform: uppercase;">
                            Rank #{idx+1} &middot; {norm_fmt}
                        </span>
                        <div>
                            {status_badge}
                        </div>
                    </div>
                    <h4 style="margin: 0 0 6px 0; font-size: 1.15rem; color: #0F172A; font-weight: 700;">
                        {idea.proposed_topic}
                    </h4>
                    <div style="font-size: 0.90rem; color: #1E293B; margin-bottom: 8px;">
                        🎯 <b>Suggested Title:</b> <code>{suggested_title}</code>
                    </div>
                    <div style="font-size: 0.85rem; color: #334155; line-height: 1.5; margin-bottom: 10px;">
                        • <b>Why It Fits Your Channel:</b> Aligned with <b>{profile.channel_niche}</b> for target audience <i>{profile.target_audience}</i>. {idea.why_topic_worth_researching}<br>
                        • <b>Primary Keyword:</b> <code>{idea.main_keyword}</code> (Search Intent: {idea.search_intent})<br>
                        • <b>Recent Matching Videos:</b> {recent_vids_text}<br>
                        • <b>Search Volume Evidence:</b> Volume unavailable - based on autocomplete demand signals (Zero fabrication policy)<br>
                        • <b>Content Gap Evidence:</b> {idea.why_topic_worth_researching} ({idea.gap_state})<br>
                        • <b>Suggested Format:</b> {norm_fmt} (Tutorial, Comparison, List, Deep Dive, Case Study, Quick Tip)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 1-Click Copy snippet (Includes Streamlit built-in copy-to-clipboard button)
            copy_snippet = f"Topic: {idea.proposed_topic}\nTitle: {suggested_title}\nPrimary Keyword: {idea.main_keyword}"
            st.code(copy_snippet, language="text")

            # One-click Actions: "Start Creating" & "Save Idea"
            col_act1, col_act2 = st.columns([2.5, 1.5])
            with col_act1:
                if st.button(f"🚀 Start Creating Idea #{idx+1}", type="primary", use_container_width=True, key=f"start_creating_btn_{profile.id}_{idx}"):
                    # 1-Click Research Handoff: Immediate transfer to Tool 5 (SEO Generator)
                    st.session_state["seo_main_keyword"] = idea.main_keyword
                    st.session_state["gen_main_kw_input"] = idea.main_keyword

                    st.session_state["seo_topic_summary"] = idea.proposed_topic
                    st.session_state["gen_topic_summary_input"] = idea.proposed_topic

                    sec_str = ", ".join(idea.supporting_keywords[:4])
                    st.session_state["seo_secondary_keywords"] = sec_str
                    st.session_state["gen_sec_kws_input"] = sec_str

                    target_aud = idea.target_viewer or profile.target_audience
                    st.session_state["seo_target_viewer"] = target_aud
                    st.session_state["gen_target_viewer_input"] = target_aud

                    is_short = "short" in idea.suggested_video_format.lower()
                    st.session_state["gen_format_radio"] = "Shorts (9:16)" if is_short else "Long-form (16:9)"

                    st.session_state["current_page"] = TOOL_SEO_GENERATOR
                    st.session_state["show_channel_ideas_panel"] = False
                    st.rerun()

            with col_act2:
                saved_key = f"saved_ideas_channel_{profile.id}"
                if saved_key not in st.session_state:
                    st.session_state[saved_key] = []
                is_saved = any(s.get("topic") == idea.proposed_topic for s in st.session_state[saved_key])
                if not is_saved:
                    if st.button(f"💾 Save Idea #{idx+1}", use_container_width=True, key=f"save_idea_btn_{profile.id}_{idx}"):
                        st.session_state[saved_key].append({
                            "topic": idea.proposed_topic,
                            "keyword": idea.main_keyword,
                            "format": norm_fmt,
                            "title": suggested_title,
                            "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                        })
                        st.success("✅ Saved to channel backlog!")
                        st.rerun()
                else:
                    st.markdown("<div style='font-size: 0.85rem; color: #15803D; padding-top: 6px;'>⭐ Saved in Backlog</div>", unsafe_allow_html=True)

    # Show Channel's Saved Ideas Backlog if any
    saved_list = st.session_state.get(f"saved_ideas_channel_{profile.id}", [])
    if saved_list:
        with st.expander(f"📁 Saved Video Ideas for {profile.channel_name} ({len(saved_list)})", expanded=False):
            for s_idx, s_item in enumerate(saved_list):
                c_s1, c_s2 = st.columns([4, 1.5])
                with c_s1:
                    st.markdown(f"**#{s_idx+1}: {s_item.get('topic', 'Video Idea')}**")
                    t_str = s_item.get('title') or s_item.get('topic') or 'Draft Title'
                    d_str = s_item.get('saved_at', 'Saved in backlog')
                    st.caption(f"Keyword: `{s_item.get('keyword', '')}` &middot; Title: `{t_str}` &middot; Saved: {d_str}")
                with c_s2:
                    if st.button(f"🚀 Create", key=f"create_saved_{profile.id}_{s_idx}", use_container_width=True):
                        st.session_state["seo_main_keyword"] = s_item["keyword"]
                        st.session_state["gen_main_kw_input"] = s_item["keyword"]
                        st.session_state["seo_topic_summary"] = s_item["topic"]
                        st.session_state["gen_topic_summary_input"] = s_item["topic"]
                        st.session_state["seo_secondary_keywords"] = s_item["keyword"]
                        st.session_state["gen_sec_kws_input"] = s_item["keyword"]
                        st.session_state["seo_target_viewer"] = profile.target_audience
                        st.session_state["gen_target_viewer_input"] = profile.target_audience
                        st.session_state["current_page"] = TOOL_SEO_GENERATOR
                        st.session_state["show_channel_ideas_panel"] = False
                        st.rerun()
