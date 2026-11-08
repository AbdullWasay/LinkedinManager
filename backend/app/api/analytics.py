from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import ActivityLog, Application, EmailDraft, EmailMessage, Job, UserSettings
from app.db.session import get_db
from app.services.working_hours import next_working_window

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    jobs_discovered = (
        db.query(func.count(Job.id))
        .filter(Job.user_id == user_id, Job.is_deleted.is_(False))
        .scalar()
        or 0
    )
    avg_match = (
        db.query(func.avg(Job.match_score))
        .filter(Job.user_id == user_id, Job.match_score.isnot(None))
        .scalar()
    )
    pending_approvals = (
        db.query(func.count(EmailDraft.id))
        .filter(EmailDraft.user_id == user_id, EmailDraft.approval_status == "pending")
        .scalar()
        or 0
    )
    emails_sent = (
        db.query(func.count(EmailMessage.id))
        .filter(EmailMessage.user_id == user_id, EmailMessage.direction == "outbound")
        .scalar()
        or 0
    )
    interviews = (
        db.query(func.count(Application.id))
        .filter(Application.user_id == user_id, Application.stage == "interview")
        .scalar()
        or 0
    )
    email_jobs = (
        db.query(func.count(Job.id))
        .filter(Job.user_id == user_id, Job.is_deleted.is_(False), Job.application_mode == "email")
        .scalar()
        or 0
    )
    manual_jobs = (
        db.query(func.count(Job.id))
        .filter(
            Job.user_id == user_id,
            Job.is_deleted.is_(False),
            Job.manual_apply_required.is_(True),
            Job.manual_apply_status == "pending",
        )
        .scalar()
        or 0
    )
    sent_draft_ids = {
        m.draft_id
        for m in db.query(EmailMessage.draft_id)
        .filter(EmailMessage.user_id == user_id, EmailMessage.draft_id.isnot(None))
        .all()
    }
    approved_drafts = (
        db.query(EmailDraft)
        .filter(EmailDraft.user_id == user_id, EmailDraft.approval_status == "approved")
        .all()
    )
    ready_to_send = sum(1 for d in approved_drafts if d.id not in sent_draft_ids)
    applied = (
        db.query(func.count(Application.id))
        .filter(
            Application.user_id == user_id,
            Application.is_deleted.is_(False),
            Application.stage.in_(["sent", "replied", "interview", "offer"]),
        )
        .scalar()
        or 0
    )
    stage_rows = (
        db.query(Application.stage, func.count(Application.id))
        .filter(Application.user_id == user_id, Application.is_deleted.is_(False))
        .group_by(Application.stage)
        .all()
    )
    next_send = next_working_window()
    return {
        "jobs_discovered": jobs_discovered,
        "avg_match_score": float(avg_match) if avg_match is not None else 0,
        "pending_approvals": pending_approvals,
        "emails_sent": emails_sent,
        "emails_ready_to_send": ready_to_send,
        "applications_sent": applied,
        "interviews": interviews,
        "email_outreach_jobs": email_jobs,
        "manual_apply_pending": manual_jobs,
        "applications_by_stage": {stage: count for stage, count in stage_rows},
        "next_send": next_send,
    }


def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == "hour":
        return dt.replace(minute=0, second=0, microsecond=0).isoformat()
    return dt.date().isoformat()


