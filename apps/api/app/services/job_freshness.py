from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.integrations.job_sources.base import DiscoveredJob

MAX_AGE_DAYS = 7
PREFER_HOURS = 24


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # RemoteOK uses epoch seconds
        ts = float(value)
        if ts > 1_000_000_000_000:  # ms
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    # ISO-ish
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def extract_posted_at(discovered: DiscoveredJob) -> Optional[datetime]:
    raw = discovered.raw_payload or {}
    for key in (
        "posted_at",
        "date",
        "publication_date",
        "pubDate",
        "published_at",
        "created_at",
        "epoch",
        "jobPublishDate",  # Jobicy
        "created",
    ):
        dt = _parse_dt(raw.get(key))
        if dt:
            return dt
    return None


def is_fresh(posted_at: Optional[datetime], *, now: Optional[datetime] = None, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """Unknown post dates are allowed only for curated/startup sources handled by caller."""
    if posted_at is None:
        return True
    now = now or datetime.now(timezone.utc)
    return posted_at >= now - timedelta(days=max_age_days)


def freshness_bonus(posted_at: Optional[datetime], *, now: Optional[datetime] = None) -> float:
    """Boost match score for very recent roles (last 24h)."""
    if posted_at is None:
        return 0.0
    now = now or datetime.now(timezone.utc)
    age = now - posted_at
    if age <= timedelta(hours=PREFER_HOURS):
        return 8.0
    if age <= timedelta(days=3):
        return 4.0
    if age <= timedelta(days=MAX_AGE_DAYS):
        return 1.0
    return 0.0
