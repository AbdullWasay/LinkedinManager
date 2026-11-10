"""Auto-research founders / CEOs / startups that are hiring and list a public email.

Sources (no invented emails):
1. Hacker News "Who is hiring?" — founders often post role + email
2. YC Work at a Startup listings — scrape company pages for careers/founder emails
3. Public job boards — keep only founder/startup-flavored roles that already list an email

LinkedIn itself is not scraped (blocked). Results surface on the LinkedIn leads page.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.email_extract import is_noise_email, pick_apply_email

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "AI-Job-Hunter/0.1 (personal job search research)"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
COMPANY_PREFIX_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9 .&'’/+_-]{1,70}?)\s*(?:\(|\[|\||–|—|-)",
)

ROLE_HINTS = (
    "engineer",
    "developer",
    "full-stack",
    "fullstack",
    "full stack",
    "react",
    "next.js",
    "nextjs",
    "python",
    "fastapi",
    "typescript",
    "node",
    "nestjs",
    "software",
    "founding engineer",
    "founding fullstack",
    "ai engineer",
    "backend",
    "frontend",
)

FOUNDER_HINTS = (
    "founder",
    "founding",
    "ceo",
    "cto",
    "co-founder",
    "cofounder",
    "startup",
    "yc ",
    "y combinator",
    "seed",
    "pre-seed",
    "series a",
)

YC_QUERIES = (
    "founding engineer remote",
    "full stack engineer remote",
    "software engineer remote",
)


def _clean_text(blob: str) -> str:
    text = html.unescape(blob or "")
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _role_match(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in ROLE_HINTS)


def _founder_match(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in FOUNDER_HINTS)


def _guess_company(text: str) -> Optional[str]:
    m = COMPANY_PREFIX_RE.match(text.strip())
    if not m:
        return None
    name = m.group(1).strip(" |-–—")
    if len(name) < 2 or len(name) > 80:
        return None
    if name.lower().startswith(("http", "www", "location", "remote", "hiring")):
        return None
    return name


def _pick_founder_email(*blobs: str) -> Optional[str]:
    """Prefer hiring-looking emails; for founder posts allow any non-noise listed email."""
    email = pick_apply_email(*blobs, hiring_only=True)
    if email:
        return email
    return pick_apply_email(*blobs, hiring_only=False)


def _hn_who_is_hiring(client: httpx.Client, *, limit: int = 40) -> list[DiscoveredJob]:
    out: list[DiscoveredJob] = []
    try:
        stories = client.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": "Who is hiring", "tags": "story,author_whoishiring", "hitsPerPage": 2},
        )
        stories.raise_for_status()
        hits = stories.json().get("hits") or []
    except Exception as exc:
        logger.warning("HN who-is-hiring stories failed: %s", exc)
        return out

    for story in hits[:3]:
        story_title = str(story.get("title") or "")
        # Skip "Who wants to be hired?" candidate threads — only company hiring posts.
        if "who is hiring" not in story_title.lower():
            continue
        if "wants to be hired" in story_title.lower():
            continue
        oid = str(story.get("objectID") or "")
        if not oid:
            continue
        comments: list[dict[str, Any]] = []
        for page in range(0, 6):
            try:
                resp = client.get(
                    "https://hn.algolia.com/api/v1/search_by_date",
                    params={"tags": f"comment,story_{oid}", "hitsPerPage": 100, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json().get("hits") or []
            except Exception as exc:
                logger.warning("HN comments page %s failed: %s", page, exc)
                break
            if not batch:
                break
            comments.extend(batch)

        for comment in comments:
            raw = comment.get("comment_text") or ""
            text = _clean_text(raw)
            if not text or not _role_match(text):
                continue
            # Prefer founder/CEO/startup signals; still accept remotes with a listed email.
            if not (_founder_match(text) or "remote" in text.lower()):
                continue
            email = _pick_founder_email(text)
            if not email or is_noise_email(email):
                continue
            # Candidate posts often say "Resume:" / "Willing to relocate" — skip those.
            if any(
                k in text.lower()
                for k in ("willing to relocate", "who wants to be hired", "seeking opportunities")
            ):
                continue
            company = _guess_company(text)
            title = "Software Engineer"
            low = text.lower()
            for hint in (
                "founding engineer",
                "founding fullstack",
                "full stack engineer",
                "fullstack engineer",
                "full-stack engineer",
                "software engineer",
                "backend engineer",
                "frontend engineer",
                "ai engineer",
            ):
                if hint in low:
                    title = hint.title().replace("Ai ", "AI ")
                    break
            if company and "founding" in title.lower():
                title = f"{title} — {company}"
            elif company:
                title = f"{title} at {company}"

            comment_id = str(comment.get("objectID") or "")
            source_url = (
                f"https://news.ycombinator.com/item?id={comment_id}"
                if comment_id
                else f"https://news.ycombinator.com/item?id={oid}"
            )
            out.append(
                DiscoveredJob(
                    title=title[:200],
                    source="founder_hiring",
                    source_url=source_url,
                    company_name=company,
                    description=text[:4000],
                    location="Remote" if "remote" in low else "",
                    employment_type="full-time",
                    is_remote="remote" in low or "worldwide" in low,
                    salary_range="",
                    opportunity_type="vacancy",
                    raw_payload={
                        "application_mode": "email",
                        "apply_email": email,
                        "contact_name": company or "Hiring founder",
                        "contact_role": "Founder / hiring manager",
                        "email_status": "listed",
                        "outreach_type": "founder",
                        "startup": True,
                        "source_channel": "hacker_news",
                        "hn_story": story_title,
                        "posted_at": comment.get("created_at")
                        or datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
            if len(out) >= limit:
                return out
    return out


def _yc_jobs_with_emails(client: httpx.Client, *, limit: int = 15) -> list[DiscoveredJob]:
    out: list[DiscoveredJob] = []
    seen_slugs: set[str] = set()
    for query in YC_QUERIES:
        try:
            resp = client.get(
                "https://clify-dev.netlify.app/workatastartup/search-jobs",
                params={"q": query},
                timeout=20.0,
            )
            if resp.status_code >= 400:
                continue
            jobs = resp.json().get("data") or []
        except Exception as exc:
            logger.warning("YC search failed (%s): %s", query, exc)
            continue

        for job in jobs[:8]:
            slug = str(job.get("companySlug") or "").strip()
            company = str(job.get("companyName") or "").strip() or None
            title = str(job.get("title") or "Software Engineer").strip()
            if not slug or slug in seen_slugs or not _role_match(title):
                continue
            seen_slugs.add(slug)
            # Prefer YC company page first (often lists careers@ / founder emails).
            pages = [
                f"https://www.ycombinator.com/companies/{slug}",
                f"https://www.workatastartup.com/companies/{slug}",
            ]
            email = None
            page_text = ""
            source_url = pages[0]
            for url in pages:
                try:
                    page = client.get(url, timeout=12.0)
                    if page.status_code >= 400:
                        continue
                    page_text = _clean_text(page.text)
                    email = _pick_founder_email(page.text, page_text)
                    if email:
                        source_url = url
                        break
                except Exception:
                    continue
            if not email:
                continue
            location = str(job.get("location") or "Remote")
            out.append(
                DiscoveredJob(
                    title=title[:200],
                    source="founder_hiring",
                    source_url=source_url,
                    company_name=company,
                    description=(
                        f"YC startup {company or slug} hiring {title}. {page_text[:2500]}"
                    ),
                    location=location,
                    employment_type=str(job.get("jobType") or "full-time"),
                    is_remote="remote" in location.lower(),
                    salary_range=str(job.get("salary") or ""),
                    opportunity_type="vacancy",
                    raw_payload={
                        "application_mode": "email",
                        "apply_email": email,
                        "contact_name": company or "Hiring team",
                        "contact_role": "Founder / hiring",
                        "email_status": "listed",
                        "outreach_type": "founder",
                        "startup": True,
                        "yc": True,
                        "source_channel": "yc",
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
            if len(out) >= limit:
                return out
    return out


def _board_founder_email_jobs(client: httpx.Client, *, limit: int = 20) -> list[DiscoveredJob]:
    """Scan Jobicy for startup/founder-flavored roles that already list a hiring email."""
    out: list[DiscoveredJob] = []
    seen: set[str] = set()
    for tag in ("javascript", "python", "typescript", "react", "software"):
        try:
            resp = client.get(f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}")
            resp.raise_for_status()
            jobs = resp.json().get("jobs") or []
        except Exception as exc:
            logger.warning("Jobicy founder scan failed (%s): %s", tag, exc)
            continue
        for item in jobs:
            title = str(item.get("jobTitle") or "")
            company = str(item.get("companyName") or "")
            description = str(item.get("jobDescription") or item.get("jobExcerpt") or "")
            source_url = str(item.get("url") or "")
            blob = f"{title} {company} {description}"
            if not source_url or source_url in seen:
                continue
            if not _role_match(blob):
                continue
            if not _founder_match(blob):
                continue
            email = _pick_founder_email(description, title, company, source_url)
            if not email:
                continue
            seen.add(source_url)
            out.append(
                DiscoveredJob(
                    title=title[:200],
                    source="founder_hiring",
                    source_url=source_url,
                    company_name=company or None,
                    description=description[:4000],
                    location=str(item.get("jobGeo") or "Remote"),
                    employment_type=str(item.get("jobType") or "full-time"),
                    is_remote=True,
                    salary_range="",
                    opportunity_type="vacancy",
                    raw_payload={
                        "application_mode": "email",
                        "apply_email": email,
                        "contact_name": company or "Hiring team",
                        "contact_role": "Founder / hiring",
                        "email_status": "listed",
                        "outreach_type": "founder",
                        "startup": True,
                        "source_channel": "jobicy",
                        "posted_at": item.get("pubDate")
                        or datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
            if len(out) >= limit:
                return out
    return out


class FounderHiringAdapter:
    name = "founder_hiring"

    def fetch(self) -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []
        with httpx.Client(timeout=35.0, headers=HEADERS, follow_redirects=True) as client:
            jobs.extend(_hn_who_is_hiring(client, limit=35))
            jobs.extend(_yc_jobs_with_emails(client, limit=20))
            jobs.extend(_board_founder_email_jobs(client, limit=15))

        unique: list[DiscoveredJob] = []
        seen: set[str] = set()
        for job in jobs:
            email = str((job.raw_payload or {}).get("apply_email") or "").lower()
            dedupe = f"{email}|{job.source_url}"
            if not job.source_url or dedupe in seen:
                continue
            seen.add(dedupe)
            unique.append(job)

        logger.info("Founder hiring research fetched %s leads with emails", len(unique))
        return unique
