# AI Job Hunter — System Architecture

## Overview

Single-user web application that discovers jobs, researches companies/contacts, generates personalized outreach, and manages the application pipeline. PostgreSQL is the source of truth; Google Sheets is a synchronized user-facing management UI; Gmail handles email I/O.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Next.js        │────▶│  FastAPI         │────▶│  PostgreSQL     │
│  Dashboard      │◀────│  REST + Webhooks │◀────│  (source of     │
│  (TypeScript)   │     │  (Python)        │     │   truth)        │
└─────────────────┘     └────────┬─────────┘     └────────┬────────┘
                                 │                        │
                    ┌────────────┼────────────┐           │
                    ▼            ▼            ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  Redis   │ │  Celery  │ │  OpenAI  │ │  Google  │
              │  Broker  │ │  Workers │ │  Agents  │ │  APIs    │
              └──────────┘ └──────────┘ └──────────┘ └──────────┘
                                                    Sheets│Gmail│Drive
```

## Repository Layout

```
/
├── frontend/                 # Next.js 14 App Router + Tailwind + shadcn/ui
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # config, security, logging
│   │   ├── db/               # SQLAlchemy models, session, migrations
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic
│   │   ├── integrations/     # Google, OpenAI, search, Playwright
│   │   ├── agents/           # Specialized AI agents
│   │   ├── workers/          # Celery tasks
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── docker-compose.yml
├── docs/
├── .env.example
└── README.md
```

## Core Design Principles

1. **PostgreSQL is authoritative.** Sheets are a projection with conflict resolution.
2. **UUID everywhere.** Never use Sheets row numbers as IDs.
3. **Manual approval by default.** Agents draft; humans approve sends.
4. **Compliance before send.** Blocklist + duplicate + rate-limit checks are mandatory gates.
5. **Untrusted external input.** Job descriptions, websites, and emails are sanitized before prompting.
6. **No credential leakage.** OAuth tokens encrypted at rest; never stored in Sheets or frontend.

## Sync Strategy (PostgreSQL ↔ Google Sheets)

```
Write path:
  Dashboard/API mutate → PostgreSQL (txid, updated_at, version)
                      → enqueue sheets_push task
                      → update sheet row keyed by UUID column A

Read path (every 5–15 min or webhook):
  sheets_pull → compare sheet row hash vs DB version
             → if sheet newer AND no pending local write → apply to DB
             → if conflict → keep DB, flag Activity Log, last-writer-wins by updated_at
```

- Column A of every worksheet = `id` (UUID)
- Soft deletes via `is_deleted` / status, mirrored to Sheets
- Settings & Blocklist edits in Sheets are first-class and enforced before sends

## Google Integration Boundaries

| Service | Responsibility |
|---------|----------------|
| OAuth 2.0 | Auth for Sheets, Gmail, Drive scopes |
| Sheets API | Create workbook, CRUD rows, sync |
| Gmail API | Send, threads, labels, reply watch |
| Drive API | Store generated PDF resumes/cover letters |

## Agent Architecture

Agents are pure services with typed I/O. They never send email or mutate blocklists directly.

```
Orchestrator
  ├─ JobDiscoveryAgent → vacancies / hiring signals
  ├─ JobMatchingAgent → scores + recommendations
  ├─ CompanyResearchAgent → firmographics
  ├─ ContactDiscoveryAgent → people + email verification status
  ├─ ResumeAgent → CV selection / tailored PDF
  ├─ EmailGenerationAgent → draft subject/body
  ├─ ComplianceAgent → blocklist / duplicate / limits
  └─ ResponseClassificationAgent → reply labels
```

All agent runs are logged to `activity_logs` with input/output hashes.

## Background Automation (Celery)

| Task | Default cadence |
|------|-----------------|
| job_discovery | every 6h |
| company_research | daily |
| matching | after discovery |
| contact_research | after qualification |
| sheets_sync | every 10 min |
| gmail_reconcile | every 15 min (+ push notifications) |
| follow_up_check | daily |

Global `automation_paused` / `emergency_stop` flags short-circuit all workers.

## Security Model

- Single-user auth initially (session + Google OAuth)
- Fernet/AES encryption for OAuth refresh tokens
- HTTPS in production
- Rate limiting on public endpoints
- Audit log for sends, sync conflicts, blocklist hits
- Prompt-injection hardening on all LLM boundaries

## Deployment

Local: Docker Compose (Postgres, Redis, API, worker, frontend, flower optional)  
Production: AWS/Render equivalent with managed Postgres, Redis, and automated DB backups.
