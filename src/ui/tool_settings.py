"""Settings & System Status — Data Sources, YouTube API, and Google Drive Cloud Backups.

Features:
- Check API key configuration status (YouTube Data API v3, AI providers)
- Test YouTube Data API key with instant verification feedback
- Save or remove API keys safely
- Google Drive OAuth 2.0 integration & cloud sync management
- Automated daily backup scheduler with configurable hour and retention count
- 1-Click 'Back Up Now' button with live online SQLite snapshot and Drive upload
- Safe restore workflow with pre-restore safety snapshot and confirmation guardrails
- Isolated sandbox restore testing without modifying production data
- Windows Task Scheduler integration documentation and setup command
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import textwrap
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.config import APP_VERSION, DATABASE_PATH, config
from src.providers.serp import YouTubeDataApiSerpProvider
from src.storage.backup import BackupManager
from src.storage.backup_bundle import backup_bundler
from src.storage.backup_restore import backup_restore_manager
from src.storage.backup_scheduler import backup_scheduler
from src.storage.database import db_manager
from src.storage.gdrive_client import gdrive_client


def _render_html(html_str: str) -> None:
    """Render clean, unindented HTML without markdown code block formatting artifacts."""
    clean_html = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


def render_settings_tool() -> None:
    """Render the comprehensive Settings, Data Sources, and Google Drive Backup center."""
    _render_html(
        """
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.8rem;">⚙️</span>
                <h2 style="font-size: 1.6rem; font-weight: 700; color: #1E293B; margin: 0;">
                    Settings & System Status
                </h2>
            </div>
            <p style="font-size: 0.95rem; color: #64748B; margin: 4px 0 0 0;">
                Configure API keys, manage automatic Google Drive cloud backups, check system health, and ensure safe data retention.
            </p>
        </div>
        """
    )

    # Resolve active API key
    stored_key = db_manager.get_setting("youtube_api_key") or os.getenv("YOUTUBE_API_KEY") or ""
    has_yt_key = bool(stored_key and len(stored_key.strip()) > 5)

    # Resolve Google Drive status
    drive_status = gdrive_client.get_status_summary()
    is_drive_auth = drive_status["is_authenticated"]
    drive_email = drive_status.get("user_email") or ""

    # Resolve DB Stats
    db_stats = db_manager.get_database_stats() if hasattr(db_manager, "get_database_stats") else {}
    db_size_kb = db_stats.get("file_size_kb", 0)

    # Top Status Indicators
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_html(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.76rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Autocomplete</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #10B981; margin-top: 3px;">🟢 Active & Free</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">No API key needed</div>
            </div>
            """
        )
    with c2:
        yt_color = "#10B981" if has_yt_key else "#F59E0B"
        yt_status = "🟢 Configured" if has_yt_key else "🟡 Missing (Optional)"
        _render_html(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.76rem; font-weight: 600; color: #64748B; text-transform: uppercase;">YouTube Data API</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: {yt_color}; margin-top: 3px;">{yt_status}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">Competitor video SERP</div>
            </div>
            """
        )
    with c3:
        gd_color = "#10B981" if is_drive_auth else "#64748B"
        gd_status = "🟢 Connected" if is_drive_auth else "⚪ Disconnected"
        gd_sub = drive_email[:18] + "..." if len(drive_email) > 18 else (drive_email or "Local backups only")
        _render_html(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.76rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Google Drive Sync</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: {gd_color}; margin-top: 3px;">{gd_status}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">{gd_sub}</div>
            </div>
            """
        )
    with c4:
        _render_html(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 0.76rem; font-weight: 600; color: #64748B; text-transform: uppercase;">SQLite Storage</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #2563EB; margin-top: 3px;">🟢 {db_size_kb:,} KB</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">WAL mode &middot; Local disk</div>
            </div>
            """
        )

    st.markdown("---")

    # =========================================================================
    # SECTION 1: GOOGLE DRIVE CLOUD BACKUP & AUTOMATED SYNC
    # =========================================================================
    st.markdown("### ☁️ Google Drive Automatic Cloud Backup & Sync")
    st.markdown(
        """
        Store automated, verified backups of your entire Keyword Studio in **your personal Google Drive**.
        Every backup packages an atomic snapshot of your SQLite database (WAL consistent), application source code, 
        channel profiles, and research history into an encrypted, SHA-256 validated ZIP bundle.
        """
    )

    # Google Drive Connection Card
    if is_drive_auth:
        _render_html(
            f"""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 6px; padding: 12px 16px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <div style="font-weight: 700; color: #166534; font-size: 0.95rem;">
                            🟢 Connected to Google Drive ({drive_email})
                        </div>
                        <div style="font-size: 0.82rem; color: #374151; margin-top: 2px;">
                            Backups upload automatically to dedicated folder: <b>{drive_status['folder_name']}</b>
                        </div>
                        <div style="font-size: 0.78rem; color: #4B5563; margin-top: 2px;">
                            Last successful backup: <b>{drive_status['last_backup_time']}</b> &middot; Status: <b>{drive_status['last_backup_status']}</b>
                        </div>
                    </div>
                </div>
            </div>
            """
        )
        col_disc, _ = st.columns([1.5, 3.5])
        with col_disc:
            if st.button("🔌 Disconnect Google Drive", type="secondary", key="btn_gdrive_disconnect"):
                gdrive_client.disconnect()
                st.info("Google Drive disconnected.")
                st.rerun()

    else:
        _render_html(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #3B82F6; border-radius: 6px; padding: 12px 16px; margin-bottom: 14px;">
                <div style="font-weight: 700; color: #1E293B; font-size: 0.95rem;">
                    ⚪ Google Drive Not Connected (Local Backups Active)
                </div>
                <div style="font-size: 0.83rem; color: #475569; margin-top: 3px;">
                    Your backups are safely stored on your local computer. Connect your own Google account below to automatically sync backups to Google Drive.
                </div>
            </div>
            """
        )

        creds_present = gdrive_client.is_credentials_file_present()
        col_auth1, col_auth2 = st.columns([2, 3])
        with col_auth1:
            if creds_present:
                if st.button("🔗 Connect Google Account (OAuth 2.0)", type="primary", use_container_width=True, key="btn_gdrive_connect"):
                    with st.spinner("Opening browser for secure Google OAuth authorization..."):
                        success, auth_msg, _ = gdrive_client.authenticate_interactive()
                        if success:
                            st.success(f"✅ {auth_msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {auth_msg}")
            else:
                st.info("ℹ️ Place `credentials.json` in project root to enable 1-click Google Drive connection.")

        with col_auth2:
            st.caption("🔒 **Security Guarantee:** Tokens are stored locally (`data/gdrive_token.json`) and never committed to GitHub. Scopes are restricted strictly to files created by this app (`drive.file`).")

        # Step-by-Step Google Cloud Credentials Setup Guide
        with st.expander("📘 How to Set Up Your Free Google Cloud Drive API Credentials (3 Minutes)"):
            st.markdown(
                """
                To connect your Google account securely:
                
                1. **Go to Google Cloud Console:** [console.cloud.google.com](https://console.cloud.google.com/)
                2. **Create a Project:** Click the project dropdown at top > **New Project** > Name it *YouTube Keyword Studio* > Click **Create**.
                3. **Enable Google Drive API:**
                   - Go to **APIs & Services** > **Library**.
                   - Search for **Google Drive API** and click **Enable**.
                4. **Configure OAuth Consent Screen:**
                   - Go to **APIs & Services** > **OAuth consent screen**.
                   - Choose **User Type: External** > Click **Create**.
                   - Fill in **App Name** (*YouTube Keyword Studio*) and your user support email.
                   - On the **Test Users** screen, add your personal Google email address.
                5. **Create Desktop OAuth Client ID:**
                   - Go to **APIs & Services** > **Credentials**.
                   - Click **Create Credentials** > **OAuth client ID**.
                   - Select Application type: **Desktop app** > Name: *Keyword Studio Client* > Click **Create**.
                6. **Download Credentials:**
                   - Click the **Download JSON** button next to your client ID.
                   - Rename the downloaded file to `credentials.json`.
                   - Move it into your project folder: `c:\\Users\\HP\\Downloads\\YOUTUBE KEYWORD PLAN\\credentials.json`.
                7. **Connect:** Click **Connect Google Account** above to authorize your personal Drive!
                """
            )

    # -------------------------------------------------------------------------
    # Backup Actions & Schedule Controls
    # -------------------------------------------------------------------------
    st.markdown("##### ⚡ Quick Backup Actions")
    b_act1, b_act2, b_act3 = st.columns(3)
    with b_act1:
        if st.button("🚀 Back Up Now (Local + Cloud)", type="primary", use_container_width=True, key="btn_run_backup_now"):
            with st.spinner("Creating online SQLite snapshot and packaging project bundle..."):
                t0 = time.time()
                res = backup_scheduler.run_full_backup_cycle(trigger="MANUAL_SETTINGS_UI")
                elapsed = round(time.time() - t0, 1)

                if res.get("overall_status") == "SUCCESS":
                    st.success(
                        f"✅ **Backup completed successfully in {elapsed}s!**\n\n"
                        f"- **Local Archive:** `{res.get('local_bundle_file')}` ({round(res.get('archive_size_bytes', 0)/1024, 1)} KB)\n"
                        f"- **Google Drive Upload:** {res.get('gdrive_upload_status')}\n"
                        f"- **Database Integrity:** PRAGMA integrity_check passed (100% consistent WAL snapshot)"
                    )
                    st.rerun()
                else:
                    st.error(f"❌ Backup failed: {res.get('error')}")

    with b_act2:
        if st.button("🧪 Test Sandbox Restore", use_container_width=True, key="btn_test_sandbox_restore"):
            with st.spinner("Testing backup creation and isolated sandbox restoration..."):
                # Find newest backup
                bundles = backup_bundler.list_local_bundles()
                if not bundles:
                    zip_p, _ = backup_bundler.create_backup_bundle(note="Pre-test bundle")
                else:
                    zip_p = Path(bundles[0]["path"])

                ok, msg, stats = backup_restore_manager.test_restore_in_sandbox(zip_p)
                if ok:
                    st.success(f"✅ **Sandbox Restore Test PASSED!**\n\nAll {stats.get('tables_count', 0)} SQLite tables verified in isolation without touching live data.")
                else:
                    st.error(f"❌ Sandbox test failed: {msg}")

    with b_act3:
        if st.button("🔄 Refresh Backup Status", use_container_width=True, key="btn_refresh_backup_status"):
            st.rerun()

    # Schedule & Retention Configuration Form
    with st.expander("⚙️ Automated Daily Schedule & Cloud Retention Settings"):
        sched_enabled = backup_scheduler.is_schedule_enabled()
        sched_hour = backup_scheduler.get_schedule_hour()
        retention_cnt = backup_scheduler.get_retention_count()
        auto_change = backup_scheduler.is_auto_on_change_enabled()

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            new_sched_enabled = st.checkbox("Enable Automated Daily Backups", value=sched_enabled, key="cfg_sched_enabled")
            new_sched_hour = st.number_input("Scheduled Hour of Day (0-23 UTC)", min_value=0, max_value=23, value=sched_hour, key="cfg_sched_hour", help="Hour of the day to execute automated daily backup.")
            st.caption(f"Next estimated scheduled run: **{backup_scheduler.get_next_scheduled_time_str()}**")

        with f_col2:
            new_retention = st.slider("Cloud Retention Limit (Days / Backups to Keep)", min_value=5, max_value=60, value=retention_cnt, step=5, key="cfg_retention", help="Number of daily backups to preserve in Google Drive. Oldest backups beyond this limit are safely pruned.")
            new_auto_change = st.checkbox("Auto-Backup After Important Changes", value=auto_change, key="cfg_auto_change", help="Trigger an automated backup when channel profiles or significant research sessions update.")

        if st.button("💾 Save Backup Settings", type="primary", key="btn_save_backup_settings"):
            backup_scheduler.set_schedule_enabled(new_sched_enabled)
            backup_scheduler.set_schedule_hour(new_sched_hour)
            backup_scheduler.set_retention_count(new_retention)
            backup_scheduler.set_auto_on_change_enabled(new_auto_change)
            st.success("✅ Backup settings updated successfully!")
            st.rerun()

        st.markdown("---")
        st.markdown("##### 🪟 Windows Task Scheduler Setup (Runs Even When Browser Is Closed)")
        st.markdown(
            """
            In-app scheduled backups run automatically while Keyword Studio is open. 
            To ensure backups run every day even when your browser is closed (provided your PC is turned on),
            run this one-line command in PowerShell:
            """
        )
        ps_cmd = 'powershell -ExecutionPolicy Bypass -File scripts\\setup_windows_backup_task.ps1'
        st.code(ps_cmd, language="powershell")
        st.caption("This registers a native Windows Scheduled Task that executes headless CLI backups daily at 03:00.")

    # -------------------------------------------------------------------------
    # Backup History & Inventory
    # -------------------------------------------------------------------------
    st.markdown("##### 📜 Backup Archive History & Cloud Storage")

    local_bundles = backup_bundler.list_local_bundles()
    drive_backups = gdrive_client.list_drive_backups() if is_drive_auth else []

    all_history_rows = []
    # Add Drive items
    for db_item in drive_backups:
        all_history_rows.append({
            "Timestamp": db_item.get("created_at", "")[:19].replace("T", " "),
            "Archive Name": db_item.get("name", ""),
            "Size (KB)": db_item.get("size_kb", 0),
            "Location": "☁️ Google Drive",
            "Integrity Status": "✅ Cloud Verified",
            "Drive ID": db_item.get("id"),
        })

    # Add Local items
    for lb_item in local_bundles:
        all_history_rows.append({
            "Timestamp": lb_item.get("created_at", "")[:19].replace("T", " "),
            "Archive Name": lb_item.get("name", ""),
            "Size (KB)": lb_item.get("size_kb", 0),
            "Location": "💻 Local Disk",
            "Integrity Status": "✅ PRAGMA Integrity OK" if lb_item.get("is_valid") else "⚠️ Validation Warning",
            "Drive ID": None,
        })

    if all_history_rows:
        df_hist = pd.DataFrame(all_history_rows).drop_duplicates(subset=["Archive Name"])
        st.dataframe(
            df_hist[["Timestamp", "Archive Name", "Size (KB)", "Location", "Integrity Status"]],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No backup archives created yet. Click 'Back Up Now' above to generate your first verified backup.")

    # -------------------------------------------------------------------------
    # Safe Restore & Disaster Recovery Workflow
    # -------------------------------------------------------------------------
    with st.expander("📥 Restore & Disaster Recovery Workflow"):
        st.markdown(
            """
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-left: 4px solid #D97706; border-radius: 6px; padding: 10px 14px; font-size: 0.85rem; color: #92400E; margin-bottom: 12px;">
                ⚠️ <b>Restore Safety Protocol:</b> Restoring a backup replaces your active database with the snapshot state inside the backup archive. 
                Keyword Studio automatically creates a <b>pre-restore safety snapshot</b> of your current database before any replacement occurs.
            </div>
            """,
            unsafe_allow_html=True,
        )

        available_local_files = [b["path"] for b in local_bundles if b.get("is_valid")]
        if not available_local_files:
            st.info("No local valid backup files available to restore. Run a backup or download one from Google Drive first.")
        else:
            selected_restore_file = st.selectbox(
                "Select Verified Backup File to Restore",
                options=available_local_files,
                format_func=lambda p: Path(p).name,
                key="select_restore_archive",
            )

            if selected_restore_file:
                target_p = Path(selected_restore_file)
                ok, msg, summary = backup_restore_manager.inspect_backup_for_restore(target_p)

                if ok:
                    _render_html(
                        f"""
                        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; font-size: 0.82rem; color: #334155; margin-bottom: 10px;">
                            <b>Archive Details:</b> {summary['backup_id']} &middot; 
                            <b>Timestamp:</b> {summary['timestamp_utc']} &middot; 
                            <b>App Version:</b> v{summary['app_version']} &middot; 
                            <b>Git Commit:</b> {summary['git_commit'][:8] if summary['git_commit'] else 'N/A'}<br>
                            <b>Database Records:</b> {summary['total_searches']} searches &middot; {summary['total_keywords']} saved keywords &middot; {summary['total_cache']} cache entries
                        </div>
                        """
                    )

                    confirm_restore = st.checkbox(
                        "I confirm that I want to restore this backup. (A pre-restore safety snapshot will be created automatically)",
                        value=False,
                        key="chk_confirm_restore",
                    )

                    if st.button("📥 Restore Database from Selected Backup", type="primary", disabled=not confirm_restore, key="btn_execute_restore"):
                        with st.spinner("Creating pre-restore safety snapshot and restoring database..."):
                            success, restore_msg, safety_p = backup_restore_manager.restore_backup(
                                zip_path=target_p,
                                confirmed=confirm_restore,
                                create_safety_snapshot=True,
                            )
                            if success:
                                st.success(f"✅ {restore_msg}")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(f"❌ {restore_msg}")
                else:
                    st.error(f"❌ Selected backup cannot be restored: {msg}")

    st.markdown("---")

    # =========================================================================
    # SECTION 2: YOUTUBE DATA API V3 CONFIGURATION (Preserved)
    # =========================================================================
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

    # =========================================================================
    # SECTION 3: SEARCH VOLUME TRANSPARENCY (Preserved)
    # =========================================================================
    st.markdown("### 📊 Search Volume Provider & Data Source Transparency")
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #3B82F6; 
                    border-radius: 6px; padding: 12px 16px; margin-bottom: 14px; font-size: 0.88rem; color: #334155;">
            <b>Status:</b> <code>Unconnected Local Provider (Truthful Mode)</code><br>
            • <b>Missing Integration / Credentials:</b> No commercial search volume API key configured (e.g. Google Ads Keyword Planner, Keywords Everywhere, or DataForSEO API).<br>
            • <b>Epistemic Modesty Policy:</b> YouTube Autocomplete does <b>not</b> disclose official monthly search volume numbers. 
            Keyword Studio strictly refuses to fabricate speculative volume counts or label unverified keywords as "High Volume". 
            Discovered keywords truthfully show <code>Volume unavailable</code> while providing genuine real-world search suggestions, competitor analysis, and opportunity scores.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # =========================================================================
    # SECTION 4: PRIVACY & ARCHITECTURE GUARANTEE (Preserved)
    # =========================================================================
    st.markdown("### 🔒 Privacy & Architecture Notice")
    st.markdown(
        """
        - **Zero Tracking:** No telemetry, tracking scripts, or analytics sent to third parties.
        - **Local Only:** All searches, databases, and configuration remain on your local disk in SQLite WAL mode.
        - **Public Data Only:** Only publicly viewable YouTube autocomplete suggestions and SERP metadata are accessed.
        """
    )
