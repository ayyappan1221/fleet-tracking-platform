# Vehicle Tracking & Fleet Monitoring Platform

> GPS location logging, route lifecycle management, geofencing, and maintenance tracking for delivery fleets.

## Overview

FastAPI backend + React (Vite) frontend. Fleet managers manage vehicles, plan routes, and watch alerts; drivers progress route stops; mechanics track maintenance records. JWT auth with three roles: `manager`, `driver`, `mechanic`.

- Health: `GET /health` → `{"status": "ok"}` (not under `/api`)
- API routers: `/api/*` (45 endpoints, 12 routers)
- Success envelope: `{ "success", "data", "message" }`; errors: FastAPI `detail`

## Architecture

- [Architecture](docs/diagrams/architecture.md)
- [ER Diagram](docs/diagrams/er_diagram.md) (current, 13 tables)
- [ER Diagram v1 (DBML)](docs/diagrams/er_diagram_v1.dbml) — **stale**, Review-I only
- [Class Diagram](docs/diagrams/class_diagram.md)

## Tech Stack

| Layer      | Technology |
|:-----------|:-----------|
| Frontend   | React 18 + Vite + Leaflet (OSM live maps; plain CSS, no Tailwind) |
| Backend    | FastAPI (Python 3.11+) |
| Auth       | python-jose (JWT HS256) + bcrypt |
| ORM        | SQLAlchemy 2.0 |
| Database   | SQLite (default dev/CI) / PostgreSQL (production) |
| API docs   | Swagger UI at `/docs` |
| CI         | GitHub Actions (backend pytest + frontend build) |
| Deploy     | Render or Railway (backend), Vercel (frontend), Railway Postgres — see [docs/ci-deploy-notes.md](docs/ci-deploy-notes.md) |

## Features

- Vehicle CRUD with status filter
- Route planning (multi-stop), lifecycle: planned → in_progress → completed, stop arrive
- GPS location recording (pinger) + latest lookup + paginated list
- Geofence boundaries (inclusion/exclusion, coordinates as JSON string)
- Maintenance records with status transitions
- Alerts with severity filter and manager-gated fleet-wide mark-read
- Live fleet map (Leaflet + OpenStreetMap) + per-route replay map
- Driver leaderboard with behavior-based safety scores + per-route score endpoint
- Fuel fill logging with km/L + cost/km efficiency stats and efficiency-drop alerts
- Idle-time tracking (minutes per day, 7-day strip)
- Pre/post-trip inspections (DVIR-lite checklist) with fail alerts
- Cost-per-km, utilization, and on-time KPIs (manager report)
- CSV exports: locations, alerts, fuel
- Email OTP: signup verification + passwordless login (SMTP configurable; dev returns `dev_otp`)
- Password strength policy (8+, upper, lower, digit, special) enforced server-side
- Dashboard summary: 7 fleet statistics (role-scoped: managers see fleet, others see own data)
- Role-based access (manager / driver / mechanic)

Not implemented (do not expect): turn-by-turn nav, predictive ML maintenance, hardware GPS/MQTT integration, native mobile app, multi-tenant isolation.

## Ports

| Mode | Backend | Frontend |
|:-----|:--------|:---------|
| Canonical (`uvicorn` + `vite.config.js`) | `8000` | `5173` (proxies `/api` → `:8000`) |
| `start.bat` / `vite.local.config.js` | `8001` | `5174` (`strictPort`) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+

SQLite works out of the box — no DB server for local dev.

### Backend

```bash
git clone https://github.com/ayyappan1221/fleet-tracking-platform.git
cd fleet-tracking-platform

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env        # Windows: copy .env.example .env
# Keep DATABASE_URL=sqlite:///./fleet.db for SQLite

uvicorn app.main:app --reload --port 8000
```

Tables migrate automatically on startup (`alembic upgrade head`, with `create_all` fallback). Swagger: `http://localhost:8000/docs`.

Health: `curl http://localhost:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Register via the Sign Up tab or Swagger `/api/auth/register`.

**First user bootstrap:** the first registered user may take the manager role; later self-register with `role=manager` is rejected with **403**. Every account must verify its email with the 6-digit code before login works.

### JWT + OTP behavior

- Token lifetime: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480) — **no refresh endpoint**; expired tokens clear client-side and redirect to `/login`
- 401 on API calls: interceptor clears token and redirects to `/login`
- Role comes from JWT `role` claim; frontend decodes payload for UX gating only — server enforces
- Passwords: min 8 chars + upper + lower + digit + special (server returns 422 otherwise)
- OTP codes: 6 digits, 10-min TTL, 60s resend cooldown, 5-attempt lockout, single-use, SHA-256 hashed at rest
- Real email delivery needs `SMTP_HOST/USER/PASSWORD` in `.env`; without SMTP the API returns `dev_otp` outside production

### Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| DATABASE_URL | SQLite or Postgres URL | `sqlite:///./fleet.db` |
| SECRET_KEY | JWT signing secret | dev placeholder (must change in production) |
| ALGORITHM | JWT algorithm | `HS256` |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token lifetime | `480` |
| BCRYPT_ROUNDS | Hash rounds | `12` |
| DEBUG | Debug mode | `true` |
| APP_ENV | `development` / `production` | `development` |
| APP_HOST / APP_PORT | Bind address/port | `0.0.0.0` / `8000` |
| FRONTEND_ORIGIN | CORS origins (comma-separated) | `http://localhost:5173` |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM | Outgoing mail for OTP codes (empty = log-only dev mode) | empty |
| OTP_TTL_SECONDS / OTP_COOLDOWN_SECONDS / OTP_MAX_ATTEMPTS | Code lifetime / resend wait / guess limit | `600` / `60` / `5` |
| VITE_API_URL | Frontend API base (prod; dev defaults `/api` via proxy) | see `frontend/.env.example` |

