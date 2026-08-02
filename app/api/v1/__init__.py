from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.routes import router as routes_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(vehicles_router)
router.include_router(routes_router)

__all__ = ["router"]
