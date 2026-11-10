from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    Application,
    ApplicationEvent,
    BlocklistEntry,
    Company,
    Contact,
    EmailDraft,
    EmailMessage,
    Job,
    Resume,
    UserProfile,
    UserSettings,
)
from app.db.seed import ensure_default_user
from app.integrations.google import drive as drive_integration
from app.integrations.google import gmail as gmail_integration
from app.integrations.job_sources import EMAIL_FIRST_ADAPTERS
from app.services.activity import log_activity
from app.services.discovery import ingest_discovered_job, run_discovery
from app.services.email_generation import generate_outreach_email
from app.services.resume_matching import select_resume_for_job
from app.services.working_hours import is_working_hours

logger = logging.getLogger(__name__)


def _profile_dict(profile: UserProfile) -> dict[str, Any]:
    return {
        "full_name": profile.full_name,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "education": profile.education or {},
        "professional_background": profile.professional_background or {},
        "projects": profile.projects or [],
        "target_positions": profile.target_positions or [],
        "target_markets": profile.target_markets or [],
        "employment_types": profile.employment_types or [],
        "match_weights": profile.match_weights or {},
        "extra": (profile.salary_expectations or {}).get("_prefs") or {},
    }


def _blocked(db: Session, user_id: UUID, email: str, company_name: Optional[str] = None) -> bool:
    now = datetime.now(timezone.utc)
    q = db.query(BlocklistEntry).filter(
        BlocklistEntry.user_id == user_id,
        BlocklistEntry.is_deleted.is_(False),
    )
    entries = q.all()
    email_l = email.lower()
    domain = email_l.split("@")[-1] if "@" in email_l else ""
    company_l = (company_name or "").lower()
    for e in entries:
        if e.expires_at and e.expires_at < now and not e.is_permanent:
            continue
        val = (e.value or "").lower()
        if e.entry_type == "email" and val == email_l:
            return True
        if e.entry_type == "domain" and val == domain:
            return True
        if e.entry_type == "company" and company_l and val == company_l:
            return True
    return False


def _sent_today(db: Session, user_id: UUID) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(EmailMessage.id))
        .filter(
            EmailMessage.user_id == user_id,
            EmailMessage.direction == "outbound",
            EmailMessage.created_at >= start,
        )
        .scalar()
        or 0
    )


def _already_contacted(db: Session, user_id: UUID, email: str, job_id: UUID) -> bool:
    contact_ids = [
        c.id
        for c in db.query(Contact).filter(Contact.user_id == user_id, Contact.email == email).all()
    ]
    if not contact_ids:
        return False
    existing = (
        db.query(Application)
        .filter(
            Application.user_id == user_id,
            Application.job_id == job_id,
            Application.contact_id.in_(contact_ids),
            Application.is_deleted.is_(False),
        )
        .first()
    )
    if existing and existing.stage in {"sent", "replied", "interview", "offer", "approved", "drafted"}:
        return True
    # Also check outbound messages to this email
    prior = (
        db.query(EmailMessage)
        .filter(
            EmailMessage.user_id == user_id,
            EmailMessage.direction == "outbound",
            EmailMessage.to_email == email,
        )
        .first()
    )
    return prior is not None


def upsert_contact_for_job(db: Session, user_id: UUID, job: Job, apply_meta: dict[str, Any]) -> Optional[Contact]:
    email = (apply_meta.get("apply_email") or job.apply_email or "").strip()
    if not email:
        return None
    existing = (
        db.query(Contact)
        .filter(Contact.user_id == user_id, Contact.email == email, Contact.is_deleted.is_(False))
        .order_by(Contact.created_at.asc())
        .first()
    )
    status = apply_meta.get("email_status") or "verified"
    if existing:
        existing.email_status = status if status != "guessed" or existing.email_status == "guessed" else existing.email_status
        if apply_meta.get("contact_name"):
            existing.full_name = apply_meta["contact_name"]
        if apply_meta.get("contact_role"):
            existing.role_title = apply_meta["contact_role"]
        if job.company_id:
            existing.company_id = job.company_id
        return existing

    contact = Contact(
        user_id=user_id,
        company_id=job.company_id,
        full_name=str(apply_meta.get("contact_name") or email.split("@")[0].title()),
        role_title=str(apply_meta.get("contact_role") or "Founder"),
        email=email,
        email_status=status,
        source=job.source,
        notes=f"Auto-discovered for job {job.title}",
    )
    db.add(contact)
    db.flush()
    return contact


