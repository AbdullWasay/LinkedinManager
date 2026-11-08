from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import UserProfile
from app.db.seed import ensure_default_user
from app.schemas.profile import ProfileUpdate
from app.services.activity import log_activity


def get_profile(db: Session) -> UserProfile:
    user = ensure_default_user(db)
    if user.profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return user.profile


def update_profile(db: Session, payload: ProfileUpdate) -> UserProfile:
    user = ensure_default_user(db)
    profile = user.profile
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)

    if "full_name" in data:
        user.name = data["full_name"]

    log_activity(
        db,
        user_id=user.id,
        category="system",
        action="profile_updated",
        message="User profile updated",
        details={"fields": list(data.keys())},
        commit=False,
    )
    db.commit()
    db.refresh(profile)
    return profile
