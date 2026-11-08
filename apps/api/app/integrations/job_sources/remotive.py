from __future__ import annotations

import logging

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import enrich_payload_with_email, pick_apply_email

logger = logging.getLogger(__name__)

STACK_HINTS = (
    "full stack",
    "fullstack",
    "react",
    "next",
    "node",
    "nestjs",
    "python",
    "fastapi",
    "typescript",
    "javascript",
    "frontend",
    "backend",
    "software engineer",
    "developer",
)


class RemotiveAdapter:
    name = "remotive"

    def fetch(self) -> list[DiscoveredJob]:
        url = "https://remotive.com/api/remote-jobs?category=software-dev"
        headers = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search)"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()

        jobs: list[DiscoveredJob] = []
        for item in payload.get("jobs", []):
            title = str(item.get("title") or "")
            lower = title.lower()
            tags = " ".join(item.get("tags") or []).lower()
            description = str(item.get("description") or "")
            source_url = str(item.get("url") or "")
            blob = f"{lower} {tags}"
            email = pick_apply_email(description, source_url, str(item.get("company_name") or ""))
            if not any(k in blob for k in STACK_HINTS) and not email:
                continue
            raw = enrich_payload_with_email(dict(item), description, source_url)
            jobs.append(
                DiscoveredJob(
                    title=title,
                    source=self.name,
                    source_url=source_url,
                    company_name=str(item.get("company_name") or "") or None,
                    description=description,
                    location=str(item.get("candidate_required_location") or "Remote"),
                    employment_type=str(item.get("job_type") or "full-time"),
                    is_remote=True,
                    salary_range=str(item.get("salary") or ""),
                    raw_payload=raw,
                )
            )
        logger.info("Remotive fetched %s filtered jobs", len(jobs))
        return jobs
