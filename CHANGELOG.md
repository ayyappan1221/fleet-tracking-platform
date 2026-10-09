# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Authorization layer: role helpers (`is_manager`, `require_manager`, manager-only fleet-wide alert mark-read) with JWT `role` claim enforcement
- 41 service-layer unit tests (suite total: **93 tests** across 15 test files; 0.3.0 shipped 43 across 10 — service coverage expanded post-release)
- CI hardening: pinned tested dependency versions documented in `docs/ci-deploy-notes.md`, `/health` healthcheck wired for Render/Railway
- Frontend: shared `errorMessage()` helper reading FastAPI `detail` (string + validation arrays) alongside success `message`
- Frontend: 401 interceptor (clears token, redirects to `/login`, skips auth endpoints); JWT `exp` check in `ProtectedRoute`
- Frontend: `utils/auth.js` (decode role/exp client-side, no signature verify — server verifies)
- Frontend: catch-all 404 route (`NotFound.jsx`) inside and outside auth shell
- Frontend: missing CSS (`.stat-value`, `.stat-label`, `.sidebar-signout`), `:focus-visible` outlines, mobile sidebar layout
- Frontend: aria-labels on placeholder-only inputs and filter selects (Vehicles, Routes, Locations, Maintenance, Alerts)

### Fixed
- Geofences create contract: send `coordinates` as JSON **string** (was parsed array → 422); drop `is_active` from create (not in `GeofenceCreate`); if "Active" unchecked, PATCH `{is_active: false}` after create
- Alerts: hide "Mark read" on fleet-wide alerts (`vehicle_id == null`) for non-managers (backend requires manager)
- All pages: `err.response?.data?.message` → `errorMessage(err, fallback)` so FastAPI `detail` surfaces
- Vehicles fetch/delete and Dashboard load errors now render in UI (were console-only)
- README removed overclaims (Tailwind, Leaflet, behavior scoring, email/SMS, screenshots, turn-by-turn); documented ports, health, roles, JWT no-refresh, first-user manager bootstrap, 403 privileged self-register

### Notes
- No backend logic changes; no test deletions; no dependency upgrades

## [0.3.0] - 2026-09-20 (Review-II Release)

### Added
- 5 new API routers: locations (3 endpoints), dashboard (1 endpoint), alerts (3 endpoints), geofences (3 endpoints), maintenance (3 endpoints)
- 27 total API endpoints across 8 routers (auth, vehicles, routes, locations, dashboard, alerts, geofences, maintenance)
- Dashboard aggregation service returning 7 fleet statistics
- CRUD services for locations, alerts, geofences, and maintenance
- Frontend Routes page with route planning, multi-stop management, and lifecycle actions (start/arrive/complete)
- Frontend Locations page with GPS pinger form, location listing, and latest-lookup
- Frontend Dashboard aligned to all 7 backend summary keys
- GitHub Actions CI pipeline (backend pytest + frontend build)
- 43 pytest tests across 10 test files with 40%+ service coverage (suite later expanded to 93 total / 41 service tests — see [Unreleased])
- Production config hardening: Postgres URL normalization, multi-origin CORS, SQLite thread-safety, lifespan startup
- ER diagram v2 covering all 8 database tables
- README v2 with 27-row endpoint table, env vars, and deploy instructions

### Changed
- Maintenance GET list key contract: dual-key (`maintenance` + `records`) for backward compatibility
- Dashboard cards: 6 → 7 cards matching backend schema

## [0.1.0] - Day 1 (Problem Statement Finalization)

### Added
- Problem_Statement.md with project scope, domain, entities, and user roles
- Basic FastAPI project structure (app/, tests/, docs/)
- PostgreSQL database configuration with SQLAlchemy 2.0
- User model with role-based access (manager, driver, mechanic)
- Authentication schemas (register, login, token response)
- Auth router with /register and /login endpoints
- JWT token creation and verification with python-jose
- Password hashing with bcrypt
- Environment-based configuration (.env.example)
- .gitignore for Python/PostgreSQL/IDE
- MIT License
- README v1 with setup and local run instructions

## [0.2.0] - Week 2 (Days 2-11, Review-I Prep)

### Added
- Architecture, ER, and Class/Module diagrams (v1) in docs/diagrams/
- Vehicle model, schemas, service layer, and full CRUD API endpoints
- Route model, schemas, service layer, and route planning API
- Route stop management (mark as arrived)
- Basic multi-stop optimization (nearest-neighbor algorithm)
- Integration tests for vehicle CRUD and route planning flows
- API endpoint documentation in README
- pytest.ini with async test configuration
- 6 total commits across Weeks 1-2
