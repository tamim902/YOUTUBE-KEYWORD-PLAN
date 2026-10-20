"""Streamlit UI styling definitions, Apple-inspired White Motion Design system.

Features:
- Apple-inspired typography: San Francisco font stack (-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI").
- Premium White design palette: #FFFFFF canvas, #F8FAFC secondary, #111827 text, #E5E7EB borders, #2563EB primary accent.
- Hardware-accelerated GPU micro-animations (transform, opacity) with cubic-bezier timing (120ms - 280ms).
- Interactive cursor & pointer feedback: subtle card elevations, button active pressed state, focus rings.
- Touch-device safe: hover transforms disabled on touch screens via pointer: coarse media queries.
- Strict prefers-reduced-motion accessibility compliance: zero animation flicker when motion reduction is requested.
- Responsive breakpoints for mobile (320px–480px), tablet (481px–1024px), desktop (1440px), and widescreen (1920px+).
- Unmistakable demo data separation pills and contextual guide callout styling.
"""

CUSTOM_CSS = """
<style>
    /* =========================================================================
       1. Global Theme, Font Stack & Layout Reset (Apple-Inspired White Theme)
       ========================================================================= */
    :root {
        --bg-canvas: #FFFFFF;
        --bg-secondary: #F8FAFC;
        --bg-surface: #FFFFFF;
        --bg-surface-elevated: #FFFFFF;
        --bg-surface-subtle: #F1F5F9;
        --text-primary: #111827;
        --text-secondary: #374151;
        --text-muted: #64748B;
        --border-subtle: #E5E7EB;
        --border-highlight: #2563EB;
        --border-card: #E2E8F0;
        --brand-primary: #2563EB;
        --brand-indigo: #4F46E5;
        --brand-violet: #7C3AED;
        --accent-emerald: #15803D;
        --accent-amber: #B45309;
        --accent-rose: #B91C1C;
        --font-stack: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Ambient background glow on crisp white canvas */
    .stApp {
        background-color: var(--bg-canvas);
        background-image:
            radial-gradient(1200px 600px at 50% -120px, rgba(37, 99, 235, 0.04), transparent 70%),
            radial-gradient(900px 450px at 85% 15%, rgba(124, 58, 237, 0.03), transparent 60%);
        background-attachment: fixed;
        color: var(--text-primary);
        font-family: var(--font-stack);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Main container clean Apple-like spacing */
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 3rem;
        max-width: 1440px;
    }

    /* =========================================================================
       1B. Apple-Inspired SaaS Sidebar & Navigation System
       ========================================================================= */
    [data-testid="stSidebar"] {
        background-color: #FAFAFA !important;
        border-right: 1px solid #E2E8F0 !important;
        box-shadow: 1px 0 4px rgba(0, 0, 0, 0.02) !important;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 1rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
    }

    /* Brand Header Container */
    .ks-sidebar-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.35rem 0.25rem 0.65rem 0.25rem;
    }

    .ks-brand-badge {
        width: 32px;
        height: 32px;
        border-radius: 9px;
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
        flex-shrink: 0;
    }

    .ks-brand-icon {
        width: 17px;
        height: 17px;
    }

    .ks-brand-info {
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .ks-brand-title {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 14.5px;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .ks-pro-tag {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 9.5px;
        font-weight: 700;
        letter-spacing: 0.06em;
        padding: 2px 6px;
        border-radius: 5px;
        background: #EEF2FF;
        color: #4F46E5;
        border: 1px solid #E0E7FF;
        text-transform: uppercase;
        margin-left: auto;
    }

    .ks-sidebar-divider {
        height: 1px;
        background: #E2E8F0;
        margin: 0.15rem 0 0.75rem 0;
    }

    /* Streamlit Radio Overhaul into SaaS Navigation Items */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        display: none !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
        width: 100% !important;
    }

    /* Hide standard radio bullet circle */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-of-type {
        display: none !important;
    }

    /* Nav Item Pill Container */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        padding: 7px 10px !important;
        margin: 0 !important;
        border-radius: 8px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-left: 3px solid transparent !important;
        cursor: pointer !important;
        transition: background-color 160ms cubic-bezier(0.16, 1, 0.3, 1),
                    border-color 160ms cubic-bezier(0.16, 1, 0.3, 1),
                    box-shadow 160ms cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-sizing: border-box !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background-color: #F1F5F9 !important;
        border-color: #E2E8F0 !important;
        border-left-color: #CBD5E1 !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:focus-within {
        outline: 2px solid #93C5FD !important;
        outline-offset: 1px !important;
    }

    /* Active Nav Item State */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background-color: #EFF6FF !important;
        border-color: #DBEAFE !important;
        border-left: 3px solid #2563EB !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.05) !important;
    }

    /* Nav Item Typography */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #475569 !important;
        margin: 0 !important;
        line-height: 1.35 !important;
        display: flex !important;
        align-items: center !important;
        gap: 9px !important;
        transition: color 160ms ease !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover [data-testid="stMarkdownContainer"] p {
        color: #0F172A !important;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p {
        color: #1D4ED8 !important;
        font-weight: 600 !important;
    }

    /* Section Groups Header Injection (Scoped to Main Full Navigation) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(1),
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(5),
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(10),
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(13) {
        position: relative !important;
    }

    /* Group 1: WORKSPACE (above item 1) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(1) {
        margin-top: 20px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(1)::before {
        content: "WORKSPACE";
        position: absolute;
        top: -18px;
        left: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #94A3B8;
        text-transform: uppercase;
        pointer-events: none;
    }

    /* Group 2: DISCOVERY & INTELLIGENCE (above item 5) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(5) {
        margin-top: 28px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(5)::before {
        content: "DISCOVERY & INTELLIGENCE";
        position: absolute;
        top: -18px;
        left: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #94A3B8;
        text-transform: uppercase;
        pointer-events: none;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(5)::after {
        content: "";
        position: absolute;
        top: -24px;
        left: 4px;
        right: 4px;
        height: 1px;
        background-color: #E2E8F0;
        pointer-events: none;
    }

    /* Group 3: WORKFLOW & MANAGEMENT (above item 10) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(10) {
        margin-top: 28px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(10)::before {
        content: "WORKFLOW & MANAGEMENT";
        position: absolute;
        top: -18px;
        left: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #94A3B8;
        text-transform: uppercase;
        pointer-events: none;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(10)::after {
        content: "";
        position: absolute;
        top: -24px;
        left: 4px;
        right: 4px;
        height: 1px;
        background-color: #E2E8F0;
        pointer-events: none;
    }

    /* Group 4: STUDIO & CONFIGURATION (above item 13) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(13) {
        margin-top: 28px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(13)::before {
        content: "STUDIO & CONFIGURATION";
        position: absolute;
        top: -18px;
        left: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #94A3B8;
        text-transform: uppercase;
        pointer-events: none;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"][aria-label="Go to page"] > label:nth-of-type(13)::after {
        content: "";
        position: absolute;
        top: -24px;
        left: 4px;
        right: 4px;
        height: 1px;
        background-color: #E2E8F0;
        pointer-events: none;
    }

    /* Lucide Vector SVG Mask System (16px icon grid, consistent 2px stroke) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"] p::before {
        content: "";
        display: inline-block;
        width: 16px;
        height: 16px;
        flex-shrink: 0;
        background-color: #64748B;
        -webkit-mask-size: contain;
        mask-size: contain;
        -webkit-mask-repeat: no-repeat;
        mask-repeat: no-repeat;
        -webkit-mask-position: center;
        mask-position: center;
        transition: background-color 160ms ease;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:hover p::before {
        background-color: #0F172A;
    }

    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p::before {
        background-color: #2563EB !important;
    }

    /* Item 1: Sparkles (Overview & Showcase) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Overview"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(1) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/%3E%3Cpath d='M5 3v4'/%3E%3Cpath d='M19 17v4'/%3E%3Cpath d='M3 5h4'/%3E%3Cpath d='M17 19h4'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/%3E%3Cpath d='M5 3v4'/%3E%3Cpath d='M19 17v4'/%3E%3Cpath d='M3 5h4'/%3E%3Cpath d='M17 19h4'/%3E%3C/svg%3E");
    }

    /* Item 2: LayoutDashboard (Dashboard) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Dashboard"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(2) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E");
    }

    /* Item 3: Search (New Keyword Research) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="New Keyword"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(3) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.3-4.3'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cpath d='m21 21-4.3-4.3'/%3E%3C/svg%3E");
    }

    /* Item 4: ListTree (Keyword Results) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Keyword Results"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(4) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12h-8'/%3E%3Cpath d='M21 6H8'/%3E%3Cpath d='M21 18h-8'/%3E%3Cpath d='M3 6v4c0 1.1.9 2 2 2h3'/%3E%3Cpath d='M3 10v6c0 1.1.9 2 2 2h3'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12h-8'/%3E%3Cpath d='M21 6H8'/%3E%3Cpath d='M21 18h-8'/%3E%3Cpath d='M3 6v4c0 1.1.9 2 2 2h3'/%3E%3Cpath d='M3 10v6c0 1.1.9 2 2 2h3'/%3E%3C/svg%3E");
    }

    /* Item 5: Puzzle (Pattern Generator) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Pattern"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(5) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19.439 7.85c0 0-1.439 2.15-1.439 4.15 0 2.21 1.79 4 4 4v2.5a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2 2 2 0 0 0-4 0 2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3a2 2 0 0 0-2-2 2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2 2 2 0 0 0 2-2 2 2 0 0 1 2-2h3a2 2 0 0 1 2 2 2 2 0 0 0 4 0 2 2 0 0 1 2-2h2.5a2 2 0 0 1 2 2v1.5'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19.439 7.85c0 0-1.439 2.15-1.439 4.15 0 2.21 1.79 4 4 4v2.5a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2 2 2 0 0 0-4 0 2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3a2 2 0 0 0-2-2 2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2 2 2 0 0 0 2-2 2 2 0 0 1 2-2h3a2 2 0 0 1 2 2 2 2 0 0 0 4 0 2 2 0 0 1 2-2h2.5a2 2 0 0 1 2 2v1.5'/%3E%3C/svg%3E");
    }

    /* Item 6: Video (YouTube Video Research) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="YouTube Video"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(6) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.934a.5.5 0 0 0-.777-.416L16 11'/%3E%3Crect width='14' height='12' x='2' y='6' rx='2'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.934a.5.5 0 0 0-.777-.416L16 11'/%3E%3Crect width='14' height='12' x='2' y='6' rx='2'/%3E%3C/svg%3E");
    }

    /* Item 7: Lightbulb (Content Opportunities) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Content Opportunities"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(7) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5'/%3E%3Cpath d='M9 18h6'/%3E%3Cpath d='M10 22h4'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5'/%3E%3Cpath d='M9 18h6'/%3E%3Cpath d='M10 22h4'/%3E%3C/svg%3E");
    }

    /* Item 8: PackageSearch (Niche Product Opportunity Finder) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Niche Product"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(8) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l2-1.14'/%3E%3Cpath d='m7.5 4.27 9 5.15'/%3E%3Cpolyline points='3.29 7 12 12 20.71 7'/%3E%3Cline x1='12' x2='12' y1='22' y2='12'/%3E%3Ccircle cx='18.5' cy='15.5' r='2.5'/%3E%3Cpath d='M20.27 17.27 22 19'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l2-1.14'/%3E%3Cpath d='m7.5 4.27 9 5.15'/%3E%3Cpolyline points='3.29 7 12 12 20.71 7'/%3E%3Cline x1='12' x2='12' y1='22' y2='12'/%3E%3Ccircle cx='18.5' cy='15.5' r='2.5'/%3E%3Cpath d='M20.27 17.27 22 19'/%3E%3C/svg%3E");
    }

    /* Item 9: Tag (Product Opportunity Planner) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Product Opportunity Planner"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(9) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z'/%3E%3Ccircle cx='7.5' cy='7.5' r='.5' fill='black'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z'/%3E%3Ccircle cx='7.5' cy='7.5' r='.5' fill='black'/%3E%3C/svg%3E");
    }

    /* Item 10: Radio (Research Monitor) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Research Monitor"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(10) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4.9 19.1C1 15.2 1 8.8 4.9 4.9'/%3E%3Cpath d='M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5'/%3E%3Ccircle cx='12' cy='12' r='2'/%3E%3Cpath d='M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5'/%3E%3Cpath d='M19.1 4.9C23 8.8 23 15.1 19.1 19'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4.9 19.1C1 15.2 1 8.8 4.9 4.9'/%3E%3Cpath d='M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5'/%3E%3Ccircle cx='12' cy='12' r='2'/%3E%3Cpath d='M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5'/%3E%3Cpath d='M19.1 4.9C23 8.8 23 15.1 19.1 19'/%3E%3C/svg%3E");
    }

    /* Item 11: Bookmark (Saved Research) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Saved Research"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(11) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z'/%3E%3C/svg%3E");
    }

    /* Item 12: BookOpen (User Guide) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="User Guide"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(12) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/%3E%3Cpath d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/%3E%3Cpath d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/%3E%3C/svg%3E");
    }

    /* Item 13: ShieldCheck (Studio Profile & Auth) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Studio Profile"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(13) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/%3E%3Cpath d='m9 12 2 2 4-4'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'/%3E%3Cpath d='m9 12 2 2 4-4'/%3E%3C/svg%3E");
    }

    /* Item 14: Sliders (Settings & Data Sources) */
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input[value*="Settings & Data"]) p::before,
    [data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:nth-of-type(14) p::before {
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='4' x2='4' y1='21' y2='14'/%3E%3Cline x1='4' x2='4' y1='10' y2='3'/%3E%3Cline x1='12' x2='12' y1='21' y2='12'/%3E%3Cline x1='12' x2='12' y1='8' y2='3'/%3E%3Cline x1='20' x2='20' y1='21' y2='16'/%3E%3Cline x1='20' x2='20' y1='12' y2='3'/%3E%3Cline x1='1' x2='7' y1='14' y2='14'/%3E%3Cline x1='9' x2='15' y1='8' y2='8'/%3E%3Cline x1='17' x2='23' y1='16' y2='16'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='4' x2='4' y1='21' y2='14'/%3E%3Cline x1='4' x2='4' y1='10' y2='3'/%3E%3Cline x1='12' x2='12' y1='21' y2='12'/%3E%3Cline x1='12' x2='12' y1='8' y2='3'/%3E%3Cline x1='20' x2='20' y1='21' y2='16'/%3E%3Cline x1='20' x2='20' y1='12' y2='3'/%3E%3Cline x1='1' x2='7' y1='14' y2='14'/%3E%3Cline x1='9' x2='15' y1='8' y2='8'/%3E%3Cline x1='17' x2='23' y1='16' y2='16'/%3E%3C/svg%3E");
    }

    /* Bottom Workspace Status Card (Apple White Card Styling) */
    .sidebar-workspace-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 12px;
        margin-top: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        transition: border-color 160ms ease, box-shadow 160ms ease;
    }

    .sidebar-workspace-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    }

    .workspace-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }

    .workspace-avatar {
        width: 28px;
        height: 28px;
        border-radius: 7px;
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        letter-spacing: -0.02em;
        flex-shrink: 0;
    }

    .workspace-info {
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    .workspace-name {
        font-size: 12.5px;
        font-weight: 600;
        color: #0F172A;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }

    .workspace-role {
        font-size: 10.5px;
        color: #64748B;
        line-height: 1.2;
    }

    .workspace-status-badge {
        margin-left: auto;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        font-weight: 600;
        color: #15803D;
        background: #F0FDF4;
        border: 1px solid #DCFCE7;
        padding: 2px 6px;
        border-radius: 9999px;
        white-space: nowrap;
    }

    .status-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background-color: #22C55E;
    }

    .workspace-details {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding-top: 8px;
        border-top: 1px solid #F1F5F9;
        font-size: 11px;
    }

    .workspace-detail-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .detail-label {
        color: #64748B;
    }

    .detail-value {
        color: #1E293B;
        font-weight: 500;
    }

    /* Sidebar profile navigation button */
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        color: #475569 !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 11.5px !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        transition: all 160ms cubic-bezier(0.16, 1, 0.3, 1) !important;
        margin-top: 8px !important;
        width: 100% !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }

    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    }

    /* =========================================================================
       1C. Phase 18: Command-Style Search, Compact Mode & Refined Interaction Tokens
       ========================================================================= */
    :root {
        --ks-sidebar-bg: #FAFAFA;
        --ks-nav-pill-active: #EFF6FF;
        --ks-nav-pill-hover: #F1F5F9;
        --ks-nav-border-active: #2563EB;
        --ks-nav-text-active: #1D4ED8;
        --ks-nav-text-muted: #475569;
        --ks-nav-icon-inactive: #64748B;
        --ks-nav-icon-hover: #0F172A;
        --ks-nav-icon-active: #2563EB;
        --ks-nav-radius: 8px;
        --ks-nav-transition: 160ms cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Command-Style Navigation Search Input */
    [data-testid="stSidebar"] div[data-testid="stTextInput"] {
        margin-bottom: 6px !important;
    }

    [data-testid="stSidebar"] div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 12.5px !important;
        color: #1E293B !important;
        padding: 6px 10px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        transition: border-color 160ms ease, box-shadow 160ms ease !important;
    }

    [data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
        outline: none !important;
    }

    /* Search Results Label */
    .nav-search-results-label {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #2563EB;
        text-transform: uppercase;
        padding: 6px 4px 4px 4px;
        margin-bottom: 2px;
    }

    /* Empty Navigation Search State */
    .nav-empty-state {
        background: #FFFFFF;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 14px 10px;
        text-align: center;
        margin: 6px 0 10px 0;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }

    /* Compact View Toggle Switch */
    [data-testid="stSidebar"] div[data-testid="stToggle"] {
        padding: 0 4px !important;
        margin-bottom: 4px !important;
    }

    [data-testid="stSidebar"] div[data-testid="stToggle"] label p {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 11px !important;
        color: #64748B !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }

    /* Smooth focus rings for accessibility */
    *:focus-visible {
        outline: 2px solid var(--brand-primary) !important;
        outline-offset: 2px !important;
    }

    /* Custom subtle Apple-style scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #F1F5F9;
    }
    ::-webkit-scrollbar-thumb {
        background: #CBD5E1;
        border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #94A3B8;
    }

    /* =========================================================================
       2. Keyframes & GPU-Accelerated Micro-Animations
       ========================================================================= */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes fadeInScale {
        from {
            opacity: 0;
            transform: scale(0.98);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes pulseGlow {
        0%, 100% {
            opacity: 1;
            transform: scale(1);
        }
        50% {
            opacity: 0.6;
            transform: scale(0.92);
        }
    }

    .animate-fade-in {
        animation: fadeInUp 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    .animate-scale-in {
        animation: fadeInScale 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* =========================================================================
       3. Status Badges, Pills & Demo Labels
       ========================================================================= */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 600;
        border-radius: 9999px;
        background-color: rgba(37, 99, 235, 0.08);
        color: #1D4ED8;
        border: 1px solid rgba(37, 99, 235, 0.22);
        letter-spacing: 0.015em;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }

    .badge-success {
        background-color: rgba(21, 128, 61, 0.08);
        color: #15803D;
        border: 1px solid rgba(21, 128, 61, 0.22);
    }

    .badge-warning {
        background-color: rgba(180, 83, 9, 0.08);
        color: #B45309;
        border: 1px solid rgba(180, 83, 9, 0.25);
    }

    .badge-danger {
        background-color: rgba(185, 28, 28, 0.08);
        color: #B91C1C;
        border: 1px solid rgba(185, 28, 28, 0.25);
    }

    .badge-neutral {
        background-color: rgba(100, 116, 139, 0.08);
        color: #475569;
        border: 1px solid rgba(100, 116, 139, 0.2);
    }

    /* Unmistakable Demo Data Pill */
    .demo-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.85rem;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 6px;
        background: rgba(180, 83, 9, 0.08);
        color: #B45309;
        border: 1px dashed rgba(180, 83, 9, 0.45);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .dot-live {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--accent-emerald);
        box-shadow: 0 0 6px rgba(21, 128, 61, 0.5);
        animation: pulseGlow 2s infinite ease-in-out;
    }

    .dot-demo {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--accent-amber);
        box-shadow: 0 0 5px rgba(180, 83, 9, 0.4);
    }

    /* =========================================================================
       4. Apple-Inspired Hero & Showcase Components
       ========================================================================= */
    .premium-hero {
        text-align: center;
        padding: 3.5rem 1.75rem 2.75rem 1.75rem;
        margin-bottom: 2rem;
        border-radius: 20px;
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid var(--border-subtle);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.06), 0 1px 3px 0 rgba(0, 0, 0, 0.02);
        position: relative;
        overflow: hidden;
    }

    .hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 1.15rem;
        border-radius: 9999px;
        background: rgba(37, 99, 235, 0.08);
        border: 1px solid rgba(37, 99, 235, 0.22);
        color: #1D4ED8;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        margin-bottom: 1.25rem;
    }

    .hero-title {
        font-size: clamp(2.1rem, 5vw, 3.5rem);
        font-weight: 800;
        line-height: 1.12;
        color: #111827;
        letter-spacing: -0.035em;
        margin: 0 auto 1.25rem auto;
        max-width: 920px;
    }

    .hero-gradient-text {
        background: linear-gradient(135deg, #111827 30%, #2563EB 85%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        font-size: clamp(1.05rem, 2vw, 1.25rem);
        color: var(--text-muted);
        line-height: 1.6;
        max-width: 780px;
        margin: 0 auto 2.25rem auto;
        font-weight: 400;
    }

    .hero-pillars-row {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 1.5rem;
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid #F1F5F9;
    }

    .hero-pillar-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-weight: 500;
    }

    /* Showcase & SaaS Card Containers */
    .showcase-card,
    .saas-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.65rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.03);
        margin-bottom: 1.5rem;
        transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .showcase-card:hover,
    .saas-card:hover {
        transform: translateY(-2px);
        border-color: #CBD5E1;
        box-shadow: 0 12px 24px -4px rgba(37, 99, 235, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
    }

    .feature-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.35rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .feature-card:hover {
        transform: translateY(-3px);
        border-color: #93C5FD;
        box-shadow: 0 10px 20px -3px rgba(37, 99, 235, 0.08);
    }

    .feature-icon-box {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: rgba(37, 99, 235, 0.08);
        border: 1px solid rgba(37, 99, 235, 0.18);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
        margin-bottom: 1rem;
    }

    /* =========================================================================
       5. Refined Metric Cards, Data Surfaces & Smart Guide Cards
       ========================================================================= */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.02);
        transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease, box-shadow 0.18s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #2563EB, #7C3AED);
        opacity: 0.85;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #93C5FD;
        box-shadow: 0 8px 20px -3px rgba(37, 99, 235, 0.09);
    }

    .metric-card h4 {
        margin: 0;
        font-size: 0.78rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }

    .metric-card p {
        margin: 0.4rem 0 0 0;
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: -0.025em;
    }

    /* Smart User Guide & Contextual Callouts */
    .guide-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-left: 4px solid var(--brand-primary);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }

    .guide-callout-best {
        background: rgba(37, 99, 235, 0.04);
        border: 1px solid rgba(37, 99, 235, 0.2);
        border-radius: 10px;
        padding: 0.95rem 1.25rem;
        margin: 0.75rem 0;
    }

    .guide-step-box {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        padding: 0.85rem 0;
        border-bottom: 1px solid #F1F5F9;
    }

    .guide-step-badge {
        flex-shrink: 0;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--brand-primary);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.82rem;
        font-weight: 700;
    }

    /* Smart Workflow Assistant Box */
    .workflow-assistant-card {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.03) 0%, rgba(124, 58, 237, 0.03) 100%);
        border: 1px solid rgba(37, 99, 235, 0.25);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }

    /* Phase 17: Interactive Tour Callout Card */
    .tour-callout-card {
        background: #FFFFFF;
        border: 1px solid #BFDBFE;
        border-top: 3px solid #2563EB;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 14px -2px rgba(37, 99, 235, 0.08);
        animation: fadeInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Phase 17: Goal Selector Cards for 7-Goal Onboarding */
    .goal-card {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.15rem;
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .goal-card:hover {
        transform: translateY(-2px);
        border-color: #93C5FD;
        box-shadow: 0 6px 16px -2px rgba(37, 99, 235, 0.08);
    }

    /* Phase 17: Smart Workflow Progress Checklist */
    .workflow-checklist-container {
        background: #FFFFFF;
        border: 1px solid var(--border-subtle);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    .checklist-progress-bg {
        width: 100%;
        height: 8px;
        background: #F1F5F9;
        border-radius: 9999px;
        overflow: hidden;
        margin: 0.75rem 0 1rem 0;
    }

    .checklist-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #2563EB, #10B981);
        border-radius: 9999px;
        transition: width 0.4s ease;
    }

    .checklist-step-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.65rem 0.5rem;
        border-bottom: 1px solid #F8FAFC;
        font-size: 0.86rem;
    }

    .checklist-step-row:last-child {
        border-bottom: none;
    }

    /* Action bar container */
    .action-bar {
        background-color: #F8FAFC;
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 0.85rem 1.15rem;
        margin: 1rem 0;
    }

    /* Copy box */
    .copy-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.85rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.85rem;
        color: #1E293B;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 220px;
        overflow-y: auto;
    }

    /* Auth card container */
    .auth-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 2rem;
        max-width: 650px;
        margin: 1.5rem auto;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
    }

    /* Footer text */
    .footer-text {
        color: var(--text-muted);
        font-size: 0.82rem;
        text-align: center;
        margin-top: 3.5rem;
        border-top: 1px solid #E5E7EB;
        padding-top: 1.5rem;
        line-height: 1.6;
    }

    /* Streamlit interactive button enhancements */
    button[kind="primary"] {
        background-color: var(--brand-primary) !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    }
    button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
    }
    button[kind="primary"]:active {
        transform: scale(0.985) !important;
    }

    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        transition: transform 0.12s ease, border-color 0.12s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: #94A3B8 !important;
        background-color: #F8FAFC !important;
        transform: translateY(-1px) !important;
    }
    button[kind="secondary"]:active {
        transform: scale(0.985) !important;
    }

    /* =========================================================================
       6. Responsive Breakpoint Optimizations (320px, 480px, 768px, 1024px, 1440px, 1920px)
       ========================================================================= */
    /* Mobile & Compact Screens (320px - 480px) */
    @media (max-width: 480px) {
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        .premium-hero {
            padding: 2rem 1rem 1.5rem 1rem;
        }
        .hero-title {
            font-size: 1.85rem;
        }
        .hero-pillars-row {
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
        }
        .metric-card p {
            font-size: 1.4rem;
        }
    }

    /* Tablet & Handheld (481px - 768px) */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2.15rem;
        }
        .hero-subtitle {
            font-size: 0.95rem;
        }
    }

    /* Tablet Medium / Laptop (769px - 1024px) */
    @media screen and (min-width: 769px) and (max-width: 1024px) {
        .hero-title {
            font-size: 2.5rem;
        }
    }

    /* Desktop Standard & Large (1440px+) */
    @media (min-width: 1440px) {
        .block-container {
            max-width: 1380px;
        }
    }

    /* Desktop Ultra-Wide (1920px+) */
    @media screen and (min-width: 1920px) {
        .block-container {
            max-width: 1560px;
        }
    }

    /* Touch screen hover suppression to prevent mobile stuck-hover */
    @media (hover: none) and (pointer: coarse) {
        .metric-card:hover,
        .feature-card:hover,
        .showcase-card:hover,
        .saas-card:hover {
            transform: none !important;
            box-shadow: none !important;
        }
    }

    /* =========================================================================
       8. Phase 20: Unified Premium SaaS Design System Components
       ========================================================================= */
    :root {
        --ks-canvas: #FFFFFF;
        --ks-surface: #F8FAFC;
        --ks-surface-card: #FFFFFF;
        --ks-text-primary: #0F172A;
        --ks-text-secondary: #475569;
        --ks-text-muted: #64748B;
        --ks-border: #E2E8F0;
        --ks-border-light: #F1F5F9;
        --ks-accent-blue: #2563EB;
        --ks-accent-indigo: #4F46E5;
        --ks-accent-violet: #7C3AED;
        --ks-card-radius: 12px;
        --ks-badge-radius: 9999px;
        --ks-transition-fast: 160ms cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Standardized SaaS Page Header Component */
    .ks-page-header {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        padding: 0.25rem 0 1.15rem 0;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid #E2E8F0;
        position: relative;
    }

    .ks-breadcrumb {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #64748B;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-bottom: 0.2rem;
    }

    .ks-breadcrumb .ks-crumb-sep {
        color: #CBD5E1;
        font-weight: 400;
    }

    .ks-breadcrumb .ks-crumb-active {
        color: #2563EB;
    }

    .ks-header-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .ks-page-title-group {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .ks-page-title {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 1.55rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.025em;
        margin: 0;
        line-height: 1.25;
    }

    .ks-page-subtitle {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.45;
        margin: 0.15rem 0 0 0;
        max-width: 900px;
    }

    .ks-header-badges {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    /* Standardized Card & Content Surfaces (.ks-card) */
    .ks-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.35rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: transform 160ms cubic-bezier(0.16, 1, 0.3, 1),
                    border-color 160ms ease,
                    box-shadow 160ms ease;
    }

    .ks-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.06);
    }

    .ks-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.85rem;
        padding-bottom: 0.65rem;
        border-bottom: 1px solid #F1F5F9;
    }

    .ks-card-title {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.96rem;
        font-weight: 600;
        color: #0F172A;
        letter-spacing: -0.01em;
        margin: 0;
    }

    .ks-card-subtitle {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.8rem;
        color: #64748B;
        margin: 0;
    }

    .ks-card-body {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.88rem;
        color: #334155;
        line-height: 1.5;
    }

    /* Standardized Badges & Provenance Indicators */
    .ks-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.22rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        letter-spacing: 0.015em;
        line-height: 1.2;
        white-space: nowrap;
    }

    .ks-badge-primary {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #DBEAFE;
    }

    .ks-badge-success {
        background: #F0FDF4;
        color: #15803D;
        border: 1px solid #DCFCE7;
    }

    .ks-badge-warning {
        background: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
    }

    .ks-badge-error {
        background: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
    }

    .ks-badge-neutral {
        background: #F8FAFC;
        color: #475569;
        border: 1px solid #E2E8F0;
    }

    .ks-badge-provenance {
        background: #FAF5FF;
        color: #6B21A8;
        border: 1px solid #E9D5FF;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }

    .ks-badge-provenance .prov-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #9333EA;
    }

    .ks-badge-demo {
        background: #FFFBEB;
        color: #B45309;
        border: 1px dashed #F59E0B;
        text-transform: uppercase;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    /* Standardized Empty State Component (.ks-empty-state) */
    .ks-empty-state {
        background: #FFFFFF;
        border: 1px dashed #CBD5E1;
        border-radius: 14px;
        padding: 2.25rem 1.5rem;
        text-align: center;
        margin: 1.25rem 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .ks-empty-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #F8FAFC;
        color: #475569;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 0.85rem;
        border: 1px solid #E2E8F0;
    }

    .ks-empty-title {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.35rem;
    }

    .ks-empty-desc {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
        font-size: 0.85rem;
        color: #64748B;
        max-width: 480px;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    /* Streamlit Native Tabs, Expanders & Dataframe Polish */
    [data-baseweb="tab-list"] {
        gap: 4px !important;
        border-bottom: 1px solid #E2E8F0 !important;
        padding-bottom: 2px !important;
        background: transparent !important;
    }

    [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 16px !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 0.86rem !important;
        font-weight: 500 !important;
        color: #64748B !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        transition: all 160ms cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    [data-baseweb="tab"]:hover {
        color: #0F172A !important;
        background: #F8FAFC !important;
    }

    [data-baseweb="tab"][aria-selected="true"] {
        color: #2563EB !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #2563EB !important;
        background: #F8FAFC !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 0.75rem !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] summary {
        padding: 0.75rem 1rem !important;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #1E293B !important;
        border-radius: 10px !important;
        transition: background-color 150ms ease !important;
    }

    [data-testid="stExpander"] summary:hover {
        background-color: #F8FAFC !important;
        color: #2563EB !important;
    }

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        padding: 1rem 1.25rem !important;
        border-top: 1px solid #F1F5F9 !important;
    }

    /* =========================================================================
       7. Accessibility: Prefers Reduced Motion Safety
       ========================================================================= */
    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
        .dot-live {
            animation: none !important;
        }
    }
</style>
"""
