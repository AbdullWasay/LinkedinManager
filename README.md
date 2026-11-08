# AI Job Hunter (LinkedIn Manager)

Private job-outreach dashboard for **Abdul Wasay**.

PostgreSQL is the source of truth. Gmail sends mail. Google Sheets can sync. This is a web app (not Electron).

## Repo layout (Vercel-ready)

```text
/
├── apps/
│   ├── web/     Next.js UI  → deploy on Vercel
│   └── api/     FastAPI + Celery → deploy on Render/Railway
├── package.json
├── apps/web/vercel.json
├── render.yaml
├── docker-compose.yml
└── docs/
```

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for Vercel + Render steps. On Vercel set **Root Directory** to `apps/web`.

## Stack

- **Web:** Next.js, React, TypeScript, Tailwind
- **API:** Python, FastAPI, SQLAlchemy, Alembic, Celery
- **Data:** PostgreSQL, Redis
- **Integrations:** Google OAuth / Sheets / Gmail / Drive

## Local quick start

```bash
cp .env.example .env
# set AUTH_PASSWORD, TOKEN_ENCRYPTION_KEY, Google + AI keys
```

### API

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 and sign in with `AUTH_PASSWORD`.

### Docker (optional)

```bash
docker compose up --build
```

## Deploy summary

| Piece | Host | Root / notes |
|-------|------|----------------|
| UI | **Vercel** | Root Directory = `apps/web` |
| API + workers | **Render** (or Railway) | Root = `apps/api`, use `render.yaml` |
| Postgres / Redis | Render managed / Neon / Upstash | set `DATABASE_URL`, `REDIS_URL` |

On Vercel set `API_PROXY_TARGET` to your public API URL so `/api/*` rewrites work and login cookies stay first-party.
