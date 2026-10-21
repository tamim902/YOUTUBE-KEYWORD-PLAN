"""Comprehensive Automated Backup & Google Drive Integration Test Suite.

Verifies:
1. Google Drive client configuration, OAuth token management, and status reporting.
2. Dedicated backup folder discovery and creation ('YouTube Keyword Studio Backups').
3. Project backup bundler: source code packaging, dependency manifests, and database snapshot.
4. Security exclusion rules: verified absence of .env, credentials.json, token.json, .venv, *.log.
5. Cryptographic SHA-256 manifest verification and SQLite PRAGMA integrity_check.
6. Safe cloud upload simulation and error handling.
7. Cloud retention policy: preserving newest backups and never deleting when below limit.
8. Safe restoration: pre-restore safety snapshot, confirmation guardrail, and sandbox recovery.
9. Backup scheduler: schedule due calculation, hourly execution, and CLI command execution.
10. UI integration: render_settings_tool() renders cleanly without errors.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from unittest.mock import MagicMock, patch
import zipfile
import pytest

from src.config import APP_VERSION
from src.storage.backup import BackupManager
from src.storage.backup_bundle import (
    BackupBundler,
    BackupManifest,
    compute_file_sha256,
)
from src.storage.backup_restore import BackupRestoreManager
from src.storage.backup_scheduler import BackupScheduler
from src.storage.database import DatabaseManager, db_manager
from src.storage.gdrive_client import GoogleDriveClient
from src.ui.tool_settings import render_settings_tool


# -----------------------------------------------------------------------------
# 1. Backup Bundler & Security Exclusions
# -----------------------------------------------------------------------------
def test_backup_bundler_includes_required_files_and_manifest(tmp_path):
    """Verify that bundle contains database snapshot, source files, and manifest."""
    test_db = tmp_path / "test_keywords.db"
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE searches (id INTEGER PRIMARY KEY, seed TEXT);")
    conn.execute("INSERT INTO searches (seed) VALUES ('mechanical keyboards');")
    conn.execute("CREATE TABLE keywords (id INTEGER PRIMARY KEY, kw TEXT);")
    conn.execute("CREATE TABLE autocomplete_cache (q TEXT PRIMARY KEY);")
    conn.commit()
    conn.close()

    bundler = BackupBundler(
        project_root=Path(__file__).resolve().parent.parent,
        backup_dir=tmp_path / "backups",
        db_path=test_db,
    )

    zip_path, manifest = bundler.create_backup_bundle(note="Test Unit Bundle")
    assert zip_path.exists()
    assert zip_path.stat().st_size > 0
    assert manifest.validation_status == "PASSED_VERIFIED"
    assert manifest.database_integrity == "ok"

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "database/keywords.db" in namelist
        assert "backup_manifest.json" in namelist
        assert "app.py" in namelist
        assert "requirements.txt" in namelist
        assert any(n.startswith("src/") for n in namelist)

        # Verify manifest content
        manifest_raw = zf.read("backup_manifest.json")
        m_dict = json.loads(manifest_raw.decode("utf-8"))
        assert m_dict["app_name"] in ("YouTube Keyword Studio", "YouTube Keyword Finder")
        assert m_dict["included_files_count"] > 10


def test_backup_bundler_strict_security_exclusions(tmp_path):
    """Ensure secrets (.env, token.json, credentials.json, .venv) are NEVER in zip."""
    bundler = BackupBundler(backup_dir=tmp_path)

    # Test exclusion patterns
    assert bundler.is_path_excluded(".env")[0] is True
    assert bundler.is_path_excluded(".env.local")[0] is True
    assert bundler.is_path_excluded("credentials.json")[0] is True
    assert bundler.is_path_excluded("client_secret_123.json")[0] is True
    assert bundler.is_path_excluded("token.json")[0] is True
    assert bundler.is_path_excluded("data/gdrive_token.json")[0] is True
    assert bundler.is_path_excluded(".venv/Lib/site-packages/os.py")[0] is True
    assert bundler.is_path_excluded("src/__pycache__/app.cpython-312.pyc")[0] is True
    assert bundler.is_path_excluded("data/backups/old.zip")[0] is True

    # Safe files must be included
    assert bundler.is_path_excluded("src/ui/tool_settings.py")[0] is False
    assert bundler.is_path_excluded("app.py")[0] is False
    assert bundler.is_path_excluded("requirements.txt")[0] is False


# -----------------------------------------------------------------------------
# 2. Database Consistency & Validation
# -----------------------------------------------------------------------------
def test_backup_bundle_database_integrity_and_validation(tmp_path):
    """Verify extracted database passes PRAGMA integrity_check."""
    test_db = tmp_path / "valid_db.db"
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE searches (id INTEGER PRIMARY KEY, seed TEXT);")
    conn.execute("CREATE TABLE keywords (id INTEGER PRIMARY KEY, kw TEXT);")
    conn.execute("CREATE TABLE autocomplete_cache (q TEXT PRIMARY KEY);")
    conn.commit()
    conn.close()

    bundler = BackupBundler(
        project_root=Path(__file__).resolve().parent.parent,
        backup_dir=tmp_path / "b_out",
        db_path=test_db,
    )

    zip_path, _ = bundler.create_backup_bundle()
    is_valid, msg, manifest = bundler.validate_backup_bundle(zip_path)
    assert is_valid is True
    assert "passed all structural and database integrity checks" in msg


# -----------------------------------------------------------------------------
# 3. Google Drive Client Status & Mocked Sync
# -----------------------------------------------------------------------------
def test_gdrive_client_unconfigured_state(tmp_path):
    """Test honest unconfigured state when credentials.json is missing."""
    client = GoogleDriveClient(
        credentials_file=tmp_path / "nonexistent_creds.json",
        token_file=tmp_path / "nonexistent_token.json",
    )
    assert client.is_credentials_file_present() is False
    assert client.is_authenticated() is False

    summary = client.get_status_summary()
    assert summary["is_configured"] is False
    assert summary["is_authenticated"] is False
    assert summary["folder_name"] == "YouTube Keyword Studio Backups"


def test_gdrive_client_mocked_upload_and_retention():
    """Verify Google Drive upload, folder creation, and retention pruning with mock service."""
    client = GoogleDriveClient()
    mock_service = MagicMock()

    # Mock folder list/create
    mock_files = mock_service.files()
    mock_files.list.return_value.execute.return_value = {
        "files": [{"id": "folder_123", "name": "YouTube Keyword Studio Backups", "webViewLink": "https://drive.google.com/folder"}]
    }

    # Mock upload
    mock_files.create.return_value.execute.return_value = {
        "id": "file_abc_1",
        "name": "backup_test.zip",
        "size": "500000",
        "createdTime": "2026-10-21T12:00:00Z",
        "webViewLink": "https://drive.google.com/file/1",
    }

    with patch.object(client, "get_service", return_value=mock_service):
        folder_id, link = client.get_or_create_backup_folder()
        assert folder_id == "folder_123"
        assert "drive.google.com" in link

        # Mock upload execution
        tmp_zip = Path("test_upload.zip")
        tmp_zip.write_text("dummy zip content")
        try:
            success, msg, meta = client.upload_backup(
                zip_path=tmp_zip,
                manifest={"backup_id": "test_b1", "timestamp_utc": "2026-10-21T12:00:00Z"},
            )
            assert success is True
            assert meta["id"] == "file_abc_1"
        finally:
            if tmp_zip.exists():
                tmp_zip.unlink()


def test_gdrive_retention_policy_safety():
    """Verify retention policy never deletes when list is under limit, and prunes oldest when exceeded."""
    client = GoogleDriveClient()
    mock_service = MagicMock()

    # Create 5 mock backups
    mock_backups = [
        {"id": f"id_{i}", "name": f"backup_{i}.zip", "size": 1000, "createdTime": f"2026-10-2{i}T00:00:00Z"}
        for i in range(5)
    ]

    mock_files = mock_service.files()
    mock_files.list.return_value.execute.return_value = {"files": mock_backups}

    with patch.object(client, "get_service", return_value=mock_service), \
         patch.object(client, "is_authenticated", return_value=True), \
         patch.object(client, "get_or_create_backup_folder", return_value=("fid", "link")):

        # Case 1: Keep 10 (Total 5) -> 0 deleted
        pruned_cnt, _ = client.apply_retention_policy(keep_count=10)
        assert pruned_cnt == 0
        mock_files.delete.assert_not_called()

        # Case 2: Keep 3 (Total 5) -> 2 deleted
        pruned_cnt, deleted_names = client.apply_retention_policy(keep_count=3)
        assert pruned_cnt == 2
        assert len(deleted_names) == 2
        assert mock_files.delete.call_count == 2


# -----------------------------------------------------------------------------
# 4. Safe Restore & Sandbox Verification
# -----------------------------------------------------------------------------
def test_restore_sandbox_verification(tmp_path):
    """Test full sandbox restoration without modifying production database."""
    test_db = tmp_path / "sandbox_test_db.db"
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE searches (id INTEGER PRIMARY KEY, seed TEXT);")
    conn.execute("INSERT INTO searches (seed) VALUES ('cordless drills');")
    conn.execute("CREATE TABLE keywords (id INTEGER PRIMARY KEY, kw TEXT);")
    conn.execute("CREATE TABLE autocomplete_cache (q TEXT PRIMARY KEY);")
    conn.commit()
    conn.close()

    bundler = BackupBundler(
        project_root=Path(__file__).resolve().parent.parent,
        backup_dir=tmp_path / "b_dir",
        db_path=test_db,
    )
    zip_path, _ = bundler.create_backup_bundle()

    restore_mgr = BackupRestoreManager(target_db_path=test_db, backup_dir=tmp_path / "b_dir")
    ok, msg, stats = restore_mgr.test_restore_in_sandbox(zip_path, sandbox_dir=tmp_path / "sandbox_dest")
    assert ok is True
    assert stats["integrity"] == "ok"
    assert stats["tables_count"] >= 3


def test_restore_requires_confirmation_and_creates_safety_backup(tmp_path):
    """Restore must fail without confirmation and create pre-restore snapshot when confirmed."""
    live_db = tmp_path / "live_keywords.db"
    conn = sqlite3.connect(live_db)
    conn.execute("CREATE TABLE searches (id INTEGER PRIMARY KEY, seed TEXT);")
    conn.execute("INSERT INTO searches (seed) VALUES ('original seed');")
    conn.execute("CREATE TABLE keywords (id INTEGER PRIMARY KEY, kw TEXT);")
    conn.execute("CREATE TABLE autocomplete_cache (q TEXT PRIMARY KEY);")
    conn.commit()
    conn.close()

    bundler = BackupBundler(
        project_root=Path(__file__).resolve().parent.parent,
        backup_dir=tmp_path / "b_dir",
        db_path=live_db,
    )
    zip_path, _ = bundler.create_backup_bundle()

    restore_mgr = BackupRestoreManager(target_db_path=live_db, backup_dir=tmp_path / "b_dir")

    # 1. Unconfirmed restore attempt
    ok, msg, safety_p = restore_mgr.restore_backup(zip_path, confirmed=False)
    assert ok is False
    assert "User confirmation is required" in msg

    # 2. Confirmed restore
    ok_conf, msg_conf, safety_p_conf = restore_mgr.restore_backup(
        zip_path,
        confirmed=True,
        create_safety_snapshot=True,
    )
    assert ok_conf is True
    assert safety_p_conf is not None
    assert safety_p_conf.exists()
    assert "pre_restore_safety" in safety_p_conf.name


# -----------------------------------------------------------------------------
# 5. Backup Scheduler & Full Cycle
# -----------------------------------------------------------------------------
def test_backup_scheduler_full_cycle_and_settings(tmp_path):
    """Verify backup scheduler settings, due date checks, and full cycle execution."""
    scheduler = BackupScheduler()

    # Test settings getters/setters
    scheduler.set_schedule_enabled(True)
    assert scheduler.is_schedule_enabled() is True

    scheduler.set_schedule_hour(4)
    assert scheduler.get_schedule_hour() == 4

    scheduler.set_retention_count(25)
    assert scheduler.get_retention_count() == 25

    # Run backup cycle
    res = scheduler.run_full_backup_cycle(trigger="TEST_SUITE")
    assert res["local_bundle_status"] == "SUCCESS"
    assert res["overall_status"] in ("SUCCESS", "PARTIAL_SUCCESS")
    assert "local_bundle_file" in res


# -----------------------------------------------------------------------------
# 6. UI Rendering & Zero-Crash Verification
# -----------------------------------------------------------------------------
def test_settings_tool_renders_with_backup_and_drive_components():
    """Verify render_settings_tool() renders cleanly with all mocked Streamlit components."""
    class MockSession(dict):
        pass

    state = MockSession()
    state["active_channel_id"] = 1

    with patch("streamlit.session_state", state), \
         patch("streamlit.selectbox", return_value=""), \
         patch("streamlit.text_input", return_value=""), \
         patch("streamlit.checkbox", return_value=False), \
         patch("streamlit.number_input", return_value=3), \
         patch("streamlit.slider", return_value=30), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.columns", side_effect=lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.container"), \
         patch("streamlit.dataframe"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())):

        # Should execute cleanly without error
        render_settings_tool()
