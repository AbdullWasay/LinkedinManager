from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_token, encrypt_token
from app.db.models import OAuthCredential
from app.db.seed import ensure_default_user
from app.services.activity import log_activity

logger = logging.getLogger(__name__)


class GoogleNotConfiguredError(Exception):
    pass


def google_is_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id and settings.google_client_secret)


def _client_config() -> dict:
    settings = get_settings()
    if not google_is_configured():
        raise GoogleNotConfiguredError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
        )
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def build_auth_url(state: str) -> str:
    settings = get_settings()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=settings.google_scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code(code: str) -> Credentials:
    settings = get_settings()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=settings.google_scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    flow.fetch_token(code=code)
    return flow.credentials


def get_credential_row(db: Session, user_id: UUID) -> Optional[OAuthCredential]:
    return (
        db.query(OAuthCredential)
        .filter(OAuthCredential.user_id == user_id, OAuthCredential.provider == "google")
        .one_or_none()
    )


def store_credentials(db: Session, user_id: UUID, creds: Credentials) -> OAuthCredential:
    row = get_credential_row(db, user_id)
    if row is None:
        row = OAuthCredential(user_id=user_id, provider="google")
        db.add(row)

    if creds.token:
        row.access_token_enc = encrypt_token(creds.token)
    if creds.refresh_token:
        row.refresh_token_enc = encrypt_token(creds.refresh_token)
    row.scopes = list(creds.scopes or get_settings().google_scopes)
    if creds.expiry:
        expiry = creds.expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        row.token_expiry = expiry

    log_activity(
        db,
        user_id=user_id,
        category="security",
        action="google_oauth_connected",
        message="Google OAuth credentials stored (encrypted)",
        details={"scopes": row.scopes},
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row


def credentials_from_row(row: OAuthCredential) -> Credentials:
    settings = get_settings()
    return Credentials(
        token=decrypt_token(row.access_token_enc) if row.access_token_enc else None,
        refresh_token=decrypt_token(row.refresh_token_enc) if row.refresh_token_enc else None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=row.scopes or settings.google_scopes,
    )


def get_valid_credentials(db: Session, user_id: UUID) -> Credentials:
    if not google_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    row = get_credential_row(db, user_id)
    if row is None or not row.refresh_token_enc:
        raise HTTPException(status_code=401, detail="Google account not connected")

    creds = credentials_from_row(row)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                logger.exception("Failed to refresh Google token")
                log_activity(
                    db,
                    user_id=user_id,
                    category="security",
                    action="google_token_refresh_failed",
                    message=str(exc),
                    status="failure",
                )
                raise HTTPException(status_code=401, detail="Google token refresh failed") from exc
            store_credentials(db, user_id, creds)
        else:
            raise HTTPException(status_code=401, detail="Google credentials invalid")
    return creds


def disconnect_google(db: Session, user_id: UUID) -> None:
    row = get_credential_row(db, user_id)
    if row is None:
        return
    db.delete(row)
    log_activity(
        db,
        user_id=user_id,
        category="security",
        action="google_oauth_disconnected",
        message="Google OAuth credentials removed",
        commit=False,
    )
    db.commit()


def auth_status(db: Session) -> dict:
    user = ensure_default_user(db)
    row = get_credential_row(db, user.id)
    spreadsheet_id = row.spreadsheet_id if row else None
    return {
        "authenticated": True,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "google_connected": bool(row and row.refresh_token_enc),
        "scopes": (row.scopes if row else []) or [],
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}" if spreadsheet_id else None
        ),
        "drive_folder_id": row.drive_folder_id if row else None,
        "google_configured": google_is_configured(),
    }
