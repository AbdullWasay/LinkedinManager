from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.integrations.google import gmail as gmail_integration

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/reconcile")
def reconcile_inbox(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    try:
        messages = gmail_integration.list_recent_messages(db, user_id, max_results=25)
        return {"count": len(messages), "messages": messages}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
