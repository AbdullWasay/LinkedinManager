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
    "python",
    "fastapi",
    "typescript",
    "javascript",
    "frontend",
    "backend",
    "software engineer",
    "developer",
)


class ArbeitnowAdapter:
    name = "arbeitnow"

    def fetch(self) -> list[DiscoveredJob]:
        headers = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search)"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            response = client.get("https://www.arbeitnow.com/api/job-board-api")
            response.raise_for_status()
            payload = response.json()

        jobs: list[DiscoveredJob] = []
        for item in payload.get("data") or []:
            title = str(item.get("title") or "")
            description = str(item.get("description") or "")
            source_url = str(item.get("url") or "")
            company = str(item.get("company_name") or "") or None
            blob = f"{title.lower()} {description.lower()}"
            email = pick_apply_email(description, source_url, company or "")
            if not any(k in blob for k in STACK_HINTS) and not email:
                continue
            remote = bool(item.get("remote")) or "remote" in (item.get("location") or "").lower()
            if not remote and not email:
                continue
            raw = enrich_payload_with_email(dict(item), description, source_url)
            jobs.append(
                DiscoveredJob(
                    title=title,
                    source=self.name,
                    source_url=source_url,
                    company_name=company,
                    description=description,
                    location=str(item.get("location") or "Remote"),
                    employment_type="full-time",
                    is_remote=True,
                    salary_range="",
                    raw_payload=raw,
                )
            )
        logger.info("Arbeitnow fetched %s filtered jobs", len(jobs))
        return jobs
