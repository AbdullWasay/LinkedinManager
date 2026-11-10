"""Extract hiring-relevant emails from job text / payloads."""

from __future__ import annotations

import re
from typing import Iterable, Optional

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
MAILTO_RE = re.compile(r"mailto:([^\s\"'<>]+)", re.I)

NOISE_LOCAL_PARTS = {
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "mailer-daemon",
    "postmaster",
    "bounce",
    "bounces",
    "unsubscribe",
    "newsletter",
    "marketing",
    "notifications",
    "notification",
    "alerts",
    "alert",
    "privacy",
    "legal",
    "compliance",
    "accommodations",
    "accommodation",
    "accomodations",  # common misspelling in listings
    "accomodation",
    "hiringaccommodation",
    "hiringaccomodation",
    "webmaster",
    "abuse",
    "example",
    "test",
    "spam",
    "security",
    "support",
    "help",
    "info",
    "press",
    "media",
    "sales",
    "billing",
    "finance",
    "accounts",
    "accounting",
    "paypal",
    "stripe",
}
FAKE_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "email.com",
    "test.com",
    "domain.com",
    "sentry.io",
    "wixpress.com",
    "googleapis.com",
    "schema.org",
    "placeholder.workatastartup.com",
}

# Shared inboxes / apply portals that are not a real hiring contact.
BLOCKED_EXACT_EMAILS = {
    "workatastartup@ycombinator.com",
    "jobs@ycombinator.com",
    "apply@ycombinator.com",
}

HIRING_LOCAL_HINTS = (
    "career",
    "jobs",
    "job",
    "hiring",
    "talent",
    "people",
    "join",
    "apply",
    "hr",
    "recruit",
    "team",
    "founder",
    "hello",
    "work",
    "opportunity",
)


def _clean(email: str) -> str:
    # Strip trailing junk that shows up in scraped mailto / HTML entities.
    return email.strip().strip(".,);]>\"'\\/").lower()


def is_noise_email(email: str) -> bool:
    e = _clean(email)
    if "@" not in e:
        return True
    if e in BLOCKED_EXACT_EMAILS:
        return True
    local, _, domain = e.partition("@")
    if not local or not domain or "." not in domain:
        return True
    if domain in FAKE_DOMAINS or domain.endswith(".example") or domain.endswith(".workatastartup.com"):
        return True
    if local in NOISE_LOCAL_PARTS:
        return True
    if any(
        p in local
        for p in (
            "noreply",
            "no-reply",
            "mailer-",
            "accommodat",
            "accomodat",
            "unsubscribe",
        )
    ):
        return True
    return False


def is_hiring_looking_email(email: str) -> bool:
    e = _clean(email)
    if is_noise_email(e):
        return False
    local = e.split("@", 1)[0]
    return any(h in local for h in HIRING_LOCAL_HINTS)


def extract_emails(*blobs: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for blob in blobs:
        if not blob:
            continue
        for match in MAILTO_RE.findall(blob):
            e = _clean(match)
            if e and e not in seen and not is_noise_email(e):
                seen.add(e)
                found.append(e)
        for match in EMAIL_RE.findall(blob):
            e = _clean(match)
            if e and e not in seen and not is_noise_email(e):
                seen.add(e)
                found.append(e)
    return found


def pick_apply_email(
    *blobs: str,
    preferred: Optional[str] = None,
    hiring_only: bool = True,
) -> Optional[str]:
    """Pick a contact email.

    hiring_only=True (default): only careers/jobs/talent/recruit/people/etc.
    Avoids support/security/accommodations noise that appears in many board HTML pages.
    """
    # Explicit/curated contacts (preferred) are kept unless they are noise.
    # Scraped board text still requires a hiring-looking local-part by default.
    if preferred:
        pref = _clean(preferred)
        if pref and not is_noise_email(pref):
            return pref
    emails = extract_emails(*blobs)
    if not emails:
        return None
    hiring = [e for e in emails if is_hiring_looking_email(e)]
    if hiring:
        return hiring[0]
    if hiring_only:
        return None
    return emails[0]


def enrich_payload_with_email(payload: dict, *blobs: str) -> dict:
    """Copy payload and set apply_email / application_mode when a real email is present."""
    out = dict(payload or {})
    existing = str(out.get("apply_email") or "").strip()
    email = pick_apply_email(*blobs, preferred=existing or None)
    if not email:
        return out
    out["apply_email"] = email
    if not out.get("application_mode"):
        out["application_mode"] = "email"
    out.setdefault("email_status", "listed")
    out.setdefault("outreach_type", "founder")
    return out
