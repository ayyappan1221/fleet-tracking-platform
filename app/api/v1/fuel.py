"""
Fuel API endpoints.

All endpoints are under /api/fuel and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    get_vehicle_or_404,
    is_manager,
    owned_vehicle_ids,
    require_vehicle_access,
)
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.route import Route
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.fuel import (
    FuelCreate,
    FuelEfficiency,
    FuelListResponse,
    FuelRead,
)
from app.services import fuel_service as fuel_svc

router = APIRouter(prefix="/fuel", tags=["fuel"])


def _require_fuel_vehicle(db: Session, vehicle_id: int, user: User):
    """Owner, assigned driver, or manager may log/view fuel for a vehicle."""
    vehicle = get_vehicle_or_404(db, vehicle_id)
    if is_manager(user):
        return vehicle
    if vehicle.owner_id == user.id:
        return vehicle
    assigned = (
        db.query(Route)
        .filter(Route.vehicle_id == vehicle_id, Route.driver_id == user.id)
        .first()
    )
    if assigned is not None:
        return vehicle
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this vehicle",
    )


@router.post(
    "/",
    response_model=ApiResponse[FuelRead],
    status_code=status.HTTP_201_CREATED,
)
def log_fill(
    fuel_data: FuelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a fuel fill-up for a vehicle."""
    try:
        _require_fuel_vehicle(db, fuel_data.vehicle_id, current_user)
        fill = fuel_svc.log_fill(db, fuel_data)
        return api_success(fill, "Fuel fill logged")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/vehicle/{vehicle_id}", response_model=ApiResponse[FuelListResponse])
def list_vehicle_fuel(
    vehicle_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List fuel logs for a vehicle (owner/driver-assigned/manager)."""
    _require_fuel_vehicle(db, vehicle_id, current_user)
    logs, total = fuel_svc.list_for_vehicle(
        db, vehicle_id=vehicle_id, skip=skip, limit=limit
    )
    return api_success(
        {"fuel_logs": logs, "total": total},
        "Fuel logs fetched",
    )


@router.get(
    "/vehicle/{vehicle_id}/efficiency",
    response_model=ApiResponse[FuelEfficiency],
)
def fuel_efficiency(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Efficiency stats (km/L, cost/km) for a vehicle."""
    _require_fuel_vehicle(db, vehicle_id, current_user)
    stats = fuel_svc.efficiency_stats(db, vehicle_id)
    return api_success(stats, "Fuel efficiency computed")
