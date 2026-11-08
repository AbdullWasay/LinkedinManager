from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.integrations.google import sheets as sheets_integration
from app.schemas.auth import SyncStatusResponse

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusResponse)
def get_sync_status(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user_id),
) -> SyncStatusResponse:
    return SyncStatusResponse(**sheets_integration.sync_status(db, user_id))


@router.post("/sheets/push")
def push_sheets(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    try:
        return sheets_integration.push_all(db, user_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sheets/pull")
def pull_sheets(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    try:
        return sheets_integration.pull_mutable_sheets(db, user_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sheets/full")
def full_sync(db: Session = Depends(get_db), user_id=Depends(get_current_user_id)) -> dict:
    try:
        pull = sheets_integration.pull_mutable_sheets(db, user_id)
        push = sheets_integration.push_all(db, user_id)
        return {"pull": pull, "push": push}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
