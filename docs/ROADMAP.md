# AI Job Hunter — Implementation Roadmap

## Phase 1 — Foundation & Profile ✅ (this sprint)

- [x] Monorepo: Next.js + FastAPI + Docker Compose
- [x] PostgreSQL models + Alembic migrations
- [x] Seed Abdul Wasay profile (editable, no fabricated claims)
- [x] Settings + activity log APIs
- [x] Dashboard shell with profile & settings pages
- [x] Health checks, logging, `.env.example`, README

## Phase 2 — Google Integrations ✅ (this sprint)

- [x] Google OAuth 2.0 (Sheets, Gmail, Drive scopes)
- [x] Encrypted token storage
- [x] Auto-create spreadsheet `AI Job Hunter - Abdul Wasay` + 8 worksheets
- [x] Two-way sync service (UUID-keyed, conflict handling)
- [x] Gmail client foundation (send + thread IDs)
- [x] Drive client foundation (resume folder)
- [x] Sync status + auth status in dashboard

## Phase 3 — Job Discovery & Matching

- Extensible source adapters (Greenhouse, Lever, Ashby, Remote OK, WWR, YC, Search)
- Vacancy vs hiring-signal distinction
- Duplicate detection
- AI matching engine + configurable weights
- Jobs UI

## Phase 4 — Company & Contact Research

- Company research agent
- Contact discovery + email verification status
- Compliance: no duplicate outreach per opportunity
- Companies/Contacts UI

## Phase 5 — Resume & Email Generation

- Resume variants + Drive PDF storage
- Factual consistency checks
- Personalized email generation (all outreach types)
- Drafts UI

## Phase 6 — Approval, Send, Replies

- Manual approval workflow (mandatory)
- Gmail send with PDF attachments
- Reply monitoring + AI classification
- Stop follow-ups on reply/opt-out

## Phase 7 — Follow-ups, Automation, Analytics

- Celery schedules
- Pause / resume / emergency stop
- Follow-up sequences
- Dashboard analytics from real DB

## Phase 8 — Hardening & Production

- Integration tests, security review
- Rate limits, backups, quota handling
- Deploy to AWS/Render
- E2E verification of Definition of Done

## Testing Gates (per phase)

Do not advance until:

1. Unit tests for critical services pass
2. Docker Compose stack boots cleanly
3. Documented manual checklist for that phase is verified
4. Failed integrations surface errors (never silent)

## Permissions Required From You

Before Phase 2 can be verified end-to-end against live Google APIs:

1. Google Cloud project with OAuth client (Web)
2. Enabled APIs: Sheets, Gmail, Drive
3. `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
4. `TOKEN_ENCRYPTION_KEY` (Fernet)
5. Optional later: `OPENAI_API_KEY`, search API keys

Phase 1 runs fully offline with Docker (Postgres + Redis + API + frontend).
