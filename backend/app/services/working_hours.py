from __future__ import annotations

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

MARKET_TZ = {
    "uk": "Europe/London",
    "united kingdom": "Europe/London",
    "london": "Europe/London",
    "germany": "Europe/Berlin",
    "berlin": "Europe/Berlin",
    "europe": "Europe/Berlin",
    "uae": "Asia/Dubai",
    "dubai": "Asia/Dubai",
    "pakistan": "Asia/Karachi",
    "karachi": "Asia/Karachi",
    "usa": "America/New_York",
    "us": "America/New_York",
    "united states": "America/New_York",
    "canada": "America/Toronto",
    "toronto": "America/Toronto",
}


def resolve_timezone(location: str | None = None, markets: list[str] | None = None) -> str:
    location_l = (location or "").lower()
    for key, tz in MARKET_TZ.items():
        if key in location_l:
            return tz
    for market in markets or []:
        market_l = market.lower()
        for key, tz in MARKET_TZ.items():
            if key in market_l:
                return tz
    return "Europe/London"


def is_working_hours(
    *,
    location: str | None = None,
    markets: list[str] | None = None,
    now: datetime | None = None,
    start_hour: int = 8,
    end_hour: int = 20,
    weekdays_only: bool = False,
) -> dict:
    """Remote outreach window.

    Default is every day 08:00–20:00 local (not Mon–Fri only), so the daily
    30-email target can refill on weekends for remote-first roles.
    """
    tz_name = resolve_timezone(location, markets)
    tz = ZoneInfo(tz_name)
    local_now = (now or datetime.now(tz)).astimezone(tz)
    weekday = local_now.weekday()
    in_week = weekday < 5
    start = time(start_hour, 0)
    end = time(end_hour, 0)
    in_hours = start <= local_now.time() < end
    day_ok = in_week if weekdays_only else True
    return {
        "timezone": tz_name,
        "local_time": local_now.isoformat(),
        "is_weekday": in_week,
        "in_working_hours": bool(day_ok and in_hours),
        "window": f"{start_hour:02d}:00-{end_hour:02d}:00",
    }


def next_working_window(
    *,
    timezones: list[str] | None = None,
    start_hour: int = 8,
    end_hour: int = 20,
    weekdays_only: bool = False,
    now_utc: datetime | None = None,
) -> dict:
    """Find the soonest upcoming working-hours window across candidate timezones."""
    now_utc = now_utc or datetime.now(ZoneInfo("UTC"))
    zones = timezones or sorted(set(MARKET_TZ.values()))
    candidates: list[dict] = []

    for tz_name in zones:
        tz = ZoneInfo(tz_name)
        local = now_utc.astimezone(tz)
        for day_offset in range(0, 8):
            day = (local + timedelta(days=day_offset)).date()
            if weekdays_only and day.weekday() >= 5:
                continue
            start_local = datetime.combine(day, time(start_hour, 0), tzinfo=tz)
            end_local = datetime.combine(day, time(end_hour, 0), tzinfo=tz)
            if day_offset == 0 and local >= end_local:
                continue
            if day_offset == 0 and start_local <= local < end_local:
                candidates.append(
                    {
                        "timezone": tz_name,
                        "status": "open_now",
                        "starts_at": start_local.astimezone(ZoneInfo("UTC")).isoformat(),
                        "ends_at": end_local.astimezone(ZoneInfo("UTC")).isoformat(),
                        "seconds_until_start": 0,
                        "local_window": f"{start_hour:02d}:00-{end_hour:02d}:00",
                    }
                )
                break
            if start_local > local:
                delta = int((start_local.astimezone(ZoneInfo("UTC")) - now_utc).total_seconds())
                candidates.append(
                    {
                        "timezone": tz_name,
                        "status": "scheduled",
                        "starts_at": start_local.astimezone(ZoneInfo("UTC")).isoformat(),
                        "ends_at": end_local.astimezone(ZoneInfo("UTC")).isoformat(),
                        "seconds_until_start": max(0, delta),
                        "local_window": f"{start_hour:02d}:00-{end_hour:02d}:00",
                    }
                )
                break

    if not candidates:
        return {
            "status": "unknown",
            "seconds_until_start": None,
            "starts_at": None,
            "timezone": None,
            "message": "No working window found",
        }

    open_now = [c for c in candidates if c["status"] == "open_now"]
    if open_now:
        chosen = sorted(open_now, key=lambda c: c["ends_at"])[0]
        return {
            **chosen,
            "message": f"Sending window open now ({chosen['timezone']})",
            "any_open_now": True,
        }

    chosen = sorted(candidates, key=lambda c: c["seconds_until_start"])[0]
    return {
        **chosen,
        "message": f"Next send window: {chosen['timezone']} {chosen['local_window']}",
        "any_open_now": False,
    }
