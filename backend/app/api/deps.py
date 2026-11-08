from collections.abc import Generator
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.seed import ensure_default_user
from app.db.session import get_db


def get_current_user_id(db: Session = Depends(get_db)) -> UUID:
    """Phase 1–2: single-user mode."""
    return ensure_default_user(db).id


def db_session() -> Generator[Session, None, None]:
    yield from get_db()
