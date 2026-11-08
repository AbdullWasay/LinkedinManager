"""HTTP triggers for scheduled automation (free alternative to Celery/Redis)."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Header, HTTPException

from app.core.config import get_settings
from app.workers import tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])


def _authorize(authorization: str | None, x_cron_secret: str | None) -> None:
    settings = get_settings()
    expected = (settings.cron_secret or settings.secret_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")

    provided = ""
    if x_cron_secret:
        provided = x_cron_secret.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized cron request")


@router.post("/discovery")
def cron_discovery(
    authorization: str | None = Header(default=None),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    """Discover jobs + draft outreach (optionally auto-send if enabled)."""
    _authorize(authorization, x_cron_secret)
    return tasks.daily_outreach_task()


@router.post("/send")
def cron_send(
    authorization: str | None = Header(default=None),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    """Send approved drafts (working-hours aware)."""
    _authorize(authorization, x_cron_secret)
    return tasks.hourly_outreach_send_task()


@router.post("/sheets-sync")
def cron_sheets_sync(
    authorization: str | None = Header(default=None),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    _authorize(authorization, x_cron_secret)
    return tasks.sheets_sync_task()


@router.post("/gmail-reconcile")
def cron_gmail_reconcile(
    authorization: str | None = Header(default=None),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    _authorize(authorization, x_cron_secret)
    return tasks.gmail_reconcile_task()
