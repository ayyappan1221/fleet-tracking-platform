"""FastAPI application entry point for the fleet tracking platform."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models  # importing models registers them for create_all


DEMO_USERS = [
    {"email": "manager@fleet.com", "name": "Demo Manager", "password": "Password@123", "role": "manager"},
    {"email": "driver@fleet.com", "name": "Demo Driver", "password": "Password@123", "role": "driver"},
    {"email": "mechanic@fleet.com", "name": "Demo Mechanic", "password": "Password@123", "role": "mechanic"},
]


def _seed_demo_users():
    from app.core.security import hash_password
    from app.models.user import User

    db = SessionLocal()
    try:
        for u in DEMO_USERS:
            exists = db.query(User).filter(User.email == u["email"]).first()
            if not exists:
                db.add(User(email=u["email"], name=u["name"], password_hash=hash_password(u["password"]), role=u["role"]))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    _seed_demo_users()
    yield


app = FastAPI(
    title="Vehicle Tracking & Fleet Monitoring Platform",
    description="Real-time GPS tracking, route optimization, and fleet management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Fleet Tracking API is running. Check /docs for API documentation."}
