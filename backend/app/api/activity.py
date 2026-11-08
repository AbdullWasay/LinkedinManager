from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import ActivityLog
from app.db.session import get_db
from app.schemas.activity import ActivityLogResponse

router = APIRouter(prefix="/activity-logs", tags=["activity"])


@router.get("", response_model=list[ActivityLogResponse])
def list_activity_logs(
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> list[ActivityLog]:
    q = db.query(ActivityLog).filter(ActivityLog.user_id == user_id)
    if category:
        q = q.filter(ActivityLog.category == category)
    return q.order_by(ActivityLog.created_at.desc()).limit(limit).all()
