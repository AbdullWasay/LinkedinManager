from __future__ import annotations

import logging
from typing import Any

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import enrich_payload_with_email, pick_apply_email

logger = logging.getLogger(__name__)

STACK_TAGS = {
    "javascript",
    "typescript",
    "react",
    "nextjs",
    "node",
    "nodejs",
    "python",
    "fastapi",
    "fullstack",
    "full-stack",
    "backend",
    "frontend",
    "engineer",
    "dev",
    "ai",
}

STACK_TITLE_HINTS = (
    "full stack",
    "fullstack",
    "react",
    "next",
    "python",
    "node",
    "fastapi",
    "typescript",
    "software engineer",
    "backend",
    "frontend",
    "developer",
)


class RemoteOKAdapter:
    name = "remoteok"

    def fetch(self) -> list[DiscoveredJob]:
        headers = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search)"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            response = client.get("https://remoteok.com/api")
            response.raise_for_status()
            payload = response.json()

        jobs: list[DiscoveredJob] = []
        for item in payload:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            tags = {str(t).lower() for t in (item.get("tags") or [])}
            title = str(item.get("position") or "")
            description = str(item.get("description") or "")
            url = str(item.get("url") or item.get("apply_url") or "")
            email = pick_apply_email(description, url, str(item.get("company") or ""))
            stack_ok = bool(tags.intersection(STACK_TAGS)) or any(
                k in title.lower() for k in STACK_TITLE_HINTS
            )
            # Keep stack matches OR any listing with a real apply email.
            if not stack_ok and not email:
                continue
            salary_min = item.get("salary_min") or 0
            salary_max = item.get("salary_max") or 0
            salary = ""
            if salary_min or salary_max:
                salary = f"${salary_min}-${salary_max}" if salary_max else f"${salary_min}+"
            raw: dict[str, Any] = item if isinstance(item, dict) else {}
            raw = enrich_payload_with_email(raw, description, url)
            jobs.append(
                DiscoveredJob(
                    title=title,
                    source=self.name,
                    source_url=url,
                    company_name=str(item.get("company") or "") or None,
                    description=description,
                    location=str(item.get("location") or "Remote"),
                    employment_type="full-time",
                    is_remote=True,
                    salary_range=salary,
                    raw_payload=raw,
                )
            )
        logger.info("RemoteOK fetched %s filtered jobs", len(jobs))
        return jobs
