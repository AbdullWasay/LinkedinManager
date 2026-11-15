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

# Titles we actively want.
TARGET_TITLE_PATTERNS = [
    r"\bsoftware\s+(engineer|developer|dev)\b",
    r"\bfull[\s-]?stack\b",
    r"\bfront[\s-]?end\b",
    r"\bback[\s-]?end\b",
    r"\bweb\s+developer\b",
    r"\bapplication\s+developer\b",
    r"\breact\b",
    r"\bnext\.?js\b",
    r"\bnode\.?js\b",
    r"\bnest\.?js\b",
    r"\btypescript\b",
    r"\bpython\b",
    r"\bfastapi\b",
    r"\bai\s+(engineer|developer|application)\b",
    r"\bml\s+(system\s+)?engineer\b",
    r"\bmachine\s+learning\s+(system\s+)?engineer\b",
    r"\bllm\s+engineer\b",
    r"\bgenai\b",
    r"\bfounding\s+engineer\b",
    r"\bplatform\s+engineer\b",
    r"\bdevops\b",
    r"\bsite\s+reliability\b",
    r"\bsre\b",
    r"\bmobile\s+(engineer|developer)\b",
    r"\bios\s+(engineer|developer)\b",
    r"\bandroid\s+(engineer|developer)\b",
    r"\bkotlin\b",
    r"\bforward[\s-]?deployed\s+engineer\b",
    r"\bdata\s+engineer\b",
    r"\bdata\s+scientist\b",
    r"\bstaff\s+engineer\b",
    r"\bprincipal\s+(software|ml|ai|machine learning)?\s*(system\s+)?engineer\b",
    r"\bsoftware\s+engineering\s+manager\b",
    r"\bsolutions?\s+architect\b",
]

# Non-engineering roles that currently pollute discovery.
IRRELEVANT_TITLE_PATTERNS = [
    r"\baccount\s+executive\b",
    r"\bsales\b",
    r"\bbusiness\s+development\b",
    r"\bcommunity\s+(strategy|manager|lead)\b",
    r"\btalent\s+community\b",
    r"\bcustomer\s+strategy\b",
    r"\bcustomer\s+success\b",
    r"\bcustomer\s+integration\b",
    r"\bimplementation\s+(manager|consultant|specialist)\b",
    r"\benterprise\s+implementation\b",
    r"\bproduct\s+marketing\b",
    r"\bmarketing\s+manager\b",
    r"\brevenue\b",
    r"\bbusiness\s+partner\b",
    r"\bsolutions\s+analyst\b",
    r"\bproduct\s+manager\b",
    r"\bprogram\s+manager\b",
    r"\brecruiter\b",
    r"\bpeople\s+ops\b",
    r"\bhr\b",
    r"\bdesigner\b",
    r"\bux\s+writer\b",
    r"\bcontent\s+(writer|strategist|manager)\b",
    r"\bsupport\s+(specialist|agent|representative)\b",
    r"\bcustomer\s+support\b",
    r"\boperations\s+manager\b",
    r"\bfinance\b",
    r"\baccountant\b",
    r"\blegal\b",
    r"\bnurse\b",
    r"\bclinical\b(?!.*\b(engineer|developer|software)\b)",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _contains_any(haystack: str, needles: list[str]) -> bool:
    return any(n in haystack for n in needles)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.I) for p in patterns)


def is_irrelevant_role(title: str, description: str = "") -> bool:
    title_n = _normalize(title)
    if not title_n:
        return True
    if _matches_any(title_n, IRRELEVANT_TITLE_PATTERNS):
        return True
    # Guard: "engineer" alone is not enough if title is clearly customer/sales ops.
    if _matches_any(title_n, [r"\b(customer|sales|community|marketing|account)\b"]) and not _matches_any(
        title_n, TARGET_TITLE_PATTERNS
    ):
        return True
    return False


def is_target_engineering_role(title: str, description: str = "") -> bool:
    title_n = _normalize(title)
    if not title_n:
        return False
    if is_irrelevant_role(title_n, description):
        return False
    if _matches_any(title_n, TARGET_TITLE_PATTERNS):
        return True
    # Allow generic "software/developer/engineer" titles that aren't rejected above.
    if re.search(r"\b(software|developer|engineer)\b", title_n):
        # Reject vague "Integration Engineer" / "IT Engineer" without software/AI signal
        # unless description clearly points to coding stack.
        desc_n = _normalize(description)[:2500]
        coding_signal = _contains_any(
            f"{title_n} {desc_n}",
            [
                "react",
                "next.js",
                "typescript",
                "javascript",
                "node",
                "python",
                "fastapi",
                "django",
                "flask",
                "full stack",
                "fullstack",
                "backend",
                "frontend",
                "api",
                "llm",
                "machine learning",
                "postgresql",
                "kubernetes",
                "docker",
            ],
        )
        if "software" in title_n or "developer" in title_n:
            return True
        return coding_signal
    return False


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

    concerns: list[str] = []
    relevant = is_target_engineering_role(title, description)
    irrelevant = is_irrelevant_role(title, description)

    if irrelevant or not relevant:
        concerns.append("Not a software / full-stack / AI engineering role")
        return {
            "match_score": 15.0,
            "relevant_strengths": [],
            "missing_requirements": ["software/full-stack/AI engineering title"],
            "potential_concerns": concerns,
            "recommended_action": "skip",
            "role_relevant": False,
            "breakdown": {
                "technical_skills": 0.0,
                "experience": 0.0,
                "responsibilities": 10.0,
                "location": 0.0,
                "remote": 0.0,
                "employment_type": 0.0,
                "salary": 0.0,
            },
        }

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
            if any(a in blob for a in aliases):
                missing_skills.append(skill)

    skill_score = min(100.0, (len(matched_skills) / max(8, 1)) * 100.0)
    title_hit = _matches_any(title, TARGET_TITLE_PATTERNS)
    responsibility_score = 90.0 if title_hit else 70.0

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
        experience_score = 55.0
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
        concerns.append("US work auth / citizenship language — mention sponsorship + relocation")

    strengths = matched_skills[:8] or (["Title aligns with target engineering roles"] if title_hit else [])
    action = "apply" if total >= 70 and is_remote else ("review" if total >= 55 else "skip")
    if us_auth and action == "skip" and total >= 55 and is_remote:
        action = "apply"

    return {
        "match_score": round(total, 1),
        "relevant_strengths": strengths,
        "missing_requirements": missing_skills[:6],
        "potential_concerns": concerns,
        "recommended_action": action,
        "role_relevant": True,
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
