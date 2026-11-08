"""Auto-discover UK/US local businesses that look like they have no website.

Flow (free, no API key):
1. Nominatim finds local businesses by city + trade
2. Skip places that already have a proper website
3. Pull a public email from OSM tags or from public web pages (DuckDuckGo → page scrape)
4. Queue as cold_website outreach for automatic drafting/sending
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import quote, unquote

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.cold_lead_validation import email_is_personal, market_allowed
from app.services.email_extract import FAKE_DOMAINS, _clean, is_noise_email

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DDG_URL = "https://html.duckduckgo.com/html/"
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)

SEARCH_TARGETS: list[dict[str, str]] = [
    {"market": "UK", "city": "Manchester"},
    {"market": "UK", "city": "Birmingham"},
    {"market": "UK", "city": "Leeds"},
    {"market": "UK", "city": "Bristol"},
    {"market": "UK", "city": "Edinburgh"},
    {"market": "UK", "city": "Glasgow"},
    {"market": "US", "city": "Austin"},
    {"market": "US", "city": "Denver"},
    {"market": "US", "city": "Portland"},
    {"market": "US", "city": "Nashville"},
    {"market": "US", "city": "Phoenix"},
    {"market": "US", "city": "Charlotte"},
]

TRADE_QUERIES = [
    "hairdresser",
    "barber",
    "cafe",
    "plumber",
    "electrician",
    "dentist",
    "florist",
    "bakery",
    "car wash",
    "nail salon",
]

SOCIAL_HOST_HINTS = (
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "yelp.com",
    "tripadvisor.",
    "booksy.com",
    "treatwell.",
    "fresha.com",
    "visitmanchester.com",
    "timeout.com",
    "yelp.co",
)

OWNER_OK_LOCAL = {
    "info",
    "hello",
    "contact",
    "owner",
    "enquiries",
    "enquiry",
    "bookings",
    "booking",
    "appointments",
    "admin",
    "office",
    "mail",
    "me",
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "lead"


def _website_is_missing_or_social(website: str) -> bool:
    w = (website or "").strip().lower()
    if not w:
        return True
    return any(h in w for h in SOCIAL_HOST_HINTS)


def _owner_email_ok(email: str) -> bool:
    e = _clean(email)
    if not e or "@" not in e:
        return False
    local, _, domain = e.partition("@")
    if domain in FAKE_DOMAINS or domain.endswith(".example"):
        return False
    if any(x in e for x in ("noreply", "no-reply", "sentry.io", "wixpress.com", "googleapis.com")):
        return False
    if local in OWNER_OK_LOCAL or email_is_personal(e):
        return True
    if is_noise_email(e):
        return False
    return True


def lead_to_discovered(
    *,
    business_name: str,
    owner_name: str,
    owner_email: str,
    market: str,
    city: str = "",
    business_type: str = "local business",
    source_url: Optional[str] = None,
    notes: Optional[str] = None,
    email_status: str = "listed",
) -> DiscoveredJob:
    market_l = (market or "").strip()
    city_l = (city or "").strip()
    location = ", ".join(p for p in [city_l, market_l] if p) or market_l or "UK/US"
    url = (source_url or "").strip() or (
        f"https://www.openstreetmap.org/search?query={quote(business_name + ' ' + city_l)}"
    )
    title = f"Website build offer — {business_name}"
    description = (
        f"Cold website outreach to {owner_name} at {business_name} ({business_type}). "
        f"Location: {location}. Marked as having no proper website (or only social/directory links). "
        f"Offer: modern business website, Google visibility, contact/booking. "
        f"{notes or ''}"
    ).strip()
    return DiscoveredJob(
        title=title,
        source="cold_website",
        source_url=url,
        company_name=business_name,
        description=description,
        location=location,
        employment_type="contract",
        is_remote=True,
        salary_range="",
        opportunity_type="cold_website",
        raw_payload={
            "application_mode": "email",
            "apply_email": owner_email.strip().lower(),
            "contact_name": owner_name.strip(),
            "contact_role": "Owner",
            "email_status": email_status,
            "outreach_type": "cold_website",
            "business_type": business_type,
            "market": market_l,
            "city": city_l,
            "no_website": True,
            "notes": notes,
            "auto_discovered": True,
        },
    )


def _ddg_links(client: httpx.Client, query: str, n: int = 4) -> list[str]:
    try:
        resp = client.post(DDG_URL, data={"q": query}, timeout=20.0)
    except Exception:
        return []
    hrefs = re.findall(r"uddg=([^&\"]+)", resp.text)
    out: list[str] = []
    for h in hrefs:
        url = unquote(h)
        if url.startswith("http") and "duckduckgo.com" not in url:
            out.append(url)
        if len(out) >= n:
            break
    if not out:
        out = re.findall(r'class="result__a"[^>]*href="(https?://[^"]+)"', resp.text)[:n]
    return out


def _emails_from_url(client: httpx.Client, url: str) -> list[str]:
    try:
        page = client.get(url, timeout=15.0)
        if page.status_code >= 400:
            return []
        found = sorted({_clean(e) for e in EMAIL_RE.findall(page.text)})
        return [e for e in found if _owner_email_ok(e)]
    except Exception:
        return []


def _find_email_for_business(
    client: httpx.Client,
    *,
    business_name: str,
    city: str,
    market: str,
    tagged_email: str = "",
) -> tuple[str, str]:
    """Return (email, source_url)."""
    tagged = _clean(tagged_email)
    if tagged and _owner_email_ok(tagged):
        return tagged, ""

    queries = [
        f'"{business_name}" {city} email contact',
        f'"{business_name}" {city} @gmail.com OR @yahoo.co.uk OR @outlook.com',
    ]
    if market.upper() == "US":
        queries.append(f'"{business_name}" {city} "@gmail.com" OR "@yahoo.com" contact')

    for q in queries:
        for link in _ddg_links(client, q, n=4):
            emails = _emails_from_url(client, link)
            if emails:
                # Prefer personal inbox for owner outreach.
                personal = [e for e in emails if email_is_personal(e)]
                chosen = personal[0] if personal else emails[0]
                return chosen, link
        time.sleep(0.4)
    return "", ""


def _nominatim_places(
    client: httpx.Client,
    *,
    trade: str,
    city: str,
    market: str,
    limit: int = 6,
) -> list[dict[str, Any]]:
    countrycodes = "gb" if market.upper() == "UK" else "us"
    try:
        resp = client.get(
            NOMINATIM_URL,
            params={
                "q": f"{trade} {city}",
                "format": "json",
                "limit": str(limit),
                "addressdetails": 1,
                "extratags": 1,
                "countrycodes": countrycodes,
            },
            timeout=20.0,
        )
        if resp.status_code >= 400:
            return []
        return list(resp.json() or [])
    except Exception:
        logger.exception("Nominatim failed for %s %s", trade, city)
        return []


class ColdWebsiteAdapter:
    name = "cold_website"

    def fetch(self) -> list[DiscoveredJob]:
        day = int(time.strftime("%j"))
        targets = SEARCH_TARGETS[day % len(SEARCH_TARGETS) :] + SEARCH_TARGETS[: day % len(SEARCH_TARGETS)]
        targets = targets[:3]
        trades = TRADE_QUERIES[day % len(TRADE_QUERIES) :] + TRADE_QUERIES[: day % len(TRADE_QUERIES)]
        trades = trades[:3]

        headers = {
            "User-Agent": "LinkedinManager/1.0 (cold website research; https://mylinkedinmanager.vercel.app)",
            "Accept": "application/json,text/html",
        }
        jobs: list[DiscoveredJob] = []
        seen_emails: set[str] = set()
        seen_names: set[str] = set()

        with httpx.Client(timeout=25.0, headers=headers, follow_redirects=True) as client:
            for target in targets:
                market = target["market"]
                city = target["city"]
                if not market_allowed(market):
                    continue
                for trade in trades:
                    places = _nominatim_places(client, trade=trade, city=city, market=market, limit=5)
                    time.sleep(1.1)  # Nominatim usage policy
                    for place in places:
                        name = (place.get("name") or str(place.get("display_name") or "").split(",")[0]).strip()
                        if len(name) < 2:
                            continue
                        key = f"{name.lower()}|{city.lower()}"
                        if key in seen_names:
                            continue
                        tags = place.get("extratags") or {}
                        website = str(tags.get("website") or tags.get("contact:website") or "")
                        if not _website_is_missing_or_social(website):
                            continue

                        tagged_email = str(tags.get("email") or tags.get("contact:email") or "")
                        email, found_url = _find_email_for_business(
                            client,
                            business_name=name,
                            city=city,
                            market=market,
                            tagged_email=tagged_email,
                        )
                        if not email or email in seen_emails:
                            continue

                        osm_url = (
                            f"https://www.openstreetmap.org/{place.get('osm_type')}/{place.get('osm_id')}"
                            if place.get("osm_type") and place.get("osm_id")
                            else f"https://www.openstreetmap.org/search?query={quote(name + ' ' + city)}"
                        )
                        source_url = found_url or osm_url
                        personal = email_is_personal(email)
                        jobs.append(
                            lead_to_discovered(
                                business_name=name,
                                owner_name=name.split()[0],
                                owner_email=email,
                                market=market,
                                city=city,
                                business_type=trade,
                                source_url=source_url,
                                notes="Auto-discovered: public email found; no proper website listed.",
                                email_status="listed" if not personal else "unverified",
                            )
                        )
                        seen_emails.add(email)
                        seen_names.add(key)
                        if len(jobs) >= 18:
                            logger.info("Cold website auto-discovery found %s leads", len(jobs))
                            return jobs
                    if len(jobs) >= 18:
                        break
                if len(jobs) >= 18:
                    break

        logger.info("Cold website auto-discovery found %s leads", len(jobs))
        return jobs
