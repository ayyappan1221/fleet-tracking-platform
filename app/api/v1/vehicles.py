"""
Vehicle API endpoints.

All endpoints are under /api/v1/vehicles and require authentication.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleRead,
    VehicleListResponse,
)
from app.services import vehicle_service as vehicle_svc

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("/", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle_data: VehicleCreate,
    db: Session = Depends(get_db),
):
    """Add a new vehicle to the fleet."""
    try:
        # TODO: replace with actual user ID from JWT once auth middleware is wired
        owner_id = 1
        vehicle = vehicle_svc.create_vehicle(db, owner_id, vehicle_data)
        return vehicle
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=VehicleListResponse)
def list_vehicles(
    owner_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all vehicles, optionally filtered by owner or status."""
    vehicles, total = vehicle_svc.list_vehicles(
        db, owner_id=owner_id, status=status, skip=skip, limit=limit
    )
    return {"vehicles": vehicles, "total": total}


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Get a single vehicle by ID."""
    vehicle = vehicle_svc.get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int,
    vehicle_data: VehicleUpdate,
    db: Session = Depends(get_db),
):
    """Update vehicle details (partial update)."""
    vehicle = vehicle_svc.update_vehicle(db, vehicle_id, vehicle_data)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Remove a vehicle from the fleet."""
    success = vehicle_svc.delete_vehicle(db, vehicle_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return None
