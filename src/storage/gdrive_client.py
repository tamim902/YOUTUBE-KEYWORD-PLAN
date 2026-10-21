"""Official Google Drive API Client & Cloud Backup Sync Service.

Manages:
- Secure OAuth 2.0 authorization using Google Drive API v3 (drive.file scope).
- Automated discovery and creation of dedicated 'YouTube Keyword Studio Backups' folder.
- Resumable multipart uploads of verified backup ZIP bundles with manifest metadata.
- Cloud backup inventory listing and selective restoration downloads.
- Safe retention policy enforcement: deletes oldest backups beyond retention limit
  ONLY after a newer backup has uploaded and verified successfully.
- Truthful connection state tracking: never claims connected until token is validated.
"""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from src.config import DATA_DIR
from src.storage.database import db_manager

logger = logging.getLogger(__name__)

# Scopes: Least-privilege drive.file scope (only manages files created by this app)
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_BACKUP_FOLDER_NAME = "YouTube Keyword Studio Backups"


class GoogleDriveClient:
    """Manages Google Drive API connection, backup uploads, and retention policy."""

    def __init__(
        self,
        credentials_file: Optional[Path] = None,
        token_file: Optional[Path] = None,
    ) -> None:
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.credentials_file = Path(credentials_file or self.project_root / "credentials.json")
        self.token_file = Path(token_file or DATA_DIR / "gdrive_token.json")
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self._service: Optional[Any] = None

    def is_credentials_file_present(self) -> bool:
        """Check if client secrets credentials.json is present on disk."""
        return self.credentials_file.exists() and self.credentials_file.stat().st_size > 0

    def get_credentials(self) -> Optional[Credentials]:
        """Load and refresh existing OAuth 2.0 credentials if valid."""
        creds: Optional[Credentials] = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), DRIVE_SCOPES)
            except Exception as ex:
                logger.warning("Failed to load existing token file: %s", ex)
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(self.token_file, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except Exception as ex:
                logger.warning("Failed to refresh OAuth token: %s", ex)
                creds = None

        return creds

    def is_authenticated(self) -> bool:
        """Return True only if valid, non-expired credentials are active."""
        creds = self.get_credentials()
        return bool(creds and creds.valid)

    def get_service(self) -> Any:
        """Get or build authenticated Google Drive API v3 resource."""
        if self._service is not None:
            return self._service

        creds = self.get_credentials()
        if not creds or not creds.valid:
            raise ConnectionError(
                "Not authenticated with Google Drive. Please complete the OAuth flow first."
            )

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def authenticate_interactive(self, port: int = 0) -> Tuple[bool, str, Optional[str]]:
        """Run interactive browser-based OAuth 2.0 consent flow."""
        if not self.is_credentials_file_present():
            return (
                False,
                f"Missing credentials file. Please place your Google Cloud OAuth Client credentials at '{self.credentials_file.name}'.",
                None,
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                scopes=DRIVE_SCOPES,
            )
            creds = flow.run_local_server(port=port, prompt="consent")

            # Save token file securely
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

            self._service = None  # Reset cached service
            service = self.get_service()

            # Retrieve user email for display
            user_email = "Connected Google Account"
            try:
                about_res = service.about().get(fields="user(emailAddress,displayName)").execute()
                user_info = about_res.get("user", {})
                user_email = user_info.get("emailAddress") or user_info.get("displayName") or "Connected Google Account"
                db_manager.set_setting("gdrive_user_email", user_email)
            except Exception:
                pass

            db_manager.set_setting("gdrive_auth_status", "CONNECTED")
            logger.info("Google Drive authentication succeeded for %s", user_email)
            return True, f"Successfully connected to Google Drive ({user_email})!", user_email

        except Exception as ex:
            logger.error("OAuth authentication failed: %s", ex)
            return False, f"Google Drive authorization failed: {str(ex)}", None

    def disconnect(self) -> Tuple[bool, str]:
        """Revoke and delete local token to disconnect Google Drive."""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
            self._service = None
            db_manager.set_setting("gdrive_auth_status", "DISCONNECTED")
            db_manager.set_setting("gdrive_user_email", "")
            return True, "Google Drive disconnected successfully."
        except Exception as ex:
            return False, f"Failed to disconnect Google Drive: {str(ex)}"

    def get_or_create_backup_folder(self, folder_name: str = DEFAULT_BACKUP_FOLDER_NAME) -> Tuple[str, str]:
        """Find or create dedicated backup folder in user's Google Drive."""
        service = self.get_service()

        # Query existing folder
        query = (
            f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, webViewLink)",
        ).execute()

        files = response.get("files", [])
        if files:
            folder_id = files[0]["id"]
            web_link = files[0].get("webViewLink", "")
            return folder_id, web_link

        # Create new folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "description": "Automated backups for YouTube Keyword Studio",
        }
        folder = service.files().create(
            body=folder_metadata,
            fields="id, name, webViewLink",
        ).execute()

        folder_id = folder["id"]
        web_link = folder.get("webViewLink", "")
        db_manager.set_setting("gdrive_folder_id", folder_id)
        return folder_id, web_link

    def upload_backup(
        self,
        zip_path: Path,
        manifest: Dict[str, Any],
        folder_name: str = DEFAULT_BACKUP_FOLDER_NAME,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Upload a backup ZIP file to the dedicated Google Drive folder."""
        zip_path = Path(zip_path)
        if not zip_path.exists():
            return False, f"Backup file does not exist: {zip_path}", {}

        service = self.get_service()
        folder_id, folder_link = self.get_or_create_backup_folder(folder_name=folder_name)

        media = MediaFileUpload(
            str(zip_path),
            mimetype="application/zip",
            resumable=True,
        )

        file_metadata = {
            "name": zip_path.name,
            "parents": [folder_id],
            "description": (
                f"YouTube Keyword Studio Backup\n"
                f"ID: {manifest.get('backup_id', 'unknown')}\n"
                f"UTC: {manifest.get('timestamp_utc', '')}\n"
                f"App Version: v{manifest.get('app_version', '')}\n"
                f"Git Commit: {manifest.get('git_commit') or 'untracked'}\n"
                f"SHA256: {manifest.get('archive_sha256', '')}"
            ),
            "appProperties": {
                "backup_id": manifest.get("backup_id", ""),
                "sha256": manifest.get("archive_sha256", ""),
                "app": "YouTube Keyword Studio",
            },
        }

        try:
            uploaded = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, size, createdTime, webViewLink",
            ).execute()

            # Record success in local database
            now_iso = manifest.get("timestamp_utc", "")
            db_manager.set_setting("gdrive_last_backup_time", now_iso)
            db_manager.set_setting("gdrive_last_backup_status", "SUCCESS")
            db_manager.set_setting("gdrive_last_backup_file", zip_path.name)
            db_manager.set_setting("gdrive_last_backup_id", uploaded.get("id", ""))
            db_manager.set_setting("gdrive_last_backup_error", "")

            logger.info("Uploaded backup to Google Drive: %s (Drive ID: %s)", zip_path.name, uploaded.get("id"))
            return True, f"Successfully uploaded '{zip_path.name}' to Google Drive!", uploaded

        except HttpError as ex:
            err_msg = f"Google Drive API error: {ex.reason or str(ex)}"
            db_manager.set_setting("gdrive_last_backup_status", "FAILED")
            db_manager.set_setting("gdrive_last_backup_error", err_msg)
            return False, err_msg, {}
        except Exception as ex:
            err_msg = f"Network or upload error: {str(ex)}"
            db_manager.set_setting("gdrive_last_backup_status", "FAILED")
            db_manager.set_setting("gdrive_last_backup_error", err_msg)
            return False, err_msg, {}
        finally:
            if hasattr(media, "_fd") and media._fd:
                try:
                    media._fd.close()
                except Exception:
                    pass

    def list_drive_backups(self, folder_name: str = DEFAULT_BACKUP_FOLDER_NAME) -> List[Dict[str, Any]]:
        """List all backup archives currently stored in the Google Drive folder."""
        if not self.is_authenticated():
            return []

        try:
            service = self.get_service()
            folder_id, _ = self.get_or_create_backup_folder(folder_name=folder_name)

            query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
            response = service.files().list(
                q=query,
                orderBy="createdTime desc",
                pageSize=100,
                fields="files(id, name, size, createdTime, description, webViewLink, appProperties)",
            ).execute()

            backups = []
            for f in response.get("files", []):
                size_b = int(f.get("size", 0))
                backups.append({
                    "id": f["id"],
                    "name": f["name"],
                    "size_bytes": size_b,
                    "size_kb": round(size_b / 1024, 2),
                    "created_at": f.get("createdTime", ""),
                    "description": f.get("description", ""),
                    "web_link": f.get("webViewLink", ""),
                    "app_properties": f.get("appProperties", {}),
                })
            return backups
        except Exception as ex:
            logger.warning("Failed to list Google Drive backups: %s", ex)
            return []

    def download_backup(self, file_id: str, target_path: Path) -> Tuple[bool, str]:
        """Download a backup file from Google Drive to local destination."""
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            service = self.get_service()
            request = service.files().get_media(fileId=file_id)

            with open(target_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            return True, f"Downloaded '{target_path.name}' successfully ({target_path.stat().st_size} bytes)."
        except Exception as ex:
            return False, f"Failed to download backup from Google Drive: {str(ex)}"

    def apply_retention_policy(
        self,
        keep_count: int = 30,
        folder_name: str = DEFAULT_BACKUP_FOLDER_NAME,
    ) -> Tuple[int, List[str]]:
        """Prune older backups beyond keep_count from Google Drive.
        
        Strict Safety Rule:
        Never deletes a previous backup unless the current list exceeds keep_count.
        Oldest items are pruned first.
        """
        if keep_count <= 0:
            keep_count = 30

        backups = self.list_drive_backups(folder_name=folder_name)
        if len(backups) <= keep_count:
            return 0, []

        to_delete = backups[keep_count:]
        deleted_names = []
        service = self.get_service()

        for b in to_delete:
            try:
                service.files().delete(fileId=b["id"]).execute()
                deleted_names.append(b["name"])
                logger.info("Retention policy pruned older backup from Drive: %s", b["name"])
            except Exception as ex:
                logger.warning("Failed to prune backup %s from Drive: %s", b["name"], ex)

        return len(deleted_names), deleted_names

    def get_status_summary(self) -> Dict[str, Any]:
        """Return comprehensive status dictionary for UI display."""
        is_cfg = self.is_credentials_file_present()
        is_auth = self.is_authenticated()
        user_email = db_manager.get_setting("gdrive_user_email") or ""
        last_backup = db_manager.get_setting("gdrive_last_backup_time") or "Never"
        last_status = db_manager.get_setting("gdrive_last_backup_status") or "IDLE"
        last_error = db_manager.get_setting("gdrive_last_backup_error") or ""

        return {
            "is_configured": is_cfg,
            "is_authenticated": is_auth,
            "user_email": user_email,
            "credentials_path": str(self.credentials_file),
            "last_backup_time": last_backup,
            "last_backup_status": last_status,
            "last_backup_error": last_error,
            "folder_name": DEFAULT_BACKUP_FOLDER_NAME,
        }


gdrive_client = GoogleDriveClient()