@router.get("/daily")
def daily(
    days: int = Query(default=14, ge=1, le=90),
    range_key: str | None = Query(default=None, alias="range"),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> dict:
    """Time series for dashboard charts.

    range: 2h | 24h | 7d | 30d | 14d (default via days)
    """
    now = datetime.now(timezone.utc)
    selected = (range_key or "").lower().strip()
    if selected == "2h":
        start = now - timedelta(hours=2)
        granularity = "hour"
        steps = 2
        step = timedelta(hours=1)
    elif selected == "24h":
        start = now - timedelta(hours=23)
        start = start.replace(minute=0, second=0, microsecond=0)
        granularity = "hour"
        steps = 24
        step = timedelta(hours=1)
    elif selected in {"7d", "7"}:
        days = 7
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        granularity = "day"
        steps = days
        step = timedelta(days=1)
    elif selected in {"30d", "30", "month"}:
        days = 30
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        granularity = "day"
        steps = days
        step = timedelta(days=1)
    else:
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        granularity = "day"
        steps = days
        step = timedelta(days=1)
        selected = f"{days}d"

    jobs = (
        db.query(Job.discovered_at)
        .filter(Job.user_id == user_id, Job.is_deleted.is_(False), Job.discovered_at >= start)
        .all()
    )
    emails = (
        db.query(EmailMessage.created_at)
        .filter(
            EmailMessage.user_id == user_id,
            EmailMessage.direction == "outbound",
            EmailMessage.created_at >= start,
        )
        .all()
    )

    jobs_by: dict[str, int] = {}
    emails_by: dict[str, int] = {}
    for (ts,) in jobs:
        if not ts:
            continue
        key = _bucket_key(ts.astimezone(timezone.utc), granularity)
        jobs_by[key] = jobs_by.get(key, 0) + 1
    for (ts,) in emails:
        if not ts:
            continue
        key = _bucket_key(ts.astimezone(timezone.utc), granularity)
        emails_by[key] = emails_by.get(key, 0) + 1

    series = []
    cursor = start if granularity == "hour" else start
    if granularity == "hour":
        cursor = start.replace(minute=0, second=0, microsecond=0)
    for i in range(steps):
        point = cursor + (step * i)
        key = _bucket_key(point, granularity)
        label = point.strftime("%H:%M") if granularity == "hour" else point.strftime("%b %d")
        series.append(
            {
                "date": key,
                "label": label,
                "jobs_found": jobs_by.get(key, 0),
                "emails_sent": emails_by.get(key, 0),
            }
        )

    return {
        "range": selected,
        "granularity": granularity,
        "days": days if granularity == "day" else None,
        "series": series,
        "totals": {
            "jobs_found": sum(p["jobs_found"] for p in series),
            "emails_sent": sum(p["emails_sent"] for p in series),
        },
    }


@router.get("/activity-summary")
def activity_summary(
    limit: int = Query(default=20, ge=5, le=100),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> dict:
    """Group noisy activity into human summaries."""
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(300)
        .all()
    )
    buckets: list[dict] = []

    def add(key: str, singular: str, plural: str, count: int, when, details: dict | None = None):
        if count <= 0:
            return
        existing = next((b for b in buckets if b["key"] == key), None)
        if existing:
            existing["count"] += count
            existing["title"] = (
                f"{existing['count']} {singular}" if existing["count"] == 1 else f"{existing['count']} {plural}"
            )
            if when and (not existing["created_at"] or when.isoformat() > existing["created_at"]):
                existing["created_at"] = when.isoformat()
            if details:
                existing["details"] = {**(existing.get("details") or {}), **details}
            return
        buckets.append(
            {
                "key": key,
                "title": f"{count} {singular}" if count == 1 else f"{count} {plural}",
                "count": count,
                "created_at": when.isoformat() if when else None,
                "details": details or {},
            }
        )

    # Collapse consecutive similar events by day+action
    from collections import defaultdict

    grouped: dict[tuple, dict] = {}
    order: list[tuple] = []
    for log in logs:
        day = log.created_at.date().isoformat() if log.created_at else "unknown"
        key = (day, log.category, log.action)
        if key not in grouped:
            grouped[key] = {"count": 0, "when": log.created_at, "logs": [], "message": log.message}
            order.append(key)
        grouped[key]["count"] += 1
        grouped[key]["logs"].append(log)

    for key in order:
        day, category, action = key
        g = grouped[key]
        count = g["count"]
        when = g["when"]
        if action == "daily_outreach":
            # Prefer details from latest
            details = g["logs"][0].details or {}
            sent = details.get("emails_sent")
            drafts = details.get("drafts_created")
            if isinstance(sent, int) and sent:
                add(f"{day}-sent", "email sent", "emails sent", sent, when, details)
            if isinstance(drafts, int) and drafts:
                add(f"{day}-drafts", "outreach draft created", "outreach drafts created", drafts, when, details)
            continue
        if action == "job_discovery":
            details = g["logs"][0].details or {}
            saved = details.get("saved") or details.get("fetched") or count
            add(f"{day}-jobs", "new job found", "new jobs found", int(saved), when, details)
            continue
        if action == "gmail_send":
            add(f"{day}-gmail", "email sent", "emails sent", count, when)
            continue
        if action == "sheets_push":
            add(f"{day}-sheets", "Google Sheets sync", "Google Sheets syncs", count, when)
            continue
        if action.startswith("blocklist"):
            add(f"{day}-block", "blocklist update", "blocklist updates", count, when)
            continue
        if action == "settings_updated":
            add(f"{day}-settings", "settings update", "settings updates", count, when)
            continue
        label = action.replace("_", " ")
        add(f"{day}-{action}", label, f"{label} events", count, when)

    return {"items": buckets[:limit]}


@router.get("/next-send")
def next_send(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    window = next_working_window()
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).one_or_none()
    daily_limit = (settings.daily_send_limit if settings else None) or 30
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = (
        db.query(func.count(EmailMessage.id))
        .filter(
            EmailMessage.user_id == user_id,
            EmailMessage.direction == "outbound",
            EmailMessage.created_at >= start,
        )
        .scalar()
        or 0
    )
    sent_draft_ids = {
        m.draft_id
        for m in db.query(EmailMessage.draft_id)
        .filter(EmailMessage.user_id == user_id, EmailMessage.draft_id.isnot(None))
        .all()
    }
    approved = (
        db.query(EmailDraft)
        .filter(
            EmailDraft.user_id == user_id,
            EmailDraft.approval_status.in_(["approved", "edited"]),
        )
        .all()
    )
    ready = sum(1 for d in approved if d.id not in sent_draft_ids)
    remaining_today = max(0, daily_limit - sent_today)
    next_batch = min(ready, remaining_today)
    return {
        **window,
        "emails_ready": ready,
        "emails_in_next_batch": next_batch,
        "daily_send_limit": daily_limit,
        "sent_today": sent_today,
        "remaining_today": remaining_today,
    }
