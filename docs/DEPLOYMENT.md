# Deployment (full stack on Vercel + Neon)

Gemelli/Kingswell-style outcome: **frontend + backend both live**, one login URL.

| Piece | Host | Notes |
|-------|------|--------|
| UI | Vercel project `mylinkedinmanager` | Root Directory `apps/web` |
| API | Vercel project `linkedinmanager-api` | Root Directory `apps/api` (FastAPI) |
| Postgres | Neon project `linkedin-manager` | `DATABASE_URL` on the API project |
| Redis / Celery | optional later (Render workers) | Login & CRUD work without Redis |

Scheduled Celery jobs (outreach beat, sheets sync) need a separate worker host later. Auth, jobs UI, and API routes work on Vercel Functions.

## Projects

### 1) API — `linkedinmanager-api`

- Framework: **FastAPI**
- Root Directory: `apps/api`
- Build: `alembic upgrade head` (migrations)
- Required env: `DATABASE_URL`, `AUTH_PASSWORD`, `SECRET_KEY`, `FRONTEND_URL`, `CORS_ORIGINS`, `TOKEN_ENCRYPTION_KEY`, Google/AI keys as needed

Public URL: `https://linkedinmanager-api.vercel.app` (confirm after deploy).

### 2) UI — `mylinkedinmanager`

- Framework: **Next.js**
- Root Directory: `apps/web`
- Env:

| Name | Value |
|------|--------|
| `API_PROXY_TARGET` | `https://linkedinmanager-api.vercel.app` |
| `NEXT_PUBLIC_API_URL` | leave empty |
| `FRONTEND_URL` | `https://mylinkedinmanager.vercel.app` |

## Google OAuth (optional)

- JS origins: `https://mylinkedinmanager.vercel.app`
- Redirect: `https://linkedinmanager-api.vercel.app/api/v1/auth/google/callback`

## Local

```bash
# API
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Web
cd apps/web && npm run dev
```
