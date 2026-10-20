"""YouTube SEO Content Factory & One-Click Video Package UI (Phase 32).

Renders the unified video content preparation workspace, format-adaptive package
generators, editable sections (Titles, Outline, Description, Thumbnail, Tags),
transparent SEO readiness checklist, and one-click actions.
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.intelligence.content_factory import (
    ContentFactoryEngine,
    ReadinessStatus,
    TitleCandidate,
    VideoContentPackage,
    VideoFormat,
    VideoPurpose,
    content_factory_engine,
)
from src.models.channel import ChannelProfile
from src.storage.database import db_manager


def render_content_factory_workspace(is_ready: bool) -> None:
    """Render the unified YouTube Video Content Factory workspace."""
    if not is_ready:
        st.warning("Database is initializing. Content Factory will be available momentarily.")
        return

    channels = channel_manager.get_all_channels()
    if not channels:
        st.info("No channel profiles found.")
        return

    # Active Channel
    active_cid = int(st.session_state.get("active_channel_id", 1))
    channel = channel_manager.get_channel(active_cid) or channels[0]

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%); border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                        <span style="font-size: 1.4rem;">📦</span>
                        <h3 style="margin: 0; font-size: 1.28rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                            One-Click Video Package Factory
                        </h3>
                        <span style="background: rgba(16, 185, 129, 0.08); color: #059669; font-size: 0.74rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 6px;">
                            UNIFIED SEO WORKSPACE
                        </span>
                    </div>
                    <div style="font-size: 0.88rem; color: #64748B; line-height: 1.45;">
                        Prepare complete, publish-ready YouTube packages: Title candidates, pacing outline, 8-part description, thumbnail concept, tags, and verified pre-publish checklist.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # 1. Topic & Workspace Configuration
    # --------------------------------------------------------------------------
    with st.container():
        # Topic Source Selector
        topic_mode = st.radio(
            "Topic Source",
            options=["💡 Choose from Saved Ideas / Research", "✏️ Start from a New Topic"],
            horizontal=True,
            key="cf_topic_source_radio",
            label_visibility="collapsed",
        )

        default_topic = ""
        default_kw = ""
        default_supp: List[str] = []

        if "Choose from Saved Ideas" in topic_mode:
            # Query recent daily ideas and searches for this channel
            daily_ideas = db_manager.get_daily_ideas_by_channel(channel.id or 1)
            recent_searches = db_manager.get_recent_searches(limit=10)

            idea_options = []
            for i in daily_ideas[:8]:
                idea_options.append((
                    f"💡 [Idea] {i.proposed_topic}",
                    i.proposed_topic,
                    i.main_keyword,
                    i.supporting_keywords,
                ))
            for s in recent_searches[:5]:
                seed = s.get("seed_keyword", "")
                if seed:
                    idea_options.append((
                        f"🔍 [Search] {seed}",
                        seed.title(),
                        seed,
                        [f"{seed} tutorial", f"best {seed}"],
                    ))

            if idea_options:
                selected_opt = st.selectbox(
                    "Select a Saved Topic Opportunity",
                    options=[opt[0] for opt in idea_options],
                    key="cf_saved_topic_select",
                )
                match = next((opt for opt in idea_options if opt[0] == selected_opt), None)
                if match:
                    default_topic = match[1]
                    default_kw = match[2]
                    default_supp = match[3]
            else:
                st.caption("No saved ideas yet for this channel. Enter a new topic below.")
                default_topic = f"Best {channel.channel_niche} in {datetime.now().year}"
                default_kw = channel.channel_niche.lower()
        else:
            default_topic = st.session_state.get("active_seed_input", f"How to Master {channel.channel_niche}")
            default_kw = st.session_state.get("active_seed_input", channel.channel_niche.lower())

        # Inputs Grid
        col_t1, col_t2 = st.columns([2.5, 2.5])
        with col_t1:
            in_topic = st.text_input("Candidate Video Topic", value=default_topic, key="cf_in_topic", placeholder="e.g. Best Mechanical Keyboards for Programming")
            in_kw = st.text_input("Primary SEO Keyword", value=default_kw, key="cf_in_kw", placeholder="e.g. best mechanical keyboard for coding")

        with col_t2:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                in_format = st.selectbox(
                    "Video Format",
                    options=[VideoFormat.LONG_FORM.value, VideoFormat.SHORTS.value],
                    format_func=lambda x: "🎬 Long-form Video (16:9)" if x == VideoFormat.LONG_FORM.value else "⚡ YouTube Shorts (Vertical 9:16)",
                    key="cf_in_format",
                )
            with col_f2:
                in_purpose = st.selectbox(
                    "Video Purpose",
                    options=[
                        VideoPurpose.TUTORIAL.value,
                        VideoPurpose.REVIEW.value,
                        VideoPurpose.COMPARISON.value,
                        VideoPurpose.EDUCATIONAL.value,
                        VideoPurpose.TROUBLESHOOTING.value,
                    ],
                    format_func=lambda x: {
                        VideoPurpose.TUTORIAL.value: "🛠️ Tutorial & Walkthrough",
                        VideoPurpose.REVIEW.value: "⭐ Product Review & Buyer Guide",
                        VideoPurpose.COMPARISON.value: "⚖️ Comparison & Shootout",
                        VideoPurpose.EDUCATIONAL.value: "🎓 Educational & Deep-Dive",
                        VideoPurpose.TROUBLESHOOTING.value: "🔧 Problem Troubleshooting",
                    }.get(x, x),
                    key="cf_in_purpose",
                )

            in_viewer = st.text_input("Target Audience", value=channel.target_audience, key="cf_in_viewer")

        # Collapsible Advanced Product & Research Info
        with st.expander("⚙️ Optional Research Context, Products & Source Links", expanded=False):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                p_name = st.text_input("Product Name / Model (Optional)", placeholder="e.g. Keychron Q1 HE", key="cf_p_name")
                p_url = st.text_input("Affiliate / Product URL", placeholder="https://amzn.to/...", key="cf_p_url")
                p_specs = st.text_input("Key Specs / Price", placeholder="e.g. $199, Hall Effect Switches, PBT Keycaps", key="cf_p_specs")
            with col_a2:
                user_notes = st.text_area("Your Notes / Personal Experience", height=68, placeholder="Key points from your real testing to include in outline...", key="cf_user_notes")
                source_links_raw = st.text_input("External Sources / Reference URLs (comma-separated)", placeholder="https://youtube.com/watch?v=..., https://docs...", key="cf_sources")

        # Primary Generation Button
        if st.button("⚡ Generate One-Click Video Package", type="primary", use_container_width=True, key="cf_btn_generate"):
            if not in_kw.strip():
                st.error("Please provide at least a primary SEO keyword to generate the package.")
                return

            with st.spinner(f"Assembling format-adapted video package for {channel.channel_name}..."):
                p_info = None
                if p_name.strip():
                    p_info = {"name": p_name.strip(), "url": p_url.strip(), "specs": p_specs.strip()}

                s_links = [s.strip() for s in source_links_raw.split(",") if s.strip()] if source_links_raw else None

                pkg = content_factory_engine.generate_package(
                    channel_id=channel.id or 1,
                    topic=in_topic.strip() or in_kw.strip().title(),
                    primary_keyword=in_kw.strip(),
                    format_type=VideoFormat(in_format),
                    purpose_type=VideoPurpose(in_purpose),
                    supporting_keywords=default_supp if default_supp else None,
                    target_viewer=in_viewer.strip(),
                    product_info=p_info,
                    user_notes=user_notes.strip() if user_notes else None,
                    source_links=s_links,
                )
                st.session_state["cf_active_package"] = pkg.to_dict()
                st.success("✅ SEO Content Package generated successfully!")
                st.rerun()

    # --------------------------------------------------------------------------
    # 2. Display and Edit Active Content Package
    # --------------------------------------------------------------------------
    active_pkg_dict = st.session_state.get("cf_active_package")
    if not active_pkg_dict:
        # Check if any saved package exists in SQLite to preview
        saved_packages = content_factory_engine.list_packages(channel_id=channel.id, limit=1)
        if saved_packages:
            active_pkg_dict = saved_packages[0].to_dict()
            st.session_state["cf_active_package"] = active_pkg_dict

    if not active_pkg_dict:
        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 12px; padding: 2rem; text-align: center; margin: 1.5rem 0;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📦</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #1E293B; margin-bottom: 0.25rem;">
                    No Active Content Package
                </div>
                <div style="font-size: 0.86rem; color: #64748B;">
                    Select an idea or enter a topic above, then click <b>Generate One-Click Video Package</b> to build your video blueprint.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    pkg = VideoContentPackage.from_dict(active_pkg_dict)
    render_active_package_workspace(pkg, channel)


def render_active_package_workspace(pkg: VideoContentPackage, channel: ChannelProfile) -> None:
    """Render the tabs and editable controls for an active VideoContentPackage."""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Package Meta Header
    fmt_badge = "🎬 LONG-FORM" if pkg.format_type == VideoFormat.LONG_FORM else "⚡ SHORTS"
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.15rem 1.35rem; margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;">
                <span style="background: rgba(79, 70, 229, 0.08); color: #4F46E5; font-size: 0.74rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 6px;">
                    {fmt_badge} • {pkg.purpose_type.value.upper()}
                </span>
                <span style="font-size: 0.82rem; color: #64748B;">Target Workspace: <b>{pkg.channel_name}</b></span>
            </div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">
                {pkg.selected_title}
            </div>
            <div style="font-size: 0.84rem; color: #475569;">
                Primary Keyword: <code>{pkg.primary_keyword}</code> | Target Viewer: <i>{pkg.target_viewer}</i>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # Content Package Tabs
    # --------------------------------------------------------------------------
    tabs = st.tabs([
        "🏷️ Title Options",
        "📋 Video Outline",
        "📝 Description",
        "🖼️ Thumbnail Concept",
        "🏷️ Tags & Keywords",
        "✅ SEO Readiness & Fact-Check",
    ])

    # Tab 1: Title Options
    with tabs[0]:
        st.markdown("##### 🏷️ Candidate Title Angles & Character Safety")
        st.caption("Review calculated title variations. Keywords placed near the start maximize search visibility on mobile screens.")

        for idx, t in enumerate(pkg.title_options):
            is_chosen = (t.title == pkg.selected_title)
            c_card, c_btn = st.columns([5.5, 1.5])
            with c_card:
                badge_bg = "#F0FDF4" if is_chosen else "#F8FAFC"
                border_c = "#22C55E" if is_chosen else "#E2E8F0"
                len_color = "#15803D" if "Optimal" in t.length_status else ("#DC2626" if "Truncation" in t.length_status else "#4B5563")

                st.markdown(
                    f"""
                    <div style="background: {badge_bg}; border: 1px solid {border_c}; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                            <span style="font-size: 0.76rem; font-weight: 700; color: #475569;">Angle: {t.angle}</span>
                            <span style="font-size: 0.74rem; font-weight: 600; color: {len_color};">{t.char_count} chars • {t.length_status}</span>
                        </div>
                        <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A;">
                            {t.title}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if t.claim_warning:
                    st.warning(t.claim_warning)

            with c_btn:
                btn_type = "primary" if is_chosen else "secondary"
                btn_txt = "✓ Selected" if is_chosen else "Use Title"
                if st.button(btn_txt, key=f"cf_title_sel_{idx}", type=btn_type, use_container_width=True):
                    pkg.selected_title = t.title
                    st.session_state["cf_active_package"] = pkg.to_dict()
                    st.rerun()

        # Editable Title Override
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        new_title = st.text_input("Edit Selected Title Manually", value=pkg.selected_title, key="cf_edit_title_input")
        if new_title != pkg.selected_title:
            pkg.selected_title = new_title
            st.session_state["cf_active_package"] = pkg.to_dict()

    # Tab 2: Outline
    with tabs[1]:
        st.markdown("##### 📋 Pacing & Production Outline")
        st.caption(f"Structured outline for **{pkg.outline.get('format', 'Video')}**. Pacing: {pkg.outline.get('pacing', 'Standard')}")

        sections = pkg.outline.get("sections", [])
        for idx, s in enumerate(sections):
            with st.expander(f"{s.get('section_name')} — {s.get('purpose')}", expanded=True):
                st.markdown(f"**Timing:** `{s.get('timestamp_hint')}`")
                st.markdown("**Talking Points:**")
                for tp in s.get("talking_points", []):
                    st.markdown(f"- {tp}")
                st.markdown(f"**Viewer Question Answered:** *{', '.join(s.get('questions_answered', []))}*")
                if s.get("evidence_needed"):
                    st.info(f"**Evidence to Gather:** {s.get('evidence_needed')}")

    # Tab 3: Description
    with tabs[2]:
        st.markdown("##### 📝 8-Part YouTube SEO Description")
        desc_chars = len(pkg.description_text)
        char_status_color = "#15803D" if desc_chars <= 4800 else "#DC2626"
        st.caption(f"Total Characters: <b style='color:{char_status_color};'>{desc_chars} / 5,000 max</b>", unsafe_allow_html=True)

        edit_desc = st.text_area(
            "Full Editable Description Text",
            value=pkg.description_text,
            height=280,
            key="cf_desc_textarea",
        )
        if edit_desc != pkg.description_text:
            pkg.description_text = edit_desc
            st.session_state["cf_active_package"] = pkg.to_dict()

        if st.button("📋 Copy Description to Clipboard", key="cf_btn_copy_desc"):
            st.toast("Description copied to clipboard!")

    # Tab 4: Thumbnail Concept
    with tabs[3]:
        st.markdown("##### 🖼️ Mobile-First Thumbnail Concept")
        if pkg.thumbnail_concept:
            tc = pkg.thumbnail_concept
            st.markdown(
                f"""
                <div style="background: #0F172A; border-radius: 12px; padding: 1.5rem; color: #FFFFFF; margin-bottom: 1rem;">
                    <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
                        RECOMMENDED ON-THUMBNAIL TEXT (3-4 WORDS MAX)
                    </div>
                    <div style="font-size: 2rem; font-weight: 900; color: #FACC15; letter-spacing: -0.02em; margin-bottom: 1rem; font-family: -apple-system, sans-serif;">
                        {tc.hook_text}
                    </div>
                    <div style="border-top: 1px solid #334155; padding-top: 1rem; font-size: 0.88rem; line-height: 1.5; color: #CBD5E1;">
                        <div><b>• Visual Composition:</b> {tc.visual_composition}</div>
                        <div><b>• Main Focal Point:</b> {tc.main_subject_focal_point}</div>
                        <div><b>• Contrast & Readability:</b> {tc.color_contrast_notes}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No thumbnail concept available.")

    # Tab 5: Tags
    with tabs[4]:
        st.markdown("##### 🏷️ Genuine Tag Suggestions")
        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; font-size: 0.84rem; color: #475569;">
                ℹ️ <b>YouTube Algorithm Note:</b> YouTube explicitly states that tags play a minor role in video discovery compared to your title, description, and audience retention. Use only accurate, relevant phrases.
            </div>
            """,
            unsafe_allow_html=True,
        )
        tag_pills = " ".join([f"<code style='font-size:0.9rem; padding: 0.2rem 0.5rem; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; display:inline-block; margin: 0.2rem;'>{t}</code>" for t in pkg.tags])
        st.markdown(tag_pills, unsafe_allow_html=True)
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        st.code(", ".join(pkg.tags), language="text")

    # Tab 6: SEO Readiness & Fact-Check
    with tabs[5]:
        st.markdown("##### ✅ Pre-Publish SEO Readiness Evaluation")
        st.caption("Deterministic evaluation of length, keyword naturalness, and affiliate compliance. We never guarantee rankings or views.")

        for r in pkg.seo_readiness:
            badge_bg = "#F0FDF4" if r.status == ReadinessStatus.PASS else ("#FEF2F2" if r.status == ReadinessStatus.NEEDS_REVIEW else "#F8FAFC")
            badge_fg = "#15803D" if r.status == ReadinessStatus.PASS else ("#DC2626" if r.status == ReadinessStatus.NEEDS_REVIEW else "#475569")
            icon = "✅" if r.status == ReadinessStatus.PASS else ("⚠️" if r.status == ReadinessStatus.NEEDS_REVIEW else "ℹ️")

            st.markdown(
                f"""
                <div style="background: {badge_bg}; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                        <span style="font-weight: 700; color: #0F172A; font-size: 0.92rem;">{icon} {r.item_name}</span>
                        <span style="font-size: 0.74rem; font-weight: 800; color: {badge_fg}; background: #FFFFFF; border: 1px solid #CBD5E1; padding: 0.1rem 0.45rem; border-radius: 4px;">{r.status.value}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #475569; line-height: 1.45;">
                        {r.explanation}
                    </div>
                    <div style="font-size: 0.8rem; color: #64748B; margin-top: 0.2rem;">
                        👉 <i>{r.recommendation}</i>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("##### 🔍 Evidence & Fact-Check Audit")
        for e in pkg.evidence_checklist:
            st.markdown(f"- **[{e.status}]** *{e.source_provenance}:* {e.fact_statement} *(Note: {e.notes})*")

    # --------------------------------------------------------------------------
    # 3. One-Click Action Center
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### ⚡ One-Click Actions")

    col_act1, col_act2, col_act3, col_act4 = st.columns(4)

    with col_act1:
        if st.button("💾 Save Package to SQLite", type="primary", use_container_width=True, key="cf_save_btn"):
            pkg_id = content_factory_engine.save_package(pkg)
            st.session_state["cf_active_package"] = pkg.to_dict()
            st.success(f"Package saved to database (ID: {pkg_id})!")
            st.rerun()

    with col_act2:
        md_content = content_factory_engine.export_as_markdown(pkg)
        st.download_button(
            "📥 Download Package (.md)",
            data=md_content,
            file_name=f"video_package_{pkg.primary_keyword.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
            key="cf_download_md_btn",
        )

    with col_act3:
        json_content = json.dumps(pkg.to_dict(), indent=2)
        st.download_button(
            "📥 Download JSON Data",
            data=json_content,
            file_name=f"video_package_{pkg.primary_keyword.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
            key="cf_download_json_btn",
        )

    with col_act4:
        if st.button("📋 Copy Markdown Package", use_container_width=True, key="cf_copy_md_btn"):
            st.toast("Full package copied to clipboard!")

    # Calendar Integration Row
    with st.expander("📅 Schedule on Content Calendar", expanded=False):
        col_cal1, col_cal2 = st.columns([2, 1])
        with col_cal1:
            target_date = st.date_input("Target Recording / Publishing Date", value=datetime.now().date() + timedelta(days=7), key="cf_cal_date")
        with col_cal2:
            st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
            if st.button("Add to Content Calendar →", use_container_width=True, key="cf_cal_add_btn"):
                cal_id = content_factory_engine.create_calendar_entry(pkg, str(target_date))
                pkg.calendar_item_id = cal_id
                content_factory_engine.save_package(pkg)
                st.session_state["cf_active_package"] = pkg.to_dict()
                st.success(f"Added to Content Calendar for {target_date} (Item #{cal_id})!")

    # --------------------------------------------------------------------------
    # 4. Saved Content Packages History
    # --------------------------------------------------------------------------
    saved_pkgs = content_factory_engine.list_packages(channel_id=channel.id, limit=10)
    if saved_pkgs:
        with st.expander(f"📂 Saved Video Packages for {channel.channel_name} ({len(saved_pkgs)})", expanded=False):
            for sp in saved_pkgs:
                col_p_info, col_p_load, col_p_del = st.columns([4, 1.2, 0.8])
                with col_p_info:
                    st.markdown(f"**{sp.selected_title}** (`{sp.primary_keyword}` • {sp.format_type.value})")
                    st.caption(f"Created: {sp.created_at[:10]} | Target: {sp.target_viewer}")
                with col_p_load:
                    if st.button("Open Package", key=f"cf_load_pkg_{sp.id}", use_container_width=True):
                        st.session_state["cf_active_package"] = sp.to_dict()
                        st.rerun()
                with col_p_del:
                    if st.button("Delete", key=f"cf_del_pkg_{sp.id}", use_container_width=True):
                        content_factory_engine.delete_package(sp.id)
                        if pkg.id == sp.id:
                            st.session_state["cf_active_package"] = None
                        st.rerun()
