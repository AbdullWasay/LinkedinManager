from __future__ import annotations

import logging

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import enrich_payload_with_email, pick_apply_email

logger = logging.getLogger(__name__)


class JobicyAdapter:
    name = "jobicy"

    def fetch(self) -> list[DiscoveredJob]:
        headers = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search)"}
        jobs: list[DiscoveredJob] = []
        with httpx.Client(timeout=30.0, headers=headers) as client:
            for tag in ("javascript", "python", "typescript", "software", "react"):
                response = client.get(f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}")
                response.raise_for_status()
                for item in response.json().get("jobs", []):
                    title = str(item.get("jobTitle") or "")
                    lower = title.lower()
                    description = str(item.get("jobDescription") or item.get("jobExcerpt") or "")
                    source_url = str(item.get("url") or "")
                    email = pick_apply_email(
                        description, source_url, str(item.get("companyName") or "")
                    )
                    if not any(
                        k in lower
                        for k in [
                            "full",
                            "react",
                            "next",
                            "node",
                            "nest",
                            "python",
                            "fastapi",
                            "typescript",
                            "frontend",
                            "backend",
                            "software",
                            "engineer",
                            "developer",
                            "ai",
                        ]
                    ) and not email:
                        continue
                    raw = enrich_payload_with_email(dict(item), description, source_url)
                    salary = ""
                    if item.get("annualSalaryMin"):
                        salary = (
                            f"{item.get('salaryCurrency', 'USD')} "
                            f"{item.get('annualSalaryMin')}-{item.get('annualSalaryMax')}"
                        )
                    jobs.append(
                        DiscoveredJob(
                            title=title,
                            source=self.name,
                            source_url=source_url,
                            company_name=str(item.get("companyName") or "") or None,
                            description=description,
                            location=str(item.get("jobGeo") or "Remote"),
                            employment_type=str(item.get("jobType") or "full-time"),
                            is_remote=True,
                            salary_range=salary,
                            raw_payload=raw,
                        )
                    )
        seen: set[str] = set()
        unique: list[DiscoveredJob] = []
        for job in jobs:
            if not job.source_url or job.source_url in seen:
                continue
            seen.add(job.source_url)
            unique.append(job)
        logger.info("Jobicy fetched %s filtered jobs", len(unique))
        return unique
