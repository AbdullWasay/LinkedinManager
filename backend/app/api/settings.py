from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import settings as settings_service

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    return settings_service.get_settings_record(db)


@router.patch("/settings", response_model=SettingsResponse)
def patch_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsResponse:
    return settings_service.update_settings(db, payload)


@router.post("/automation/pause", response_model=SettingsResponse)
def pause_automation(db: Session = Depends(get_db)) -> SettingsResponse:
    return settings_service.set_automation_flags(db, automation_paused=True)


@router.post("/automation/resume", response_model=SettingsResponse)
def resume_automation(db: Session = Depends(get_db)) -> SettingsResponse:
    return settings_service.set_automation_flags(db, automation_paused=False, emergency_stop=False)


@router.post("/automation/emergency-stop", response_model=SettingsResponse)
def emergency_stop(db: Session = Depends(get_db)) -> SettingsResponse:
    return settings_service.set_automation_flags(db, emergency_stop=True)
