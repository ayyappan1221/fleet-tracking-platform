"""
Geofence API endpoints.

All endpoints are under /api/geofences and require a valid JWT.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.geofence import GeofenceCreate, GeofenceRead, GeofenceUpdate, GeofenceListResponse
from app.services import geofence_service as geofence_svc

router = APIRouter(prefix="/geofences", tags=["geofences"])


@router.post(
    "/",
    response_model=ApiResponse[GeofenceRead],
    status_code=status.HTTP_201_CREATED,
)
def create_geofence(
    geofence_data: GeofenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new geofence boundary owned by the authenticated user."""
    try:
        geofence = geofence_svc.create_geofence(db, owner_id=current_user.id, data=geofence_data)
        return api_success(geofence, "Geofence created")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[GeofenceListResponse])
def list_geofences(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List geofences for the authenticated user."""
    geofences, total = geofence_svc.list_geofences(
        db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return api_success(
        {"geofences": geofences, "total": total},
        "Geofences fetched",
    )


@router.patch("/{geofence_id}", response_model=ApiResponse[GeofenceRead])
def update_geofence(
    geofence_id: int,
    geofence_data: GeofenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update geofence details (partial update)."""
    geofence = geofence_svc.update_geofence(db, geofence_id, geofence_data)
    if not geofence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geofence {geofence_id} not found",
        )
    return api_success(geofence, "Geofence updated")
