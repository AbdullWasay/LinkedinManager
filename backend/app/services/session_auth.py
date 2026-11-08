"""Signed session cookies for single-owner app access."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, Request, Response

from app.core.config import get_settings

COOKIE_NAME = "jh_session"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _signing_key() -> bytes:
    settings = get_settings()
    return hashlib.sha256(f"jh-session:{settings.secret_key}".encode()).digest()


def create_session_token(*, user_id: UUID, email: str, name: str = "") -> str:
    settings = get_settings()
    payload = {
        "uid": str(user_id),
        "email": (email or "").strip().lower(),
        "name": name or "",
        "exp": int(time.time()) + int(settings.session_max_age_hours * 3600),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_signing_key(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_session_token(token: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc
    expected = hmac.new(_signing_key(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid session signature")
    try:
        payload = json.loads(_b64decode(body))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid session payload") from exc
    if int(payload.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Session expired — please log in again")
    return payload


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    secure = settings.app_env.lower() == "production" or settings.frontend_url.startswith("https")
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=int(settings.session_max_age_hours * 3600),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def read_session(request: Request) -> Optional[dict[str, Any]]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return verify_session_token(token)
    except HTTPException:
        return None


def password_matches(candidate: str) -> bool:
    settings = get_settings()
    expected = (settings.auth_password or "").strip()
    if not expected:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def email_allowed(email: str) -> bool:
    settings = get_settings()
    allowed = settings.allowed_login_email_list
    if not allowed:
        # Fall back to the bootstrap user email.
        allowed = [settings.default_user_email.strip().lower()]
    return (email or "").strip().lower() in allowed


def auth_is_required() -> bool:
    """Auth is required whenever a password is configured, or in production."""
    settings = get_settings()
    if settings.auth_disabled:
        return False
    if (settings.auth_password or "").strip():
        return True
    return settings.app_env.lower() == "production"