def create_draft_for_job(
    db: Session,
    user: Any,
    profile: UserProfile,
    job: Job,
    *,
    auto_approve: bool = False,
) -> Optional[EmailDraft]:
    apply_meta = (job.match_details or {}).get("application") or {}
    if not job.apply_email and not apply_meta.get("apply_email"):
        return None
    if job.id is None:
        db.flush()

    contact = upsert_contact_for_job(db, user.id, job, {**apply_meta, "apply_email": job.apply_email})
    if contact is None or not contact.email:
        return None

    if _blocked(db, user.id, contact.email, None):
        return None
    if _already_contacted(db, user.id, contact.email, job.id):
        return None

    # Skip pure guessed emails for auto-approve path; still allow draft creation with pending
    email_status = contact.email_status or apply_meta.get("email_status") or "unverified"
    outreach_type = str(
        apply_meta.get("outreach_type")
        or (job.raw_payload or {}).get("outreach_type")
        or ("cold_website" if job.source == "cold_website" or job.opportunity_type == "cold_website" else "founder")
    )
    is_cold_website = outreach_type == "cold_website"

    company_name = None
    if job.company_id:
        company = db.query(Company).filter(Company.id == job.company_id).one_or_none()
        company_name = company.name if company else None

    # Cold website offers: portfolio link in body, no CV attachment.
    resume = None if is_cold_website else select_resume_for_job(db, user.id, job)
    generated = generate_outreach_email(
        profile=_profile_dict(profile),
        job={
            "title": job.title,
            "company_name": company_name,
            "description": job.description,
            "location": job.location,
            "salary_range": job.salary_range,
            "source_url": job.source_url,
        },
        contact={
            "full_name": contact.full_name,
            "role_title": contact.role_title,
            "email": contact.email,
        },
        resume_name=resume.name if resume else None,
        attach_resume=bool(
            not is_cold_website
            and resume
            and (resume.local_path or resume.drive_file_id or resume.drive_url)
        ),
        outreach_type=outreach_type,
    )

    application = (
        db.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job.id, Application.is_deleted.is_(False))
        .one_or_none()
    )
    if application is None:
        application = Application(
            user_id=user.id,
            job_id=job.id,
            company_id=job.company_id,
            contact_id=contact.id,
            resume_id=resume.id if resume else None,
            stage="drafted",
        )
        db.add(application)
        db.flush()
        db.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="draft_created",
                payload={
                    "contact_email": contact.email,
                    "resume_id": str(resume.id) if resume else None,
                    "resume_name": resume.name if resume else None,
                },
            )
        )
    else:
        application.contact_id = contact.id
        if resume:
            application.resume_id = resume.id
        application.stage = "drafted" if application.stage in {"discovered", "qualified", "researched"} else application.stage

    existing_draft = (
        db.query(EmailDraft)
        .filter(
            EmailDraft.user_id == user.id,
            EmailDraft.application_id == application.id,
            EmailDraft.approval_status.in_(["pending", "approved"]),
        )
        .one_or_none()
    )
    if existing_draft:
        if resume and existing_draft.resume_id != resume.id:
            existing_draft.resume_id = resume.id
            db.flush()
        return existing_draft

    # Auto-send mode: approve verified/listed emails immediately (no manual review).
    # Guessed emails stay pending and are never auto-sent.
    can_auto = auto_approve and email_status != "guessed"
    draft = EmailDraft(
        user_id=user.id,
        application_id=application.id,
        contact_id=contact.id,
        resume_id=(resume.id if resume else application.resume_id) if not is_cold_website else None,
        subject=generated["subject"],
        body=generated["body"],
        outreach_type=outreach_type,
        approval_status="approved" if can_auto else "pending",
        blocklist_checked_at=datetime.now(timezone.utc),
        duplicate_checked_at=datetime.now(timezone.utc),
        match_score_snapshot=job.match_score,
    )
    db.add(draft)
    db.flush()
    return draft


