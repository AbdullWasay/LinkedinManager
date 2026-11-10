from __future__ import annotations

from typing import Any, Optional

from app.integrations.llm import chat_json, llm_available, llm_in_cooldown


SYSTEM = """You write short, natural founder/CEO outreach emails for a job candidate.
Rules:
- Sound human and specific to the role/company.
- 120-180 words max.
- No fluff, no fake achievements.
- Include LinkedIn and portfolio links exactly as provided.
- Do not invent employers, dates, or projects not in the profile.
- NEVER say the candidate is based in the US, lives in the US, or is a US citizen.
- Do not invent any home location. Prefer remote/international framing without naming a city unless the profile explicitly provides one.
- If the role requires US citizenship / work authorization / no sponsorship, still apply and briefly note openness to relocating to the US for a sponsored role.
- If work_auth.mention_sponsorship_relocation is true, include one short sentence about being open to moving to the US with visa sponsorship.
- If a resume will be attached, mention that briefly (e.g. "I've attached my CV").
- Return JSON with keys: subject, body.
- Body should be plain text with line breaks.
"""

COLD_WEBSITE_SYSTEM = """You write short cold emails offering website creation to UK/US local business owners.
Rules:
- Friendly, specific, non-salesy.
- 90-140 words max.
- Mention they appear to have no website / weak online presence.
- Offer a simple modern site (booking/contact, mobile-friendly, Google-ready).
- Include portfolio and LinkedIn exactly as provided.
- Do not invent prices, fake case studies, or claim you already built their site.
- Return JSON with keys: subject, body.
- Body plain text with line breaks.
"""


def _job_text(job: dict[str, Any]) -> str:
    return " ".join(
        str(job.get(k) or "")
        for k in ("title", "company_name", "description", "location", "salary_range")
    ).lower()


