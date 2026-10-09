# CI / Deploy notes — Review-II

## Health endpoint
- Canonical health route is **`GET /health`** (`app/main.py` → `{"status": "ok"}`).
  There is no `/api/health`. `railway.json` (`healthcheckPath: /health`) and
  `render.yaml` (`healthCheckPath: /health`) both target the real route.
- API routers live under **`/api/*`** (`app.include_router(..., prefix="/api")`).

## Deploy targets (pick ONE backend)
| Target | File | Notes |
|:-------|:-----|:------|
| Render backend + managed Postgres | `render.yaml` | `DATABASE_URL` wired via `fromDatabase`; set `FRONTEND_ORIGIN` in dashboard to the real Vercel URL (placeholder in file, `sync: false` preserves dashboard value). |
| Railway backend (+ Railway Postgres plugin) | `railway.json`, `Procfile` | Health check `/health`. Add `DATABASE_URL` (plugin `${{Postgres.DATABASE_URL}}`, normalized `postgres://` → `postgresql+psycopg2://` by `app/core/config.py`), `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`, `FRONTEND_ORIGIN`. No secrets committed. |
| Vercel serverless API (alternative) | `vercel.json`, `api/index.py` | `/api/*` rewrites to the Mangum handler; SPA fallback for the rest. Requires `mangum` (in `requirements.txt`, NOT in local `.venv` — installed by CI/backend deploy) and a `DATABASE_URL` Postgres env var in the Vercel dashboard. If the backend runs on Render/Railway instead, set `VITE_API_URL=https://<backend>/api` (see `frontend/.env.example`) and the `/api` rewrite is unused. |

## Postgres wiring
- `DATABASE_URL` supports `sqlite:///./fleet.db` (local + CI) and Postgres
  (`postgresql+psycopg2://...`; bare `postgres://`/`postgresql://` URLs from
  providers are auto-normalized — see `app/core/config.py`).
- CI intentionally keeps SQLite: **do not set `DATABASE_URL` in CI**.
- Production also needs: `SECRET_KEY` (random, never a dev default —
  the app refuses to boot in `production` with one), `APP_ENV=production`,
  `DEBUG=false`, `FRONTEND_ORIGIN=<vercel-url>`.

## Ports
- Canonical: backend `:8000`, frontend `:5173` (`vite.config.js`, `.env.example`, README).
- `start.bat` uses `:8001` + `:5174` (`frontend/vite.local.config.js`) to avoid clashes.

## Requirements — tested versions (no upgrades made)
`requirements.txt`/`requirements-dev.txt` use `>=` lower bounds. Versions below
are what `pytest -q` was green against in Review-II (local `.venv` freeze);
lower bounds were NOT raised and packages NOT upgraded:

- fastapi==0.141.1, uvicorn==0.52.1, SQLAlchemy==2.0.52, psycopg2-binary==2.9.12,
  pydantic==2.13.4, email-validator==2.3.0, python-jose==3.5.0, bcrypt==5.0.0,
  python-multipart==0.0.32, python-dotenv==1.2.2
- mangum>=0.17.0 — declared for the Vercel target; not installed locally, installed in CI/deploy via `requirements.txt`.
- pytest==9.1.1, pytest-asyncio==1.4.0, httpx==0.28.1
- No `ruff`/`flake8` in dev reqs → CI lint uses `ruff`/`flake8` if present,
  else `python -m py_compile` fallback (no new heavy deps added, per task).

## Remaining manual deploy steps
1. Render: create Web Service from `render.yaml`, replace `FRONTEND_ORIGIN`
   placeholder in dashboard, confirm generated `SECRET_KEY`.
2. Railway: add Postgres plugin, set env vars listed above, deploy.
3. Vercel: set root to `frontend/` equivalent (`buildCommand`/`outputDirectory`
   already point there); for serverless API set `DATABASE_URL`; otherwise set
   `VITE_API_URL` to the Render/Railway backend URL.
4. Verify: `GET <backend>/health` → `{"status":"ok"}`; `GET <backend>/docs`.