def send_draft(db: Session, user_id: UUID, draft: EmailDraft) -> dict[str, Any]:
    if draft.approval_status not in {"approved", "edited"}:
        raise ValueError("Draft is not approved for sending")

    contact = db.query(Contact).filter(Contact.id == draft.contact_id).one_or_none()
    if contact is None or not contact.email:
        raise ValueError("Draft has no contact email")
    if contact.email_status == "guessed":
        raise ValueError("Refusing to auto-send guessed email addresses")
    if _blocked(db, user_id, contact.email):
        raise ValueError("Recipient is blocklisted")

    application = db.query(Application).filter(Application.id == draft.application_id).one_or_none()
    job = None
    if application:
        job = db.query(Job).filter(Job.id == application.job_id).one_or_none()
    is_cold_website = draft.outreach_type == "cold_website" or (
        job is not None and (job.source == "cold_website" or job.opportunity_type == "cold_website")
    )

    resume = None
    attachment_path = None
    attach_errors: list[str] = []
    body = draft.body

    if not is_cold_website:
        if draft.resume_id:
            resume = db.query(Resume).filter(Resume.id == draft.resume_id).one_or_none()
        if resume is None and application and application.resume_id:
            resume = db.query(Resume).filter(Resume.id == application.resume_id).one_or_none()
        if resume is None and job:
            resume = select_resume_for_job(db, user_id, job)
            if resume:
                draft.resume_id = resume.id
                application.resume_id = resume.id

        from pathlib import Path

        from app.db.models import Resume as ResumeModel
        from app.services.resume_matching import resume_has_attachable_file

        def _try_attach(candidate: Resume) -> Optional[str]:
            try:
                path = drive_integration.resolve_local_cv_path(
                    db,
                    user_id,
                    local_path=candidate.local_path,
                    drive_file_id=candidate.drive_file_id,
                    drive_url=candidate.drive_url,
                    preferred_name=f"{candidate.variant or 'cv'}.pdf",
                )
                if path and Path(path).exists() and Path(path).stat().st_size > 0:
                    return str(path)
                attach_errors.append(f"{candidate.name}: file missing after resolve")
            except Exception as exc:
                logger.warning("Could not resolve CV attachment for resume %s: %s", candidate.id, exc)
                attach_errors.append(f"{candidate.name}: {exc}")
            return None

        if resume:
            attachment_path = _try_attach(resume)

        # Fallback: any file-backed CV (prefer master/fullstack)
        if not attachment_path:
            fallbacks = (
                db.query(ResumeModel)
                .filter(ResumeModel.user_id == user_id)
                .order_by(ResumeModel.is_master.desc(), ResumeModel.updated_at.desc())
                .all()
            )
            for candidate in fallbacks:
                if resume and candidate.id == resume.id:
                    continue
                if not resume_has_attachable_file(candidate):
                    continue
                attachment_path = _try_attach(candidate)
                if attachment_path:
                    resume = candidate
                    draft.resume_id = candidate.id
                    if application:
                        application.resume_id = candidate.id
                    break

        if not attachment_path:
            raise ValueError(
                "CV was not attached. Upload the PDF on the CVs page (Drive links need Google reconnect "
                "with Drive read access). "
                + ("; ".join(attach_errors[:2]) if attach_errors else "")
            )

        if "attached" not in body.lower():
            body = body.rstrip() + f"\n\nI've attached my {resume.name if resume else 'CV'} for convenience.\n"

    sent = gmail_integration.send_email(
        db,
        user_id,
        to_email=contact.email,
        subject=draft.subject,
        body=body,
        attachment_path=attachment_path,
        thread_id=application.thread_id if application else None,
    )

    msg = EmailMessage(
        user_id=user_id,
        application_id=draft.application_id,
        draft_id=draft.id,
        direction="outbound",
        gmail_message_id=sent.get("gmail_message_id"),
        thread_id=sent.get("thread_id"),
        from_email=None,
        to_email=contact.email,
        subject=draft.subject,
        body=body,
        labels=sent.get("label_ids") or [],
        sent_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    draft.approval_status = "approved"
    if application:
        application.stage = "sent"
        application.thread_id = sent.get("thread_id")
        db.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="email_sent",
                payload={
                    "gmail_message_id": sent.get("gmail_message_id"),
                    "to": contact.email,
                    "resume_id": str(resume.id) if resume else None,
                    "resume_name": resume.name if resume else None,
                    "attachment": bool(attachment_path),
                },
            )
        )
    # Keep pipeline tabs clean: sent opportunities belong under Applied.
    if job is not None:
        job.status = "applied"
        job.version = (job.version or 1) + 1
    contact.last_contacted_at = datetime.now(timezone.utc)
    db.commit()
    return sent


