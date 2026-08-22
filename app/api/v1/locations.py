"""
Location API endpoints.

All endpoints are under /api/locations and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.location import (
    LocationCreate,
    LocationRead,
    LocationListResponse,
)
from app.services import location_service as location_svc

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post(
    "/",
    response_model=ApiResponse[LocationRead],
    status_code=status.HTTP_201_CREATED,
)
def record_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a new GPS location for a vehicle."""
    try:
        location = location_svc.record_location(db, location_data)
        return api_success(location, "Location recorded")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[LocationListResponse])
def list_locations(
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all locations, optionally filtered by vehicle."""
    locations, total = location_svc.list_locations(
        db, vehicle_id=vehicle_id, skip=skip, limit=limit
    )
    return api_success(
        {"locations": locations, "total": total},
        "Locations fetched",
    )


@router.get("/vehicle/{vehicle_id}/latest", response_model=ApiResponse[LocationRead])
def get_latest_location(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the most recent GPS location for a specific vehicle."""
    location = location_svc.get_latest_location(db, vehicle_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No locations found for vehicle {vehicle_id}",
        )
    return api_success(location, "Latest location fetched")
