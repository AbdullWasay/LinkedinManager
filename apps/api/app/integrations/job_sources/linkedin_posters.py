"""LinkedIn job-poster outreach leads.

LinkedIn blocks unauthenticated scraping, so leads are added manually (or via
your own research): paste the job post URL + the poster's reachable email.
These are treated as authentic email outreach opportunities.
"""

from __future__ import annotations

from app.integrations.job_sources.base import DiscoveredJob

# Seed examples stay empty — real leads come from POST /linkedin-leads.
LINKEDIN_POSTER_LEADS: list[DiscoveredJob] = []


class LinkedInPosterAdapter:
    name = "linkedin_poster"

    def fetch(self) -> list[DiscoveredJob]:
        return list(LINKEDIN_POSTER_LEADS)


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
    email = poster_email.strip().lower()
    name = (poster_name or "").strip()
    company = (company_name or "").strip() or None
    desc = (
        f"LinkedIn job post outreach. Role: {title}. "
        f"Poster: {name}. Company: {company or 'n/a'}. "
        f"{notes or 'Approach the person who posted the role directly.'}"
    )
    return DiscoveredJob(
        title=title.strip(),
        source="linkedin_poster",
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
            "contact_role": "Recruiter / job poster",
            "email_status": email_status,
            "outreach_type": "linkedin_poster",
            "poster_linkedin": poster_linkedin,
            "posted_at": None,  # filled by API as now
            "source_channel": "linkedin",
        },
    )