def run_daily_outreach(
    db: Session,
    *,
    discover: bool = True,
    max_send: Optional[int] = None,
    force_auto_send: bool = False,
) -> dict[str, Any]:
    user = ensure_default_user(db)
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).one()
    profile = user.profile
    if profile is None:
        raise RuntimeError("Profile missing")

    if settings.emergency_stop or settings.automation_paused:
        return {"skipped": True, "reason": "automation_paused_or_stopped"}

    result: dict[str, Any] = {
        "discovered": {},
        "drafts_created": 0,
        "emails_sent": 0,
        "skipped_guessed": 0,
        "deferred_off_hours": 0,
        "errors": [],
    }

    if discover:
        result["discovered"] = run_discovery(db, adapters=EMAIL_FIRST_ADAPTERS, min_score=50.0)

    # Prefer templates during bulk drafting so rate-limits don't stall the 30/day pipeline.
    try:
        from app.integrations.llm import _trip_cooldown

        _trip_cooldown(90.0)
    except Exception:
        pass

    # Prefer high-match email jobs that still need a draft / send.
    jobs = (
        db.query(Job)
        .filter(
            Job.user_id == user.id,
            Job.is_deleted.is_(False),
            Job.application_mode == "email",
            Job.apply_email.isnot(None),
            Job.status.notin_(["sent", "replied", "interview", "offer", "rejected", "closed"]),
        )
        .order_by(Job.match_score.desc().nullslast(), Job.discovered_at.desc())
        .limit(120)
        .all()
    )

    auto_send = bool(settings.auto_send_enabled or force_auto_send)
    daily_limit = settings.daily_send_limit or 30
    already = _sent_today(db, user.id)
    remaining = max(0, daily_limit - already)
    if max_send is not None:
        remaining = min(remaining, max_send)

    drafts: list[EmailDraft] = []
    for job in jobs:
        try:
            draft = create_draft_for_job(db, user, profile, job, auto_approve=auto_send)
            if draft:
                drafts.append(draft)
                # Count newly drafted applications still in drafted stage as pipeline progress.
                if draft.approval_status in {"pending", "approved", "edited"}:
                    result["drafts_created"] += 1
        except Exception as exc:
            result["errors"].append({"job_id": str(job.id), "error": str(exc)})
    db.commit()

    if auto_send and remaining > 0:
        approved = (
            db.query(EmailDraft)
            .filter(
                EmailDraft.user_id == user.id,
                EmailDraft.approval_status == "approved",
            )
            .order_by(EmailDraft.created_at.asc())
            .all()
        )
        # Only send drafts that haven't been sent yet
        sent_draft_ids = {
            m.draft_id
            for m in db.query(EmailMessage)
            .filter(EmailMessage.user_id == user.id, EmailMessage.draft_id.isnot(None))
            .all()
        }
        profile_markets = list(profile.target_markets or [])
        for draft in approved:
            if remaining <= 0:
                break
            if draft.id in sent_draft_ids:
                continue
            contact = db.query(Contact).filter(Contact.id == draft.contact_id).one_or_none()
            if contact and contact.email_status == "guessed":
                result["skipped_guessed"] += 1
                continue

            application = db.query(Application).filter(Application.id == draft.application_id).one_or_none()
            job = db.query(Job).filter(Job.id == application.job_id).one_or_none() if application else None
            hours = is_working_hours(
                location=job.location if job else None,
                markets=profile_markets,
            )
            if not hours["in_working_hours"]:
                result["deferred_off_hours"] += 1
                continue

            try:
                send_draft(db, user.id, draft)
                result["emails_sent"] += 1
                remaining -= 1
            except Exception as exc:
                logger.exception("Failed sending draft %s", draft.id)
                result["errors"].append({"draft_id": str(draft.id), "error": str(exc)})
                db.rollback()

    log_activity(
        db,
        user_id=user.id,
        category="email",
        action="daily_outreach",
        message=(
            f"Outreach run: drafts={result['drafts_created']}, sent={result['emails_sent']}, "
            f"skipped_guessed={result['skipped_guessed']}"
        ),
        details=result,
        status="warning" if result["errors"] else "success",
    )
    return result
