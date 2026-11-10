from __future__ import annotations

import re
from typing import Any

SKILL_ALIASES = {
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs", "next"],
    "typescript": ["typescript", "ts"],
    "node.js": ["node.js", "nodejs", "node"],
    "nest.js": ["nest.js", "nestjs", "nest"],
    "python": ["python"],
    "fastapi": ["fastapi"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "docker": ["docker"],
    "aws": ["aws", "amazon web services"],
    "websocket": ["websocket", "websockets", "socket.io", "socketio"],
    "ai": ["ai", "llm", "openai", "langchain", "genai"],
}

TARGET_KEYWORDS = [
    "full-stack",
    "fullstack",
    "full stack",
    "react",
    "next.js",
    "nextjs",
    "node",
    "nestjs",
    "nest.js",
    "python",
    "fastapi",
    "typescript",
    "ai",
    "llm",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _contains_any(haystack: str, needles: list[str]) -> bool:
    return any(n in haystack for n in needles)


def preferred_currency_hit(text: str, currencies: list[str]) -> bool:
    upper = text.upper()
    aliases = {
        "USD": ["USD", "$", "US DOLLAR", "DOLLARS"],
        "AED": ["AED", "DIRHAM"],
        "GBP": ["GBP", "£", "POUND"],
        "EUR": ["EUR", "€", "EURO"],
    }
    for cur in currencies:
        for alias in aliases.get(cur.upper(), [cur.upper()]):
            if alias in upper:
                return True
    return False


def score_job(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    weights = profile.get("match_weights") or {
        "technical_skills": 0.35,
        "experience": 0.15,
        "responsibilities": 0.10,
        "location": 0.10,
        "remote": 0.20,
        "employment_type": 0.05,
        "salary": 0.05,
    }

    title = _normalize(str(job.get("title") or ""))
    description = _normalize(str(job.get("description") or ""))
    location = _normalize(str(job.get("location") or ""))
    salary = _normalize(str(job.get("salary_range") or ""))
    blob = f"{title} {description} {location} {salary}"

    skills = [
        _normalize(s)
        for s in (profile.get("professional_background") or {}).get("skills") or []
    ]
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    for skill in skills:
        aliases = SKILL_ALIASES.get(skill, [skill])
        if _contains_any(blob, aliases):
            matched_skills.append(skill)
        else:
            # Only treat core skills as missing when clearly required in text.
            if any(a in blob for a in aliases):
                missing_skills.append(skill)

    skill_score = min(100.0, (len(matched_skills) / max(8, 1)) * 100.0)

    title_hit = _contains_any(title, TARGET_KEYWORDS)
    responsibility_score = 85.0 if title_hit else 45.0

    remote_required = bool((profile.get("extra") or {}).get("remote_only", True))
    is_remote = bool(job.get("is_remote")) or "remote" in blob
    remote_score = 100.0 if is_remote else (0.0 if remote_required else 40.0)

    markets = [_normalize(m) for m in profile.get("target_markets") or []]
    market_hit = any(m in location or m in blob for m in markets) or "worldwide" in location or "global" in blob
    location_score = 90.0 if market_hit or is_remote else 35.0

    employment = _normalize(str(job.get("employment_type") or "full-time"))
    wanted = [_normalize(x) for x in profile.get("employment_types") or []]
    employment_score = 90.0 if not wanted or any(w in employment or employment in w for w in wanted) else 50.0

    currencies = (profile.get("extra") or {}).get("preferred_currencies") or ["USD", "AED", "GBP", "EUR"]
    salary_score = 80.0 if preferred_currency_hit(salary or blob, currencies) or not salary else 55.0

    experience_score = 70.0
    if "senior" in title or "5+" in blob or "5 years" in blob:
        experience_score = 55.0  # stretch but still possible
    if "junior" in title or "intern" in title:
        experience_score = 40.0

    total = (
        skill_score * weights.get("technical_skills", 0.35)
        + experience_score * weights.get("experience", 0.15)
        + responsibility_score * weights.get("responsibilities", 0.10)
        + location_score * weights.get("location", 0.10)
        + remote_score * weights.get("remote", 0.20)
        + employment_score * weights.get("employment_type", 0.05)
        + salary_score * weights.get("salary", 0.05)
    )

    concerns: list[str] = []
    if remote_required and not is_remote:
        concerns.append("Not clearly remote")
    if experience_score < 60:
        concerns.append("Experience bar may be high (senior/5+ years)")
    if "german" in blob and "c2" in blob:
        concerns.append("Requires native/C2 German")
    us_auth = any(
        m in blob
        for m in (
            "us citizen",
            "u.s. citizen",
            "united states citizen",
            "without sponsorship",
            "no sponsorship",
            "green card",
            "authorized to work in the us",
            "authorized to work in the united states",
        )
    )
    if us_auth:
        # Still apply — outreach should mention open to US relocation with sponsorship.
        concerns.append("US work auth / citizenship language — mention sponsorship + relocation")

    strengths = matched_skills[:8] or (["Title aligns with target roles"] if title_hit else [])
    action = "apply" if total >= 70 and is_remote else ("review" if total >= 55 else "skip")
    if us_auth and action == "skip" and total >= 55 and is_remote:
        action = "apply"

    return {
        "match_score": round(total, 1),
        "relevant_strengths": strengths,
        "missing_requirements": missing_skills[:6],
        "potential_concerns": concerns,
        "recommended_action": action,
        "breakdown": {
            "technical_skills": round(skill_score, 1),
            "experience": round(experience_score, 1),
            "responsibilities": round(responsibility_score, 1),
            "location": round(location_score, 1),
            "remote": round(remote_score, 1),
            "employment_type": round(employment_score, 1),
            "salary": round(salary_score, 1),
        },
    }
