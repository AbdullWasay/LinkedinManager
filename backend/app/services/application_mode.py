from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import pick_apply_email

FORM_HOST_HINTS = (
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "workable.com",
    "apply.workable.com",
    "myworkdayjobs.com",
    "workday.com",
    "smartrecruiters.com",
    "icims.com",
    "bamboohr.com",
    "indeed.com",
    "linkedin.com",
    "wellfound.com",
    "angel.co",
    "remoteok.com",
    "remoteok.io",
    "remotive.com",
    "jobicy.com",
    "builtin.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "dover.com",
    "recruitee.com",
    "personio.de",
    "personio.com",
    "teamtailor.com",
    "jobs.eu",
    "notion.site",
)

FORM_TEXT_HINTS = (
    "apply on our website",
    "apply on the website",
    "application form",
    "fill out the form",
    "submit your application",
    "apply via",
    "click apply",
    "easy apply",
    "apply now",
    "careers page",
    "online application",
)

EMAIL_TEXT_HINTS = (
    "send your cv",
    "send your resume",
    "email your cv",
    "email your resume",
    "send an email",
    "apply by email",
    "email us at",
    "email your application",
    "send applications to",
)

API_APPLY_HINTS = (
    "submit their application via a post request",
    "submit your application via a post request",
    "application via a post request",
    "apply via a post request",
    "post request to our api",
    "we ask candidates to submit their application via a post",
)

API_ENDPOINT_RE = re.compile(r"(?:^|\n)\s*POST\s+(https?://[^\s]+)", re.I | re.M)
API_APPLY_RE = re.compile(
    r"https?://[^\s\"']+/api/[^\s\"']*(?:hiring|apply)[^\s\"']*|"
    r"\"roleSlug\"\s*:",
    re.I,
)

def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def detect_application_mode(
    *,
    source_url: str = "",
    description: str = "",
    raw_payload: Optional[dict[str, Any]] = None,
    source: str = "",
) -> dict[str, Any]:
    """Classify how a candidate should apply.

    Returns:
      application_mode: email | external_form | api_apply | unknown
      apply_url: preferred application URL
      apply_email: extracted email if any
      manual_apply_required: True when user must apply via form themselves
      detection_reason: short explanation
    """
    raw_payload = raw_payload or {}
    description_raw = description or ""
    text = f"{description_raw} {' '.join(str(v) for v in raw_payload.values() if isinstance(v, (str, int, float)))}".lower()
    url = source_url or str(raw_payload.get("url") or raw_payload.get("apply_url") or "")
    host = _host(url)

    # API / POST apply (e.g. Propr-style technical screening)
    endpoint_match = API_ENDPOINT_RE.search(description_raw)
    marker_match = API_APPLY_RE.search(description_raw)
    hint_hit = any(h in text for h in API_APPLY_HINTS)
    if endpoint_match or (hint_hit and marker_match) or (hint_hit and "request body" in text):
        endpoint = endpoint_match.group(1).rstrip(".,);") if endpoint_match else None
        if not endpoint and marker_match:
            maybe = marker_match.group(0)
            if maybe.lower().startswith("http"):
                endpoint = maybe.rstrip(".,);")
        return {
            "application_mode": "api_apply",
            "apply_url": endpoint or url,
            "apply_email": None,
            "manual_apply_required": True,
            "detection_reason": "job asks you to apply with an HTTP POST to their API",
            "apply_method": "POST",
            "api_endpoint": endpoint,
        }

    # Explicit override from curated/startup adapters
    payload_email = str(raw_payload.get("apply_email") or "").strip()
    payload_mode = str(raw_payload.get("application_mode") or "").strip().lower()
    if payload_mode == "api_apply":
        endpoint = str(raw_payload.get("api_endpoint") or raw_payload.get("apply_url") or url or "").strip() or None
        return {
            "application_mode": "api_apply",
            "apply_url": endpoint or url,
            "apply_email": None,
            "manual_apply_required": True,
            "detection_reason": raw_payload.get("detection_reason")
            or "listing requires HTTP POST application to company API",
            "apply_method": "POST",
            "api_endpoint": endpoint,
        }
    if payload_mode == "email" and payload_email:
        return {
            "application_mode": "email",
            "apply_url": url,
            "apply_email": payload_email,
            "manual_apply_required": False,
            "detection_reason": "startup/founder listing with direct email contact",
            "email_status": raw_payload.get("email_status") or "verified",
            "contact_name": raw_payload.get("contact_name"),
            "contact_role": raw_payload.get("contact_role"),
            "outreach_type": raw_payload.get("outreach_type") or "founder",
        }

    # Prefer a real hiring/contact email anywhere in the listing — including boards.
    # Boards used to be hard-classified as forms even when careers@ was present.
    apply_email = pick_apply_email(
        description or "",
        url,
        " ".join(str(v) for v in raw_payload.values() if isinstance(v, str)),
        preferred=payload_email or None,
        # Boards: only careers/jobs/talent-style addresses unless payload sets apply_email.
        hiring_only=not bool(payload_email),
    )
    if apply_email:
        reason = "contact email found in listing"
        if any(h in text for h in EMAIL_TEXT_HINTS):
            reason = "explicit email application instructions"
        elif "mailto:" in (description or "").lower() or "mailto:" in url.lower():
            reason = "mailto link found"
        status = str(raw_payload.get("email_status") or "listed")
        return {
            "application_mode": "email",
            "apply_url": url,
            "apply_email": apply_email,
            "manual_apply_required": False,
            "detection_reason": reason,
            "email_status": status if status != "guessed" else "listed",
            "contact_name": raw_payload.get("contact_name"),
            "contact_role": raw_payload.get("contact_role"),
            "outreach_type": raw_payload.get("outreach_type") or "founder",
        }

    if any(h in host for h in FORM_HOST_HINTS) or source in {
        "remoteok",
        "remotive",
        "jobicy",
        "arbeitnow",
        "web_research",
    }:
        return {
            "application_mode": "external_form",
            "apply_url": url,
            "apply_email": None,
            "manual_apply_required": True,
            "detection_reason": "listing uses an external application form / job board",
        }

    if any(h in text for h in FORM_TEXT_HINTS):
        return {
            "application_mode": "external_form",
            "apply_url": url,
            "apply_email": None,
            "manual_apply_required": True,
            "detection_reason": "description points to an online application form",
        }
    # Conservative default: treat as form so we never auto-email by mistake
    return {
        "application_mode": "unknown",
        "apply_url": url,
        "apply_email": None,
        "manual_apply_required": True,
        "detection_reason": "could not confirm email apply path; defaulting to manual review",
    }


