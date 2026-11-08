from __future__ import annotations

import logging

from app.db.models import UserSettings
from app.db.seed import get_default_user
from app.db.session import SessionLocal
from app.integrations.google import gmail as gmail_integration
from app.integrations.google import sheets as sheets_integration
from app.services.activity import log_activity
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _automation_blocked(db) -> bool:
    user = get_default_user(db)
    if user is None:
        return True
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).one_or_none()
    if settings is None:
        return True
    return bool(settings.automation_paused or settings.emergency_stop)


@celery_app.task(name="app.workers.tasks.sheets_sync_task")
def sheets_sync_task() -> dict:
    db = SessionLocal()
    try:
        if _automation_blocked(db):
            return {"skipped": True, "reason": "automation_paused_or_stopped"}
        user = get_default_user(db)
        if user is None:
            return {"skipped": True, "reason": "no_user"}
        pull = sheets_integration.pull_mutable_sheets(db, user.id)
        push = sheets_integration.push_all(db, user.id)
        return {"pull": pull, "push": push}
    except Exception as exc:
        logger.exception("sheets_sync_task failed")
        user = get_default_user(db)
        if user:
            log_activity(
                db,
                user_id=user.id,
                category="sync",
                action="sheets_sync_failed",
                message=str(exc),
                status="failure",
            )
        return {"error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.daily_outreach_task")
def daily_outreach_task() -> dict:
    from app.services.outreach import run_daily_outreach

    db = SessionLocal()
    try:
        if _automation_blocked(db):
            return {"skipped": True, "reason": "automation_paused_or_stopped"}
        result = run_daily_outreach(db, discover=True)
        user = get_default_user(db)
        if user:
            try:
                sheets_integration.push_all(db, user.id)
            except Exception as exc:
                result.setdefault("errors", []).append({"source": "sheets_sync", "error": str(exc)})
        return result
    except Exception as exc:
        logger.exception("daily_outreach_task failed")
        return {"error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.hourly_outreach_send_task")
def hourly_outreach_send_task() -> dict:
    """Send approved drafts only when recipient local time is in working hours."""
    from app.services.outreach import run_daily_outreach

    db = SessionLocal()
    try:
        if _automation_blocked(db):
            return {"skipped": True, "reason": "automation_paused_or_stopped"}
        # No rediscovery — just attempt sends for drafts already approved.
        return run_daily_outreach(db, discover=False, force_auto_send=True)
    except Exception as exc:
        logger.exception("hourly_outreach_send_task failed")
        return {"error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.gmail_reconcile_task")
def gmail_reconcile_task() -> dict:
    db = SessionLocal()
    try:
        if _automation_blocked(db):
            return {"skipped": True, "reason": "automation_paused_or_stopped"}
        user = get_default_user(db)
        if user is None:
            return {"skipped": True, "reason": "no_user"}
        messages = gmail_integration.list_recent_messages(db, user.id, max_results=25)
        log_activity(
            db,
            user_id=user.id,
            category="email",
            action="gmail_reconcile",
            message=f"Reconciled {len(messages)} inbox messages",
            details={"count": len(messages)},
        )
        return {"count": len(messages)}
    except Exception as exc:
        logger.exception("gmail_reconcile_task failed")
        return {"error": str(exc)}
    finally:
        db.close()
