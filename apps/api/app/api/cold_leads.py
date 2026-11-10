from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Application, Company, Job
from app.db.seed import ensure_default_user
from app.db.session import get_db
from app.integrations.job_sources.cold_website import ColdWebsiteAdapter
from app.services.discovery import _profile_dict, ingest_discovered_job
from app.services.outreach import create_draft_for_job

router = APIRouter(prefix="/cold-leads", tags=["cold-leads"])

SENT_APPLICATION_STAGES = ("sent", "replied", "interview", "offer")


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
                draft = create_draft_for_job(db, user, user.profile, job, auto_approve=True)
                if draft:
                    drafts += 1
            except Exception as exc:
                db.rollback()
                user = ensure_default_user(db)
                profile = _profile_dict(user.profile)
                errors.append(f"{discovered.title}: draft failed — {exc}")
        except Exception as exc:
            db.rollback()
            user = ensure_default_user(db)
            profile = _profile_dict(user.profile)
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
    sent_ids = {
        row[0]
        for row in db.query(Application.job_id)
        .filter(
            Application.user_id == user_id,
            Application.is_deleted.is_(False),
            Application.stage.in_(SENT_APPLICATION_STAGES),
        )
        .all()
        if row[0] is not None
    }
    q = db.query(Job).filter(
        Job.user_id == user_id,
        Job.is_deleted.is_(False),
        Job.source == "cold_website",
        Job.status.notin_(["applied", "sent", "rejected", "closed"]),
    )
    if sent_ids:
        q = q.filter(~Job.id.in_(list(sent_ids)))
    jobs = q.order_by(Job.discovered_at.desc()).limit(100).all()
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
def add_lead_removed() -> dict:
    """Manual owner entry is disabled — discovery finds and queues leads automatically."""
    raise HTTPException(
        status_code=410,
        detail=(
            "Manual owner entry is disabled. Use POST /cold-leads/discover "
            "or wait for the scheduled auto-research run."
        ),
    )
