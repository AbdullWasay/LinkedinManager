# Deployment + free automation

| Piece | Host | Notes |
|-------|------|--------|
| UI | Vercel `mylinkedinmanager` | Root `apps/web` |
| API | Vercel `linkedinmanager-api` | Root `apps/api` |
| Postgres | Neon `linkedin-manager` | Shared by API + automation |
| Scheduled jobs | **GitHub Actions** (free) | No Render / Redis / Celery required |

## Automation (laptop can be off)

`.github/workflows/automation.yml` runs:

- Discovery + draft: 06:00 / 12:00 / 16:00 / 21:00 UTC
- Send approved emails: hourly at :15 UTC
- Sheets + Gmail sync: every 30 minutes

Manual run: GitHub → Actions → **Automation** → Run workflow.

### Required GitHub Secrets

Repo → Settings → Secrets and variables → Actions:

`DATABASE_URL`, `SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `AUTH_PASSWORD`, `ALLOWED_LOGIN_EMAILS`, `FRONTEND_URL`, `CORS_ORIGINS`, `DEFAULT_USER_EMAIL`, `DEFAULT_USER_NAME`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_SHEETS_TITLE`, `GROQ_API_KEY`, `GROQ_MODEL`, `GEMINI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, `GEMINI_MODEL`

Use the same Neon `DATABASE_URL` as the Vercel API (`postgresql+psycopg://…`).

### App settings

In the dashboard Settings: enable **auto_send**, leave automation **unpaused**, connect Google/Gmail once.

## Optional HTTP cron

`POST /api/v1/cron/{discovery|send|sheets-sync|gmail-reconcile}` with header `X-Cron-Secret: <CRON_SECRET>`.
