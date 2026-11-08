from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import Application, Company, Job
from app.db.session import get_db
from app.integrations.google import sheets as sheets_integration
from app.schemas.jobs import DiscoveryRunResponse, JobListResponse, JobResponse, ManualApplyUpdate
from app.services.application_mode import detect_application_mode, is_authentic_job_row
from app.services.discovery import run_discovery

SENT_APPLICATION_STAGES = ("sent", "replied", "interview", "offer")


def _exclude_sent_job_ids(db: Session, user_id: UUID, query):
    """Hide opportunities that already had outreach emailed — those live under Applied."""
    sent_job_ids = (
        db.query(Application.job_id)
        .filter(
            Application.user_id == user_id,
            Application.is_deleted.is_(False),
            Application.stage.in_(SENT_APPLICATION_STAGES),
        )
        .subquery()
    )
    return query.filter(~Job.id.in_(sent_job_ids))


def _merge_apply_meta(job: Job, apply_meta: dict) -> None:
    details = dict(job.match_details or {})
    details["application"] = {
        **(details.get("application") or {}),
        "detection_reason": apply_meta.get("detection_reason"),
        "email_status": apply_meta.get("email_status"),
        "apply_method": apply_meta.get("apply_method"),
        "api_endpoint": apply_meta.get("api_endpoint"),
    }
    job.match_details = details
    job.application_mode = apply_meta.get("application_mode") or job.application_mode
    job.apply_url = apply_meta.get("apply_url") or job.apply_url
    job.apply_email = apply_meta.get("apply_email")
    job.manual_apply_required = bool(apply_meta.get("manual_apply_required", True))
    job.version += 1

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_response(job: Job, company_name: Optional[str] = None) -> JobResponse:
    return JobResponse(
        id=job.id,
        title=job.title,
        company_id=job.company_id,
        company_name=company_name,
        description=job.description,
        source=job.source,
        source_url=job.source_url,
        location=job.location,
        employment_type=job.employment_type,
        is_remote=job.is_remote,
        salary_range=job.salary_range,
        opportunity_type=job.opportunity_type,
        application_mode=job.application_mode,
        apply_url=job.apply_url,
        apply_email=job.apply_email,
        manual_apply_required=job.manual_apply_required,
        manual_apply_status=job.manual_apply_status,
        status=job.status,
        match_score=job.match_score,
        match_details=job.match_details or {},
        discovered_at=job.discovered_at,
        posted_at=job.posted_at,
        updated_at=job.updated_at,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    remote_only: bool = True,
    manual_apply_required: Optional[bool] = None,
    application_mode: Optional[str] = None,
    manual_apply_status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobListResponse:
    q = db.query(Job).filter(Job.user_id == user_id, Job.is_deleted.is_(False))
    # Cold website leads have their own tab.
    q = q.filter(Job.source != "cold_website")
    q = _exclude_sent_job_ids(db, user_id, q)
    if status:
        q = q.filter(Job.status == status)
    if min_score is not None:
        q = q.filter(Job.match_score >= min_score)
    if remote_only:
        q = q.filter(Job.is_remote.is_(True))
    if manual_apply_required is not None:
        q = q.filter(Job.manual_apply_required.is_(manual_apply_required))
    if application_mode:
        q = q.filter(Job.application_mode == application_mode)
    if manual_apply_status:
        q = q.filter(Job.manual_apply_status == manual_apply_status)
    total = q.count()
    # Prefer freshest postings, then match score
    jobs = (
        q.order_by(Job.posted_at.desc().nullslast(), Job.match_score.desc().nullslast(), Job.discovered_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    company_ids = [j.company_id for j in jobs if j.company_id]
    companies = {}
    if company_ids:
        companies = {
            c.id: c.name
            for c in db.query(Company).filter(Company.id.in_(company_ids)).all()
        }

    return JobListResponse(
        total=total,
        items=[_to_response(j, companies.get(j.company_id) if j.company_id else None) for j in jobs],
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobResponse:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    company_name = None
    if job.company_id:
        company = db.query(Company).filter(Company.id == job.company_id).one_or_none()
        company_name = company.name if company else None
    return _to_response(job, company_name)


@router.patch("/{job_id}/manual-apply", response_model=JobResponse)
def update_manual_apply(
    job_id: UUID,
    payload: ManualApplyUpdate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> JobResponse:
    allowed = {"pending", "reminded", "applied", "skipped"}
    if payload.manual_apply_status not in allowed:
        raise HTTPException(status_code=400, detail=f"manual_apply_status must be one of {sorted(allowed)}")
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.manual_apply_status = payload.manual_apply_status
    if payload.manual_apply_status == "applied" and job.status in {"discovered", "qualified", "researched", "drafted"}:
        job.status = "sent"
    job.version += 1
    db.commit()
    db.refresh(job)
    company_name = None
    if job.company_id:
        company = db.query(Company).filter(Company.id == job.company_id).one_or_none()
        company_name = company.name if company else None
    return _to_response(job, company_name)


@router.post("/reclassify-apply-mode")
def reclassify_apply_mode(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    jobs = db.query(Job).filter(Job.user_id == user_id, Job.is_deleted.is_(False)).all()
    updated = 0
    for job in jobs:
        meta = detect_application_mode(
            source_url=job.source_url or "",
            description=job.description or "",
            raw_payload=job.raw_payload or {},
            source=job.source,
        )
        job.application_mode = meta["application_mode"]
        job.apply_url = meta.get("apply_url") or job.source_url
        job.apply_email = meta.get("apply_email")
        job.manual_apply_required = bool(meta["manual_apply_required"])
        if job.manual_apply_required and job.manual_apply_status not in {"applied", "skipped", "reminded"}:
            job.manual_apply_status = "pending"
        details = dict(job.match_details or {})
        details["application"] = meta
        if job.manual_apply_required:
            concerns = list(details.get("potential_concerns") or [])
            note = "Requires manual application via company/job-board form"
            if note not in concerns:
                concerns.append(note)
            details["potential_concerns"] = concerns
            if details.get("recommended_action") == "apply":
                details["recommended_action"] = "manual_apply"
        job.match_details = details
        job.version += 1
        updated += 1
    db.commit()
    try:
        sheets_integration.push_all(db, user_id)
    except Exception as exc:
        return {"updated": updated, "sheets_error": str(exc)}
    return {"updated": updated}


@router.post("/purge-inauthentic")
def purge_inauthentic_jobs(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    """Soft-delete API-apply roles, form scrapes, guessed emails, and jobs with no email path."""
    jobs = db.query(Job).filter(Job.user_id == user_id, Job.is_deleted.is_(False)).all()
    removed = 0
    kept = 0
    reasons: dict[str, int] = {}
    for job in jobs:
        if is_authentic_job_row(job):
            kept += 1
            continue
        job.is_deleted = True
        job.version += 1
        removed += 1
        key = job.application_mode or "unknown"
        reasons[key] = reasons.get(key, 0) + 1
    db.commit()
    try:
        sheets_integration.push_all(db, user_id)
    except Exception as exc:
        return {"kept": kept, "removed": removed, "by_mode": reasons, "sheets_error": str(exc)}
    return {"kept": kept, "removed": removed, "by_mode": reasons}


@router.post("/reclassify-modes")
def reclassify_application_modes(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    """Re-run application-mode detection for existing jobs (e.g. API apply listings)."""
    jobs = db.query(Job).filter(Job.user_id == user_id, Job.is_deleted.is_(False)).all()
    changed = 0
    by_mode: dict[str, int] = {}
    for job in jobs:
        meta = detect_application_mode(
            source_url=job.source_url or "",
            description=job.description or "",
            raw_payload=job.raw_payload or {},
            source=job.source,
        )
        mode = meta.get("application_mode") or "unknown"
        by_mode[mode] = by_mode.get(mode, 0) + 1
        if (
            job.application_mode != mode
            or (job.apply_url or None) != (meta.get("apply_url") or None)
            or bool(job.manual_apply_required) != bool(meta.get("manual_apply_required", True))
        ):
            _merge_apply_meta(job, meta)
            changed += 1
    db.commit()
    try:
        sheets_integration.push_all(db, user_id)
    except Exception as exc:
        return {"scanned": len(jobs), "changed": changed, "by_mode": by_mode, "sheets_error": str(exc)}
    return {"scanned": len(jobs), "changed": changed, "by_mode": by_mode}


@router.post("/discover", response_model=DiscoveryRunResponse)
def discover_jobs(
    sync_sheets: bool = True,
    min_score: float = Query(default=55.0, ge=0, le=100),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> DiscoveryRunResponse:
    try:
        result = run_discovery(db, min_score=min_score)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Discovery failed: {exc}") from exc

    if sync_sheets:
        try:
            sheets_integration.push_all(db, user_id)
        except Exception as exc:
            # Don't fail discovery if sheets sync fails; surface as error entry.
            result["errors"].append({"source": "sheets_sync", "error": str(exc)})

    return DiscoveryRunResponse(**result)
