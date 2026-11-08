from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Job, Resume

# Default keyword packs used when a CV doesn't define its own.
DEFAULT_KEYWORDS = {
    "ai": [
        "ai",
        "a.i",
        "ml",
        "llm",
        "genai",
        "machine learning",
        "artificial intelligence",
        "deep learning",
        "nlp",
        "computer vision",
        "openai",
        "langchain",
        "rag",
        "prompt",
        "data scientist",
        "ai engineer",
        "ai developer",
        "ml engineer",
    ],
    "fullstack": [
        "full stack",
        "fullstack",
        "full-stack",
        "software engineer",
        "software developer",
        "react",
        "next.js",
        "nextjs",
        "node",
        "nestjs",
        "typescript",
        "javascript",
        "frontend",
        "front-end",
        "backend",
        "back-end",
        "web developer",
    ],
    "frontend": ["frontend", "front-end", "react", "next.js", "ui engineer", "web engineer"],
    "backend": ["backend", "back-end", "api", "nestjs", "fastapi", "python", "node", "server"],
    "master": [],
}


def extract_drive_file_id(url_or_id: str | None) -> Optional[str]:
    if not url_or_id:
        return None
    value = url_or_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", value):
        return value
    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", value)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", value)
    if match:
        return match.group(1)
    return None


def _keywords_for(resume: Resume) -> list[str]:
    content = resume.content_json or {}
    custom = content.get("keywords") or []
    if isinstance(custom, list) and custom:
        return [str(k).lower() for k in custom]
    return list(DEFAULT_KEYWORDS.get(resume.variant, []))


def _job_haystack(job: Job) -> str:
    return f"{job.title or ''} {job.description or ''}".lower()


def _token_hits(needle: str, haystack: str) -> int:
    """Count meaningful token overlaps; ignore ultra-common words."""
    stop = {"the", "and", "for", "with", "developer", "engineer", "software", "role"}
    hits = 0
    for token in re.split(r"[\s/|,+.]+", needle.lower()):
        token = token.strip()
        if len(token) < 3 or token in stop:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack):
            hits += 1
    return hits


def score_resume_for_job(resume: Resume, job: Job) -> int:
    haystack = _job_haystack(job)
    score = 0
    for label in resume.role_labels or []:
        label_l = str(label).lower().strip()
        if not label_l:
            continue
        if label_l in haystack:
            score += 12
        else:
            score += 3 * _token_hits(label_l, haystack)
    for kw in _keywords_for(resume):
        kw_l = str(kw).lower().strip()
        if not kw_l:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(kw_l)}(?![a-z0-9])", haystack):
            score += 4
    # Prefer attachable files slightly when scores are close
    if resume.local_path or resume.drive_file_id or resume.drive_url:
        score += 1
    if resume.is_master:
        score += 1
    return score


def resume_has_attachable_file(resume: Resume) -> bool:
    from pathlib import Path

    if resume.local_path and Path(resume.local_path).exists():
        return True
    return bool(resume.drive_file_id or resume.drive_url)


def select_resume_for_job(db: Session, user_id: UUID, job: Job) -> Optional[Resume]:
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.is_master.desc(), Resume.updated_at.desc())
        .all()
    )
    if not resumes:
        return None
    # Never pick empty placeholder CVs when a file-backed CV exists.
    usable = [r for r in resumes if resume_has_attachable_file(r)]
    if not usable:
        return None
    ranked = sorted(
        usable,
        key=lambda r: (score_resume_for_job(r, job), 1 if r.is_master else 0),
        reverse=True,
    )
    best = ranked[0]
    if score_resume_for_job(best, job) <= 1:
        for preferred in usable:
            if preferred.is_master or preferred.variant == "fullstack":
                return preferred
    return best
