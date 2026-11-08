from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ActivityLogResponse(BaseModel):
    id: UUID
    category: str
    action: str
    status: str
    message: str
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
