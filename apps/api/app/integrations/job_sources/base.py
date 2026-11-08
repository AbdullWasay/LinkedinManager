from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class DiscoveredJob:
    title: str
    source: str
    source_url: str
    company_name: Optional[str] = None
    description: str = ""
    location: str = ""
    employment_type: str = "full-time"
    is_remote: bool = True
    salary_range: str = ""
    opportunity_type: str = "vacancy"
    raw_payload: dict[str, Any] = field(default_factory=dict)


class JobSourceAdapter(Protocol):
    name: str

    def fetch(self) -> list[DiscoveredJob]:
        ...
