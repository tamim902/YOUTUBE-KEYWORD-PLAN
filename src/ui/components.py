"""Reusable UI components for the Streamlit dashboard."""

from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

from src.config import APP_NAME, APP_VERSION, config
from src.ui.styles import CUSTOM_CSS


PAGE_LANDING = "✨ Overview & Showcase"
PAGE_DASHBOARD = "📊 Dashboard"
PAGE_NEW_RESEARCH = "🔍 New Keyword Research"
PAGE_RESULTS = "📋 Keyword Results"
PAGE_PATTERNS = "🧩 Pattern Generator"
PAGE_SAVED = "💾 Saved Research"
PAGE_SETTINGS = "⚙️ Settings & Data Sources"
PAGE_VIDEO_RESEARCH = "🎥 YouTube Video Research"
PAGE_SERP = PAGE_VIDEO_RESEARCH
PAGE_CONTENT_OPPORTUNITIES = "💡 Content Opportunities"
PAGE_PRODUCT_OPPORTUNITIES = "📦 Niche Product Opportunity Finder"
PAGE_PRODUCT_PLANNER = "🏷️ Product Opportunity Planner"
PAGE_RESEARCH_MONITOR = "📡 Research Monitor"
PAGE_CHANNELS = "📺 Channel Portfolio"
PAGE_MORNING_REPORT = "🌅 Morning Idea Report"
PAGE_DESCRIPTION_STUDIO = "✍️ Description Studio"
PAGE_SEO_AUDIT = "🩺 SEO & Content Audit"
PAGE_ANALYTICS = "📈 Analytics & Growth Intelligence"
PAGE_STRATEGY = "🧭 Content Strategy Autopilot"
PAGE_VALIDATION = "🎯 Topic Validation & Growth Intelligence"
PAGE_USER_GUIDE = "📖 User Guide"
PAGE_AUTH = "🔐 Studio Profile & Auth"

# ==============================================================================
# Master Upgrade: Exactly Five Primary Tools Definitions
# ==============================================================================
TOOL_KEYWORD_RESEARCH = "🔍 Keyword Research"
TOOL_VIDEO_RESEARCH = "🎥 YouTube Video Research"
TOOL_COMPETITOR_RESEARCH = "🎯 Competitor Research"
TOOL_60_DAY_OPPORTUNITIES = "⚡ 60-Day Opportunities"
TOOL_SEO_GENERATOR = "✨ SEO Generator"
TOOL_SETTINGS = "⚙️ Settings"

FIVE_PRIMARY_TOOLS = [
    TOOL_KEYWORD_RESEARCH,
    TOOL_VIDEO_RESEARCH,
    TOOL_COMPETITOR_RESEARCH,
    TOOL_60_DAY_OPPORTUNITIES,
    TOOL_SEO_GENERATOR,
]

# Legacy alias for backward compatibility
FOUR_CORE_TOOLS = FIVE_PRIMARY_TOOLS

TOOL_CANONICAL_MAP = {
    "✨ SEO Generator": TOOL_SEO_GENERATOR,
    "✨ SEO Title, Description & Tags Generator": TOOL_SEO_GENERATOR,
    "⚡ 60-Day Opportunities": TOOL_60_DAY_OPPORTUNITIES,
    "⚡ Last 60 Days Opportunity Finder": TOOL_60_DAY_OPPORTUNITIES,
    "60-Day Opportunity Finder": TOOL_60_DAY_OPPORTUNITIES,
    "Keyword Research": TOOL_KEYWORD_RESEARCH,
    "YouTube Video Research": TOOL_VIDEO_RESEARCH,
    "Video Research": TOOL_VIDEO_RESEARCH,
    "Competitor Research": TOOL_COMPETITOR_RESEARCH,
    "SEO Generator": TOOL_SEO_GENERATOR,
    "Settings": TOOL_SETTINGS,
}

# Core Phase 6 navigation pages
NAVIGATION_PAGES = [
    PAGE_DASHBOARD,
    PAGE_NEW_RESEARCH,
    PAGE_RESULTS,
    PAGE_PATTERNS,
    PAGE_SAVED,
    PAGE_SETTINGS,
]

