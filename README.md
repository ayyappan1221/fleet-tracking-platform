# Vehicle Tracking & Fleet Monitoring Platform

> Real-time GPS tracking, route optimization, and predictive maintenance for delivery fleets

## Overview

This platform lets fleet managers track vehicles on a live map, drivers follow optimized routes with turn-by-turn directions, and mechanics stay ahead of maintenance issues before they cause breakdowns. Built with FastAPI on the backend, React on the frontend, and PostgreSQL for storage.

## Architecture Diagram

![Architecture](docs/diagrams/architecture.png)

## Tech Stack

| Layer         | Technology                                      |
|:--------------|:------------------------------------------------|
| Frontend      | React.js + Tailwind CSS + Leaflet maps          |
| Backend       | FastAPI (Python 3.11)                           |
| Auth          | python-jose + passlib/bcrypt                    |
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

![Dashboard](docs/screenshots/dashboard-placeholder.png)

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15 (or Docker)
- Node.js 20+ and npm (for frontend)

### Setup (Backend)

```bash
# Clone the repo
git clone https://github.com/your-username/vehicle-fleet-platform.git
cd vehicle-fleet-platform

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and set your values
cp .env.example .env
# Edit .env with your database credentials

# Run the server
uvicorn app.main:app --reload --port 8000
```

API docs will be available at `http://localhost:8000/docs`

### Environment Variables

| Variable                  | Description                        | Required |
|:--------------------------|:-----------------------------------|:--------:|
| DATABASE_URL            | PostgreSQL connection string       | Y        |
| SECRET_KEY              | JWT signing secret                 | Y        |
| ALGORITHM               | JWT algorithm (HS256)              | N        |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry in minutes         | N        |
| DEBUG                   | Debug mode                         | N        |
| APP_PORT                | Server port                        | N        |

### API Documentation

Live Swagger UI at `http://localhost:8000/docs`

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

[Your Name] - Student, Semester 5 Capstone Project
