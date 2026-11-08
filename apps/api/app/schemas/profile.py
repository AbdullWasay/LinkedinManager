from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    education: Optional[dict[str, Any]] = None
    professional_background: Optional[dict[str, Any]] = None
    projects: Optional[list[Any]] = None
    target_positions: Optional[list[Any]] = None
    target_markets: Optional[list[Any]] = None
    salary_expectations: Optional[dict[str, Any]] = None
    employment_types: Optional[list[Any]] = None
    match_weights: Optional[dict[str, Any]] = None


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    linkedin_url: str
    portfolio_url: str
    education: dict[str, Any]
    professional_background: dict[str, Any]
    projects: list[Any]
    target_positions: list[Any]
    target_markets: list[Any]
    salary_expectations: dict[str, Any]
    employment_types: list[Any]
    match_weights: dict[str, Any]

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    id: UUID
    email: str
    name: str

    model_config = {"from_attributes": True}
