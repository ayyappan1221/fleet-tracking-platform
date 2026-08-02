"""
Route API endpoints.

Endpoints:
  GET    /api/v1/routes          - list all routes
  POST   /api/v1/routes          - plan a new route with stops
  GET    /api/v1/routes/{id}     - get a single route
  POST   /api/v1/routes/{id}/start  - start a route
  POST   /api/v1/routes/{id}/complete - complete a route
  POST   /api/v1/stops/{id}/arrive   - mark a stop as arrived
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.route import RouteCreate, RouteRead, RouteListResponse
from app.services import route_service as route_svc

router = APIRouter(
    prefix="/routes",
    tags=["routes"],
)


@router.post("/", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def plan_route(route_data: RouteCreate, db: Session = Depends(get_db)):
    """Plan a new delivery route with multi-stop optimization."""
    try:
        route = route_svc.plan_route(db, route_data)
        return route
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=RouteListResponse)
def list_routes(
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List routes, optionally filtered by vehicle or driver."""
    routes, total = route_svc.list_routes(
        db, vehicle_id=vehicle_id, driver_id=driver_id, skip=skip, limit=limit
    )
    return {"routes": routes, "total": total}


@router.get("/{route_id}", response_model=RouteRead)
def get_route(route_id: int, db: Session = Depends(get_db)):
    """Get a single route by ID."""
    route = route_svc.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route {route_id} not found",
        )
    return route


@router.post("/{route_id}/start", response_model=RouteRead)
def start_route(
    route_id: int,
    started_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Start a planned route (mark as in-progress)."""
    try:
        route = route_svc.start_route(db, route_id, started_at)
        return route
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{route_id}/complete", response_model=RouteRead)
def complete_route(route_id: int, db: Session = Depends(get_db)):
    """Mark a route as completed."""
    try:
        route = route_svc.complete_route(db, route_id)
        return route
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/stops/{stop_id}/arrive", status_code=status.HTTP_200_OK)
def mark_stop_arrived(stop_id: int, db: Session = Depends(get_db)):
    """Mark a delivery stop as arrived."""
    try:
        route_svc.mark_stop_arrived(db, stop_id)
        return {"message": f"Stop {stop_id} marked as arrived"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
