# Deployment (Vercel + API host)

Vercel hosts the **Next.js UI**. FastAPI, Celery, Postgres, and Redis cannot run as long-lived processes on Vercel, so the API stack deploys to **Render** (or Railway/Fly).

## Repo layout (Vercel monorepo)

```text
/
├── apps/
│   ├── web/          ← Next.js (deploy on Vercel)
│   └── api/          ← FastAPI + Celery (deploy on Render)
├── package.json           ← npm workspace root
├── apps/web/vercel.json   ← used when Root Directory = apps/web
├── render.yaml
└── docker-compose.yml
```

## 1) Deploy API (Render)

1. Connect this GitHub repo to [Render](https://render.com).
2. Use `render.yaml` (Blueprint) or create Web + Worker services with **Root Directory** `apps/api`.
3. Set env vars (from `.env.example`): `AUTH_PASSWORD`, `ALLOWED_LOGIN_EMAILS`, Google keys, AI keys, `FRONTEND_URL`, `CORS_ORIGINS`.
4. Note the public API URL, e.g. `https://linkedin-manager-api.onrender.com`.

## 2) Deploy UI (Vercel)

1. Import the same GitHub repo in [Vercel](https://vercel.com).
2. **Root Directory:** `apps/web` (Project Settings → General → Root Directory).
   - Required for a clean deploy. `apps/web/vercel.json` marks the app as Next.js.
   - Leave **Output Directory** blank (do not override to `.next` or `apps/web/.next`).
   - If Root Directory is empty, Vercel looks for `.next` at the repo root while `next build` writes it under `apps/web/.next` → `NEXT_OUTPUT_DIR_MISSING`.
3. Framework preset: **Next.js** (auto-detected). Build/Install can stay at defaults when Root Directory is `apps/web`.
4. Environment variables:

| Name | Value |
|------|--------|
| `API_PROXY_TARGET` | `https://your-api.onrender.com` |
| `NEXT_PUBLIC_API_URL` | leave empty (same-origin `/api` via rewrite) **or** your API URL |

5. Deploy. Your site URL will be like `https://linkedin-manager.vercel.app`.

**Note:** Vercel only hosts the Next.js UI. Celery workers and long-lived FastAPI must stay on Render (see `render.yaml`). That is the supported full-stack layout for this repo.

## 3) Wire Google OAuth for production

In Google Cloud Console → OAuth client:

- Authorized JavaScript origins: `https://your-app.vercel.app`
- Redirect URI: `https://your-api.onrender.com/api/v1/auth/google/callback`

On the API host set:

```bash
FRONTEND_URL=https://your-app.vercel.app
CORS_ORIGINS=https://your-app.vercel.app
GOOGLE_REDIRECT_URI=https://your-api.onrender.com/api/v1/auth/google/callback
```

## 4) Local development after restructure

```bash
# API
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Web
cd apps/web && npm install && npm run dev
# or from repo root: npm install && npm run dev
```
