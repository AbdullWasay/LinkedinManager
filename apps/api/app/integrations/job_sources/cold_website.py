"""Auto-discover UK/US local businesses that look like they have no website.

Free flow (no invented emails):
1. Nominatim finds local businesses by city + trade
2. Keep places with a public email and no proper website (missing, or social/booking only)
3. For custom-domain emails, skip if that domain already serves a real website
4. Also crawl public tourism listing pages for personal emails with no independent webUrl
5. Queue as cold_website outreach for automatic drafting/sending
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import quote, urljoin

import httpx

from app.integrations.job_sources.base import DiscoveredJob
from app.services.cold_lead_validation import PERSONAL_DOMAINS, email_is_personal, market_allowed
from app.services.email_extract import FAKE_DOMAINS, _clean, is_noise_email

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
LISTING_HREF_RE = re.compile(r'href="([^"]*listing/[^"]+)"', re.I)
WEBURL_RE = re.compile(r'webUrl"\s*:\s*"([^"]*)"', re.I)

SEARCH_TARGETS: list[dict[str, str]] = [
    {"market": "UK", "city": "Manchester"},
    {"market": "UK", "city": "Birmingham"},
    {"market": "UK", "city": "Leeds"},
    {"market": "UK", "city": "Bristol"},
    {"market": "UK", "city": "Liverpool"},
    {"market": "UK", "city": "Sheffield"},
    {"market": "UK", "city": "Nottingham"},
    {"market": "UK", "city": "Edinburgh"},
    {"market": "UK", "city": "Glasgow"},
    {"market": "UK", "city": "Cardiff"},
    {"market": "UK", "city": "Brighton"},
    {"market": "UK", "city": "Newcastle"},
    {"market": "UK", "city": "Leicester"},
    {"market": "UK", "city": "Coventry"},
    {"market": "US", "city": "Austin"},
    {"market": "US", "city": "Denver"},
    {"market": "US", "city": "Portland"},
    {"market": "US", "city": "Nashville"},
    {"market": "US", "city": "Phoenix"},
    {"market": "US", "city": "Charlotte"},
    {"market": "US", "city": "Columbus"},
    {"market": "US", "city": "Milwaukee"},
    {"market": "US", "city": "Kansas City"},
    {"market": "US", "city": "Oklahoma City"},
    {"market": "US", "city": "Salt Lake City"},
    {"market": "US", "city": "Raleigh"},
]

TRADE_QUERIES = [
    "cafe",
    "restaurant",
    "bar",
    "pub",
    "hairdresser",
    "barber",
    "florist",
    "bakery",
    "plumber",
    "electrician",
    "car wash",
    "nail salon",
    "laundry",
    "butcher",
    "pet grooming",
]

DIRECTORY_SOURCES: list[dict[str, str]] = [
    {"market": "UK", "city": "Manchester", "url": "https://www.visitmanchester.com/food-and-drink"},
    {"market": "UK", "city": "Manchester", "url": "https://www.visitmanchester.com/shopping"},
    {"market": "UK", "city": "Birmingham", "url": "https://visitbirmingham.com/food-and-drink"},
    {"market": "UK", "city": "Bristol", "url": "https://www.visitbristol.co.uk/food-and-drink"},
    {"market": "UK", "city": "Liverpool", "url": "https://www.visitliverpool.com/food-and-drink"},
    {"market": "UK", "city": "Leeds", "url": "https://www.visitleeds.co.uk/food-and-drink"},
    {"market": "UK", "city": "Edinburgh", "url": "https://edinburgh.org/food-drink/"},
]

SOCIAL_HOST_HINTS = (
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "yelp.com",
    "yelp.co",
    "tripadvisor.",
    "booksy.com",
    "treatwell.",
    "fresha.com",
    "linktr.ee",
)

DIRECTORY_HOST_HINTS = (
    "visitmanchester.com",
    "visitbirmingham.com",
    "visitbristol.co.uk",
    "simpleviewinc.com",
    "timeout.com",
)

CHAIN_HINTS = (
    "wagamama",
    "starbucks",
    "costa",
    "mcdonald",
    "kfc",
    "subway",
    "nando",
    "pizza express",
    "brewdog",
    "pret a manger",
    "greggs",
    "burger king",
    "five guys",
    "chipotle",
    "selfridges",
    "gordon ramsay",
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
    "reservations",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

NOMINATIM_HEADERS = {
    "User-Agent": "LinkedinManager/1.0 (cold-website research; https://mylinkedinmanager.vercel.app)",
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "lead"


def _unescape(url: str) -> str:
    return (url or "").replace("\\/", "/").replace("\\u002F", "/")


def _website_is_missing_or_social(website: str) -> bool:
    w = _unescape(website or "").strip().lower()
    if not w or w in ("http://", "https://", "#", "null", "none"):
        return True
    if any(h in w for h in SOCIAL_HOST_HINTS):
        return True
    if any(h in w for h in DIRECTORY_HOST_HINTS):
        return True
    return False


def _looks_like_chain(name: str, email: str = "") -> bool:
    blob = f"{name} {email}".lower()
    return any(h in blob for h in CHAIN_HINTS)


def _owner_email_ok(email: str) -> bool:
    e = _clean(email)
    if not e or "@" not in e:
        return False
    local, _, domain = e.partition("@")
    if domain in FAKE_DOMAINS or domain.endswith(".example"):
        return False
    if any(x in e for x in ("noreply", "no-reply", "sentry.io", "wixpress.com", "googleapis.com")):
        return False
    if any(h in domain for h in ("visitmanchester", "visitbirmingham", "visitbristol", "simpleview")):
        return False
    if local in OWNER_OK_LOCAL or email_is_personal(e) or domain in PERSONAL_DOMAINS:
        return True
    if is_noise_email(e):
        return False
    return True


def _domain_has_live_website(client: httpx.Client, email: str) -> bool:
    """If the contact uses a custom domain that already serves a site, skip."""
    e = _clean(email)
    if "@" not in e:
        return False
    domain = e.split("@", 1)[1].lower()
    if domain in PERSONAL_DOMAINS or domain.endswith(".gov.uk") or domain.endswith(".gov"):
        return domain.endswith(".gov.uk") or domain.endswith(".gov")
    for host in (domain, f"www.{domain}"):
        for scheme in ("https", "http"):
            try:
                resp = client.get(f"{scheme}://{host}", timeout=8.0)
                if resp.status_code < 400 and len(resp.text or "") > 1500:
                    return True
            except Exception:
                continue
    return False


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
        f"Location: {location}. Appears to have no proper website (missing, social-only, or booking-link only). "
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


def _extract_title(html: str, fallback: str) -> str:
    m = TITLE_RE.search(html or "")
    if not m:
        return fallback
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    title = title.split("|")[0].split(" - ")[0].split(" – ")[0].strip()
    return title or fallback


def _nominatim_leads(client: httpx.Client, *, limit: int = 20) -> list[DiscoveredJob]:
    # Rotate by day+hour so repeated "Find now" clicks explore different cities/trades.
    day = int(time.strftime("%j")) + int(time.strftime("%H")) + int(time.strftime("%M")) // 10
    cities = SEARCH_TARGETS[day % len(SEARCH_TARGETS) :] + SEARCH_TARGETS[: day % len(SEARCH_TARGETS)]
    trades = TRADE_QUERIES[day % len(TRADE_QUERIES) :] + TRADE_QUERIES[: day % len(TRADE_QUERIES)]

    jobs: list[DiscoveredJob] = []
    seen_emails: set[str] = set()

    # Always hit high-yield city×trade pairs, then rotate extras for coverage.
    pairs: list[tuple[str, str, str]] = [
        ("UK", "Manchester", "cafe"),
        ("UK", "Manchester", "bar"),
        ("UK", "Birmingham", "hairdresser"),
        ("UK", "Birmingham", "bakery"),
        ("UK", "Birmingham", "cafe"),
        ("UK", "Leeds", "bar"),
        ("UK", "Bristol", "pub"),
        ("UK", "Liverpool", "cafe"),
        ("US", "Milwaukee", "bakery"),
        ("US", "Austin", "cafe"),
        ("US", "Denver", "barber"),
        ("US", "Portland", "florist"),
    ]
    for i, target in enumerate(cities[:6]):
        pairs.append((target["market"], target["city"], trades[i % len(trades)]))
        pairs.append((target["market"], target["city"], trades[(i + 4) % len(trades)]))
    # Dedupe while preserving order
    deduped: list[tuple[str, str, str]] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for pair in pairs:
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        deduped.append(pair)
    pairs = deduped[:18]

    for market, city, trade in pairs:
        if not market_allowed(market):
            continue
        country = "UK" if market.upper() == "UK" else "USA"
        query = f"{trade} {city} {country}"
        try:
            resp = client.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 25, "extratags": 1, "addressdetails": 1},
                headers=NOMINATIM_HEADERS,
                timeout=25.0,
            )
            time.sleep(1.05)
            if resp.status_code >= 400:
                continue
            places = resp.json()
        except Exception:
            logger.exception("Nominatim failed for %s", query)
            continue

        for place in places:
            tags = place.get("extratags") or {}
            name = (place.get("name") or (place.get("display_name") or "").split(",")[0]).strip()
            if len(name) < 2 or _looks_like_chain(name):
                continue
            email = _clean(tags.get("email") or tags.get("contact:email") or "")
            if not email or not _owner_email_ok(email) or email in seen_emails:
                continue
            website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
            if not _website_is_missing_or_social(str(website)):
                continue
            if _domain_has_live_website(client, email):
                continue

            osm_type = place.get("osm_type") or "node"
            osm_id = place.get("osm_id")
            source_url = (
                f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
                if osm_id
                else f"https://www.openstreetmap.org/search?query={quote(name + ' ' + city)}"
            )
            owner = name.split()[0]
            jobs.append(
                lead_to_discovered(
                    business_name=name,
                    owner_name=owner,
                    owner_email=email,
                    market=market,
                    city=city,
                    business_type=trade,
                    source_url=source_url,
                    notes="Auto-discovered via OpenStreetMap (public email, no proper website tagged).",
                    email_status="listed" if not email_is_personal(email) else "unverified",
                )
            )
            seen_emails.add(email)
            if len(jobs) >= limit:
                return jobs
    return jobs


def _directory_leads(client: httpx.Client, *, limit: int = 10) -> list[DiscoveredJob]:
    """Personal-email listings whose webUrl is missing or social-only."""
    jobs: list[DiscoveredJob] = []
    seen: set[str] = set()
    day = int(time.strftime("%j"))
    sources = DIRECTORY_SOURCES[day % len(DIRECTORY_SOURCES) :] + DIRECTORY_SOURCES[: day % len(DIRECTORY_SOURCES)]

    for source in sources[:5]:
        market = source["market"]
        city = source["city"]
        try:
            page = client.get(source["url"], headers=BROWSER_HEADERS, timeout=25.0)
            if page.status_code >= 400:
                continue
            listing_urls = []
            for href in LISTING_HREF_RE.findall(page.text):
                full = urljoin(source["url"], href)
                if full not in listing_urls:
                    listing_urls.append(full)
        except Exception:
            logger.exception("Directory fetch failed %s", source["url"])
            continue

        for listing_url in listing_urls[:24]:
            try:
                resp = client.get(listing_url, headers=BROWSER_HEADERS, timeout=20.0)
                time.sleep(0.2)
                if resp.status_code >= 400:
                    continue
                html = resp.text
            except Exception:
                continue

            emails = [_clean(e) for e in EMAIL_RE.findall(html)]
            emails = [e for e in emails if _owner_email_ok(e) and email_is_personal(e)]
            if not emails:
                continue
            email = emails[0]
            if email in seen:
                continue

            webs = [_unescape(w) for w in WEBURL_RE.findall(html)]
            if any(not _website_is_missing_or_social(w) for w in webs):
                continue

            name = _extract_title(html, fallback=_slug(listing_url).replace("-", " ").title())
            if len(name) < 2 or _looks_like_chain(name, email):
                continue
            if _domain_has_live_website(client, email):
                continue

            jobs.append(
                lead_to_discovered(
                    business_name=name,
                    owner_name=name.split()[0],
                    owner_email=email,
                    market=market,
                    city=city,
                    business_type="local business",
                    source_url=listing_url,
                    notes="Auto-discovered from a public directory listing (personal email, no independent website).",
                    email_status="unverified",
                )
            )
            seen.add(email)
            if len(jobs) >= limit:
                return jobs
    return jobs


class ColdWebsiteAdapter:
    name = "cold_website"

    def fetch(self) -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []
        seen: set[str] = set()
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            batches: list[DiscoveredJob] = []
            for label, loader in (
                ("nominatim", lambda: _nominatim_leads(client, limit=24)),
                ("directories", lambda: _directory_leads(client, limit=16)),
            ):
                try:
                    batches.extend(loader())
                except Exception as exc:
                    logger.warning("Cold website %s research failed: %s", label, exc)
            for lead in batches:
                email = str((lead.raw_payload or {}).get("apply_email") or "")
                if not email or email in seen:
                    continue
                jobs.append(lead)
                seen.add(email)
        logger.info("Cold website auto-discovery found %s leads", len(jobs))
        return jobs