### API Documentation

Live Swagger UI: `http://localhost:8000/docs`

### API Endpoints

All success responses use `{ "success": bool, "data": <payload>, "message": str }`. Errors use FastAPI `detail`.

| Method | Endpoint | Description | Auth |
|:-------|:---------|:------------|:----:|
| **Authentication** ||||
| POST | `/api/auth/register` | Register (unverified; returns `dev_otp` outside prod) | No |
| POST | `/api/auth/verify-signup` | Activate with emailed code | No |
| POST | `/api/auth/request-otp` | Send `signup_verify` or `login_otp` code | No |
| POST | `/api/auth/login` | Login → JWT (verified email required) | No |
| POST | `/api/auth/login/otp` | Passwordless login with code | No |
| **Vehicles** ||||
| POST | `/api/vehicles/` | Add vehicle | Yes |
| GET | `/api/vehicles/` | List vehicles | Yes |
| GET | `/api/vehicles/{id}` | Get vehicle | Yes |
| PATCH | `/api/vehicles/{id}` | Update vehicle | Yes |
| DELETE | `/api/vehicles/{id}` | Remove vehicle | Yes |
| **Routes** ||||
| POST | `/api/routes/` | Plan route with stops | Yes |
| GET | `/api/routes/` | List routes | Yes |
| GET | `/api/routes/{id}` | Get route + stops | Yes |
| POST | `/api/routes/{id}/start` | Start route | Yes |
| POST | `/api/routes/{id}/complete` | Complete route | Yes |
| POST | `/api/routes/stops/{id}/arrive` | Mark stop arrived | Yes |
| GET | `/api/routes/{id}/score` | Behavior score for route | Yes |
| **Locations** ||||
| POST | `/api/locations/` | Record GPS point | Yes |
| GET | `/api/locations/` | List (filter/paginate) | Yes |
| GET | `/api/locations/vehicle/{id}/latest` | Latest for vehicle | Yes |
| GET | `/api/locations/vehicle/{id}/idle-days?days=7` | Idle minutes per day | Yes |
| **Dashboard** ||||
| GET | `/api/dashboard/summary` | 7 stats (role-scoped) | Yes |
| GET | `/api/dashboard/report?days=30` | Trips, cost, KPIs | Manager |
| **Alerts** ||||
| POST | `/api/alerts/` | Create alert | Yes |
| GET | `/api/alerts/` | List (filter) | Yes |
| PATCH | `/api/alerts/{id}/read` | Mark read (fleet-wide: manager only) | Yes |
| **Geofences** ||||
| POST | `/api/geofences/` | Create (`coordinates` = JSON **string**) | Yes |
| GET | `/api/geofences/` | List | Yes |
| PATCH | `/api/geofences/{id}` | Update (incl. `is_active`) | Yes |
| DELETE | `/api/geofences/{id}` | Remove zone | Yes |
| **Maintenance** ||||
| POST | `/api/maintenance/` | Create record | Yes |
| GET | `/api/maintenance/` | List (filter; triggers due-check) | Yes |
| PATCH | `/api/maintenance/{id}` | Update (e.g. status) | Yes |
| DELETE | `/api/maintenance/{id}` | Remove record | Yes |
| POST | `/api/maintenance/check-due` | Create due alerts | Manager |
| POST | `/api/maintenance/report-issue` | Driver issue report | Yes |
| **Fuel** ||||
| POST | `/api/fuel/` | Log fill-up | Yes |
| GET | `/api/fuel/vehicle/{id}` | Fill history | Yes |
| GET | `/api/fuel/vehicle/{id}/efficiency` | km/L + cost/km stats | Yes |
| **Inspections** ||||
| POST | `/api/inspections/` | Record pre/post-trip check | Yes |
| GET | `/api/inspections/` | History (filter) | Yes |
| **Drivers** ||||
| GET | `/api/drivers/me/score` | Own behavior score | Yes |
| **Reports (CSV)** ||||
| GET | `/api/reports/locations.csv` | Location export | Yes |
| GET | `/api/reports/alerts.csv` | Alert export | Yes |
| GET | `/api/reports/fuel.csv` | Fuel export | Yes |

### Running Tests

```bash
pytest -q
```

Expect **152 passed** (16 test files). CI details: [docs/ci-deploy-notes.md](docs/ci-deploy-notes.md).

### Deployment

Pick one backend target (Render **or** Railway **or** Vercel serverless). Full env/health notes: **[docs/ci-deploy-notes.md](docs/ci-deploy-notes.md)**.

- Backend: Render (`render.yaml`) or Railway (`railway.json` + `Procfile`)
- Frontend: Vercel
- Database: Railway PostgreSQL (or Render Postgres)
- Frontend→backend: set `VITE_API_URL=https://<backend-host>/api` and `FRONTEND_ORIGIN=<frontend-url>` on the backend

### Folder Structure

```
app/
  api/          # REST endpoints (thin controllers)
  core/         # Settings, security, responses, authorization
  models/       # SQLAlchemy ORM models
  schemas/      # Pydantic request/response schemas
  services/     # Business logic
frontend/       # React (Vite) web app
tests/          # Unit + service tests (152)
docs/           # Diagrams, CI/deploy notes, contracts
```

### Future Enhancements

- Predictive maintenance using ML models on driving data
- Real hardware GPS device integration via MQTT
- Live traffic data for route optimization
- Native mobile app (React Native)
- Driver mobile app with offline mode

### License

MIT

### Author

Ayyappan — Student, Semester 5 Capstone Project
