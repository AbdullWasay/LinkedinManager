"""Startup / founder-direct openings where email outreach is possible."""

from __future__ import annotations

from app.integrations.job_sources.base import DiscoveredJob

# Public listing emails / founder contacts researched from YC and company pages.
# application_mode forced to email via payload contact fields.
STARTUP_OUTREACH: list[DiscoveredJob] = [
    DiscoveredJob(
        title="Full Stack Engineer",
        source="startup_outreach",
        source_url="https://www.ycombinator.com/companies/adyn/jobs/xV982vp6h-full-stack-engineer",
        company_name="adyn",
        description=(
            "YC startup adyn hiring first full-stack engineer. Python, modern JavaScript/React, AWS, SQL. "
            "Remote (US). Apply by email to careers@adynhealth.com with subject "
            "[Careers] Full Stack Engineer: Last Name, First Name."
        ),
        location="Remote (US)",
        employment_type="full-time",
        is_remote=True,
        salary_range="",
        opportunity_type="vacancy",
        raw_payload={
            "application_mode": "email",
            "apply_email": "careers@adynhealth.com",
            "contact_name": "Hiring Team",
            "contact_role": "Careers",
            "company_domain": "adynhealth.com",
            "email_status": "verified",
            "outreach_type": "founder",
            "startup": True,
        },
    ),
    DiscoveredJob(
        title="Full Stack Engineer",
        source="startup_outreach",
        source_url="https://www.ycombinator.com/companies/stardex/jobs/4oOXnyY-full-stack-engineer",
        company_name="Stardex",
        description=(
            "YC startup Stardex (AI ATS/CRM). Remote full stack: React, Node/TypeScript. "
            "Founder Sanket Chauhan asks candidates to email sanket@stardex.ai."
        ),
        location="Remote",
        employment_type="full-time",
        is_remote=True,
        salary_range="USD 30000-50000",
        opportunity_type="vacancy",
        raw_payload={
            "application_mode": "email",
            "apply_email": "sanket@stardex.ai",
            "contact_name": "Sanket Chauhan",
            "contact_role": "Founder",
            "company_domain": "stardex.ai",
            "email_status": "verified",
            "outreach_type": "founder",
            "startup": True,
        },
    ),
    DiscoveredJob(
        title="Full Stack Software Engineer",
        source="startup_outreach",
        source_url="https://www.ycombinator.com/companies/taskade/jobs/wRpvYFyDo-full-stack-software-engineer",
        company_name="Taskade",
        description=(
            "YC Taskade hiring full-stack software engineer. React, Node, PostgreSQL, AWS, React Native. "
            "Remote US. Founder John Xie: john@taskade.com."
        ),
        location="Remote (US)",
        employment_type="full-time",
        is_remote=True,
        salary_range="",
        opportunity_type="vacancy",
        raw_payload={
            "application_mode": "email",
            "apply_email": "john@taskade.com",
            "contact_name": "John Xie",
            "contact_role": "Founder",
            "company_domain": "taskade.com",
            "email_status": "verified",
            "outreach_type": "founder",
            "startup": True,
        },
    ),
    DiscoveredJob(
        title="Founding Engineer (Full Stack) — Remote India",
        source="startup_outreach",
        source_url="https://alhena.ai/jobs/founding_full_stack_engineer_remote",
        company_name="Alhena AI",
        description=(
            "Alhena AI founding full-stack engineer (remote India). React, React Native, generative AI. "
            "Apply by email to jobs@alhena.ai with role title in subject and portfolio links."
        ),
        location="Remote (India)",
        employment_type="full-time",
        is_remote=True,
        salary_range="",
        opportunity_type="vacancy",
        raw_payload={
            "application_mode": "email",
            "apply_email": "jobs@alhena.ai",
            "contact_name": "Hiring Team",
            "contact_role": "Careers",
            "company_domain": "alhena.ai",
            "email_status": "verified",
            "outreach_type": "founder",
            "startup": True,
        },
    ),
]


class StartupOutreachAdapter:
    name = "startup_outreach"

    def fetch(self) -> list[DiscoveredJob]:
        return list(STARTUP_OUTREACH)
