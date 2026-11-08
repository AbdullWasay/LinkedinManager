from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import UserSettings
from app.db.seed import ensure_default_user
from app.schemas.settings import SettingsUpdate
from app.services.activity import log_activity


def get_settings_record(db: Session) -> UserSettings:
    user = ensure_default_user(db)
    if user.settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return user.settings


def update_settings(db: Session, payload: SettingsUpdate) -> UserSettings:
    user = ensure_default_user(db)
    settings = user.settings
    if settings is None:
        raise HTTPException(status_code=404, detail="Settings not found")

    data = payload.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(settings, key, value)
    settings.version += 1

    log_activity(
        db,
        user_id=user.id,
        category="system",
        action="settings_updated",
        message="Settings updated",
        details={
            "fields": list(data.keys()),
            "auto_send_enabled": settings.auto_send_enabled,
        },
        commit=False,
    )
    db.commit()
    db.refresh(settings)
    return settings


def set_automation_flags(
    db: Session,
    *,
    automation_paused: bool | None = None,
    emergency_stop: bool | None = None,
) -> UserSettings:
    settings = get_settings_record(db)
    user = ensure_default_user(db)
    if automation_paused is not None:
        settings.automation_paused = automation_paused
    if emergency_stop is not None:
        settings.emergency_stop = emergency_stop
        if emergency_stop:
            settings.automation_paused = True
    settings.version += 1
    log_activity(
        db,
        user_id=user.id,
        category="system",
        action="automation_flags_updated",
        message="Automation flags updated",
        details={
            "automation_paused": settings.automation_paused,
            "emergency_stop": settings.emergency_stop,
        },
        commit=False,
    )
    db.commit()
    db.refresh(settings)
    return settings
