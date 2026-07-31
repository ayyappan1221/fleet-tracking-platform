from fastapi import FastAPI

from app.api.v1 import router as api_v1_router

app = FastAPI(
    title="Vehicle Tracking & Fleet Monitoring Platform",
    description="Real-time GPS tracking, route optimization, and fleet management API",
    version="0.1.0",
)


app.include_router(api_v1_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Fleet Tracking API is running. Check /docs for API documentation."}
