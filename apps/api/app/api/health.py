from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_ok = False
    redis_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    try:
        import redis

        client = redis.from_url(get_settings().redis_url)
        redis_ok = client.ping() is True
    except Exception:
        redis_ok = False

    status = "ok" if db_ok else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}
