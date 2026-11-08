"""Cold outreach to UK/US local business owners who appear to have no website.

Leads are either:
- added via the /cold-leads API (preferred), or
- listed in COLD_WEBSITE_LEADS after you verify a real owner email + no site.
Never invent emails — only verified contacts belong here.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from app.integrations.job_sources.base import DiscoveredJob

# Curated, verified owner emails only. Add more via the UI or append here after checking
# that the business has no website and the email is publicly listed / confirmed.
COLD_WEBSITE_LEADS: list[dict[str, Any]] = []


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "lead"


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
        f"https://cold-outreach.local/{_slug(market_l)}/{_slug(business_name)}"
    )
    title = f"Website build offer — {business_name}"
    description = (
        f"Cold website outreach to {owner_name} at {business_name} ({business_type}). "
        f"Location: {location}. Confirmed / marked as having no website. "
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
        is_remote=True,  # outreach can be delivered remotely
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
        },
    )


class ColdWebsiteAdapter:
    name = "cold_website"

    def fetch(self) -> list[DiscoveredJob]:
        jobs: list[DiscoveredJob] = []
        for row in COLD_WEBSITE_LEADS:
            try:
                jobs.append(
                    lead_to_discovered(
                        business_name=str(row["business_name"]),
                        owner_name=str(row["owner_name"]),
                        owner_email=str(row["owner_email"]),
                        market=str(row.get("market") or "UK"),
                        city=str(row.get("city") or ""),
                        business_type=str(row.get("business_type") or "local business"),
                        source_url=row.get("source_url"),
                        notes=row.get("notes"),
                        email_status=str(row.get("email_status") or "listed"),
                    )
                )
            except Exception:
                continue
        return jobs
