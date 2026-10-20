"""Settings & System Status — Simplified Core Configuration.

Provides a clean, quiet interface to:
- Check API key configuration status (YouTube Data API v3, AI providers)
- Test YouTube Data API key with instant verification feedback
- Save or remove API keys safely
- Inspect SQLite database health and run 1-click online backups
"""

from __future__ import annotations

import os
from pathlib import Path
import streamlit as st

from src.config import APP_VERSION, config
from src.providers.serp import YouTubeDataApiSerpProvider
from src.storage.database import db_manager


def render_settings_tool() -> None:
    """Render the simplified Settings & System Status view."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                ⚙️ Settings & Data Sources
            </h2>
            <p style="font-size: 0.95rem; color: #64748B; margin: 0;">
                Configure optional API connections, check data provider status, and create local database backups.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Resolve active API key
    stored_key = db_manager.get_setting("youtube_api_key") or os.getenv("YOUTUBE_API_KEY") or ""
    has_yt_key = bool(stored_key and len(stored_key.strip()) > 5)

    # Resolve AI key
    ai_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or db_manager.get_setting("gemini_api_key") or db_manager.get_setting("openai_api_key") or ""
    has_ai_key = bool(ai_key and len(ai_key.strip()) > 5)

    # Top Status Indicators
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Autocomplete</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #10B981; margin-top: 4px;">🟢 Active & Free</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">No API key needed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        yt_color = "#10B981" if has_yt_key else "#F59E0B"
        yt_status = "🟢 Configured" if has_yt_key else "🟡 Missing (Optional)"
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">YouTube Data API</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: {yt_color}; margin-top: 4px;">{yt_status}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">Competitor video data</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        ai_color = "#10B981" if has_ai_key else "#64748B"
        ai_status = "🟢 Configured" if has_ai_key else "⚪ Offline / Deterministic"
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">AI Enhancement</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: {ai_color}; margin-top: 4px;">{ai_status}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">Rule-based fallback active</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        db_stats = db_manager.get_database_stats() if hasattr(db_manager, "get_database_stats") else {}
        db_size_kb = db_stats.get("file_size_kb", 0)
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; text-align: center;">
                <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">SQLite Storage</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #2563EB; margin-top: 4px;">🟢 Healthy ({db_size_kb:,} KB)</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">WAL mode &middot; Local disk</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.write("")

    # --- Section 1: YouTube Data API v3 Configuration ---
    st.markdown("### 🔑 YouTube Data API v3 Configuration")
    st.markdown(
        """
        The **YouTube Data API v3** enables live competitor video analysis (video titles, publish dates, and public view counts).
        Google provides a free tier of **10,000 units/day**, which is more than enough for regular keyword research.
        """
    )

    col_key_input, col_key_btns = st.columns([3, 2])
    with col_key_input:
        api_key_input = st.text_input(
            "YouTube API Key",
            value=stored_key,
            type="password",
            placeholder="AIzaSy...",
            help="Get a free key from Google Cloud Console > APIs & Services > Credentials.",
            key="settings_yt_api_key_input",
        )

    with col_key_btns:
        st.write("")
        st.write("")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            save_clicked = st.button("💾 Save Key", type="primary", use_container_width=True, key="settings_save_key_btn")
        with btn_c2:
            test_clicked = st.button("🧪 Test Key", use_container_width=True, key="settings_test_key_btn")

    if save_clicked:
        clean_key = api_key_input.strip()
        if clean_key:
            db_manager.set_setting("youtube_api_key", clean_key)
            os.environ["YOUTUBE_API_KEY"] = clean_key
            st.success("✅ YouTube API key saved successfully!")
            st.rerun()
        else:
            db_manager.set_setting("youtube_api_key", "")
            if "YOUTUBE_API_KEY" in os.environ:
                del os.environ["YOUTUBE_API_KEY"]
            st.info("ℹ️ API key cleared.")
            st.rerun()

    if test_clicked:
        test_target_key = api_key_input.strip() or stored_key
        if not test_target_key:
            st.warning("⚠️ Please enter an API key above to test.")
        else:
            with st.spinner("Verifying API key with YouTube Data API v3..."):
                serp_provider = YouTubeDataApiSerpProvider()
                is_valid, msg = serp_provider.verify_api_key(test_target_key)
                if is_valid:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    st.markdown("---")

    # --- Section 2: SQLite Database & Backups ---
    st.markdown("### 💾 Local SQLite Database & Safe Backups")
    st.markdown(
        """
        Keyword Studio stores all saved research, channel profiles, and logs locally on your machine in SQLite WAL mode.
        Your data never leaves your computer.
        """
    )

    db_col1, db_col2 = st.columns([3, 2])
    with db_col1:
        st.markdown(
            f"""
            - **Database Path:** `{config.database_path}`
            - **App Version:** `v{APP_VERSION}`
            - **Schema Version:** `v{db_stats.get('schema_version', 1)}`
            - **Journal Mode:** `WAL (Write-Ahead Logging)`
            - **File Size:** `{db_size_kb:,} KB`
            """
        )

    with db_col2:
        st.write("")
        backup_clicked = st.button("🛡️ Create Verified Backup Now", type="primary", use_container_width=True, key="settings_manual_backup_btn")
        if backup_clicked:
            with st.spinner("Creating safe SQLite online backup..."):
                try:
                    from scripts.backup_data import backup_database
                    backup_path = backup_database(note="Manual backup from Settings")
                    st.success(f"✅ Backup created successfully!\n\n**File:** `{backup_path.name}`")
                except Exception as ex:
                    st.error(f"❌ Backup failed: {str(ex)}")

    st.markdown("---")

    # --- Section 3: Privacy & Architecture Guarantee ---
    st.markdown("### 🔒 Privacy & Architecture Notice")
    st.markdown(
        """
        - **Zero Tracking:** No analytics scripts, no tracking pixels, and no telemetry data sent to third parties.
        - **Local Only:** All searches and generated titles remain on your local disk in SQLite.
        - **Public Data Only:** Only publicly viewable YouTube data is ever accessed.
        """
    )
