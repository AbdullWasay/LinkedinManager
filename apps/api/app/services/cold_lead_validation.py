"""Validate UK/US cold website leads — real owner emails only, no guessed contacts."""

from __future__ import annotations

import re
from typing import Optional

from app.services.email_extract import FAKE_DOMAINS, _clean, is_noise_email

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)

ALLOWED_MARKETS = {
    "uk",
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "northern ireland",
    "us",
    "usa",
    "united states",
    "united states of america",
}

PERSONAL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "outlook.com",
    "hotmail.com",
    "hotmail.co.uk",
    "live.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
}


def market_allowed(market: str) -> bool:
    m = (market or "").strip().lower()
    if not m:
        return False
    if m in ALLOWED_MARKETS:
        return True
    return any(a in m for a in ("uk", "united kingdom", "united states", " usa", "us "))


def validate_cold_website_lead(
    *,
    business_name: str,
    owner_name: str,
    owner_email: str,
    market: str,
    city: Optional[str] = None,
    source_url: Optional[str] = None,
) -> list[str]:
    errors: list[str] = []
    if len((business_name or "").strip()) < 2:
        errors.append("Business name is required")
    if len((owner_name or "").strip()) < 2:
        errors.append("Owner name is required")
    if not market_allowed(market):
        errors.append("Market must be UK or US")

    email = _clean(owner_email or "")
    if not email or not EMAIL_RE.match(email):
        errors.append("Valid owner email is required")
    else:
        domain = email.split("@", 1)[-1]
        if domain in FAKE_DOMAINS or domain.endswith(".example"):
            errors.append("Fake/test email domains are not allowed")
        elif is_noise_email(email):
            errors.append("That email looks like noise/support, not an owner contact")

    url = (source_url or "").strip().lower()
    if url and any(x in url for x in ("example.com", "localhost", "127.0.0.1")):
        errors.append("Source URL looks like a placeholder")

    return errors


def email_is_personal(email: str) -> bool:
    e = _clean(email)
    if "@" not in e:
        return False
    return e.split("@", 1)[-1] in PERSONAL_DOMAINS