def detect_for_discovered(job: DiscoveredJob) -> dict[str, Any]:
    return detect_application_mode(
        source_url=job.source_url,
        description=job.description,
        raw_payload=job.raw_payload,
        source=job.source,
    )


AUTHENTIC_EMAIL_STATUSES = {"verified", "listed"}


def is_authentic_opportunity(apply_meta: dict[str, Any]) -> bool:
    """Keep only roles we can actually act on with a real contact path.

    Authentic means:
    - email outreach with a non-guessed apply email, or
    - explicit API/POST apply instructions
    Form-board scrapes and guessed emails are rejected.
    """
    mode = str(apply_meta.get("application_mode") or "").lower()
    if mode == "api_apply":
        return bool(apply_meta.get("api_endpoint") or apply_meta.get("apply_url"))
    if mode == "email":
        email = str(apply_meta.get("apply_email") or "").strip()
        if not email or "@" not in email:
            return False
        status = str(apply_meta.get("email_status") or "listed").lower()
        if status == "guessed":
            return False
        return status in AUTHENTIC_EMAIL_STATUSES or status in {"unverified", "listed", "verified"}
    return False


def is_authentic_job_row(job: Any) -> bool:
    """Evaluate a persisted Job (or job-like object) for authenticity."""
    details = getattr(job, "match_details", None) or {}
    app = details.get("application") if isinstance(details, dict) else {}
    meta = {
        "application_mode": getattr(job, "application_mode", None) or (app or {}).get("application_mode"),
        "apply_email": getattr(job, "apply_email", None) or (app or {}).get("apply_email"),
        "email_status": (app or {}).get("email_status"),
        "api_endpoint": (app or {}).get("api_endpoint"),
        "apply_url": getattr(job, "apply_url", None) or (app or {}).get("apply_url"),
    }
    # Board-scraped emails with no status: only accept if mode is email and email present
    # and source is startup/curated (not mass boards).
    source = str(getattr(job, "source", "") or "").lower()
    if meta["application_mode"] == "email" and meta["apply_email"] and not meta.get("email_status"):
        if source in {"remoteok", "remotive", "jobicy"}:
            return False
        meta["email_status"] = "listed"
    return is_authentic_opportunity(meta)
