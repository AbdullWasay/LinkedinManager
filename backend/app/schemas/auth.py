from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    name: Optional[str] = None
    google_connected: bool = False
    scopes: list[str] = []
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    drive_folder_id: Optional[str] = None
    google_configured: bool = False


class SyncStatusItem(BaseModel):
    resource: str
    last_pulled_at: Optional[str] = None
    last_pushed_at: Optional[str] = None
    last_error: Optional[str] = None


class SyncStatusResponse(BaseModel):
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    resources: list[SyncStatusItem] = []
