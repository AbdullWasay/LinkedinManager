# AI Job Hunter

Web-based AI job hunting and outreach management system for **Abdul Wasay**.

PostgreSQL is the source of truth. Google Sheets is a synchronized management UI. Gmail handles email. This is **not** an Electron app.

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation, profile, settings, dashboard | Implemented |
| 2 | Google OAuth, Sheets, Gmail, Drive foundations | Implemented (needs your Google Cloud credentials for live verify) |
| 3–8 | Discovery, research, outreach, automation, prod | Planned — see `docs/ROADMAP.md` |

Architecture, schema, and API contracts live in [`docs/`](docs/).

## Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, Celery
- **Data:** PostgreSQL, Redis
- **Integrations:** Google OAuth / Sheets / Gmail / Drive

## Quick start (local, without Docker)

Docker Desktop is optional. Local Homebrew Postgres + Redis works.

### Prerequisites

- Python 3.13
- Node 20+
- PostgreSQL 16+
- Redis

### 1. Environment

```bash
cp .env.example .env
# Generate TOKEN_ENCRYPTION_KEY:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Create DB:

```bash
createuser -s jobhunter   # if needed
psql -d postgres -c "ALTER USER jobhunter WITH PASSWORD 'jobhunter';"
createdb -O jobhunter ai_job_hunter
```

### 2. Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

### 4. Google OAuth (Phase 2 live)

1. Create a Google Cloud project.
2. Enable **Google Sheets API**, **Gmail API**, **Google Drive API**.
3. Create OAuth 2.0 Web client credentials.
4. Add authorized redirect URI:
   `http://localhost:8000/api/v1/auth/google/callback`
5. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
6. Open **Google Integrations** in the dashboard and click **Connect Google**.

On first connect the system:

- Stores encrypted OAuth tokens
- Creates spreadsheet `AI Job Hunter - Abdul Wasay` with 8 worksheets
- Creates Drive folder `AI Job Hunter - Resumes`
- Pushes current DB projection to Sheets

## Docker Compose

When Docker is available:

```bash
cp .env.example .env
docker compose up --build
```

Services: Postgres, Redis, API, Celery worker, Celery beat, frontend.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Permissions needed from you

To verify Phase 2 against live Google APIs, share:

1. `GOOGLE_CLIENT_ID`
2. `GOOGLE_CLIENT_SECRET`
3. Confirm redirect URI above is allowlisted

Later phases will also need `OPENAI_API_KEY` (and optional search API keys).

## Safety rules already enforced

- Manual approval is the default send mode
- `auto_send_enabled` cannot be turned on via API in Phase 1–2
- Emergency stop / pause controls exist
- OAuth tokens encrypted at rest
- Guesses vs verified emails will be distinguished in contact research (Phase 4)
- No fabricated profile claims in the seed data
