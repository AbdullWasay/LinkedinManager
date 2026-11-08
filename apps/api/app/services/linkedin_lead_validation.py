from __future__ import annotations

import re
from urllib.parse import urlparse

FAKE_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.org",
    "localhost",
    "mailinator.com",
    "guerrillamail.com",
    "yopmail.com",
    "fake.com",
    "email.com",
    "sample.com",
}

# Real LinkedIn job posts look like /jobs/view/1234567890 (usually 8+ digits)
LINKEDIN_JOB_RE = re.compile(
    r"^https?://([a-z]+\.)?linkedin\.com/jobs/view/\d{8,}(/|\?|#|$)",
    re.I,
)
LINKEDIN_PROFILE_RE = re.compile(
    r"^https?://([a-z]+\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?$",
    re.I,
)
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def validate_linkedin_lead(
    *,
    title: str,
    company_name: str | None,
    job_url: str,
    poster_name: str | None,
    poster_email: str,
    poster_linkedin: str | None = None,
) -> list[str]:
    """Return a list of validation errors (empty = ok)."""
    errors: list[str] = []
    title = (title or "").strip()
    company = (company_name or "").strip()
    job_url = (job_url or "").strip()
    poster_name = (poster_name or "").strip()
    poster_email = (poster_email or "").strip().lower()
    poster_linkedin = (poster_linkedin or "").strip()

    if len(title) < 3:
        errors.append("Role title is required")
    if len(company) < 2:
        errors.append("Company name is required for a real job position")
    if len(poster_name) < 2:
        errors.append("Recruiter / poster name is required")

    if not EMAIL_RE.match(poster_email):
        errors.append("Poster email is invalid")
    else:
        domain = poster_email.split("@", 1)[1]
        if domain in FAKE_EMAIL_DOMAINS or domain.endswith(".example") or domain.endswith(".test"):
            errors.append("Fake/test email domains are not allowed")
        if poster_email.startswith("jane@") and domain == "example.com":
            errors.append("Test placeholder emails are not allowed")

    if not LINKEDIN_JOB_RE.match(job_url):
        errors.append(
            "Job URL must be a real LinkedIn job posting like "
            "https://www.linkedin.com/jobs/view/1234567890"
        )
    else:
        # Reject tiny/placeholder numeric ids like /view/123
        m = re.search(r"/jobs/view/(\d+)", job_url)
        if m and len(m.group(1)) < 8:
            errors.append("LinkedIn job id looks fake — paste a live job posting URL")

    if poster_linkedin and not LINKEDIN_PROFILE_RE.match(poster_linkedin):
        errors.append("Poster LinkedIn must look like https://www.linkedin.com/in/username")

    # Soft check: path host
    try:
        host = (urlparse(job_url).hostname or "").lower()
        if host and "linkedin.com" not in host:
            errors.append("Job URL must be on linkedin.com")
    except Exception:
        errors.append("Job URL is invalid")

    return errors


def email_looks_corporate(poster_email: str, company_name: str | None) -> bool:
    """Heuristic: corporate domain preferred over freewebmail for auto-approve."""
    email = (poster_email or "").lower().strip()
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1]
    free = {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
    if domain in free or domain in FAKE_EMAIL_DOMAINS:
        return False
    company = re.sub(r"[^a-z0-9]", "", (company_name or "").lower())
    root = domain.split(".")[0]
    if company and (company in root or root in company):
        return True
    return True  # unknown corporate domain still ok if not free/fake
