from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.vehicles import router as vehicles_router
from app.api.v1.routes import router as routes_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.geofences import router as geofences_router
from app.api.v1.locations import router as locations_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.maintenance import router as maintenance_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(vehicles_router)
router.include_router(routes_router)
router.include_router(alerts_router)
router.include_router(geofences_router)
router.include_router(locations_router)
router.include_router(dashboard_router)
router.include_router(maintenance_router)

__all__ = ["router"]
