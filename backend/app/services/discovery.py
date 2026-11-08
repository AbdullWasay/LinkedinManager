from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Company, Job, UserProfile
from app.db.seed import ensure_default_user
from app.integrations.job_sources import DEFAULT_ADAPTERS
from app.integrations.job_sources.base import DiscoveredJob, JobSourceAdapter
from app.services.activity import log_activity
from app.services.application_mode import detect_for_discovered, is_authentic_opportunity
from app.services.job_freshness import extract_posted_at, freshness_bonus, is_fresh
from app.services.job_matching import score_job
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _profile_dict(profile: UserProfile) -> dict[str, Any]:
    return {
        "professional_background": profile.professional_background or {},
        "target_positions": profile.target_positions or [],
        "target_markets": profile.target_markets or [],
        "employment_types": profile.employment_types or [],
        "match_weights": profile.match_weights or {},
        "extra": (profile.salary_expectations or {}).get("_prefs")
        or {
            "remote_only": True,
            "preferred_currencies": ["USD", "AED", "GBP", "EUR"],
        },
    }


def _get_or_create_company(db: Session, user_id: UUID, name: Optional[str], location: str) -> Optional[Company]:
    if not name:
        return None
    existing = (
        db.query(Company)
        .filter(Company.user_id == user_id, Company.name == name, Company.is_deleted.is_(False))
        .one_or_none()
    )
    if existing:
        return existing
    company = Company(user_id=user_id, name=name, location=location or None, research_status="pending")
    db.add(company)
    db.flush()
    return company


def ingest_discovered_job(
    db: Session,
    user_id: UUID,
    profile_data: dict[str, Any],
    discovered: DiscoveredJob,
    *,
    min_score: float = 55.0,
) -> Optional[Job]:
    if not discovered.source_url:
        return None

    # Remote-only gate (cold website leads are remote-delivered services, always allowed)
    is_cold = discovered.source == "cold_website" or discovered.opportunity_type == "cold_website"
    if (
        not is_cold
        and profile_data.get("extra", {}).get("remote_only", True)
        and not discovered.is_remote
    ):
        return None

    existing = (
        db.query(Job)
        .filter(
            Job.user_id == user_id,
            Job.source == discovered.source,
            Job.source_url == discovered.source_url,
        )
        .one_or_none()
    )

    posted_at = extract_posted_at(discovered)
    # Mass boards must be <= 7 days old. Curated/startup/linkedin/watch pages can be undated.
    board_sources = {"remoteok", "remotive", "jobicy", "arbeitnow"}
    if discovered.source in board_sources:
        # Email-bearing board listings without a parseable date: treat as freshly seen today
        # so authentic contacts are not dropped solely for missing timestamps.
        apply_preview = detect_for_discovered(discovered)
        has_email = bool(apply_preview.get("apply_email"))
        if posted_at is None and has_email:
            posted_at = datetime.now(timezone.utc)
        elif posted_at is None or not is_fresh(posted_at):
            return None
    elif posted_at is not None and not is_fresh(posted_at):
        return None

    if is_cold:
        # Cold website offers are not job matches — keep them high priority for outreach.
        match = {
            "match_score": 82.0,
            "recommended_action": "apply",
            "relevant_strengths": ["website", "full stack", "freelance"],
            "missing_requirements": [],
            "potential_concerns": [],
            "breakdown": {"cold_website": 82.0},
        }
    else:
        match = score_job(
            {
                "title": discovered.title,
                "description": discovered.description,
                "location": discovered.location,
                "employment_type": discovered.employment_type,
                "is_remote": discovered.is_remote,
                "salary_range": discovered.salary_range,
            },
            profile_data,
        )
        match["match_score"] = float(match.get("match_score") or 0) + freshness_bonus(posted_at)
    apply_meta = detect_for_discovered(discovered)
    # Default board-extracted emails without status are treated as listed only for
    # non-mass-board sources; guessed contacts are never authentic.
    if apply_meta.get("application_mode") == "email" and apply_meta.get("apply_email"):
        apply_meta.setdefault("email_status", "listed")
    match = {
        **match,
        "application": apply_meta,
        "posted_at": posted_at.isoformat() if posted_at else None,
        "freshness": "24h" if freshness_bonus(posted_at) >= 8 else ("7d" if posted_at else "unknown"),
    }
    if apply_meta["manual_apply_required"]:
        if match.get("recommended_action") == "apply":
            match["recommended_action"] = "manual_apply"
        match.setdefault("potential_concerns", [])
        if "Requires manual application via company/job-board form" not in match["potential_concerns"]:
            match["potential_concerns"].append("Requires manual application via company/job-board form")

    if not is_authentic_opportunity(apply_meta):
        # Soft-delete stale copies that lost authenticity (e.g. guessed emails)
        if existing and not existing.is_deleted:
            existing.is_deleted = True
            existing.version += 1
            db.flush()
        return None

    if match["match_score"] < min_score and match["recommended_action"] == "skip":
        return None

    company = _get_or_create_company(db, user_id, discovered.company_name, discovered.location)

    if existing:
        existing.is_deleted = False
        existing.title = discovered.title
        existing.description = discovered.description
        existing.location = discovered.location
        existing.employment_type = discovered.employment_type
        existing.is_remote = discovered.is_remote
        existing.salary_range = discovered.salary_range or existing.salary_range
        existing.match_score = match["match_score"]
        existing.match_details = match
        existing.raw_payload = discovered.raw_payload
        existing.application_mode = apply_meta["application_mode"]
        existing.apply_url = apply_meta.get("apply_url") or discovered.source_url
        existing.apply_email = apply_meta.get("apply_email")
        existing.manual_apply_required = bool(apply_meta["manual_apply_required"])
        if posted_at:
            existing.posted_at = posted_at
        if company:
            existing.company_id = company.id
        existing.version += 1
        return existing

    job = Job(
        user_id=user_id,
        company_id=company.id if company else None,
        title=discovered.title,
        description=discovered.description,
        source=discovered.source,
        source_url=discovered.source_url,
        location=discovered.location,
        employment_type=discovered.employment_type,
        is_remote=discovered.is_remote,
        salary_range=discovered.salary_range or None,
        opportunity_type=discovered.opportunity_type,
        application_mode=apply_meta["application_mode"],
        apply_url=apply_meta.get("apply_url") or discovered.source_url,
        apply_email=apply_meta.get("apply_email"),
        manual_apply_required=bool(apply_meta["manual_apply_required"]),
        manual_apply_status="pending" if apply_meta["manual_apply_required"] else "skipped",
        status="qualified" if match["match_score"] >= 70 else "discovered",
        match_score=match["match_score"],
        match_details=match,
        raw_payload=discovered.raw_payload,
        posted_at=posted_at or datetime.now(timezone.utc),
    )
    db.add(job)
    return job


