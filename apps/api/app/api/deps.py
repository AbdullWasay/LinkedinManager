from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.seed import ensure_default_user
from app.db.session import get_db
from app.services.session_auth import auth_is_required, email_allowed, read_session


def get_current_user_id(request: Request, db: Session = Depends(get_db)) -> UUID:
    """Require a valid login session when auth is enabled (always for production/deploy)."""
    user = ensure_default_user(db)

    if not auth_is_required():
        return user.id

    session = read_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Login required")

    email = str(session.get("email") or "").strip().lower()
    if not email_allowed(email):
        raise HTTPException(status_code=403, detail="This account is not allowed to access the app")

    return user.id


def db_session() -> Generator[Session, None, None]:
    yield from get_db()
