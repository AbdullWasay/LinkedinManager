"""LinkedIn leads page uses automated founder/hiring research.

LinkedIn blocks unauthenticated scraping, so discovery pulls public founder /
startup hiring posts that already list an email (HN Who is hiring, YC pages,
startup boards). Manual paste is disabled.
"""

from __future__ import annotations

from app.integrations.job_sources.base import DiscoveredJob
from app.integrations.job_sources.founder_hiring import FounderHiringAdapter

LINKEDIN_POSTER_LEADS: list[DiscoveredJob] = []


class LinkedInPosterAdapter(FounderHiringAdapter):
    """Alias used by discovery — fetches founder_hiring leads automatically."""

    name = "founder_hiring"


def lead_to_discovered(
    *,
    title: str,
    company_name: str | None,
    job_url: str,
    poster_name: str | None,
    poster_email: str,
    poster_linkedin: str | None = None,
    notes: str | None = None,
    email_status: str = "listed",
) -> DiscoveredJob:
    """Legacy helper kept for any leftover callers."""
    email = poster_email.strip().lower()
    name = (poster_name or "").strip()
    company = (company_name or "").strip() or None
    desc = (
        f"Founder / hiring outreach. Role: {title}. "
        f"Contact: {name}. Company: {company or 'n/a'}. "
        f"{notes or 'Approach the person hiring directly.'}"
    )
    return DiscoveredJob(
        title=title.strip(),
        source="founder_hiring",
        source_url=job_url.strip(),
        company_name=company,
        description=desc,
        location="Remote",
        employment_type="full-time",
        is_remote=True,
        salary_range="",
        opportunity_type="vacancy",
        raw_payload={
            "application_mode": "email",
            "apply_email": email,
            "contact_name": name,
            "contact_role": "Founder / hiring",
            "email_status": email_status,
            "outreach_type": "founder",
            "poster_linkedin": poster_linkedin,
            "posted_at": None,
            "source_channel": "manual_legacy",
        },
    )
