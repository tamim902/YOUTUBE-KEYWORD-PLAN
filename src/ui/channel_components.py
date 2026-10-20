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
                st.session_state["active_channel_id"] = c_id
                # Automatically sync seed keyword across session
                st.session_state["kr_last_query"] = chan.channel_niche.split("&")[0].strip()
                st.session_state["vr_target_keyword"] = chan.channel_niche.split("&")[0].strip()
                st.session_state["opp_last_seed"] = chan.channel_niche.split("&")[0].strip()
                st.rerun()

    with c_pills[4]:
        # Quick Ideas Action Button
        show_ideas_btn = st.button("💡 Find Channel Ideas", type="primary", use_container_width=True, key="hdr_find_ideas_btn")
        if show_ideas_btn:
            st.session_state["show_channel_ideas_panel"] = not st.session_state.get("show_channel_ideas_panel", False)
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


def render_channel_ideas_panel(profile: ChannelProfile) -> None:
    """Render research-backed video ideas tailored specifically to the active channel."""
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; 
                    border-radius: 8px; padding: 14px 18px; margin: 12px 0 20px 0;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="margin: 0 0 4px 0; font-size: 1.25rem; font-weight: 700; color: #0F172A;">
                        💡 Research-Backed Video Ideas for {profile.channel_name}
                    </h3>
                    <p style="margin: 0; font-size: 0.88rem; color: #64748B;">
                        Tailored to <b>{profile.channel_niche}</b> ({profile.target_audience}) &middot; Rolling 60-day gap evidence
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner(f"Analyzing video opportunities and 60-day competitor gaps for '{profile.channel_name}'..."):
        ideas = daily_opportunity_engine._generate_ideas_for_channel(channel=profile, count=4)

    if not ideas:
        st.warning("No fresh ideas generated for this niche. Try updating your niche and subtopics in the profile editor.")
        return

    # Render each idea as a clean, actionable card
    for idx, idea in enumerate(ideas):
        with st.container():
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <span style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 0.76rem; padding: 3px 10px; border-radius: 12px; text-transform: uppercase;">
                            Idea #{idx+1} &middot; {idea.suggested_video_format}
                        </span>
                        <span style="font-size: 0.78rem; color: #64748B;">
                            60-Day Gap: <b>{idea.recent_relevant_videos_found} matching recent videos</b>
                        </span>
                    </div>
                    <h4 style="margin: 0 0 6px 0; font-size: 1.15rem; color: #0F172A; font-weight: 700;">
                        {idea.proposed_topic}
                    </h4>
                    <div style="font-size: 0.88rem; color: #334155; margin-bottom: 8px;">
                        🎯 <b>Suggested Title:</b> <code>{idea.seo_focused_title_options[0] if idea.seo_focused_title_options else idea.proposed_topic}</code>
                    </div>
                    <div style="font-size: 0.85rem; color: #475569; line-height: 1.5; margin-bottom: 10px;">
                        • <b>Why it fits:</b> {idea.why_topic_worth_researching}<br>
                        • <b>Keyword Evidence:</b> Primary: <code>{idea.main_keyword}</code> (Search Intent: {idea.search_intent})<br>
                        • <b>Unique Angle:</b> {idea.suggested_thumbnail_concept}
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8;">
                        {idea.source_and_coverage_summary}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # One-click "Start Creating" action button
            col_act1, col_act2 = st.columns([2, 4])
            with col_act1:
                if st.button(f"🚀 Start Creating Idea #{idx+1}", type="primary", use_container_width=True, key=f"start_creating_btn_{profile.id}_{idx}"):
                    # Transfer idea directly to Tool 5 (SEO Generator)
                    st.session_state["seo_main_keyword"] = idea.main_keyword
                    st.session_state["seo_topic_summary"] = idea.proposed_topic
                    st.session_state["seo_secondary_keywords"] = ", ".join(idea.supporting_keywords[:4])
                    st.session_state["seo_target_viewer"] = idea.target_viewer
                    st.session_state["current_page"] = TOOL_SEO_GENERATOR
                    st.session_state["show_channel_ideas_panel"] = False
                    st.rerun()

    if st.button("✕ Close Ideas Panel", key="close_ideas_panel_btn"):
        st.session_state["show_channel_ideas_panel"] = False
        st.rerun()
