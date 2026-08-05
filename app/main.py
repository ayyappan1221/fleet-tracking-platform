from fastapi import FastAPI

from app.api.v1 import router as api_v1_router
from app.core.database import Base, engine
from app import models  # importing models registers them for create_all

app = FastAPI(
    title="Vehicle Tracking & Fleet Monitoring Platform",
    description="Real-time GPS tracking, route optimization, and fleet management API",
    version="0.1.0",
)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(api_v1_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Fleet Tracking API is running. Check /docs for API documentation."}
