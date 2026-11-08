from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.models import BlocklistEntry
from app.db.session import get_db
from app.integrations.google import sheets as sheets_integration
from app.services.activity import log_activity

router = APIRouter(prefix="/blocklist", tags=["blocklist"])


class BlocklistCreate(BaseModel):
    entry_type: str = Field(description="email | domain | company | person | keyword")
    value: str
    reason: Optional[str] = None
    is_permanent: bool = True
    expires_at: Optional[datetime] = None


class BlocklistResponse(BaseModel):
    id: UUID
    entry_type: str
    value: str
    reason: Optional[str] = None
    is_permanent: bool
    expires_at: Optional[datetime] = None
    is_deleted: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BlocklistResponse])
def list_blocklist(
    include_deleted: bool = False,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[BlocklistEntry]:
    q = db.query(BlocklistEntry).filter(BlocklistEntry.user_id == user_id)
    if not include_deleted:
        q = q.filter(BlocklistEntry.is_deleted.is_(False))
    return q.order_by(BlocklistEntry.created_at.desc()).limit(limit).all()


@router.post("", response_model=BlocklistResponse)
def add_blocklist(
    payload: BlocklistCreate,
    sync_sheets: bool = True,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> BlocklistEntry:
    entry_type = payload.entry_type.strip().lower()
    value = payload.value.strip()
    if entry_type not in {"email", "domain", "company", "person", "keyword", "job"}:
        raise HTTPException(status_code=400, detail="Invalid entry_type")
    if not value:
        raise HTTPException(status_code=400, detail="value is required")
    if entry_type == "email":
        value = value.lower()

    existing = (
        db.query(BlocklistEntry)
        .filter(
            BlocklistEntry.user_id == user_id,
            BlocklistEntry.entry_type == entry_type,
            BlocklistEntry.value == value,
            BlocklistEntry.is_deleted.is_(False),
        )
        .one_or_none()
    )
    if existing:
        return existing

    entry = BlocklistEntry(
        user_id=user_id,
        entry_type=entry_type,
        value=value,
        reason=payload.reason,
        is_permanent=payload.is_permanent,
        expires_at=payload.expires_at,
    )
    db.add(entry)
    log_activity(
        db,
        user_id=user_id,
        category="compliance",
        action="blocklist_add",
        message=f"Blocked {entry_type}: {value}",
        details={"entry_type": entry_type, "value": value},
        commit=False,
    )
    db.commit()
    db.refresh(entry)
    if sync_sheets:
        try:
            sheets_integration.push_all(db, user_id)
        except Exception:
            pass
    return entry


@router.delete("/{entry_id}")
def remove_blocklist(
    entry_id: UUID,
    sync_sheets: bool = True,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    entry = (
        db.query(BlocklistEntry)
        .filter(BlocklistEntry.id == entry_id, BlocklistEntry.user_id == user_id)
        .one_or_none()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.is_deleted = True
    entry.version += 1
    log_activity(
        db,
        user_id=user_id,
        category="compliance",
        action="blocklist_remove",
        message=f"Unblocked {entry.entry_type}: {entry.value}",
        commit=False,
    )
    db.commit()
    if sync_sheets:
        try:
            sheets_integration.push_all(db, user_id)
        except Exception:
            pass
    return {"ok": True}
