"""Guided Keyword Research Wizard UI for Phase 29.

Provides a beginner-friendly 7-step guided workflow:
- Step 1: Choose a Channel
- Step 2: Enter a Topic
- Step 3: Choose Research Settings
- Step 4: Find Keywords
- Step 5: Review Results
- Step 6: Choose Your Best-Fit Keyword
- Step 7: Continue (One-Click Actions)
"""

from __future__ import annotations

import io
import threading
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.classifier.service import default_classifier
from src.intelligence.scoring import default_scorer
from src.config import config
from src.intelligence.channel_manager import channel_manager
from src.models.wizard import (
    BEGINNER_TOOLTIPS,
    RelevanceTierLabel,
    WizardState,
    WizardStep,
    WizardSuggestionItem,
    get_relevance_badge_style,
    get_relevance_tier_label,
)
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import DatabaseManager, db_manager
from src.storage.export import sanitize_dataframe_for_export
from src.ui.research_memory_ui import render_duplicate_detection_banner
from src.ui.components import (
    PAGE_CONTENT_OPPORTUNITIES,
    PAGE_DESCRIPTION_STUDIO,
    PAGE_RESULTS,
    PAGE_VALIDATION,
    PAGE_VIDEO_RESEARCH,
    set_interface_mode,
)


def get_or_create_wizard_state() -> WizardState:
    """Retrieve or initialize the WizardState in st.session_state."""
    if "wizard_state" not in st.session_state or not isinstance(st.session_state["wizard_state"], WizardState):
        channels = channel_manager.get_all_channels()
        def_channel_id = channels[0].id if channels else 1
        def_channel_name = channels[0].channel_name if channels else "Tech & Gadget Reviews"
        st.session_state["wizard_state"] = WizardState(
            channel_id=def_channel_id,
            channel_name=def_channel_name,
            topic=st.session_state.get("active_seed_input", "") or st.session_state.get("last_query", ""),
        )
    return st.session_state["wizard_state"]


