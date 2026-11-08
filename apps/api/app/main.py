from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    activity,
    analytics,
    applications,
    auth,
    blocklist,
    cold_leads,
    emails,
    health,
    jobs,
    linkedin_leads,
    outreach,
    profile,
    resumes,
    settings,
    sync,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.seed import ensure_default_user
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    db = SessionLocal()
    try:
        ensure_default_user(db)
    except Exception:
        logger.exception("Failed to seed default user — DB may not be ready yet")
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    cfg = get_settings()
    app = FastAPI(title=cfg.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(profile.router, prefix="/api/v1")
    app.include_router(resumes.router, prefix="/api/v1")
    app.include_router(settings.router, prefix="/api/v1")
    app.include_router(sync.router, prefix="/api/v1")
    app.include_router(activity.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(emails.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(linkedin_leads.router, prefix="/api/v1")
    app.include_router(cold_leads.router, prefix="/api/v1")
    app.include_router(applications.router, prefix="/api/v1")
    app.include_router(outreach.router, prefix="/api/v1")
    app.include_router(blocklist.router, prefix="/api/v1")
    return app


app = create_app()
