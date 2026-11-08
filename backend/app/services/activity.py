from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ActivityLog


def log_activity(
    db: Session,
    *,
    user_id: UUID,
    category: str,
    action: str,
    message: str = "",
    status: str = "success",
    details: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> ActivityLog:
    entry = ActivityLog(
        user_id=user_id,
        category=category,
        action=action,
        message=message,
        status=status,
        details=details or {},
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry
