"""High-signal openings found via public web research (vacancy mode)."""

from __future__ import annotations

from app.integrations.job_sources.base import DiscoveredJob

# Facts-only curated listings researched from public job pages.
CURATED: list[DiscoveredJob] = [
    DiscoveredJob(
        title="Full-Stack Developers – Python / React – Remote UK",
        source="web_research",
        source_url="https://www.engineeringjobs.co.uk/job/225755139/full-stack-developers-python-react-remote-uk",
        company_name="Bath and West Community Energy (BWCE)",
        description=(
            "Remote UK full-stack roles building Home Energy Efficiency Advice Tool. "
            "Stack: Python, FastAPI, PostgreSQL, React, React Native, TypeScript, AWS, applied AI. "
            "Pay: £45,000–£70,000. 0.7–1.0 FTE remote within UK."
        ),
        location="United Kingdom (Remote)",
        employment_type="full-time",
        is_remote=True,
        salary_range="GBP 45000-70000",
        opportunity_type="vacancy",
        raw_payload={"currency": "GBP", "markets": ["UK"]},
    ),
    DiscoveredJob(
        title="Senior Full Stack Developer – Next.js / FastAPI (Remote UK Contract)",
        source="web_research",
        source_url="https://freehire.me/jobs/senior-full-stack-developer-uk-contract-remote-ps400-day-outside-ir35-9nexus-kmt36ufa",
        company_name="9NEXUS",
        description=(
            "Remote UK contract outside IR35. Next.js/React/TypeScript, Python FastAPI, "
            "Pub/Sub, SSE/WebSockets, GenAI agents, GCP, Terraform, pytest/Playwright. "
            "Pay: £400/day."
        ),
        location="United Kingdom (Remote)",
        employment_type="remote-contract",
        is_remote=True,
        salary_range="GBP 400/day",
        opportunity_type="vacancy",
        raw_payload={"currency": "GBP", "markets": ["UK"]},
    ),
    DiscoveredJob(
        title="Fullstack (FastAPI + Next.js) Developer with Backend focus",
        source="web_research",
        source_url="https://rockethunt.ai/en/vacancies/e795aed9-d5ec-4d5b-8873-516bbfbdc686",
        company_name="ITM",
        description=(
            "Fully remote FastAPI + Next.js role with backend focus. Python, PostgreSQL, Redis, "
            "ElasticSearch, GCP/AWS, Docker/K8s, LLM APIs. Salary listed USD 8,000–10,000/month. "
            "Senior experience bar is high (listed 10+ years)."
        ),
        location="Remote (UTC+1 to UTC+5)",
        employment_type="full-time",
        is_remote=True,
        salary_range="USD 8000-10000/month",
        opportunity_type="vacancy",
        raw_payload={"currency": "USD", "markets": ["Europe", "Worldwide"]},
    ),
    DiscoveredJob(
        title="Founding Engineer (Python / FastAPI / Next.js), Supply Chain SaaS",
        source="web_research",
        source_url="https://builtin.com/job/founding-engineer-python-fastapi-next-js-supply-chain-saas/12053542",
        company_name="Sierra Studio",
        description=(
            "Remote founding engineer: Python, FastAPI, SQLAlchemy, PostgreSQL, WebSockets, Next.js, "
            "third-party ERP integrations, Alembic, AI features. Pay: USD 6,000–8,000/month + equity. "
            "Listed as remote Brazil with some in-person early sessions."
        ),
        location="Remote (Brazil-focused, international product)",
        employment_type="full-time",
        is_remote=True,
        salary_range="USD 6000-8000/month + equity",
        opportunity_type="vacancy",
        raw_payload={"currency": "USD", "markets": ["Worldwide"]},
    ),
    DiscoveredJob(
        title="Software Engineer – Python / Next.js / React (Remote UK)",
        source="web_research",
        source_url="https://builtin.com/job/software-engineer/12076873",
        company_name="Exclusive Networks",
        description=(
            "Remote UK software engineer building full-stack apps with Python, Next.js, React, "
            "REST APIs, PostgreSQL/MySQL. FastAPI desirable. Fixed-term 6 months with extension potential."
        ),
        location="United Kingdom (Remote)",
        employment_type="contract",
        is_remote=True,
        salary_range="",
        opportunity_type="vacancy",
        raw_payload={"markets": ["UK"]},
    ),
    DiscoveredJob(
        title="Remote Full-Stack Software Developer – React/Next.js / Nest.js (Germany)",
        source="web_research",
        source_url="https://www.remotery.co/job/remote-full-stack-software-developer-reactnextjs-angular-nestjs-nodejs-at-fast-rocket-gmbh-in-germany-full-time-7e6136",
        company_name="Fast Rocket GmbH",
        description=(
            "Fully remote within Germany. React/Next.js, Nest.js, Node.js, TypeScript, Docker, Azure OpenAI. "
            "Pay: €45k–€60k. Requires proficient German (C2) and English."
        ),
        location="Germany (Remote)",
        employment_type="full-time",
        is_remote=True,
        salary_range="EUR 45000-60000",
        opportunity_type="vacancy",
        raw_payload={"currency": "EUR", "markets": ["Germany", "Europe"]},
    ),
    DiscoveredJob(
        title="Senior Full Stack AI Engineer (Next.js + NestJS + AI Tools)",
        source="web_research",
        source_url="https://ae.indeed.com/job/senior-full-stack-ai-engineer-nextjs-nestjs-ai-tools-4a93cf227c356797",
        company_name="Marketplace platform (Dubai)",
        description=(
            "Next.js, TypeScript, NestJS, Node.js, PostgreSQL, Docker, marketplace/payments. "
            "Remote UAE preferred / hybrid remote Dubai. Pay from AED 7,000/month."
        ),
        location="Dubai, UAE (Hybrid remote)",
        employment_type="full-time",
        is_remote=True,
        salary_range="AED 7000+/month",
        opportunity_type="vacancy",
        raw_payload={"currency": "AED", "markets": ["UAE"]},
    ),
    DiscoveredJob(
        title="Senior Backend Engineer – Intents API (NestJS, Remote EMEA)",
        source="web_research",
        source_url="https://www.mncjobsgulf.com/jobs/senior-backend-engineer-intents-api-remote-2260162",
        company_name="mLabs",
        description=(
            "Remote within EMEA. TypeScript/Node.js NestJS backend for high-throughput intents API. "
            "Compensation listed USD 130k–$165k."
        ),
        location="Remote EMEA (Europe / Middle East / Africa)",
        employment_type="full-time",
        is_remote=True,
        salary_range="USD 130000-165000",
        opportunity_type="vacancy",
        raw_payload={"currency": "USD", "markets": ["Europe", "UAE", "Worldwide"]},
    ),
]


class CuratedResearchAdapter:
    name = "web_research"

    def fetch(self) -> list[DiscoveredJob]:
        return list(CURATED)
