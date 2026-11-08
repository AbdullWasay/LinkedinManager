from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: UUID
    title: str
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    is_remote: bool
    salary_range: Optional[str] = None
    opportunity_type: str
    application_mode: str = "unknown"
    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    manual_apply_required: bool = True
    manual_apply_status: str = "pending"
    status: str
    match_score: Optional[float] = None
    match_details: dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime
    posted_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ManualApplyUpdate(BaseModel):
    manual_apply_status: str = Field(description="pending | reminded | applied | skipped")


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int


class DiscoveryRunResponse(BaseModel):
    fetched: int
    saved: int
    updated: int
    by_source: dict[str, int]
    errors: list[dict[str, str]]