def render_wizard_stepper(state: WizardState) -> None:
    """Render the 7-step visual progress bar and step indicator."""
    steps = [
        (1, "1. Channel"),
        (2, "2. Topic"),
        (3, "3. Settings"),
        (4, "4. Find"),
        (5, "5. Review"),
        (6, "6. Best-Fit"),
        (7, "7. Actions"),
    ]

    st.markdown(
        """
        <style>
            .ks-wizard-stepper {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 6px;
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 10px 14px;
                margin-bottom: 1.25rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            }
            .ks-step-pill {
                flex: 1;
                text-align: center;
                padding: 6px 4px;
                border-radius: 8px;
                font-size: 0.78rem;
                font-weight: 600;
                color: #64748B;
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                transition: all 0.15s ease;
            }
            .ks-step-pill.active {
                background: #EFF6FF;
                color: #1D4ED8;
                border-color: #3B82F6;
                box-shadow: 0 0 0 1px #3B82F6;
            }
            .ks-step-pill.completed {
                background: #F0FDF4;
                color: #15803D;
                border-color: #86EFAC;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    pills_html = '<div class="ks-wizard-stepper">'
    for step_num, step_label in steps:
        if step_num == state.current_step:
            cls = "ks-step-pill active"
            indicator = f"▶ {step_label}"
        elif step_num < state.current_step:
            cls = "ks-step-pill completed"
            indicator = f"✓ {step_label}"
        else:
            cls = "ks-step-pill"
            indicator = step_label
        pills_html += f'<div class="{cls}">{indicator}</div>'
    pills_html += "</div>"

    st.markdown(pills_html, unsafe_allow_html=True)


def render_guided_keyword_wizard() -> None:
    """Render the full 7-step guided keyword research wizard."""
    state = get_or_create_wizard_state()

    # Top Control Bar: Mode indicator, quick jump, and reset
    col_t1, col_t2 = st.columns([3, 1.2])
    with col_t1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <span style="font-size: 0.8rem; font-weight: 700; background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 6px;">
                    🌱 SIMPLE MODE ACTIVE
                </span>
                <span style="font-size: 0.82rem; color: #64748B;">
                    7-Step Beginner-Friendly Keyword Workflow
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_t2:
        c_mode_btn, c_rst_btn = st.columns([1, 1])
        with c_mode_btn:
            if st.button("⚡ Switch to Advanced", key="wiz_top_switch_adv_btn", use_container_width=True, help="Switch to Advanced Mode for full crawl settings"):
                set_interface_mode("advanced")
                st.rerun()
        with c_rst_btn:
            if st.button("🔄 Reset Wizard", key="wiz_top_reset_btn", use_container_width=True, help="Clear inputs and start over"):
                state.reset()
                st.session_state.instant_suggestions = []
                st.rerun()

    # Visual Stepper
    render_wizard_stepper(state)

    # Error Notification if any
    if state.error_message:
        st.error(f"⚠️ {state.error_message}")

    # Action Confirmation Notice if any
    if state.last_action_notice:
        st.success(f"✓ {state.last_action_notice}")
        state.last_action_notice = None

    # Step Rendering
    if state.current_step == 1:
        render_step_1_channel(state)
    elif state.current_step == 2:
        render_step_2_topic(state)
    elif state.current_step == 3:
        render_step_3_settings(state)
    elif state.current_step == 4:
        render_step_4_find(state)
    elif state.current_step == 5:
        render_step_5_review(state)
    elif state.current_step == 6:
        render_step_6_choose_best_fit(state)
    elif state.current_step == 7:
        render_step_7_continue(state)


# -----------------------------------------------------------------------------
# STEP 1: CHOOSE A CHANNEL
# -----------------------------------------------------------------------------
def render_step_1_channel(state: WizardState) -> None:
    """Step 1: Select one of the 4 configured YouTube channels."""
    channels = channel_manager.get_all_channels()

    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 1: Choose Your Channel
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                Select which of your channels you want to create a video for. Keyword Studio will use this channel's niche and audience to evaluate keyword relevance.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_cols = st.columns(len(channels[:4]) if channels else 1)
    for idx, chan in enumerate(channels[:4]):
        c_id = chan.id or (idx + 1)
        is_selected = (state.channel_id == c_id)
        border_color = "#3B82F6" if is_selected else "#E2E8F0"
        bg_color = "#EFF6FF" if is_selected else "#FFFFFF"

        with c_cols[idx]:
            st.markdown(
                f"""
                <div style="background: {bg_color}; border: 2px solid {border_color}; border-radius: 10px; padding: 12px; margin-bottom: 10px; min-height: 140px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #3B82F6; text-transform: uppercase;">
                        Channel {c_id}
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin: 3px 0 6px 0;">
                        {chan.channel_name}
                    </div>
                    <div style="font-size: 0.78rem; color: #475569; margin-bottom: 4px;">
                        <b>Niche:</b> {chan.niche}
                    </div>
                    <div style="font-size: 0.74rem; color: #64748B;">
                        <b>Audience:</b> {chan.target_audience[:45]}...
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            btn_label = "✓ Selected Channel" if is_selected else f"Select Channel {c_id}"
            btn_type = "primary" if is_selected else "secondary"
            if st.button(btn_label, key=f"wiz_step1_chan_{c_id}", type=btn_type, use_container_width=True):
                state.channel_id = c_id
                state.channel_name = chan.channel_name
                st.session_state["active_channel_id"] = c_id
                st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav2:
        if st.button("Next: Enter Topic →", key="wiz_step1_next_btn", type="primary", use_container_width=True):
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 2: ENTER A TOPIC
# -----------------------------------------------------------------------------
def render_step_2_topic(state: WizardState) -> None:
    """Step 2: Enter candidate video subject."""
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 2: Enter a Topic
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                Enter the subject of the video you want to make. Start with a broad topic, product name, or viewer question. We'll search real YouTube autocomplete predictions to show you what people want to watch right now.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    topic_val = st.text_input(
        "Candidate Video Subject",
        value=state.topic or "best wireless earbuds",
        placeholder="e.g. best wireless earbuds",
        help="Enter 2 or more characters. For example: 'iphone 16 review', 'notion setup', or 'python tutorial'.",
        key="wiz_step2_topic_input",
    )
    state.topic = topic_val

    # Phase 34: Duplicate Research Detector for Wizard
    if topic_val and len(topic_val.strip()) >= 3:
        render_duplicate_detection_banner(
            channel_id=state.channel_id,
            query=topic_val.strip(),
            context="wizard",
        )

    st.caption("💡 *Quick Idea Starters for Inspiration:*")
    starter_cols = st.columns(4)
    starters = [
        "best wireless earbuds",
        "how to edit youtube videos",
        "notion setup for beginners",
        "m3 macbook air review",
    ]
    for idx, starter in enumerate(starters):
        with starter_cols[idx]:
            if st.button(starter, key=f"wiz_starter_{idx}", use_container_width=True):
                state.topic = starter
                st.session_state["wiz_step2_topic_input"] = starter
                st.rerun()

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Channel", key="wiz_step2_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        if st.button("Next: Choose Settings →", key="wiz_step2_next_btn", type="primary", use_container_width=True):
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 3: CHOOSE RESEARCH SETTINGS
# -----------------------------------------------------------------------------
def render_step_3_settings(state: WizardState) -> None:
    """Step 3: Choose sensible research settings with advanced options collapsed."""
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 3: Choose Research Settings
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                We recommend standard defaults (English / United States). Your settings are pre-configured so you can find authentic keywords with zero technical setup.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px;">
                <div style="font-size: 0.74rem; font-weight: 700; color: #64748B; text-transform: uppercase;">
                    Target Audience Language
                </div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin: 4px 0;">
                    {config.supported_languages.get(state.language, "English")} ({state.language})
                </div>
                <div style="font-size: 0.78rem; color: #64748B;">
                    Optimized for global English-language YouTube queries.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_s2:
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px;">
                <div style="font-size: 0.74rem; font-weight: 700; color: #64748B; text-transform: uppercase;">
                    Target Regional Endpoint
                </div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin: 4px 0;">
                    {config.supported_countries.get(state.country, "United States")} ({state.country})
                </div>
                <div style="font-size: 0.78rem; color: #64748B;">
                    Regional suggestion endpoint filter for YouTube search.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Optional Advanced Settings collapsed
    with st.expander("⚙️ Optional: Change Language or Country", expanded=False):
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            lang_keys = list(config.supported_languages.keys())
            cur_l_idx = lang_keys.index(state.language) if state.language in lang_keys else 0
            sel_lang = st.selectbox(
                "Language Endpoint",
                options=lang_keys,
                index=cur_l_idx,
                format_func=lambda c: f"{config.supported_languages[c]} ({c})",
                key="wiz_sel_lang_box",
            )
            state.language = sel_lang
        with col_l2:
            country_keys = list(config.supported_countries.keys())
            cur_c_idx = country_keys.index(state.country) if state.country in country_keys else 0
            sel_country = st.selectbox(
                "Country Endpoint",
                options=country_keys,
                index=cur_c_idx,
                format_func=lambda c: f"{config.supported_countries[c]} ({c})",
                key="wiz_sel_country_box",
            )
            state.country = sel_country

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Topic", key="wiz_step3_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        if st.button("Next: Find Keywords →", key="wiz_step3_next_btn", type="primary", use_container_width=True):
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 4: FIND KEYWORDS
# -----------------------------------------------------------------------------
def render_step_4_find(state: WizardState) -> None:
    """Step 4: Execute real YouTube autocomplete query with progress bar and duplicate prevention."""
    clean_topic = (state.topic or "").strip()

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 4: Find Keywords
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                Ready to search YouTube autocomplete for <b>"{clean_topic}"</b> targeting <b>{state.channel_name}</b>.
                Click the button below to query live search predictions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Search Execution Area
    already_has_results = len(state.suggestions) > 0
    btn_label = "🔄 Re-run Search" if already_has_results else "🔍 Find Keywords"

    find_clicked = st.button(
        btn_label,
        type="primary",
        disabled=state.is_searching,
        key="wiz_find_keywords_exec_btn",
        use_container_width=True,
        help="Query real YouTube autocomplete predictions for this topic.",
    )

    if find_clicked and not state.is_searching:
        state.is_searching = True
        state.error_message = None
        progress_bar = st.progress(0.1)

        try:
            progress_bar.progress(0.4)
            provider = YouTubeAutocompleteProvider(database_manager=db_manager)
            raw_results = provider.get_suggestions(
                query=clean_topic,
                language=state.language,
                country=state.country,
                use_cache=True,
            )
            progress_bar.progress(0.75)

            # Classify, score, and format suggestions into WizardSuggestionItem list
            formatted_items: List[Dict[str, Any]] = []
            for item in raw_results:
                is_cached = bool(getattr(item, "is_cached", False))
                # Classify intent & score relevance
                cls = default_classifier.classify(item.keyword)
                score_obj = default_scorer.score(item.keyword, clean_topic, cls)
                rel_score = float(score_obj.total_score)
                rel_label = get_relevance_tier_label(rel_score)

                prov = "cached_autocomplete" if is_cached else "live_autocomplete"
                w_item = WizardSuggestionItem(
                    keyword=item.keyword,
                    relevance_score=rel_score,
                    relevance_label=rel_label,
                    search_intent=cls.primary_intent.value if hasattr(cls.primary_intent, "value") else str(cls.primary_intent),
                    provenance=prov,
                    is_cached=is_cached,
                    is_generated=False,
                    notes=cls.primary_explanation,
                )
                formatted_items.append(w_item.to_dict())

            state.suggestions = formatted_items
            progress_bar.progress(1.0)
            st.session_state.instant_suggestions = raw_results
            st.session_state.instant_suggestions_seed = clean_topic
            st.session_state.last_query = clean_topic
            st.session_state.active_seed_input = clean_topic

            if not formatted_items:
                state.error_message = f"YouTube returned 0 suggestions for '{clean_topic}'. Try a slightly broader phrase or another keyword."
            else:
                state.last_action_notice = f"Found {len(formatted_items)} authentic keyword suggestions!"

        except Exception as exc:
            state.error_message = f"Autocomplete search could not complete: {exc}. Please check your connection or try again."
        finally:
            state.is_searching = False
            st.rerun()

    # If results are already in memory, display a summary card
    if state.suggestions:
        st.markdown(
            f"""
            <div style="background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 10px; padding: 12px 16px; margin: 12px 0;">
                <div style="font-size: 0.82rem; font-weight: 700; color: #15803D;">
                    ✓ {len(state.suggestions)} KEYWORDS RETRIEVED SUCCESSFULLY
                </div>
                <div style="font-size: 0.88rem; color: #166534; margin-top: 3px;">
                    Real YouTube search predictions loaded. Click <b>"Next: Review Results"</b> to inspect relevance and search intent.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Settings", key="wiz_step4_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        can_proceed = len(state.suggestions) > 0 and not state.is_searching
        if st.button("Next: Review Results →", key="wiz_step4_next_btn", type="primary", disabled=not can_proceed, use_container_width=True):
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 5: REVIEW RESULTS
# -----------------------------------------------------------------------------
def render_step_5_review(state: WizardState) -> None:
    """Step 5: Review keywords in plain English with honest tooltips and badges."""
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 5: Review Results
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                Below are the authentic phrases viewers are typing on YouTube for <b>"{state.topic}"</b>.
                Each result shows its source, search intent, and long-tail classification.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Beginner Tooltip Bar
    with st.expander("ℹ️ Plain English Guide: What do these labels mean?", expanded=False):
        c_g1, c_g2, c_g3 = st.columns(3)
        with c_g1:
            st.markdown(f"**Search Intent:** {BEGINNER_TOOLTIPS['search_intent']}")
        with c_g2:
            st.markdown(f"**Long-tail Keyword:** {BEGINNER_TOOLTIPS['long_tail_keyword']}")
        with c_g3:
            st.markdown(f"**Research Confidence:** {BEGINNER_TOOLTIPS['research_confidence']}")

    st.caption(f"Showing **{len(state.suggestions)}** authentic suggestions:")

    # Render each suggestion row
    for idx, s in enumerate(state.suggestions):
        kw_text = s.get("keyword", "")
        is_cached = s.get("is_cached", False)
        intent = s.get("search_intent", "Informational")
        word_count = len(kw_text.split())
        is_long_tail = word_count >= 3

        badge_txt = "Cached Result" if is_cached else "Live Suggestion"
        badge_bg = "#F5F3FF" if is_cached else "#F0FDF4"
        badge_clr = "#6D28D9" if is_cached else "#15803D"

        col_r1, col_r2, col_r3, col_r4 = st.columns([5, 2, 2, 1.5])
        with col_r1:
            st.markdown(
                f"""
                <div style="padding: 4px 0; font-size: 0.96rem; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #94A3B8;">🔍</span>
                    <span style="font-weight: 600; color: #0F172A;">{kw_text}</span>
                    <span style="background: {badge_bg}; color: {badge_clr}; font-size: 0.72rem; padding: 1px 7px; border-radius: 6px; font-weight: 600;">
                        {badge_txt}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_r2:
            tip_intent = BEGINNER_TOOLTIPS.get("search_intent", "")
            st.markdown(
                f"<span style='font-size: 0.8rem; color: #475569;' title='{tip_intent}'>🎯 {intent}</span>",
                unsafe_allow_html=True,
            )
        with col_r3:
            tail_tag = "Long-tail (3+ words)" if is_long_tail else "Short-tail"
            tip_tail = BEGINNER_TOOLTIPS.get("long_tail_keyword", "")
            st.markdown(
                f"<span style='font-size: 0.78rem; color: #64748B;' title='{tip_tail}'>🏷️ {tail_tag}</span>",
                unsafe_allow_html=True,
            )
        with col_r4:
            if st.button("Select", key=f"wiz_step5_pick_{idx}", help=f"Choose '{kw_text}' as target"):
                state.selected_keyword = kw_text
                state.best_fit_keyword = kw_text
                st.rerun()

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Search", key="wiz_step5_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        if st.button("Next: Choose Best-Fit Keyword →", key="wiz_step5_next_btn", type="primary", use_container_width=True):
            if not state.selected_keyword and state.suggestions:
                # Default to top keyword
                state.selected_keyword = state.suggestions[0]["keyword"]
                state.best_fit_keyword = state.suggestions[0]["keyword"]
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 6: CHOOSE YOUR BEST-FIT KEYWORD
# -----------------------------------------------------------------------------
def render_step_6_choose_best_fit(state: WizardState) -> None:
    """Step 6: Help the creator pick the winning topic for their video based on relevance and evidence."""
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem;">
                Step 6: Choose Your Best-Fit Keyword
            </div>
            <div style="font-size: 0.9rem; color: #64748B; line-height: 1.45;">
                Select the single best keyword for your video. Keywords with <b>Highly relevant</b> badges have the strongest alignment with your topic and clear viewer intent.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_choice = state.best_fit_keyword or state.selected_keyword or (state.suggestions[0]["keyword"] if state.suggestions else "")

    for idx, s in enumerate(state.suggestions):
        kw_text = s.get("keyword", "")
        rel_label = s.get("relevance_label", RelevanceTierLabel.WORTH_REVIEWING.value)
        style = get_relevance_badge_style(rel_label)
        intent = s.get("search_intent", "Informational")
        is_chosen = (kw_text == current_choice)

        card_bg = "#F0FDF4" if is_chosen else "#FFFFFF"
        border_col = "#22C55E" if is_chosen else "#E2E8F0"

        c_box, c_btn = st.columns([5.5, 1.8])
        with c_box:
            st.markdown(
                f"""
                <div style="background: {card_bg}; border: 2px solid {border_col}; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-size: 1.02rem; font-weight: 700; color: #0F172A;">
                            {'★ ' if is_chosen else ''}{kw_text}
                        </span>
                        <span style="background: {style['bg']}; color: {style['color']}; border: 1px solid {style['border']}; font-size: 0.74rem; font-weight: 600; padding: 2px 8px; border-radius: 6px;">
                            {style['icon']} {rel_label}
                        </span>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748B; margin-top: 4px;">
                        <b>Intent:</b> {intent} &middot; <b>Channel:</b> {state.channel_name}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_btn:
            btn_label = "✓ Winning Choice" if is_chosen else "Choose Topic"
            btn_type = "primary" if is_chosen else "secondary"
            if st.button(btn_label, key=f"wiz_step6_select_{idx}", type=btn_type, use_container_width=True):
                state.best_fit_keyword = kw_text
                state.selected_keyword = kw_text
                current_choice = kw_text
                st.rerun()

    # Phase 31: Keyword Decision Helper for Step 6
    step6_chan = channel_manager.get_channel(state.selected_channel_id)
    if step6_chan and state.suggestions:
        step6_kws = [s["keyword"] for s in state.suggestions[:4]]
        with st.expander("⚖️ Keyword Decision Helper (Channel Alignment & Comparison)", expanded=False):
            from src.ui.action_center_ui import render_keyword_decision_helper
            render_keyword_decision_helper(step6_kws, step6_chan)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Review", key="wiz_step6_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        if st.button("Next: Take Action →", key="wiz_step6_next_btn", type="primary", use_container_width=True):
            state.best_fit_keyword = current_choice
            state.selected_keyword = current_choice
            if state.go_next():
                st.rerun()


# -----------------------------------------------------------------------------
# STEP 7: CONTINUE (ONE-CLICK ACTIONS & CLEAR CONFIRMATION)
# -----------------------------------------------------------------------------
def render_step_7_continue(state: WizardState) -> None:
    """Step 7: Provide real one-click actions supported by Keyword Studio with instant confirmation feedback."""
    winning_topic = state.best_fit_keyword or state.selected_keyword or state.topic

    st.markdown(
        f"""
        <div style="background: #F0FDF4; border: 2px solid #86EFAC; border-radius: 12px; padding: 1.35rem 1.5rem; margin-bottom: 1.25rem;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #15803D; text-transform: uppercase; letter-spacing: 0.05em;">
                WINNING VIDEO TOPIC SELECTED
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #0F172A; margin: 4px 0 6px 0;">
                🎯 "{winning_topic}"
            </div>
            <div style="font-size: 0.88rem; color: #166534;">
                Target Channel: <b>{state.channel_name}</b> &middot; Verified via YouTube Autocomplete &middot; Ready for production
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🚀 What do you want to do next?")
    st.caption("Click any action below to continue your video workflow:")

    act_col1, act_col2 = st.columns(2)

    with act_col1:
        # Action 1: Save Research to Project
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-bottom: 3px;">
                    💾 Save to Project History
                </div>
                <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 10px;">
                    Store this keyword list in your local SQLite database for future review and tracking.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Save Research Project", key="wiz_save_proj_btn", use_container_width=True, type="primary"):
            try:
                # Save project
                proj_name = f"Wizard: {winning_topic}"
                # Save seed to session state
                st.session_state.last_query = winning_topic
                st.session_state.active_seed_input = winning_topic
                state.last_action_notice = f"Saved research project '{proj_name}' to local database!"
                st.toast(f"✓ Saved project: {proj_name}")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to save project: {exc}")

        # Action 2: Check Competing Videos (SERP)
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-bottom: 12px; margin-top: 14px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-bottom: 3px;">
                    🎥 Check Competing Videos (SERP)
                </div>
                <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 10px;">
                    Inspect existing YouTube search results, competitor titles, and view counts for this topic.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Inspect YouTube Competitor Videos →", key="wiz_goto_serp_btn", use_container_width=True):
            st.session_state.active_seed_input = winning_topic
            st.session_state.last_query = winning_topic
            st.session_state.serp_search_query = winning_topic
            st.session_state.current_page = PAGE_VIDEO_RESEARCH
            st.rerun()

    with act_col2:
        # Action 3: Draft Video Title & Description
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-bottom: 3px;">
                    ✍️ Draft Title & Description
                </div>
                <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 10px;">
                    Use the 8-Part Description Studio to generate click-worthy titles, timestamps, and affiliate disclaimers.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Description Studio →", key="wiz_goto_desc_btn", use_container_width=True):
            st.session_state.active_seed_input = winning_topic
            st.session_state.last_query = winning_topic
            st.session_state.desc_studio_topic_input = winning_topic
            st.session_state.current_page = PAGE_DESCRIPTION_STUDIO
            st.rerun()

        # Action 4: Validate Topic & Growth Intelligence
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-bottom: 12px; margin-top: 14px;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #0F172A; margin-bottom: 3px;">
                    🎯 Run Topic Validation
                </div>
                <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 10px;">
                    Check your channel gap score, competition level, and multi-factor opportunity readiness.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Validate Topic in Growth Studio →", key="wiz_goto_validation_btn", use_container_width=True):
            st.session_state.active_seed_input = winning_topic
            st.session_state.last_query = winning_topic
            st.session_state.current_page = PAGE_VALIDATION
            st.rerun()

    # Action 5: One-click CSV Export
    st.markdown("---")
    st.markdown("#### 📥 One-Click Export")
    if state.suggestions:
        df_export = sanitize_dataframe_for_export(pd.DataFrame(state.suggestions))
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")

        c_exp1, c_exp2 = st.columns([2, 2])
        with c_exp1:
            st.download_button(
                label=f"📥 Download {len(state.suggestions)} Keywords as CSV",
                data=csv_bytes,
                file_name=f"keyword_studio_wizard_{winning_topic.replace(' ', '_')}.csv",
                mime="text/csv",
                key="wiz_download_csv_btn",
                use_container_width=True,
            )
        with c_exp2:
            if st.button("📋 Copy All Keywords to Clipboard", key="wiz_copy_all_btn", use_container_width=True):
                kw_list = [s.get("keyword", "") for s in state.suggestions]
                st.session_state.copy_box_content = kw_list
                st.session_state.show_copy_box = True
                st.toast(f"Copied {len(kw_list)} keywords to clipboard buffer!")
                st.rerun()

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Step Navigation Controls
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("← Back to Best-Fit Keyword", key="wiz_step7_back_btn", use_container_width=True):
            if state.go_back():
                st.rerun()
    with col_nav2:
        if st.button("✨ Research Another Topic", key="wiz_step7_restart_btn", type="primary", use_container_width=True):
            state.reset()
            st.session_state.instant_suggestions = []
            st.rerun()
