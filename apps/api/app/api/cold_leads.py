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
from app.integrations.job_sources.cold_website import ColdWebsiteAdapter, lead_to_discovered
from app.services.cold_lead_validation import (
    email_is_personal,
    validate_cold_website_lead,
)
from app.services.discovery import _profile_dict, ingest_discovered_job
from app.services.outreach import create_draft_for_job

router = APIRouter(prefix="/cold-leads", tags=["cold-leads"])


class ColdLeadIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    owner_name: str = Field(min_length=2, max_length=255)
    owner_email: str = Field(min_length=5, max_length=320)
    market: str = Field(min_length=2, max_length=64, description="UK or US")
    city: Optional[str] = Field(default=None, max_length=128)
    business_type: str = Field(default="local business", max_length=128)
    source_url: Optional[str] = Field(default=None, max_length=1024)
    notes: Optional[str] = None
    confirm_no_website: bool = False
    create_draft: bool = True


@router.post("/discover")
def discover_leads(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    """Auto-find UK/US businesses with public emails and no proper website, then queue drafts."""
    user = ensure_default_user(db)
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")
    if user.profile is None:
        raise HTTPException(status_code=400, detail="Profile missing")

    profile = _profile_dict(user.profile)

    fetched = ColdWebsiteAdapter().fetch()
    saved = 0
    drafts = 0
    errors: list[str] = []
    for discovered in fetched:
        try:
            discovered.raw_payload = {
                **(discovered.raw_payload or {}),
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "confirmed_no_website": True,
            }
            job = ingest_discovered_job(db, user_id, profile, discovered, min_score=40.0)
            if job is None:
                continue
            saved += 1
            try:
                # Cold website offers are queued for send (same as previous manual flow).
                draft = create_draft_for_job(db, user, user.profile, job, auto_approve=True)
                if draft:
                    drafts += 1
            except Exception as exc:
                errors.append(f"{job.title}: draft failed — {exc}")
        except Exception as exc:
            errors.append(str(exc))
    db.commit()
    return {
        "fetched": len(fetched),
        "saved": saved,
        "drafts_created": drafts,
        "auto_approved": True,
        "errors": errors[:10],
        "message": (
            f"Found {len(fetched)} candidates, saved {saved}, queued {drafts} emails. "
            "They join the automatic send queue when auto-send is on."
        ),
    }


@router.get("")
def list_leads(db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user_id)) -> dict:
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user_id, Job.is_deleted.is_(False), Job.source == "cold_website")
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
                "location": j.location,
                "source_url": j.source_url,
                "apply_email": j.apply_email,
                "status": j.status,
                "match_score": j.match_score,
                "business_type": (j.raw_payload or {}).get("business_type"),
                "market": (j.raw_payload or {}).get("market"),
            }
            for j in jobs
        ],
    }


@router.post("")
def add_lead(
    payload: ColdLeadIn,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = ensure_default_user(db)
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")
    if user.profile is None:
        raise HTTPException(status_code=400, detail="Profile missing")
    if not payload.confirm_no_website:
        raise HTTPException(
            status_code=400,
            detail="Confirm this UK/US business has no website before saving",
        )

    errors = validate_cold_website_lead(
        business_name=payload.business_name,
        owner_name=payload.owner_name,
        owner_email=payload.owner_email,
        market=payload.market,
        city=payload.city,
        source_url=payload.source_url,
    )
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    personal = email_is_personal(payload.owner_email)
    discovered = lead_to_discovered(
        business_name=payload.business_name,
        owner_name=payload.owner_name,
        owner_email=str(payload.owner_email),
        market=payload.market,
        city=payload.city or "",
        business_type=payload.business_type,
        source_url=payload.source_url,
        notes=payload.notes,
        email_status="listed" if not personal else "unverified",
    )
    discovered.raw_payload["posted_at"] = datetime.now(timezone.utc).isoformat()
    discovered.raw_payload["confirmed_no_website"] = True

    job = ingest_discovered_job(
        db,
        user_id,
        _profile_dict(user.profile),
        discovered,
        min_score=40.0,
    )
    if job is None:
        raise HTTPException(status_code=400, detail="Lead was rejected by authenticity/freshness gates")

    draft_id = None
    warning = None
    # Owner emails (including personal Gmail) are fine for cold website offers once confirmed.
    auto_approve = True
    if payload.create_draft:
        try:
            draft = create_draft_for_job(db, user, user.profile, job, auto_approve=auto_approve)
            draft_id = str(draft.id) if draft else None
        except Exception as exc:
            warning = f"Lead saved but draft failed: {exc}"

    db.commit()
    return {
        "job_id": str(job.id),
        "title": job.title,
        "apply_email": job.apply_email,
        "draft_id": draft_id,
        "auto_approved": auto_approve,
        "message": "Cold website lead saved and queued for outreach.",
        "warning": warning,
    }
