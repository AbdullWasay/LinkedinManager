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

    user_prompt = {
        "candidate": {
            "full_name": profile.get("full_name"),
            "linkedin_url": profile.get("linkedin_url"),
            "portfolio_url": profile.get("portfolio_url"),
            "education": profile.get("education"),
            "professional_background": profile.get("professional_background"),
            "projects": profile.get("projects"),
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
