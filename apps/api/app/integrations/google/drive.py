from __future__ import annotations

import logging
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from sqlalchemy.orm import Session

from app.integrations.google.oauth import get_credential_row, get_valid_credentials
from app.services.activity import log_activity
from app.services.resume_matching import extract_drive_file_id

logger = logging.getLogger(__name__)

RESUME_FOLDER_NAME = "AI Job Hunter - Resumes"


def _cv_cache_dir() -> Path:
    """Prefer repo data/ on writable hosts; fall back to /tmp on Vercel."""
    preferred = Path(__file__).resolve().parents[3] / "data" / "cv_cache"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / "ai_job_hunter_cv_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


CV_CACHE_DIR = _cv_cache_dir()


def _drive_service(db: Session, user_id: UUID):
    creds = get_valid_credentials(db, user_id)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def ensure_resume_folder(db: Session, user_id: UUID) -> str:
    row = get_credential_row(db, user_id)
    if row is None:
        raise RuntimeError("Google not connected")
    if row.drive_folder_id:
        return row.drive_folder_id

    service = _drive_service(db, user_id)
    query = (
        f"name = '{RESUME_FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    existing = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = existing.get("files", [])
    if files:
        folder_id = files[0]["id"]
    else:
        metadata = {
            "name": RESUME_FOLDER_NAME,
            "mimeType": "application/vnd.google-apps.folder",
        }
        created = service.files().create(body=metadata, fields="id").execute()
        folder_id = created["id"]

    row.drive_folder_id = folder_id
    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="drive_folder_ready",
        message=f"Resume Drive folder ready: {RESUME_FOLDER_NAME}",
        details={"drive_folder_id": folder_id},
        commit=False,
    )
    db.commit()
    return folder_id


def upload_file(
    db: Session,
    user_id: UUID,
    *,
    local_path: str,
    name: Optional[str] = None,
) -> dict[str, Any]:
    folder_id = ensure_resume_folder(db, user_id)
    service = _drive_service(db, user_id)
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(local_path)

    mime, _ = mimetypes.guess_type(str(path))
    media = MediaFileUpload(str(path), mimetype=mime or "application/pdf", resumable=True)
    metadata = {"name": name or path.name, "parents": [folder_id]}
    uploaded = service.files().create(body=metadata, media_body=media, fields="id, name, webViewLink").execute()

    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="drive_upload",
        message=f"Uploaded {uploaded.get('name')} to Drive",
        details={"file_id": uploaded.get("id")},
    )
    return {
        "file_id": uploaded.get("id"),
        "name": uploaded.get("name"),
        "web_view_link": uploaded.get("webViewLink"),
    }


def download_file(
    db: Session,
    user_id: UUID,
    *,
    file_id: str,
    dest_path: str | Path | None = None,
    preferred_name: str | None = None,
) -> Path:
    """Download a Drive file the user can access into a local cache path."""
    file_id = extract_drive_file_id(file_id) or file_id
    service = _drive_service(db, user_id)
    try:
        meta = (
            service.files()
            .get(fileId=file_id, fields="id, name, mimeType", supportsAllDrives=True)
            .execute()
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not read this Drive file. Reconnect Google in Settings (needs Drive access), "
            "or upload the PDF on the CVs page."
        ) from exc
    name = preferred_name or meta.get("name") or f"{file_id}.pdf"
    mime = meta.get("mimeType") or ""

    cache_dir = _cv_cache_dir()
    if dest_path is None:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
        dest = cache_dir / f"{file_id}_{safe}"
    else:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

    # Google Docs need export; PDFs/binary use get_media.
    if mime.startswith("application/vnd.google-apps."):
        if not str(dest).lower().endswith(".pdf"):
            dest = dest.with_suffix(".pdf")
        request = service.files().export_media(fileId=file_id, mimeType="application/pdf")
    else:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

    with open(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    if not dest.exists() or dest.stat().st_size <= 0:
        raise RuntimeError("Downloaded CV file is empty")

    log_activity(
        db,
        user_id=user_id,
        category="sync",
        action="drive_download",
        message=f"Downloaded CV {name} from Drive",
        details={"file_id": file_id, "path": str(dest)},
    )
    return dest


def resolve_local_cv_path(
    db: Session,
    user_id: UUID,
    *,
    local_path: str | None = None,
    drive_file_id: str | None = None,
    drive_url: str | None = None,
    preferred_name: str | None = None,
) -> Optional[Path]:
    if local_path:
        path = Path(local_path)
        if path.exists():
            return path
    file_id = extract_drive_file_id(drive_file_id) or extract_drive_file_id(drive_url)
    if not file_id:
        return None
    return download_file(db, user_id, file_id=file_id, preferred_name=preferred_name)
