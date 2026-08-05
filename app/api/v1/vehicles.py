"""
Vehicle API endpoints.

All endpoints are under /api/vehicles and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleRead,
    VehicleListResponse,
)
from app.services import vehicle_service as vehicle_svc

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post(
    "/",
    response_model=ApiResponse[VehicleRead],
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    vehicle_data: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new vehicle to the fleet."""
    try:
        vehicle = vehicle_svc.create_vehicle(db, current_user.id, vehicle_data)
        return api_success(vehicle, "Vehicle created")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[VehicleListResponse])
def list_vehicles(
    owner_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicles, optionally filtered by owner or status."""
    vehicles, total = vehicle_svc.list_vehicles(
        db, owner_id=owner_id, status=status, skip=skip, limit=limit
    )
    return api_success(
        {"vehicles": vehicles, "total": total},
        "Vehicles fetched",
    )


@router.get("/{vehicle_id}", response_model=ApiResponse[VehicleRead])
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single vehicle by ID."""
    vehicle = vehicle_svc.get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return api_success(vehicle, "Vehicle fetched")


@router.patch("/{vehicle_id}", response_model=ApiResponse[VehicleRead])
def update_vehicle(
    vehicle_id: int,
    vehicle_data: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update vehicle details (partial update)."""
    vehicle = vehicle_svc.update_vehicle(db, vehicle_id, vehicle_data)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return api_success(vehicle, "Vehicle updated")


@router.delete("/{vehicle_id}", response_model=ApiResponse, status_code=status.HTTP_200_OK)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a vehicle from the fleet."""
    success = vehicle_svc.delete_vehicle(db, vehicle_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return api_success(None, "Vehicle deleted")