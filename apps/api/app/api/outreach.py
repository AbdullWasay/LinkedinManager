from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Application, Contact, EmailDraft, EmailMessage, Job, Resume
from app.db.session import get_db
from app.integrations.google import sheets as sheets_integration
from app.services.outreach import run_daily_outreach, send_draft

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/run-daily")
def run_outreach(
    discover: bool = True,
    max_send: int = Query(default=30, ge=0, le=100),
    force_auto_send: bool = False,
    sync_sheets: bool = True,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> dict:
    try:
        result = run_daily_outreach(
            db,
            discover=discover,
            max_send=max_send,
            force_auto_send=force_auto_send,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if sync_sheets:
        try:
            sheets_integration.push_all(db, user_id)
        except Exception as exc:
            result.setdefault("errors", []).append({"source": "sheets_sync", "error": str(exc)})
    return result


@router.get("/drafts")
def list_drafts(
    approval_status: str | None = None,
    ready: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> dict:
    q = db.query(EmailDraft).filter(EmailDraft.user_id == user_id)
    if approval_status:
        q = q.filter(EmailDraft.approval_status == approval_status)
    elif ready:
        q = q.filter(EmailDraft.approval_status.in_(["approved", "edited"]))
    drafts = q.order_by(EmailDraft.created_at.desc()).limit(limit).all()

    sent_draft_ids = {
        m.draft_id
        for m in db.query(EmailMessage.draft_id)
        .filter(EmailMessage.user_id == user_id, EmailMessage.draft_id.isnot(None))
        .all()
    }
    if ready:
        drafts = [d for d in drafts if d.id not in sent_draft_ids]

    contact_map = {
        c.id: c
        for c in db.query(Contact)
        .filter(Contact.id.in_([d.contact_id for d in drafts if d.contact_id]))
        .all()
    }
    app_ids = [d.application_id for d in drafts if d.application_id]
    applications = {
        a.id: a for a in db.query(Application).filter(Application.id.in_(app_ids)).all()
    } if app_ids else {}
    job_ids = [a.job_id for a in applications.values()]
    jobs = {j.id: j for j in db.query(Job).filter(Job.id.in_(job_ids)).all()} if job_ids else {}
    from app.db.models import Company

    company_ids = [j.company_id for j in jobs.values() if j.company_id]
    companies = {
        c.id: c for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
    } if company_ids else {}
    resume_ids = [d.resume_id for d in drafts if d.resume_id]
    resumes = {
        r.id: r for r in db.query(Resume).filter(Resume.id.in_(resume_ids)).all()
    } if resume_ids else {}

    items = []
    for d in drafts:
        contact = contact_map.get(d.contact_id) if d.contact_id else None
        application = applications.get(d.application_id)
        job = jobs.get(application.job_id) if application else None
        company = companies.get(job.company_id) if job and job.company_id else None
        resume = resumes.get(d.resume_id) if d.resume_id else None
        items.append(
            {
                "id": str(d.id),
                "subject": d.subject,
                "body": d.body,
                "approval_status": d.approval_status,
                "outreach_type": d.outreach_type,
                "match_score_snapshot": d.match_score_snapshot,
                "to_email": contact.email if contact else None,
                "to_name": contact.full_name if contact else None,
                "email_status": contact.email_status if contact else None,
                "job_title": job.title if job else None,
                "company_name": company.name if company else None,
                "company_hint": company.name if company else None,
                "source_url": job.source_url if job else None,
                "source": job.source if job else None,
                "resume_id": str(resume.id) if resume else None,
                "resume_name": resume.name if resume else None,
                "is_sent": d.id in sent_draft_ids,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )
    return {"total": len(items), "items": items}


@router.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: str, db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id, EmailDraft.user_id == user_id).one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.approval_status = "approved"
    db.commit()
    return {"id": str(draft.id), "approval_status": draft.approval_status}


@router.post("/drafts/{draft_id}/send")
def send_one(draft_id: str, db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    from app.db.models import UserSettings
    from app.services.outreach import _sent_today

    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id, EmailDraft.user_id == user_id).one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).one_or_none()
    daily_limit = (settings.daily_send_limit if settings else None) or 30
    if _sent_today(db, user_id) >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily send limit reached ({daily_limit}). More emails go out tomorrow.",
        )
    if draft.approval_status != "approved":
        draft.approval_status = "approved"
        db.commit()
    try:
        result = send_draft(db, user_id, draft)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sent")
def list_sent(limit: int = 30, db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    rows = (
        db.query(EmailMessage)
        .filter(EmailMessage.user_id == user_id, EmailMessage.direction == "outbound")
        .order_by(EmailMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(m.id),
                "to_email": m.to_email,
                "subject": m.subject,
                "thread_id": m.thread_id,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in rows
        ],
    }
