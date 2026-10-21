"""Tool 5: SEO Generator — Upgraded Core Workflow.

Prepares production-ready, YouTube-compliant video metadata:
- Multiple title options with character counts (sweet spot 50-65 chars)
- Structural title patterns generated via SmartKeywordPatternGenerator frameworks
- One primary recommended title with clear strategic explanation
- Natural, readable 8-part video description draft
- Relevant tag suggestions honestly labeled without fake volume claims
- Optional hashtags & content alignment checklist
- Independent editing/copying and one-click "Download Complete Package"
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import streamlit as st

from src.intelligence.content_factory import content_factory_engine, VideoFormat, VideoPurpose
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import PatternCategory, PatternConfig, PatternLanguage
from src.ui.channel_components import get_active_channel


def generate_thumbnail_text_hook(topic: str, main_kw: str) -> str:
    """Generate a high-contrast 2-5 word thumbnail text hook."""
    clean_kw = (main_kw or topic).upper()
    if "MISTAKE" in clean_kw:
        return "AVOID THIS!"
    if "VS" in clean_kw or "BETTER" in clean_kw:
        return "THE REAL WINNER"
    if "BEST" in clean_kw:
        return "DON'T BUY YET!"
    if "TUTORIAL" in clean_kw or "HOW" in clean_kw or "GUIDE" in clean_kw:
        return "DO THIS FIRST!"
    if "REVIEW" in clean_kw:
        return "WORTH IT IN 2026?"
    words = [w for w in clean_kw.split() if len(w) > 2]
    if len(words) >= 2:
        return f"{words[0]} {words[1]} EXPOSED!"
    return "WATCH THIS FIRST!"


def render_seo_generator_tool() -> None:
    """Render the upgraded Tool 5: SEO Generator."""
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
            remain YouTube's dominant ranking signals. Tags are labeled <b>"Relevant tag suggestions"</b> rather than high volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Active Channel Context
    active_chan = get_active_channel()

    # Session State
    if "seo_main_keyword" not in st.session_state:
        st.session_state.seo_main_keyword = (active_chan.channel_niche.split("&")[0].strip() if active_chan else "")
    if "seo_secondary_keywords" not in st.session_state:
        st.session_state.seo_secondary_keywords = ""
    if "seo_topic_summary" not in st.session_state:
        st.session_state.seo_topic_summary = ""
    if "seo_target_viewer" not in st.session_state:
        st.session_state.seo_target_viewer = (active_chan.target_audience if active_chan else "General Audience & Enthusiasts")
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

            # Generate base package
            pkg = content_factory_engine.generate_package(
                channel_id=1,
                topic=topic_summary.strip() or f"{clean_main.title()} Complete Guide",
                primary_keyword=clean_main,
                supporting_keywords=sup_list,
                target_viewer=target_viewer.strip() or "General Audience",
                format_type=format_type,
                purpose_type=purpose_type,
            )

            # Generate pattern-based title variants using Pattern Generator
            pat_gen = SmartKeywordPatternGenerator()
            pat_cfg = PatternConfig(
                seeds=[clean_main],
                categories=[
                    PatternCategory.BEST_BUYING,
                    PatternCategory.HOW_TO,
                    PatternCategory.REVIEWS,
                    PatternCategory.COMPARISON,
                ],
                language_mode=PatternLanguage.EN,
                include_current_year=True,
                max_generated=8,
            )
            pattern_titles = pat_gen.generate(pat_cfg)
            st.session_state["seo_pattern_titles"] = [p.keyword for p in pattern_titles]

            st.session_state.seo_generated_pkg = pkg
            st.rerun()

    # Results Section
    pkg = st.session_state.seo_generated_pkg
    if pkg:
        st.markdown("---")
        st.markdown("### 📦 Generated SEO Package")

        # 1. Recommended Title & Alternative Candidates
        st.markdown("#### 1. Title Options & Pattern Variations")
        st.caption("Click-worthy title angles crafted for 50–65 characters (optimal mobile & desktop display):")

        # Primary recommended title
        best_title = pkg.selected_title or (pkg.title_options[0].title if pkg.title_options else main_kw.title())
        t_len = len(best_title)
        if 50 <= t_len <= 65:
            sweet_badge = f"🟢 **Optimal Length ({t_len} chars)** &middot; Sweet spot (50–65 chars) for mobile and desktop feeds."
        elif t_len < 50:
            sweet_badge = f"🟡 **Compact Length ({t_len} chars)** &middot; Concise, fits mobile well."
        else:
            sweet_badge = f"⚠️ **Long Length ({t_len} chars)** &middot; Risk of truncation on mobile search."

        st.markdown(
            f"""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                <div style="font-size: 0.78rem; font-weight: 700; color: #166534; text-transform: uppercase; margin-bottom: 4px;">Recommended Primary Title</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #14532D; margin-bottom: 6px;">{best_title}</div>
                <div style="font-size: 0.82rem; color: #15803D;">{sweet_badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(best_title, language=None)

        with st.expander("👁️ View Alternative & Pattern-Based Title Options", expanded=True):
            st.markdown("###### Structured Creative Angles:")
            for idx, cand in enumerate(pkg.title_options):
                c_title_col, c_char_col = st.columns([4, 1])
                with c_title_col:
                    raw_angle = (
                        getattr(cand, "angle_type", None)
                        or getattr(cand, "angle", None)
                        or (cand.get("angle_type") if isinstance(cand, dict) else None)
                        or (cand.get("angle") if isinstance(cand, dict) else None)
                        or "Creative Angle"
                    )
                    if hasattr(raw_angle, "value"):
                        raw_angle = raw_angle.value
                    angle_str = str(raw_angle).replace("_", " ").title()

                    cand_title = getattr(cand, "title", str(cand)) if not isinstance(cand, dict) else cand.get("title", str(cand))
                    raw_promise = (
                        getattr(cand, "benefit_promise", None)
                        or getattr(cand, "length_status", None)
                        or (cand.get("benefit_promise") if isinstance(cand, dict) else None)
                        or (cand.get("length_status") if isinstance(cand, dict) else None)
                        or ""
                    )
                    st.markdown(f"**Angle {idx+1} ({angle_str}):** `{cand_title}`")
                    if raw_promise:
                        st.caption(f"Strategy: {raw_promise}")
                with c_char_col:
                    st.caption(f"{len(cand_title)} chars")

            pat_titles = st.session_state.get("seo_pattern_titles", [])
            if pat_titles:
                st.markdown("<div style='margin: 10px 0; border-top: 1px dashed #E2E8F0;'></div>", unsafe_allow_html=True)
                st.markdown("###### Pattern-Framework Title Candidates:")
                for p_idx, p_title in enumerate(pat_titles[:4]):
                    c_pt_col, c_pc_col = st.columns([4, 1])
                    with c_pt_col:
                        st.markdown(f"- 🧩 `{p_title}`")
                    with c_pc_col:
                        st.caption(f"{len(p_title)} chars")

        # 2. Thumbnail Text Hook
        thumb_hook = generate_thumbnail_text_hook(pkg.topic, main_kw)
        st.markdown("#### 2. Thumbnail Text Hook (2–5 Words)")
        st.caption("Bold, high-contrast hook for your video thumbnail to maximize CTR:")
        st.markdown(
            f"""
            <div style="background: #0F172A; color: #F8FAFC; border-radius: 8px; padding: 12px 18px; 
                        display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 1.25rem; font-weight: 800; letter-spacing: 0.05em; color: #FACC15;">
                    "{thumb_hook}"
                </span>
                <span style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase; font-weight: 600;">
                    High-CTR Overlay Text
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(thumb_hook, language=None)

        # 3. Video Description
        st.markdown("#### 3. YouTube Description Draft")
        st.caption("Structured 8-part description draft with opening hook, keyword placement, outline, and links:")
        desc_text = st.text_area(
            "Editable Video Description",
            value=pkg.description_text,
            height=240,
            key="gen_desc_editor",
        )
        with st.expander("📋 Click to Copy Description Text", expanded=False):
            st.code(desc_text, language=None)

        # 4. Tags & Hashtags
        st.markdown("#### 4. Relevant Tag Suggestions & Hashtags")
        st.caption("Extracted from topic semantics (copy directly to YouTube Studio tags box; zero fabricated volume metrics):")

        # Comma separated tag string
        tags_str = ", ".join(pkg.tags[:15]) if pkg.tags else f"{main_kw}, {main_kw} tutorial, youtube seo"
        st.text_input(
            "Relevant Tag Suggestions (Comma-separated)",
            value=tags_str,
            key="gen_tags_display",
            help="Formatted with commas for 1-click paste into YouTube Studio's tag box.",
        )
        st.code(tags_str, language=None)

        # Hashtags
        hashtags = [f"#{word.replace(' ', '')}" for word in [main_kw] + (pkg.supporting_keywords[:2] if pkg.supporting_keywords else [])]
        hashtags_str = " ".join(hashtags)
        st.caption(f"Suggested Hashtags: `{hashtags_str}`")

        # 5. SEO Content Readiness Checklist
        st.markdown("#### 5. SEO Readiness Checklist")
        if pkg.seo_readiness:
            for item in pkg.seo_readiness:
                st_icon = "✅" if item.status.value == "PASS" else "⚠️"
                st.markdown(f"- {st_icon} **{item.item_name}**: {item.explanation}")

        # 6. Master Copy & Export Row
        st.markdown("---")
        st.markdown("#### 📋 1-Click Clipboard & Export")
        with st.expander("📋 View & Copy Entire Complete Package", expanded=False):
            st.code(
                f"=== YOUTUBE VIDEO SEO PACKAGE ===\n\n"
                f"PRIMARY TITLE:\n{best_title}\n\n"
                f"THUMBNAIL HOOK:\n{thumb_hook}\n\n"
                f"ALTERNATIVE TITLES:\n" + "\n".join(f"- {t.title}" for t in pkg.title_options) + "\n\n"
                f"VIDEO DESCRIPTION:\n{desc_text}\n\n"
                f"TAGS:\n{tags_str}\n\n"
                f"HASHTAGS:\n{hashtags_str}\n\n"
                f"TARGET KEYWORD: {pkg.primary_keyword}\n"
                f"GENERATED AT: {pkg.created_at}\n",
                language=None,
            )
        c_cp1, c_cp2, c_cp3 = st.columns([2, 1.5, 1.5])

        # All-in-one formatted package block
        full_package_text = (
            f"=== YOUTUBE VIDEO SEO PACKAGE ===\n\n"
            f"PRIMARY TITLE:\n{best_title}\n\n"
            f"THUMBNAIL HOOK:\n{thumb_hook}\n\n"
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
