from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import get_settings
from app.db.seed import ensure_default_user
from app.db.session import get_db
from app.integrations.google import drive as drive_integration
from app.integrations.google import oauth as google_oauth
from app.schemas.auth import AuthStatusResponse, LoginResponse, SessionUserResponse
from app.services.session_auth import (
    auth_is_required,
    clear_session_cookie,
    create_session_token,
    email_allowed,
    password_matches,
    read_session,
    set_session_cookie,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory OAuth state for single-user local use. Replace with Redis in production.
_oauth_states: set[str] = set()


class PasswordLoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class SessionHandoffIn(BaseModel):
    token: str = Field(min_length=10, max_length=4096)


def _session_payload(request: Request, db: Session) -> dict:
    settings = get_settings()
    user = ensure_default_user(db)
    google = google_oauth.auth_status(db)
    session = read_session(request)
    logged_in = bool(session) or not auth_is_required()
    email = (session or {}).get("email") or user.email
    name = (session or {}).get("name") or user.name
    return {
        "authenticated": logged_in,
        "auth_required": auth_is_required(),
        "login_methods": {
            "password": bool((settings.auth_password or "").strip()),
            "google": google_oauth.google_is_configured(),
        },
        "user_id": user.id if logged_in else None,
        "email": email if logged_in else None,
        "name": name if logged_in else None,
        "google_connected": bool(google.get("google_connected")),
        "scopes": google.get("scopes") or [],
        "spreadsheet_id": google.get("spreadsheet_id"),
        "spreadsheet_url": google.get("spreadsheet_url"),
        "drive_folder_id": google.get("drive_folder_id"),
        "google_configured": google_oauth.google_is_configured(),
    }


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request, db: Session = Depends(get_db)) -> AuthStatusResponse:
    return AuthStatusResponse(**_session_payload(request, db))


@router.get("/me", response_model=SessionUserResponse)
def me(request: Request, db: Session = Depends(get_db)) -> SessionUserResponse:
    payload = _session_payload(request, db)
    return SessionUserResponse(
        authenticated=bool(payload["authenticated"]),
        auth_required=bool(payload["auth_required"]),
        email=payload.get("email"),
        name=payload.get("name"),
        user_id=payload.get("user_id"),
        login_methods=payload.get("login_methods") or {},
    )


@router.post("/login", response_model=LoginResponse)
def password_login(
    payload: PasswordLoginIn,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    if not (settings.auth_password or "").strip():
        raise HTTPException(
            status_code=503,
            detail="Password login is not configured. Set AUTH_PASSWORD in the server environment.",
        )
    if not password_matches(payload.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    user = ensure_default_user(db)
    email = settings.default_user_email
    if not email_allowed(email):
        raise HTTPException(status_code=403, detail="Default user email is not in ALLOWED_LOGIN_EMAILS")

    token = create_session_token(user_id=user.id, email=email, name=user.name or settings.default_user_name)
    set_session_cookie(response, token)
    return LoginResponse(
        ok=True,
        email=email,
        name=user.name,
        message="Logged in",
    )


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/session", response_model=LoginResponse)
def consume_session_handoff(payload: SessionHandoffIn, response: Response) -> LoginResponse:
    """Exchange a one-time handoff token (e.g. after Google OAuth) for a first-party cookie."""
    from app.services.session_auth import verify_session_token

    session = verify_session_token(payload.token)
    email = str(session.get("email") or "")
    if not email_allowed(email):
        raise HTTPException(status_code=403, detail="This account is not allowed to access the app")
    # Re-issue a fresh cookie session (same claims).
    from uuid import UUID

    token = create_session_token(
        user_id=UUID(str(session["uid"])),
        email=email,
        name=str(session.get("name") or ""),
    )
    set_session_cookie(response, token)
    return LoginResponse(ok=True, email=email, name=session.get("name"), message="Session established")


@router.get("/google/login")
def google_login(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if not google_oauth.google_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    # If auth is required and user is not logged in yet, Google OAuth is also the app login gate.
    # Already-logged-in users use the same endpoint to (re)connect Gmail/Drive scopes.
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
        profile = google_oauth.fetch_google_profile(creds)
        email = profile["email"]
        if not email_allowed(email):
            # Do not store credentials for unauthorized Google accounts.
            raise HTTPException(
                status_code=403,
                detail=f"{email} is not allowed to access this app",
            )
        google_oauth.store_credentials(db, user.id, creds)
        # Keep bootstrap user email aligned with the allowed Google identity.
        if email and user.email != email:
            user.email = email
            if profile.get("name"):
                user.name = profile["name"]
            db.commit()
        # Sheets are optional/disabled — only ensure Drive so CVs can attach.
        drive_integration.ensure_resume_folder(db, user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google OAuth/setup failed: {exc}") from exc

    token = create_session_token(
        user_id=user.id,
        email=email,
        name=profile.get("name") or user.name or settings.default_user_name,
    )
    # Hand the session to the frontend origin so the cookie is first-party (works with Next proxy).
    redirect = RedirectResponse(
        f"{settings.frontend_url}/login?handoff={token}&google=connected"
    )
    return redirect


@router.post("/google/disconnect")
def google_disconnect(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> dict:
    google_oauth.disconnect_google(db, user_id)
    return {"ok": True}
