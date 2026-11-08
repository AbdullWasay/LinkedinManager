from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import ensure_default_user
from app.db.session import get_db
from app.integrations.google import drive as drive_integration
from app.integrations.google import oauth as google_oauth
from app.integrations.google import sheets as sheets_integration
from app.schemas.auth import AuthStatusResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory OAuth state for single-user local use. Replace with Redis in production.
_oauth_states: set[str] = set()


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(db: Session = Depends(get_db)) -> AuthStatusResponse:
    return AuthStatusResponse(**google_oauth.auth_status(db))


@router.get("/google/login")
def google_login() -> RedirectResponse:
    if not google_oauth.google_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    state = secrets.token_urlsafe(24)
    _oauth_states.add(state)
    url = google_oauth.build_auth_url(state)
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)) -> RedirectResponse:
    settings = get_settings()
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    _oauth_states.discard(state)

    user = ensure_default_user(db)
    try:
        creds = google_oauth.exchange_code(code)
        google_oauth.store_credentials(db, user.id, creds)
        sheets_integration.ensure_spreadsheet(db, user.id)
        drive_integration.ensure_resume_folder(db, user.id)
        sheets_integration.push_all(db, user.id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google OAuth/setup failed: {exc}") from exc

    return RedirectResponse(f"{settings.frontend_url}/integrations?google=connected")


@router.post("/google/disconnect")
def google_disconnect(db: Session = Depends(get_db)) -> dict:
    user = ensure_default_user(db)
    google_oauth.disconnect_google(db, user.id)
    return {"ok": True}
