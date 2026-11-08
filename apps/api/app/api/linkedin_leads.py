from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Company, Job
from app.db.seed import ensure_default_user
from app.db.session import get_db
from app.integrations.job_sources.linkedin_posters import lead_to_discovered
from app.services.discovery import _profile_dict, ingest_discovered_job
from app.services.linkedin_lead_validation import email_looks_corporate, validate_linkedin_lead
from app.services.outreach import create_draft_for_job

router = APIRouter(prefix="/linkedin-leads", tags=["linkedin-leads"])


class LinkedInLeadIn(BaseModel):
    title: str = Field(min_length=2, max_length=512)
    company_name: str = Field(min_length=2, max_length=255)
    job_url: str = Field(min_length=8, max_length=1024)
    poster_name: str = Field(min_length=2, max_length=255)
    poster_email: str = Field(min_length=5, max_length=320)
    poster_linkedin: Optional[str] = None
    notes: Optional[str] = None
    confirm_real_job: bool = False
    create_draft: bool = True


@router.get("")
def list_leads(db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user_id)) -> dict:
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user_id, Job.is_deleted.is_(False), Job.source == "linkedin_poster")
        .order_by(Job.discovered_at.desc())
        .limit(100)
        .all()
    )
    company_ids = [j.company_id for j in jobs if j.company_id]
    companies = {
        c.id: c.name for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
    } if company_ids else {}
    return {
        "total": len(jobs),
        "items": [
            {
                "id": str(j.id),
                "title": j.title,
                "company_name": companies.get(j.company_id) if j.company_id else None,
                "source_url": j.source_url,
                "apply_email": j.apply_email,
                "posted_at": j.posted_at.isoformat() if j.posted_at else None,
                "match_score": j.match_score,
                "status": j.status,
            }
            for j in jobs
        ],
    }


@router.post("")
def add_lead(
    payload: LinkedInLeadIn,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = ensure_default_user(db)
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")
    if user.profile is None:
        raise HTTPException(status_code=400, detail="Profile missing")

    if not payload.confirm_real_job:
        raise HTTPException(
            status_code=400,
            detail="Confirm this is a real LinkedIn job with a verified recruiter before saving",
        )

    errors = validate_linkedin_lead(
        title=payload.title,
        company_name=payload.company_name,
        job_url=payload.job_url,
        poster_name=payload.poster_name,
        poster_email=payload.poster_email,
        poster_linkedin=payload.poster_linkedin,
    )
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    corporate = email_looks_corporate(payload.poster_email, payload.company_name)
    discovered = lead_to_discovered(
        title=payload.title,
        company_name=payload.company_name,
        job_url=payload.job_url,
        poster_name=payload.poster_name,
        poster_email=str(payload.poster_email),
        poster_linkedin=payload.poster_linkedin,
        notes=payload.notes,
        email_status="listed" if corporate else "unverified",
    )
    discovered.raw_payload["posted_at"] = datetime.now(timezone.utc).isoformat()
    discovered.raw_payload["confirmed_real_job"] = True

    job = ingest_discovered_job(
        db,
        user_id,
        _profile_dict(user.profile),
        discovered,
        min_score=40.0,
    )
    if job is None:
        raise HTTPException(status_code=400, detail="Lead was rejected (not authentic or too old)")

    draft_id = None
    warning = None
    # Only auto-approve corporate/verified-looking recruiter emails into ready-to-send
    auto_approve = corporate
    if payload.create_draft:
        try:
            draft = create_draft_for_job(db, user, user.profile, job, auto_approve=auto_approve)
            draft_id = str(draft.id) if draft else None
            if draft and not auto_approve:
                warning = "Draft created as pending — recruiter email looks personal/unverified"
        except Exception as exc:
            warning = f"Lead saved but draft failed: {exc}"

    db.commit()
    return {
        "job_id": str(job.id),
        "title": job.title,
        "apply_email": job.apply_email,
        "draft_id": draft_id,
        "auto_approved": auto_approve,
        "message": (
            "Verified LinkedIn job lead saved."
            if auto_approve
            else "Lead saved. Draft needs review before ready-to-send."
        ),
        "warning": warning,
    }
