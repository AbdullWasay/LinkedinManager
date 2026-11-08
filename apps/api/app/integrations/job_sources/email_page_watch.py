"""Re-scrape known public job pages daily and keep only listings with real apply emails."""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import pick_apply_email

logger = logging.getLogger(__name__)

# Watchlist of public pages that often list a direct apply email.
# Pages without a recoverable email are skipped (never guessed).
WATCH_PAGES: list[dict[str, str]] = [
    {
        "title": "Full Stack Engineer",
        "company_name": "adyn",
        "source_url": "https://www.ycombinator.com/companies/adyn/jobs/xV982vp6h-full-stack-engineer",
        "location": "Remote (US)",
    },
    {
        "title": "Full Stack Engineer",
        "company_name": "Stardex",
        "source_url": "https://www.ycombinator.com/companies/stardex/jobs/4oOXnyY-full-stack-engineer",
        "location": "Remote",
    },
    {
        "title": "Full Stack Software Engineer",
        "company_name": "Taskade",
        "source_url": "https://www.ycombinator.com/companies/taskade/jobs/wRpvYFyDo-full-stack-software-engineer",
        "location": "Remote (US)",
    },
    {
        "title": "Founding Engineer (Full Stack)",
        "company_name": "Alhena AI",
        "source_url": "https://alhena.ai/jobs/founding_full_stack_engineer_remote",
        "location": "Remote (India)",
    },
]

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _strip_tags(html: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class EmailPageWatchAdapter:
    name = "email_page_watch"

    def fetch(self) -> list[DiscoveredJob]:
        headers = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search)"}
        jobs: list[DiscoveredJob] = []
        with httpx.Client(timeout=25.0, headers=headers, follow_redirects=True) as client:
            for page in WATCH_PAGES:
                url = page["source_url"]
                try:
                    response = client.get(url)
                    if response.status_code >= 400:
                        logger.warning("Watch page %s status %s", url, response.status_code)
                        continue
                    html = response.text
                    text = _strip_tags(html)
                    email = pick_apply_email(html, text, url)
                    if not email:
                        continue
                    title = page.get("title") or "Software Engineer"
                    m = TITLE_RE.search(html)
                    if m:
                        raw_title = re.sub(r"\s+", " ", m.group(1)).strip()
                        if raw_title and len(raw_title) < 120:
                            title = raw_title.split("|")[0].split(" at ")[0].strip() or title
                    jobs.append(
                        DiscoveredJob(
                            title=title,
                            source=self.name,
                            source_url=url,
                            company_name=page.get("company_name"),
                            description=text[:4000],
                            location=page.get("location") or "Remote",
                            employment_type="full-time",
                            is_remote=True,
                            salary_range="",
                            opportunity_type="vacancy",
                            raw_payload={
                                "application_mode": "email",
                                "apply_email": email,
                                "email_status": "listed",
                                "outreach_type": "founder",
                                "watched": True,
                            },
                        )
                    )
                except Exception as exc:
                    logger.warning("Watch page failed %s: %s", url, exc)
        logger.info("Email page watch fetched %s jobs with emails", len(jobs))
        return jobs
