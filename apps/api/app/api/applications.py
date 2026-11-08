from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Application, Company, Contact, Job
from app.db.session import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
def list_applications(
    stage: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    q = db.query(Application).filter(Application.user_id == user_id, Application.is_deleted.is_(False))
    if stage:
        if stage == "applied":
            q = q.filter(Application.stage.in_(["sent", "replied", "interview", "offer"]))
        else:
            q = q.filter(Application.stage == stage)
    apps = q.order_by(Application.updated_at.desc()).limit(limit).all()
    job_ids = [a.job_id for a in apps]
    company_ids = [a.company_id for a in apps if a.company_id]
    contact_ids = [a.contact_id for a in apps if a.contact_id]
    jobs = {j.id: j for j in db.query(Job).filter(Job.id.in_(job_ids)).all()} if job_ids else {}
    companies = {
        c.id: c for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
    } if company_ids else {}
    contacts = {
        c.id: c for c in db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
    } if contact_ids else {}

    items = []
    for a in apps:
        job = jobs.get(a.job_id)
        company = companies.get(a.company_id) if a.company_id else None
        contact = contacts.get(a.contact_id) if a.contact_id else None
        items.append(
            {
                "id": str(a.id),
                "stage": a.stage,
                "notes": a.notes,
                "thread_id": a.thread_id,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                "job_title": job.title if job else None,
                "job_location": job.location if job else None,
                "source_url": job.source_url if job else None,
                "match_score": job.match_score if job else None,
                "opportunity_type": job.opportunity_type if job else None,
                "job_source": job.source if job else None,
                "company_name": company.name if company else None,
                "contact_email": contact.email if contact else (job.apply_email if job else None),
                "contact_name": contact.full_name if contact else None,
            }
        )
    return {"total": len(items), "items": items}
