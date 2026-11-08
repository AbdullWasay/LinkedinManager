from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    automation_paused: Optional[bool] = None
    emergency_stop: Optional[bool] = None
    auto_send_enabled: Optional[bool] = Field(
        default=None,
        description="Must remain false unless explicitly authorized later.",
    )
    discovery_interval_hours: Optional[int] = Field(default=None, ge=1, le=168)
    sheets_sync_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    daily_send_limit: Optional[int] = Field(default=None, ge=0, le=500)
    follow_up_days: Optional[list[int]] = None
    extra: Optional[dict[str, Any]] = None


class SettingsResponse(BaseModel):
    id: UUID
    user_id: UUID
    automation_paused: bool
    emergency_stop: bool
    auto_send_enabled: bool
    discovery_interval_hours: int
    sheets_sync_interval_minutes: int
    daily_send_limit: int
    follow_up_days: list[Any]
    extra: dict[str, Any]
    version: int

    model_config = {"from_attributes": True}
