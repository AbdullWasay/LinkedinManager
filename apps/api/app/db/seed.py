"""Seed the single-user profile for Abdul Wasay. Facts only — no fabricated claims."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Resume, User, UserProfile, UserSettings

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = {
    "full_name": "Abdul Wasay",
    "linkedin_url": "https://www.linkedin.com/in/abdulwasay308/",
    "portfolio_url": "https://abdulwasaycodes.vercel.app/",
    "education": {
        "degree": "BS Computer Science",
        "institution": "FAST NUCES",
        "year": 2025,
    },
    "professional_background": {
        "current_role": "Software Developer at LantroTech",
        "summary": (
            "Full-stack software developer with experience building production web "
            "applications, marketplaces, and AI/LLM integrations."
        ),
        "skills": [
            "React",
            "Next.js",
            "TypeScript",
            "Node.js",
            "Nest.js",
            "Python",
            "FastAPI",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "REST APIs",
            "WebSockets",
            "Socket.IO",
            "AI and LLM integrations",
            "Docker",
            "AWS",
            "Third-party integrations",
            "Marketplace development",
        ],
        "focus_areas": [
            "Full-stack development",
            "Production web applications",
            "Marketplace development",
            "Third-party integrations",
        ],
    },
    "projects": [
        {"name": "BlueOcean", "description": "Production platform"},
        {"name": "Gemelli Marketplace", "description": "Marketplace product"},
        {"name": "Prodigy", "description": "Software project"},
        {
            "name": "Prior LMS and legal technology projects",
            "description": "Previous work in LMS and legal tech domains",
        },
    ],
    "target_positions": [
        "Full-Stack Software Engineer",
        "React / Next.js Developer",
        "Node.js / NestJS Developer",
        "Python / FastAPI Developer",
        "AI Application Developer",
    ],
    "target_markets": ["UK", "Germany", "Europe", "UAE", "USA", "Canada", "Worldwide"],
    "salary_expectations": {
        "_prefs": {
            "remote_only": True,
            "preferred_currencies": ["USD", "AED", "GBP", "EUR"],
            "notes": "Remote-only international roles. Prefer pay in USD, AED, GBP, or EUR.",
        }
    },
    "employment_types": ["full-time", "remote-contract", "freelance", "part-time"],
    "match_weights": {
        "technical_skills": 0.30,
        "experience": 0.15,
        "responsibilities": 0.10,
        "location": 0.10,
        "remote": 0.20,
        "employment_type": 0.05,
        "salary": 0.10,
    },
}

SEEDED_RESUMES = [
    {
        "name": "AI Engineer CV",
        "variant": "ai",
        "is_master": False,
        "drive_url": "https://drive.google.com/file/d/1ow-T8Pa9gAOb1uYs3XEdc7Yb0G32XkPw/view",
        "drive_file_id": "1ow-T8Pa9gAOb1uYs3XEdc7Yb0G32XkPw",
        "role_labels": [
            "AI Engineer",
            "AI Developer",
            "ML Engineer",
            "LLM Engineer",
            "AI Application Developer",
        ],
        "keywords": [
            "ai",
            "ml",
            "llm",
            "machine learning",
            "artificial intelligence",
            "genai",
            "openai",
            "langchain",
            "rag",
        ],
    },
    {
        "name": "Full Stack Developer CV",
        "variant": "fullstack",
        "is_master": True,
        "drive_url": "https://drive.google.com/file/d/1IoUKPGdSJtwqeUwFxa6k0Zkmu8pX7VBh/view",
        "drive_file_id": "1IoUKPGdSJtwqeUwFxa6k0Zkmu8pX7VBh",
        "role_labels": [
            "Full Stack Developer",
            "Full-Stack Software Engineer",
            "Software Engineer",
            "Software Developer",
            "React / Next.js Developer",
            "Node.js / NestJS Developer",
        ],
        "keywords": [
            "full stack",
            "fullstack",
            "react",
            "next.js",
            "nestjs",
            "node",
            "typescript",
            "frontend",
            "backend",
        ],
    },
]


def _merge_user_into(db: Session, *, source: User, target: User) -> None:
    """Move tenant-owned rows from a duplicate user onto the primary account."""
    from app.db.models import (
        ActivityLog,
        Application,
        BlocklistEntry,
        Company,
        Contact,
        EmailDraft,
        EmailMessage,
        Job,
        OAuthCredential,
        Resume,
        SyncState,
        UserProfile,
        UserSettings,
    )

    # Unique-per-user rows: keep target, drop source copies.
    if db.query(OAuthCredential).filter(OAuthCredential.user_id == target.id).first():
        db.query(OAuthCredential).filter(OAuthCredential.user_id == source.id).delete(
            synchronize_session=False
        )
    if db.query(UserSettings).filter(UserSettings.user_id == target.id).first():
        db.query(UserSettings).filter(UserSettings.user_id == source.id).delete(
            synchronize_session=False
        )
    if db.query(UserProfile).filter(UserProfile.user_id == target.id).first():
        db.query(UserProfile).filter(UserProfile.user_id == source.id).delete(
            synchronize_session=False
        )
    db.query(SyncState).filter(SyncState.user_id == source.id).delete(synchronize_session=False)

    for model in (
        Job,
        Application,
        EmailDraft,
        EmailMessage,
        Contact,
        Company,
        Resume,
        BlocklistEntry,
        ActivityLog,
        OAuthCredential,
        UserSettings,
        UserProfile,
    ):
        db.query(model).filter(model.user_id == source.id).update(
            {model.user_id: target.id},
            synchronize_session=False,
        )


def ensure_default_user(db: Session) -> User:
    settings = get_settings()
    target_email = (settings.default_user_email or "").strip().lower()
    allowed = {
        e.strip().lower()
        for e in settings.allowed_login_email_list
        if e.strip()
    }
    if target_email:
        allowed.add(target_email)

    user = db.query(User).filter(User.email == target_email).one_or_none() if target_email else None
    # Single-tenant app: never create a second account when bootstrap/allowlist email changes.
    # Always reuse the oldest existing user and rebind its email.
    if user is None:
        existing_users = db.query(User).order_by(User.created_at.asc()).all()
        if existing_users:
            for candidate in existing_users:
                email = (candidate.email or "").strip().lower()
                if email in allowed:
                    user = candidate
                    break
            if user is None:
                user = existing_users[0]
            if target_email and user.email != target_email:
                logger.info("Rebinding bootstrap user %s -> %s", user.email, target_email)
                user.email = target_email
                if settings.default_user_name:
                    user.name = settings.default_user_name
            # Collapse accidental duplicates onto the primary account.
            for extra in existing_users:
                if extra.id == user.id:
                    continue
                _merge_user_into(db, source=extra, target=user)
                logger.warning("Merged duplicate user %s (%s) into %s", extra.id, extra.email, user.email)
                db.delete(extra)
    if user is None:
        user = User(email=settings.default_user_email, name=settings.default_user_name)
        db.add(user)
        db.flush()
        logger.info("Created default user %s", user.email)

    if user.profile is None:
        profile = UserProfile(user_id=user.id, **DEFAULT_PROFILE)
        db.add(profile)
        logger.info("Seeded user profile for %s", user.name)

    if user.settings is None:
        db.add(UserSettings(user_id=user.id))
        logger.info("Seeded default settings for %s", user.name)

    existing = {
        r.variant: r for r in db.query(Resume).filter(Resume.user_id == user.id).all()
    }
    for item in SEEDED_RESUMES:
        resume = existing.get(item["variant"])
        if resume is None:
            resume = Resume(
                user_id=user.id,
                name=item["name"],
                variant=item["variant"],
                is_master=bool(item.get("is_master")),
            )
            db.add(resume)
            existing[item["variant"]] = resume
        resume.name = item["name"]
        resume.drive_url = item["drive_url"]
        resume.drive_file_id = item["drive_file_id"]
        resume.role_labels = list(item["role_labels"])
        resume.content_json = {
            **(resume.content_json or {}),
            "keywords": list(item["keywords"]),
            "source": "google_drive",
        }
        if item.get("is_master"):
            for other in existing.values():
                if other.variant != item["variant"]:
                    other.is_master = False
            resume.is_master = True

    db.commit()
    db.refresh(user)
    return user


def get_or_create_default_user_id(db: Session) -> UUID:
    return ensure_default_user(db).id


def get_default_user(db: Session) -> Optional[User]:
    settings = get_settings()
    return db.query(User).filter(User.email == settings.default_user_email).one_or_none()
