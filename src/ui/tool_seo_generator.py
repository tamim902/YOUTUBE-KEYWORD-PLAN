"""Tool 4: SEO Title, Description & Tags Generator — Simplified Core Workflow.

Prepares production-ready, YouTube-compliant video metadata:
- Multiple title options with character counts (sweet spot 50-65 chars)
- One primary recommended title with clear explanation
- Structured, human-readable video description draft
- Relevant tag suggestions & hashtags (no fake search volume claims)
- Content alignment & SEO readiness checklist
- Independent copy buttons + 1-click "Copy Entire Package"
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.content_factory import content_factory_engine, VideoFormat, VideoPurpose


def render_seo_generator_tool() -> None:
    """Render the simplified Tool 4: SEO Title, Description & Tags Generator."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                ✨ SEO Title, Description & Tags Generator
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Generate click-worthy title candidates, structured YouTube descriptions, and relevant tags formatted for YouTube Studio.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Epistemic Modesty Notice
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #EC4899; 
                    border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.85rem; color: #475569;">
            📌 <b>SEO Reality Notice:</b> High-quality titles, descriptions, and tags help YouTube's algorithm index and categorize your video. 
            However, metadata alone does <b>not</b> guarantee views or rankings; viewer retention, click-through rate (CTR), and overall audience satisfaction 
            remain YouTube's dominant ranking signals.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Session State
    if "seo_main_keyword" not in st.session_state:
        st.session_state.seo_main_keyword = ""
    if "seo_secondary_keywords" not in st.session_state:
        st.session_state.seo_secondary_keywords = ""
    if "seo_topic_summary" not in st.session_state:
        st.session_state.seo_topic_summary = ""
    if "seo_target_viewer" not in st.session_state:
        st.session_state.seo_target_viewer = "General Audience & Enthusiasts"
    if "seo_generated_pkg" not in st.session_state:
        st.session_state.seo_generated_pkg = None

    # Input Form
    with st.container():
        c_in1, c_in2 = st.columns([2.5, 2.5])
        with c_in1:
            main_kw = st.text_input(
                "Primary Keyword (Required)",
                value=st.session_state.seo_main_keyword,
                placeholder="e.g. best mechanical keyboards 2026, python tutorial",
                key="gen_main_kw_input",
                help="The main search query you want your video to be discovered for.",
            )
        with c_in2:
            sec_kws = st.text_input(
                "Secondary Keywords (Optional, comma-separated)",
                value=st.session_state.seo_secondary_keywords,
                placeholder="e.g. quiet switches, custom keyboard build, typing test",
                key="gen_sec_kws_input",
                help="Supporting keyword phrases to naturally weave into description and tags.",
            )

        c_in3, c_in4 = st.columns([3, 2])
        with c_in3:
            topic_summary = st.text_input(
                "Video Topic / Angle (Optional)",
                value=st.session_state.seo_topic_summary,
                placeholder="e.g. In-depth sound test and buyer guide comparing top 5 keyboards under $100",
                key="gen_topic_summary_input",
                help="Brief 1-sentence summary of what your video covers.",
            )
        with c_in4:
            target_viewer = st.text_input(
                "Target Audience (Optional)",
                value=st.session_state.seo_target_viewer,
                placeholder="e.g. Beginners, Software Engineers, Typists",
                key="gen_target_viewer_input",
            )

        # Options Row
        c_opt1, c_opt2, c_opt3 = st.columns([1.5, 1.5, 2])
        with c_opt1:
            format_choice = st.radio(
                "Video Format",
                ["Long-form (16:9)", "Shorts (9:16)"],
                horizontal=True,
                key="gen_format_radio",
            )
        with c_opt2:
            tone_choice = st.selectbox(
                "Tone & Style",
                ["Informative & Engaging", "Beginner Step-by-Step", "Honest Buyer's Guide", "Direct & Contrarian"],
                key="gen_tone_select",
            )
        with c_opt3:
            st.write("")
            btn_generate = st.button("✨ Generate SEO Content Package", type="primary", use_container_width=True, key="gen_submit_btn")

    # Generate Handler
    if btn_generate and main_kw.strip():
        clean_main = main_kw.strip()
        st.session_state.seo_main_keyword = clean_main

        # Parse supporting keywords
        sup_list = [k.strip() for k in sec_kws.split(",") if k.strip()]

        with st.spinner(f"Crafting optimized SEO package for '{clean_main}'..."):
            format_type = VideoFormat.SHORTS if "Shorts" in format_choice else VideoFormat.LONG_FORM
            purpose_type = VideoPurpose.TUTORIAL if "Beginner" in tone_choice else VideoPurpose.REVIEW

            pkg = content_factory_engine.generate_package(
                channel_id=1,
                topic=topic_summary.strip() or f"{clean_main.title()} Complete Guide",
                primary_keyword=clean_main,
                supporting_keywords=sup_list,
                target_viewer=target_viewer.strip() or "General Audience",
                format_type=format_type,
                purpose_type=purpose_type,
            )
            st.session_state.seo_generated_pkg = pkg
            st.rerun()

    # Results Section
    pkg = st.session_state.seo_generated_pkg
    if pkg:
        st.markdown("---")
        st.markdown("### 📦 Generated SEO Package")

        # 1. Recommended Title & Alternative Candidates
        st.markdown("#### 1. Title Options")
        st.caption("Click-worthy title angles crafted for 50–65 characters (optimal mobile & desktop display):")

        # Primary recommended title
        best_title = pkg.selected_title or (pkg.title_options[0].title if pkg.title_options else main_kw.title())
        st.success(f"**Recommended Primary Title:**\n\n### `{best_title}`\n\n*Length: {len(best_title)} characters | High CTR hook with front-loaded primary keyword.*")

        with st.expander("👁️ View 4 Alternative Title Candidates", expanded=False):
            for idx, cand in enumerate(pkg.title_options):
                c_title_col, c_char_col = st.columns([4, 1])
                with c_title_col:
                    st.markdown(f"**Option {idx+1}:** `{cand.title}`")
                    st.caption(f"Angle: {cand.angle_type.title()} | {cand.benefit_promise}")
                with c_char_col:
                    st.caption(f"{len(cand.title)} chars")

        # 2. Video Description
        st.markdown("#### 2. YouTube Description Draft")
        st.caption("Structured 8-part description draft with opening hook, keyword placement, and timestamps:")
        desc_text = st.text_area(
            "Editable Video Description",
            value=pkg.description_text,
            height=260,
            key="gen_desc_editor",
        )

        # 3. Tags & Hashtags
        st.markdown("#### 3. Tags & Hashtags")
        st.caption("Relevant tag suggestions extracted from topic semantics (copy directly to YouTube Studio tags box):")

        # Comma separated tag string
        tags_str = ", ".join(pkg.tags[:15]) if pkg.tags else f"{main_kw}, {main_kw} tutorial, youtube seo"
        st.text_input(
            "Relevant Tag Suggestions (Comma-separated)",
            value=tags_str,
            key="gen_tags_display",
            help="Formatted with commas for 1-click paste into YouTube Studio's tag box.",
        )

        # Hashtags
        hashtags = [f"#{word.replace(' ', '')}" for word in [main_kw] + (pkg.supporting_keywords[:2] if pkg.supporting_keywords else [])]
        hashtags_str = " ".join(hashtags)
        st.caption(f"Suggested Hashtags: `{hashtags_str}`")

        # 4. SEO Content Readiness Checklist
        st.markdown("#### 4. SEO Readiness Checklist")
        if pkg.seo_readiness:
            for item in pkg.seo_readiness:
                st_icon = "✅" if item.status.value == "PASS" else "⚠️"
                st.markdown(f"- {st_icon} **{item.item_name}**: {item.explanation}")

        # 5. Master Copy & Export Row
        st.markdown("---")
        st.markdown("#### 📋 1-Click Clipboard & Export")
        c_cp1, c_cp2, c_cp3 = st.columns([2, 1.5, 1.5])

        # All-in-one formatted package block
        full_package_text = (
            f"=== YOUTUBE VIDEO SEO PACKAGE ===\n\n"
            f"PRIMARY TITLE:\n{best_title}\n\n"
            f"ALTERNATIVE TITLES:\n" + "\n".join(f"- {t.title}" for t in pkg.title_options) + "\n\n"
            f"VIDEO DESCRIPTION:\n{desc_text}\n\n"
            f"TAGS:\n{tags_str}\n\n"
            f"HASHTAGS:\n{hashtags_str}\n\n"
            f"TARGET KEYWORD: {pkg.primary_keyword}\n"
            f"GENERATED AT: {pkg.created_at}\n"
        )

        with c_cp1:
            st.download_button(
                label="📦 Download Complete Package (.txt)",
                data=full_package_text,
                file_name=f"seo_package_{main_kw.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="gen_dl_pkg_btn",
            )

        with c_cp2:
            st.download_button(
                label="📋 Download Description Only",
                data=desc_text,
                file_name=f"description_{main_kw.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="gen_dl_desc_btn",
            )

        with c_cp3:
            if st.button("🔄 Start New Package", use_container_width=True, key="gen_reset_btn"):
                st.session_state.seo_generated_pkg = None
                st.rerun()

    else:
        st.info("👆 Enter your primary keyword above and click 'Generate SEO Content Package' to create titles, descriptions, and tags.")