def _work_auth_context(job: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect US citizenship / authorization asks and how to phrase relocation."""
    text = _job_text(job)
    citizen_markers = (
        "us citizen",
        "u.s. citizen",
        "u.s.citizens",
        "united states citizen",
        "must be a citizen",
        "citizens only",
        "citizenship required",
        "green card",
        "permanent resident",
        "authorized to work in the us",
        "authorized to work in the united states",
        "work authorization in the us",
        "without sponsorship",
        "no sponsorship",
        "visa sponsorship not available",
        "cannot sponsor",
        "unable to sponsor",
        "must already be authorized",
    )
    needs_mention = any(m in text for m in citizen_markers)
    prefs = (profile or {}).get("extra") or {}
    relocation_line = prefs.get("sponsorship_relocation_line") or (
        "I'm open to relocating to the US for a sponsored role."
    )
    return {
        "requires_us_work_auth_language": needs_mention,
        "mention_sponsorship_relocation": needs_mention,
        "never_claim_us_based": True,
        "relocation_line": relocation_line if needs_mention else None,
    }


def _fallback_email(
    profile: dict[str, Any],
    job: dict[str, Any],
    contact: dict[str, Any],
    *,
    resume_name: Optional[str] = None,
    attach_resume: bool = False,
) -> dict[str, str]:
    name = profile.get("full_name") or "Abdul Wasay"
    company = job.get("company_name") or "your team"
    title = job.get("title") or "the role"
    contact_name = (contact.get("full_name") or "there").split()[0]
    linkedin = profile.get("linkedin_url") or ""
    portfolio = profile.get("portfolio_url") or ""
    skills = (profile.get("professional_background") or {}).get("skills") or []
    skill_line = ", ".join(skills[:6])
    auth = _work_auth_context(job, profile)
    relocation = (
        f"{auth['relocation_line']}\n\n"
        if auth.get("mention_sponsorship_relocation") and auth.get("relocation_line")
        else ""
    )
    cv_line = (
        f"I've attached my {resume_name or 'CV'} for convenience.\n\n"
        if attach_resume
        else "Happy to share a tailored resume or jump on a short call if useful.\n\n"
    )
    body = (
        f"Hi {contact_name},\n\n"
        f"I'm {name}, a full-stack software developer currently at LantroTech. "
        f"I saw your opening for {title} at {company} and it lines up well with the "
        f"production work I've been doing across {skill_line}.\n\n"
        f"I've shipped marketplace and production platforms (including BlueOcean and Gemelli Marketplace) "
        f"and I'm especially interested in early-stage product work where I can own features end to end.\n\n"
        f"{relocation}"
        f"Portfolio: {portfolio}\n"
        f"LinkedIn: {linkedin}\n\n"
        f"{cv_line}"
        f"Best,\n{name}"
    )
    return {
        "subject": f"{name} — interested in {title} at {company}",
        "body": body,
    }


def _fallback_cold_website_email(
    profile: dict[str, Any],
    job: dict[str, Any],
    contact: dict[str, Any],
) -> dict[str, str]:
    name = profile.get("full_name") or "Abdul Wasay"
    business = job.get("company_name") or "your business"
    contact_name = (contact.get("full_name") or "there").split()[0]
    location = job.get("location") or "your area"
    linkedin = profile.get("linkedin_url") or ""
    portfolio = profile.get("portfolio_url") or ""
    biz_type = ""
    desc = (job.get("description") or "").lower()
    if "restaurant" in desc or "cafe" in desc:
        biz_type = "hospitality"
    elif "salon" in desc or "barber" in desc:
        biz_type = "salon"
    elif "plumber" in desc or "electrician" in desc or "builder" in desc:
        biz_type = "trades"
    else:
        biz_type = "local"

    body = (
        f"Hi {contact_name},\n\n"
        f"I'm {name} — I build simple, fast websites for {biz_type} businesses in the UK and US. "
        f"I came across {business} in {location} and it looks like you don't have a website yet "
        f"(or one that's easy for customers to find).\n\n"
        f"I can put together a clean mobile-friendly site with contact/booking and basic Google visibility, "
        f"without a big agency process. Happy to send 2–3 rough directions for {business} this week if useful.\n\n"
        f"Portfolio: {portfolio}\n"
        f"LinkedIn: {linkedin}\n\n"
        f"Either way, wishing you a strong month.\n\n"
        f"Best,\n{name}"
    )
    return {
        "subject": f"Quick idea for {business}'s website",
        "body": body,
    }


def generate_outreach_email(
    *,
    profile: dict[str, Any],
    job: dict[str, Any],
    contact: dict[str, Any],
    resume_name: Optional[str] = None,
    attach_resume: bool = False,
    outreach_type: str = "founder",
) -> dict[str, str]:
    if outreach_type == "cold_website":
        return _generate_cold_website(profile=profile, job=job, contact=contact)

    if not llm_available() or llm_in_cooldown():
        return _fallback_email(
            profile, job, contact, resume_name=resume_name, attach_resume=attach_resume
        )

    work_auth = _work_auth_context(job, profile)
    user_prompt = {
        "candidate": {
            "full_name": profile.get("full_name"),
            "linkedin_url": profile.get("linkedin_url"),
            "portfolio_url": profile.get("portfolio_url"),
            "education": profile.get("education"),
            "professional_background": profile.get("professional_background"),
            "projects": profile.get("projects"),
            "location_policy": (
                "Never claim based in the US. Open to relocating to the US for sponsored roles."
            ),
        },
        "job": {
            "title": job.get("title"),
            "company_name": job.get("company_name"),
            "description": (job.get("description") or "")[:2500],
            "location": job.get("location"),
            "salary_range": job.get("salary_range"),
            "source_url": job.get("source_url"),
        },
        "contact": {
            "full_name": contact.get("full_name"),
            "role_title": contact.get("role_title"),
            "email": contact.get("email"),
        },
        "work_auth": work_auth,
        "resume": {
            "will_attach": attach_resume,
            "name": resume_name,
        },
        "tone": "direct founder outreach, concise and personalized",
    }
    try:
        result = chat_json(SYSTEM, str(user_prompt))
        subject = str(result.get("subject") or "").strip()
        body = str(result.get("body") or "").strip()
        if not subject or not body:
            return _fallback_email(
                profile, job, contact, resume_name=resume_name, attach_resume=attach_resume
            )
        # Hard guard: strip invented US-based claims the model sometimes adds.
        banned = (
            "based in the us",
            "based in the u.s",
            "based in america",
            "i'm based in us",
            "i am based in the us",
            "living in the us",
            "located in the us",
            "us-based engineer",
            "us based engineer",
        )
        low = body.lower()
        if any(b in low for b in banned):
            return _fallback_email(
                profile, job, contact, resume_name=resume_name, attach_resume=attach_resume
            )
        if (
            work_auth.get("mention_sponsorship_relocation")
            and work_auth.get("relocation_line")
            and "relocat" not in body.lower()
            and "sponsor" not in body.lower()
        ):
            body += f"\n\n{work_auth['relocation_line']}"
        linkedin = profile.get("linkedin_url") or ""
        portfolio = profile.get("portfolio_url") or ""
        if linkedin and linkedin not in body:
            body += f"\n\nLinkedIn: {linkedin}"
        if portfolio and portfolio not in body:
            body += f"\nPortfolio: {portfolio}"
        if attach_resume and "attached" not in body.lower():
            body += f"\n\nI've attached my {resume_name or 'CV'} for convenience."
        return {"subject": subject, "body": body}
    except Exception:
        return _fallback_email(
            profile, job, contact, resume_name=resume_name, attach_resume=attach_resume
        )


def _generate_cold_website(
    *,
    profile: dict[str, Any],
    job: dict[str, Any],
    contact: dict[str, Any],
) -> dict[str, str]:
    if not llm_available() or llm_in_cooldown():
        return _fallback_cold_website_email(profile, job, contact)

    user_prompt = {
        "sender": {
            "full_name": profile.get("full_name"),
            "linkedin_url": profile.get("linkedin_url"),
            "portfolio_url": profile.get("portfolio_url"),
            "background": "full-stack developer offering website builds for local businesses",
        },
        "lead": {
            "business_name": job.get("company_name"),
            "location": job.get("location"),
            "description": (job.get("description") or "")[:1500],
            "owner_name": contact.get("full_name"),
            "owner_role": contact.get("role_title") or "Owner",
        },
        "offer": "modern website + mobile + contact/booking + basic SEO for UK/US businesses without a site",
    }
    try:
        result = chat_json(COLD_WEBSITE_SYSTEM, str(user_prompt))
        subject = str(result.get("subject") or "").strip()
        body = str(result.get("body") or "").strip()
        if not subject or not body:
            return _fallback_cold_website_email(profile, job, contact)
        linkedin = profile.get("linkedin_url") or ""
        portfolio = profile.get("portfolio_url") or ""
        if linkedin and linkedin not in body:
            body += f"\n\nLinkedIn: {linkedin}"
        if portfolio and portfolio not in body:
            body += f"\nPortfolio: {portfolio}"
        return {"subject": subject, "body": body}
    except Exception:
        return _fallback_cold_website_email(profile, job, contact)
