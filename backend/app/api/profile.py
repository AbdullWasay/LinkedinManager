from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    _user_id=Depends(get_current_user_id),
) -> ProfileResponse:
    return profile_service.get_profile(db)


@router.put("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    _user_id=Depends(get_current_user_id),
) -> ProfileResponse:
    return profile_service.update_profile(db, payload)