# Full application navigation pages (14 base destinations preserved for contract tests)
ALL_NAVIGATION_PAGES = [
    PAGE_LANDING,
    PAGE_DASHBOARD,
    PAGE_NEW_RESEARCH,
    PAGE_RESULTS,
    PAGE_PATTERNS,
    PAGE_VIDEO_RESEARCH,
    PAGE_CONTENT_OPPORTUNITIES,
    PAGE_PRODUCT_OPPORTUNITIES,
    PAGE_PRODUCT_PLANNER,
    PAGE_RESEARCH_MONITOR,
    PAGE_SAVED,
    PAGE_USER_GUIDE,
    PAGE_AUTH,
    PAGE_SETTINGS,
]

# Phase 22 Four-Channel Hub destinations
PHASE22_PAGES = [
    PAGE_CHANNELS,
    PAGE_MORNING_REPORT,
    PAGE_DESCRIPTION_STUDIO,
]

# Phase 23 SEO Audit & Content Quality destinations
PHASE23_PAGES = [
    PAGE_SEO_AUDIT,
]

# Phase 24 YouTube Analytics & Growth Intelligence destinations
PHASE24_PAGES = [
    PAGE_ANALYTICS,
]

# Phase 25 YouTube Content Strategy Autopilot destinations
PHASE25_PAGES = [
    PAGE_STRATEGY,
]

# Phase 26 Topic Validation & Growth Intelligence destinations
PHASE26_PAGES = [
    PAGE_VALIDATION,
]

EXTENDED_NAVIGATION_PAGES = ALL_NAVIGATION_PAGES + PHASE22_PAGES + PHASE23_PAGES + PHASE24_PAGES + PHASE25_PAGES + PHASE26_PAGES