def run_discovery(
    db: Session,
    *,
    adapters: Optional[list[JobSourceAdapter]] = None,
    min_score: float = 55.0,
) -> dict[str, Any]:
    user = ensure_default_user(db)
    if user.profile is None:
        raise RuntimeError("Profile missing")

    profile_data = _profile_dict(user.profile)
    adapters = adapters or DEFAULT_ADAPTERS

    fetched = 0
    saved = 0
    updated = 0
    errors: list[dict[str, str]] = []
    by_source: dict[str, int] = {}

    for adapter in adapters:
        try:
            discovered_jobs = adapter.fetch()
        except Exception as exc:
            logger.exception("Adapter %s failed", adapter.name)
            errors.append({"source": adapter.name, "error": str(exc)})
            continue

        by_source[adapter.name] = 0
        for discovered in discovered_jobs:
            fetched += 1
            before = (
                db.query(Job.id)
                .filter(
                    Job.user_id == user.id,
                    Job.source == discovered.source,
                    Job.source_url == discovered.source_url,
                )
                .one_or_none()
            )
            job = ingest_discovered_job(db, user.id, profile_data, discovered, min_score=min_score)
            if job is None:
                continue
            by_source[adapter.name] += 1
            if before:
                updated += 1
            else:
                saved += 1

    db.commit()
    log_activity(
        db,
        user_id=user.id,
        category="agent",
        action="job_discovery",
        message=f"Discovery complete: fetched={fetched}, new={saved}, updated={updated}",
        details={"by_source": by_source, "errors": errors, "min_score": min_score},
        status="warning" if errors else "success",
    )
    return {
        "fetched": fetched,
        "saved": saved,
        "updated": updated,
        "by_source": by_source,
        "errors": errors,
    }
