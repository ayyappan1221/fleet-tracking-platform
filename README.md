# Vehicle Tracking & Fleet Monitoring Platform

> Real-time GPS tracking, route optimization, and predictive maintenance for delivery fleets

## Overview

This platform lets fleet managers track vehicles on a live map, drivers follow optimized routes with turn-by-turn directions, and mechanics stay ahead of maintenance issues before they cause breakdowns. Built with FastAPI on the backend, React on the frontend, and PostgreSQL for storage.

## Architecture Diagram

[Architecture](docs/diagrams/architecture.md)
[ER Diagram](docs/diagrams/er_diagram.md)
[Class Diagram](docs/diagrams/class_diagram.md)

## Tech Stack

| Layer         | Technology                                      |
|:--------------|:------------------------------------------------|
| Frontend      | React.js + Tailwind CSS + Leaflet maps          |
| Backend       | FastAPI (Python 3.11)                           |
| Auth          | python-jose + bcrypt                            |
| ORM           | SQLAlchemy 2.0                                  |
| Database      | PostgreSQL 15                                   |
| API Docs      | FastAPI auto-generated Swagger UI               |
| CI/CD         | GitHub Actions                                  |
| Deployment    | Render (backend), Vercel (frontend), Railway (DB) |

## Features

- Real-time vehicle tracking on interactive map
- Route planning with multi-stop optimization
- Driver behavior scoring (speeding, braking, acceleration)
- Maintenance scheduling based on mileage
- Geofence alerts (email/SMS)
- Admin dashboard with reports
- Mobile-responsive design

## Screenshots

| Screen | Preview |
|:-------|:--------|
| Login | ![Login](docs/screenshots/login.png) |
| Dashboard | ![Dashboard](docs/screenshots/dashboard.png) |
| Vehicles | ![Vehicles](docs/screenshots/vehicles.png) |
| Route Planning | ![Route Planning](docs/screenshots/route_planning.png) |
| Live Map | ![Live Map](docs/screenshots/live_map.png) |
| Alerts | ![Alerts](docs/screenshots/alerts.png) |
| Maintenance | ![Maintenance](docs/screenshots/maintenance.png) |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ (for the React frontend)

The backend runs out of the box with SQLite — no database server needed for local development. PostgreSQL is only required if you want to run in production mode.

### Setup (Backend)

```bash
# Clone the repo
git clone https://github.com/ayyappan1221/fleet-tracking-platform.git
cd fleet-tracking-platform

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and set your values
cp .env.example .env  # On Windows: copy .env.example .env
# Leave DATABASE_URL as sqlite:///./fleet.db to use SQLite (no setup needed)

# Run the server
uvicorn app.main:app --reload --port 8000
```

The database tables are created automatically on startup.

API docs will be available at `http://localhost:8000/docs`

### Setup (Frontend)

```bash
# In a second terminal, from the repo root
cd frontend
npm install
npm run dev
```

The Vite dev server starts on `http://localhost:5173` and proxies all `/api` requests to the FastAPI backend on port 8000. Use the login page with an account created via the register endpoint (or Swagger's `/api/auth/register`) to sign in and manage vehicles.

### Environment Variables

| Variable                    | Description                                          | Default                          |
|:----------------------------|:-----------------------------------------------------|:---------------------------------|
| DATABASE_URL                | Database connection string (SQLite or Postgres)       | `sqlite:///./fleet.db`           |
| SECRET_KEY                  | JWT signing secret                                   | `dev-secret-key-change-in-pro…`  |
| ALGORITHM                   | JWT algorithm                                        | `HS256`                          |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token lifetime in minutes                            | `480`                            |
| BCRYPT_ROUNDS               | Bcrypt hashing rounds                                | `12`                             |
| DEBUG                       | Debug mode (true/false)                              | `true`                           |
| APP_ENV                     | Environment name (`development` / `production`)      | `development`                    |
| APP_HOST                    | Bind address for uvicorn                             | `0.0.0.0`                       |
| APP_PORT                    | Server port                                          | `8000`                           |
| FRONTEND_ORIGIN             | Allowed CORS origins (comma-separated)               | `http://localhost:5173`          |

### API Documentation

Live Swagger UI at `http://localhost:8000/docs`

### API Endpoints

All responses use the `ApiResponse` envelope: `{ "success": bool, "data": <payload>, "message": str }`.

| Method   | Endpoint                                      | Description                          | Auth |
|:---------|:----------------------------------------------|:-------------------------------------|:----:|
| **Authentication** ||||
| POST     | `/api/auth/register`                          | Register a new user                  | No   |
| POST     | `/api/auth/login`                             | Login and get JWT token              | No   |
| **Vehicles** ||||
| POST     | `/api/vehicles/`                              | Add a vehicle to the fleet           | Yes  |
| GET      | `/api/vehicles/`                              | List all vehicles                    | Yes  |
| GET      | `/api/vehicles/{id}`                          | Get a single vehicle                 | Yes  |
| PATCH    | `/api/vehicles/{id}`                          | Update vehicle details               | Yes  |
| DELETE   | `/api/vehicles/{id}`                          | Remove a vehicle                     | Yes  |
| **Routes** ||||
| POST     | `/api/routes/`                                | Plan a new route with stops          | Yes  |
| GET      | `/api/routes/`                                | List all routes                      | Yes  |
| GET      | `/api/routes/{id}`                            | Get a single route with stops        | Yes  |
| POST     | `/api/routes/{id}/start`                      | Start a planned route                | Yes  |
| POST     | `/api/routes/{id}/complete`                   | Mark a route as completed            | Yes  |
| POST     | `/api/routes/stops/{id}/arrive`               | Mark a stop as arrived               | Yes  |
| **Locations** ||||
| POST     | `/api/locations/`                             | Record a GPS location for a vehicle  | Yes  |
| GET      | `/api/locations/`                             | List all locations (filterable)      | Yes  |
| GET      | `/api/locations/vehicle/{id}/latest`          | Get latest location for a vehicle    | Yes  |
| **Dashboard** ||||
| GET      | `/api/dashboard/summary`                      | Aggregated fleet statistics          | Yes  |
| **Alerts** ||||
| POST     | `/api/alerts/`                                | Create a fleet alert                 | Yes  |
| GET      | `/api/alerts/`                                | List alerts (filterable)             | Yes  |
| PATCH    | `/api/alerts/{id}/read`                       | Mark an alert as read                | Yes  |
| **Geofences** ||||
| POST     | `/api/geofences/`                             | Create a geofence boundary           | Yes  |
| GET      | `/api/geofences/`                             | List geofences for current user      | Yes  |
| PATCH    | `/api/geofences/{id}`                         | Update geofence details              | Yes  |
| **Maintenance** ||||
| POST     | `/api/maintenance/`                           | Create a maintenance record          | Yes  |
| GET      | `/api/maintenance/`                           | List maintenance records (filterable)| Yes  |
| PATCH    | `/api/maintenance/{id}`                       | Update a maintenance record          | Yes  |

### Running Tests

```bash
pytest
```

### Deployment

- Backend: Render (free tier)
- Frontend: Vercel (free tier)
- Database: Railway PostgreSQL (free tier)

### Folder Structure

```
app/
  api/          # REST endpoints (thin controllers)
  core/         # Settings, security helpers
  models/       # SQLAlchemy ORM models
  schemas/      # Pydantic request/response schemas
  services/     # Business logic
frontend/       # React (Vite) web app
tests/          # Unit tests
docs/           # Diagrams and API contract
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

Ayyappan - Student, Semester 5 Capstone Project