def apply_custom_styles() -> None:
    """Inject application CSS styles."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(phase_badge: str = f"v{APP_VERSION}", show_studio_pill: bool = True) -> None:
    """Render top application brand header with Apple-inspired typography."""
    col1, col2 = st.columns([3.5, 1.5])
    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.25rem;">
                <span style="font-size: 1.8rem;">{config.app_icon}</span>
                <div>
                    <h2 style="margin: 0; font-size: 1.5rem; font-weight: 800; color: #111827; letter-spacing: -0.025em;">
                        {APP_NAME}
                    </h2>
                    <div style="font-size: 0.85rem; color: #64748B;">
                        Local-first YouTube autocomplete discovery, recursive expansion, SERP gap inspector & content planning.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        studio_html = "<span class='status-badge badge-success' style='margin-right: 0.5rem;'><span class='dot-live'></span> Local Studio Active</span>" if show_studio_pill else ""
        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 0.5rem;">
                {studio_html}
                <span class="status-badge">{phase_badge}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Clean human-readable label mapping for SaaS sidebar items (emoji-free, clean typography)
PAGE_LABEL_CLEAN_MAP: Dict[str, str] = {
    PAGE_LANDING: "Overview & Showcase",
    PAGE_DASHBOARD: "Dashboard",
    PAGE_CHANNELS: "Channel Portfolio",
    PAGE_MORNING_REPORT: "Morning Idea Report",
    PAGE_DESCRIPTION_STUDIO: "Description Studio",
    PAGE_SEO_AUDIT: "SEO & Content Audit",
    PAGE_ANALYTICS: "Analytics & Growth Intelligence",
    PAGE_STRATEGY: "Content Strategy Autopilot",
    PAGE_VALIDATION: "Topic Validation & Growth Intelligence",
    PAGE_NEW_RESEARCH: "New Keyword Research",
    PAGE_RESULTS: "Keyword Results",
    PAGE_PATTERNS: "Pattern Generator",
    PAGE_VIDEO_RESEARCH: "YouTube Video Research",
    PAGE_CONTENT_OPPORTUNITIES: "Content Opportunities",
    PAGE_PRODUCT_OPPORTUNITIES: "Niche Product Opportunity Finder",
    PAGE_PRODUCT_PLANNER: "Product Opportunity Planner",
    PAGE_RESEARCH_MONITOR: "Research Monitor",
    PAGE_SAVED: "Saved Research",
    PAGE_USER_GUIDE: "User Guide",
    PAGE_AUTH: "Studio Profile & Auth",
    PAGE_SETTINGS: "Settings & Data Sources",
}

# Navigation section group hierarchy for breadcrumbs and categorisation (14 base destinations)
PAGE_SECTION_MAP: Dict[str, str] = {
    PAGE_LANDING: "WORKSPACE",
    PAGE_DASHBOARD: "WORKSPACE",
    PAGE_NEW_RESEARCH: "WORKSPACE",
    PAGE_RESULTS: "WORKSPACE",
    PAGE_PATTERNS: "DISCOVERY & INTELLIGENCE",
    PAGE_VIDEO_RESEARCH: "DISCOVERY & INTELLIGENCE",
    PAGE_CONTENT_OPPORTUNITIES: "DISCOVERY & INTELLIGENCE",
    PAGE_PRODUCT_OPPORTUNITIES: "DISCOVERY & INTELLIGENCE",
    PAGE_PRODUCT_PLANNER: "DISCOVERY & INTELLIGENCE",
    PAGE_RESEARCH_MONITOR: "WORKFLOW & MANAGEMENT",
    PAGE_SAVED: "WORKFLOW & MANAGEMENT",
    PAGE_USER_GUIDE: "WORKFLOW & MANAGEMENT",
    PAGE_AUTH: "STUDIO & CONFIGURATION",
    PAGE_SETTINGS: "STUDIO & CONFIGURATION",
}

# Extended section map including Phase 22 Four-Channel Hub and Phase 23 SEO Audit
EXTENDED_PAGE_SECTION_MAP: Dict[str, str] = {
    **PAGE_SECTION_MAP,
    PAGE_CHANNELS: "WORKSPACE",
    PAGE_MORNING_REPORT: "DISCOVERY & INTELLIGENCE",
    PAGE_DESCRIPTION_STUDIO: "DISCOVERY & INTELLIGENCE",
    PAGE_SEO_AUDIT: "DISCOVERY & INTELLIGENCE",
    PAGE_ANALYTICS: "DISCOVERY & INTELLIGENCE",
    PAGE_STRATEGY: "DISCOVERY & INTELLIGENCE",
    PAGE_VALIDATION: "DISCOVERY & INTELLIGENCE",
}



def render_provenance_badge(provenance_type: Optional[str] = None) -> str:
    """Return an accessible, styled provenance pill for live vs cached vs offline data sources."""
    if not provenance_type:
        return ""

    norm = provenance_type.lower()
    if "api" in norm or "youtube" in norm:
        dot_color = "#2563EB"
        label = "YouTube Data API v3"
    elif "autocomplete" in norm:
        dot_color = "#10B981"
        label = "Autocomplete Live"
    elif "sqlite" in norm or "wal" in norm or "database" in norm:
        dot_color = "#6366F1"
        label = "Local SQLite WAL"
    elif "cache" in norm:
        dot_color = "#F59E0B"
        label = "24h Local Cache"
    elif "offline" in norm or "deterministic" in norm:
        dot_color = "#64748B"
        label = "Deterministic Offline"
    elif "mock" in norm or "demo" in norm or "sample" in norm:
        dot_color = "#DC2626"
        label = "Sample Dataset"
    else:
        dot_color = "#7C3AED"
        label = provenance_type

    return (
        f'<span class="ks-badge-provenance" title="Data Source Provenance: {label}">'
        f'<span class="prov-dot" style="background-color: {dot_color};"></span>'
        f'{label}</span>'
    )


def render_page_header(
    title: str,
    subtitle: str,
    category: Optional[str] = None,
    badge_text: Optional[str] = None,
    badge_type: str = "neutral",
    provenance: Optional[str] = None,
) -> None:
    """Render a standardized Apple-inspired SaaS page header across all application pages.

    Includes:
    - Uppercase category/section breadcrumb (e.g. WORKSPACE > Dashboard).
    - Page title with clean typography.
    - Page subtitle / description.
    - Status badge (e.g. Live, Demo, Offline, Ready, Pro, v1.0.0).
    - Data provenance badge (e.g. YouTube Data API v3, Autocomplete Live, SQLite WAL).
    """
    section_crumb = category or PAGE_SECTION_MAP.get(title, "WORKSPACE")
    badge_class = f"ks-badge ks-badge-{badge_type}" if badge_type in {"primary", "success", "warning", "error", "neutral"} else "ks-badge ks-badge-neutral"

    badge_html = f'<span class="{badge_class}">{badge_text}</span>' if badge_text else ""
    prov_html = render_provenance_badge(provenance) if provenance else ""

    st.markdown(
        f"""
        <div class="ks-page-header animate-fade-in">
            <div class="ks-breadcrumb">
                <span>{section_crumb}</span>
                <span class="ks-crumb-sep">&rsaquo;</span>
                <span class="ks-crumb-active">{title}</span>
            </div>
            <div class="ks-header-top">
                <div class="ks-page-title-group">
                    <h1 class="ks-page-title">{title}</h1>
                </div>
                <div class="ks-header-badges">
                    {prov_html}
                    {badge_html}
                </div>
            </div>
            <p class="ks-page-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    title: str,
    description: str,
    icon: str = "🔍",
    action_label: Optional[str] = None,
    action_key: Optional[str] = None,
) -> bool:
    """Render a standardized empty state card with optional call-to-action button."""
    st.markdown(
        f"""
        <div class="ks-empty-state animate-scale-in">
            <div class="ks-empty-icon">{icon}</div>
            <div class="ks-empty-title">{title}</div>
            <div class="ks-empty-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if action_label:
        col_pad1, col_btn, col_pad2 = st.columns([1.5, 2, 1.5])
        with col_btn:
            key = action_key or f"empty_state_btn_{abs(hash(title)) % 10000}"
            return bool(st.button(action_label, key=key, type="primary", use_container_width=True))
    return False


def render_recommended_next_step(
    title: str,
    description: str,
    action_label: str,
    action_key: str,
    why_recommended: Optional[str] = None,
    secondary_action_label: Optional[str] = None,
    secondary_action_key: Optional[str] = None,
) -> Tuple[bool, bool]:
    """Render a context-aware next step card at the bottom of a results workflow.

    Returns:
        (primary_clicked, secondary_clicked) tuple of booleans.
    """
    why_html = f"<div style='font-size: 0.8rem; color: #475569; margin-top: 0.35rem;'>💡 <b>Why this step:</b> {why_recommended}</div>" if why_recommended else ""
    st.markdown(
        f"""
        <div class="ks-card animate-fade-in" style="border-left: 4px solid #2563EB; margin-top: 1.5rem; background: #FFFFFF;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.4rem;">
                <span class="ks-badge ks-badge-primary" style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    RECOMMENDED NEXT STEP
                </span>
            </div>
            <h4 style="margin: 0.2rem 0; font-size: 1.05rem; font-weight: 700; color: #0F172A;">{title}</h4>
            <p style="margin: 0; font-size: 0.86rem; color: #475569; line-height: 1.45;">{description}</p>
            {why_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, _ = st.columns([1.6, 1.6, 1.8])
    prim_clicked = False
    sec_clicked = False
    with col1:
        if st.button(action_label, key=action_key, type="primary", use_container_width=True):
            prim_clicked = True
    if secondary_action_label and secondary_action_key:
        with col2:
            if st.button(secondary_action_label, key=secondary_action_key, use_container_width=True):
                sec_clicked = True

    return prim_clicked, sec_clicked


def format_nav_label(page_key: str) -> str:
    """Format raw page constant into a clean, modern SaaS label."""
    return PAGE_LABEL_CLEAN_MAP.get(page_key, str(page_key))


def get_current_interface_mode() -> str:
    """Get active interface mode ('simple' or 'advanced'), checking session state and DB."""
    if "interface_mode" in st.session_state and st.session_state["interface_mode"] in ("simple", "advanced"):
        return st.session_state["interface_mode"]
    try:
        from src.storage.database import DatabaseManager
        val = DatabaseManager().get_setting("interface_mode", "simple")
        mode = "advanced" if val == "advanced" else "simple"
    except Exception:
        mode = "simple"
    st.session_state["interface_mode"] = mode
    return mode


def set_interface_mode(mode: str) -> None:
    """Set and persist active interface mode ('simple' or 'advanced')."""
    clean_mode = "advanced" if str(mode).strip().lower() in ("advanced", "adv", "pro", "expert") else "simple"
    st.session_state["interface_mode"] = clean_mode
    try:
        from src.storage.database import DatabaseManager
        DatabaseManager().set_setting("interface_mode", clean_mode)
    except Exception:
        pass


def render_beginner_tooltip(term_key: str) -> str:
    """Retrieve beginner-friendly honest tooltip text for a key concept."""
    from src.models.wizard import BEGINNER_TOOLTIPS
    return BEGINNER_TOOLTIPS.get(term_key, "Helpful guidance for this topic.")


def render_relevance_badge(score: Optional[float], is_generated: bool = False) -> str:
    """Render an HTML badge displaying plain English relevance tier with tooltip."""
    from src.models.wizard import get_relevance_badge_style, get_relevance_tier_label
    label = get_relevance_tier_label(score, is_generated=is_generated)
    style = get_relevance_badge_style(label)
    bg = style.get("bg", "#F8FAFC")
    col = style.get("color", "#64748B")
    border = style.get("border", "#E2E8F0")
    icon = style.get("icon", "⚪")
    return (
        f"<span style='background: {bg}; color: {col}; "
        f"border: 1px solid {border}; padding: 2px 8px; border-radius: 6px; "
        f"font-size: 0.76rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;' "
        f"title='{label}: Deterministic relevance classification'>{icon} {label}</span>"
    )


def render_navigation(current_page: str = PAGE_LANDING) -> str:
    """Render polished SaaS sidebar navigation menu and return selected page."""
    # Ensure current_page is valid
    if (
        current_page not in ALL_NAVIGATION_PAGES
        and current_page not in PHASE22_PAGES
        and current_page not in PHASE23_PAGES
        and current_page not in PHASE24_PAGES
        and current_page not in PHASE25_PAGES
        and current_page not in PHASE26_PAGES
    ):
        current_page = PAGE_LANDING


    # Sidebar compact preference (session-persisted)
    compact_mode = bool(st.session_state.get("sidebar_compact_mode", False))

    if compact_mode:
        st.sidebar.markdown(
            """
            <style>
                [data-testid="stSidebar"] {
                    min-width: 80px !important;
                    max-width: 86px !important;
                }
                [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
                    justify-content: center !important;
                    padding: 9px 0 !important;
                }
                [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] p {
                    font-size: 0 !important;
                    gap: 0 !important;
                    width: auto !important;
                }
                [data-testid="stSidebar"] .ks-brand-title,
                [data-testid="stSidebar"] .ks-pro-tag,
                [data-testid="stSidebar"] .workspace-info,
                [data-testid="stSidebar"] .workspace-details,
                [data-testid="stSidebar"] .workspace-status-badge,
                [data-testid="stSidebar"] .nav-search-wrapper {
                    display: none !important;
                }
                [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label::before,
                [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label::after {
                    display: none !important;
                }
                [data-testid="stSidebar"] .sidebar-workspace-card {
                    padding: 8px 4px !important;
                    text-align: center !important;
                }
                [data-testid="stSidebar"] .workspace-avatar {
                    margin: 0 auto !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # Brand Header (Apple-inspired SaaS Brand Container)
    st.sidebar.markdown(
        """
        <div class="ks-sidebar-header">
            <div class="ks-brand-badge" title="Keyword Studio SaaS">
                <svg class="ks-brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="m21 21-4.3-4.3"></path>
                </svg>
            </div>
            <div class="ks-brand-info">
                <span class="ks-brand-title">Keyword Studio</span>
            </div>
            <span class="ks-pro-tag">PRO</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Collapsible sidebar toggle (persisted in session state)
    compact_toggle = st.sidebar.toggle(
        "Compact View",
        value=compact_mode,
        key="sidebar_compact_toggle",
        help="Toggle compact icon-only navigation sidebar",
    )
    if compact_toggle != compact_mode:
        st.session_state["sidebar_compact_mode"] = compact_toggle
        st.rerun()

    # Phase 29: Interface Experience Mode (Simple Mode vs Advanced Mode)
    cur_mode = get_current_interface_mode()
    is_advanced = (cur_mode == "advanced")

    mode_toggle = st.sidebar.toggle(
        "⚡ Advanced Mode",
        value=is_advanced,
        key="sidebar_interface_mode_toggle",
        help="Turn ON for power-user multi-level crawls and technical diagnostics. Turn OFF for the beginner-friendly 7-step guided wizard.",
    )
    new_mode = "advanced" if mode_toggle else "simple"
    if new_mode != cur_mode:
        set_interface_mode(new_mode)
        st.rerun()

    st.sidebar.markdown("<div class=\"ks-sidebar-divider\"></div>", unsafe_allow_html=True)

    # Command-Style Quick Search Navigation
    raw_query = st.sidebar.text_input(
        "Quick Search",
        placeholder="🔍 Quick jump to page...",
        label_visibility="collapsed",
        key="nav_command_search_input",
    )
    search_query = raw_query.strip() if isinstance(raw_query, str) else ""

    if search_query:
        # Dynamic filter for destination pages across all 14 base + Phase 22 pages
        matching_pages = [
            p for p in EXTENDED_NAVIGATION_PAGES
            if search_query.lower() in PAGE_LABEL_CLEAN_MAP.get(p, p).lower()
            or search_query.lower() in p.lower()
        ]

        if matching_pages:
            st.sidebar.markdown(
                f"<div class='nav-search-results-label'>MATCHING DESTINATIONS ({len(matching_pages)})</div>",
                unsafe_allow_html=True,
            )
            match_index = matching_pages.index(current_page) if current_page in matching_pages else 0
            selected_page = st.sidebar.radio(
                "Matching Pages",
                options=matching_pages,
                index=match_index,
                label_visibility="collapsed",
                key="matching_navigation_radio",
                format_func=format_nav_label,
            )
            if st.sidebar.button("✕ Clear Search", key="clear_nav_search_btn"):
                st.session_state["nav_command_search_input"] = ""
                st.rerun()
        else:
            st.sidebar.markdown(
                f"""
                <div class="nav-empty-state">
                    <div style="font-size: 1.1rem; margin-bottom: 4px;">🔎</div>
                    <div style="font-weight: 600; color: #1E293B; margin-bottom: 2px; font-size: 0.8rem;">No destinations found</div>
                    <div style="font-size: 0.72rem; color: #64748B; margin-bottom: 6px;">No page matches "{search_query}"</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.sidebar.button("✕ Reset Search", key="clear_empty_nav_search_btn"):
                st.session_state["nav_command_search_input"] = ""
                st.rerun()
            selected_page = current_page
    else:
        # Standard full navigation with 4 structured groups
        default_index = ALL_NAVIGATION_PAGES.index(current_page) if current_page in ALL_NAVIGATION_PAGES else 0
        selected_page = st.sidebar.radio(
            "Go to page",
            options=ALL_NAVIGATION_PAGES,
            index=default_index,
            label_visibility="collapsed",
            key="main_navigation_radio",
            format_func=format_nav_label,
        )

        # If user is on a Phase 22, Phase 23, Phase 24, Phase 25, or Phase 26 page and hasn't changed the main radio, preserve it
        if (
            current_page in PHASE22_PAGES
            or current_page in PHASE23_PAGES
            or current_page in PHASE24_PAGES
            or current_page in PHASE25_PAGES
            or current_page in PHASE26_PAGES
        ) and selected_page == ALL_NAVIGATION_PAGES[default_index]:
            selected_page = current_page

    # Phase 28: Quick Studio Jump Drawer (Collapsible Category Navigation for Extended Studios)
    with st.sidebar.expander("✨ Extended Studios & Growth Engines", expanded=False):
        st.caption("Direct access to channel growth and content strategy engines:")
        extended_tools = [
            (PAGE_CHANNELS, "Channel Portfolio (4 Independent Channels)"),
            (PAGE_STRATEGY, "Content Strategy Autopilot"),
            (PAGE_VALIDATION, "Topic Validation & Gap Engine"),
            (PAGE_MORNING_REPORT, "Daily Morning Idea Report"),
            (PAGE_SEO_AUDIT, "SEO & Content Audit Studio"),
            (PAGE_DESCRIPTION_STUDIO, "Description Studio (8-Part)"),
            (PAGE_ANALYTICS, "Channel Analytics & Growth"),
        ]
        for p_ext, p_desc in extended_tools:
            is_active = (current_page == p_ext)
            btn_type = "primary" if is_active else "secondary"
            clean_name = PAGE_LABEL_CLEAN_MAP.get(p_ext, p_ext)
            prefix = "▶ " if is_active else ""
            if st.button(f"{prefix}{clean_name}", key=f"nav_ext_btn_{abs(hash(p_ext)) % 10000}", use_container_width=True, type=btn_type, help=p_desc):
                return p_ext


    # Studio Profile Sidebar Card (Apple-Inspired White Card)
    st.sidebar.markdown(
        """
        <div class="sidebar-workspace-card" title="Local Pro Studio Workspace">
            <div class="workspace-card-header">
                <div class="workspace-avatar">KS</div>
                <div class="workspace-info">
                    <div class="workspace-name">Local Pro Studio</div>
                    <div class="workspace-role">Local Workspace</div>
                </div>
                <span class="workspace-status-badge">
                    <span class="status-dot"></span> Active
                </span>
            </div>
            <div class="workspace-details">
                <div class="workspace-detail-row">
                    <span class="detail-label">Storage</span>
                    <span class="detail-value">SQLite WAL (Local)</span>
                </div>
                <div class="workspace-detail-row">
                    <span class="detail-label">Privacy</span>
                    <span class="detail-value">Local &middot; Opt-in APIs</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Clickable Profile Action Button routing directly to Studio Profile & Auth
    if st.sidebar.button(
        "Studio Profile & Auth \u2192",
        key="sidebar_workspace_profile_btn",
        use_container_width=True,
    ):
        return PAGE_AUTH

    return selected_page


def render_five_primary_navigation(current_page: str = TOOL_KEYWORD_RESEARCH) -> str:
    """Render the simplified 5-primary-tools sidebar navigation.

    Provides EXACTLY FIVE PRIMARY SECTIONS:
    1. Keyword Research
    2. YouTube Video Research
    3. Competitor Research
    4. 60-Day Opportunities
    5. SEO Generator
    Plus a small quiet action: Settings.
    """
    # Brand Header
    st.sidebar.markdown(
        """
        <div style="padding: 6px 2px 16px 2px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 34px; height: 34px; border-radius: 8px; background: linear-gradient(135deg, #2563EB, #7C3AED); display: flex; align-items: center; justify-content: center; color: white; font-size: 1.1rem; font-weight: bold; box-shadow: 0 2px 4px rgba(37,99,235,0.2);">
                    KS
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 1.05rem; color: #0F172A; letter-spacing: -0.01em; line-height: 1.2;">Keyword Studio</div>
                    <div style="font-size: 0.72rem; color: #64748B; font-weight: 500;">Minimal YouTube Research</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Normalize incoming page
    normalized = TOOL_CANONICAL_MAP.get(current_page, current_page)
    if normalized not in FIVE_PRIMARY_TOOLS and normalized != TOOL_SETTINGS:
        normalized = TOOL_KEYWORD_RESEARCH

    is_settings = (normalized == TOOL_SETTINGS)

    st.sidebar.markdown(
        "<div style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>PRIMARY TOOLS</div>",
        unsafe_allow_html=True,
    )

    # Determine default radio index
    radio_idx = FIVE_PRIMARY_TOOLS.index(normalized) if normalized in FIVE_PRIMARY_TOOLS else 0

    selected_tool = st.sidebar.radio(
        "Core Navigation",
        options=FIVE_PRIMARY_TOOLS,
        index=radio_idx,
        label_visibility="collapsed",
        key="five_primary_tools_radio",
    )

    st.sidebar.markdown("<div style='margin: 22px 0 14px 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)

    # Quiet Settings Action Button
    st.sidebar.markdown(
        "<div style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>SYSTEM</div>",
        unsafe_allow_html=True,
    )
    settings_btn_type = "primary" if is_settings else "secondary"
    if st.sidebar.button("⚙️ Settings & System Status", key="sidebar_quiet_settings_btn", use_container_width=True, type=settings_btn_type):
        return TOOL_SETTINGS

    # If the user was in settings, but clicked a different tool in the radio
    if is_settings:
        if selected_tool != FIVE_PRIMARY_TOOLS[radio_idx]:
            return selected_tool
        return TOOL_SETTINGS

    return selected_tool


def render_four_core_navigation(current_page: str = TOOL_KEYWORD_RESEARCH) -> str:
    """Backward-compatible wrapper routing to the 5 primary tools navigation."""
    return render_five_primary_navigation(current_page=current_page)


def render_metric_card(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    color: Optional[str] = None,
) -> None:
    """Render a styled metric card."""
    color_style = f"color: {color};" if color else ""
    sub_html = f"<div style='font-size: 0.8rem; color: #64748b; margin-top: 0.2rem;'>{subtitle}</div>" if subtitle else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <h4>{title}</h4>
            <p style="{color_style}">{value}</p>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_system_status(
    db_healthy: bool,
    recent_searches_count: int,
    total_keywords_count: int = 0,
    cached_queries_count: int = 0,
) -> None:
    """Render system health status cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            title="Engine Status",
            value="Ready" if db_healthy else "Error",
            subtitle="Local Provider Active",
            color="#059669" if db_healthy else "#dc2626",
        )

    with col2:
        render_metric_card(
            title="Local Storage",
            value="SQLite WAL",
            subtitle=f"{total_keywords_count:,} keywords stored",
            color="#0284c7",
        )

    with col3:
        render_metric_card(
            title="Saved Sessions",
            value=f"{recent_searches_count:,}",
            subtitle="Research history",
            color="#475569",
        )

    with col4:
        render_metric_card(
            title="Cache Records",
            value=f"{cached_queries_count:,}",
            subtitle="24h TTL replay",
            color="#7c3aed",
        )


def render_copy_box(keywords: List[str], label: str = "Keywords") -> None:
    """Render a copy-friendly text box containing formatted keywords."""
    if not keywords:
        st.info("No keywords available to copy.")
        return

    text_content = "\n".join(keywords)
    st.markdown(f"**📋 Copy {label} ({len(keywords)} items):**")
    st.text_area(
        label=f"Copy {label}",
        value=text_content,
        height=min(220, max(80, len(keywords) * 22)),
        label_visibility="collapsed",
        help="Click inside and press Ctrl+A, then Ctrl+C to copy all keywords to your clipboard.",
    )
    st.caption("💡 *Tip: Click inside the box, press **Ctrl+A** to select all, then **Ctrl+C** to copy.*")


def render_channel_switcher() -> int:
    """Render a compact 4-channel workspace switcher in the UI and return the active channel ID."""
    from src.intelligence.channel_manager import channel_manager
    channels = channel_manager.get_all_channels()
    
    current_chan_id = int(st.session_state.get("active_channel_id", 1))
    
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; padding: 0.4rem 0.75rem; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;">
            <div style="font-size: 0.8rem; font-weight: 700; color: #1E293B; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 0.4rem;">
                <span>📺</span> ACTIVE CHANNEL WORKSPACE
            </div>
            <div style="font-size: 0.75rem; color: #64748B;">
                Independent Niches, Exclusions, SEO Settings & Reports
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    cols = st.columns(4)
    for idx, chan in enumerate(channels[:4]):
        c_id = chan.id or (idx + 1)
        is_active = (c_id == current_chan_id)
        with cols[idx]:
            btn_label = f"{'★ ' if is_active else ''}Ch {c_id}: {chan.channel_name[:15]}"
            btn_type = "primary" if is_active else "secondary"
            if st.button(btn_label, key=f"chan_switch_top_btn_{c_id}", type=btn_type, use_container_width=True):
                st.session_state["active_channel_id"] = c_id
                st.rerun()
                
    return int(st.session_state.get("active_channel_id", 1))


