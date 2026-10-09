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

from app.core.authorization import (
    is_manager,
    owned_vehicle_ids,
    require_route_access,
    require_stop_access,
    require_vehicle_access,
)
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.route import RouteCreate, RouteRead, RouteListResponse
from app.services import route_service as route_svc
from app.services import behavior_service as behavior_svc

router = APIRouter(
    prefix="/routes",
    tags=["routes"],
)


@router.post("/", response_model=ApiResponse[RouteRead], status_code=status.HTTP_201_CREATED)
def plan_route(
    route_data: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Plan a new delivery route with multi-stop optimization."""
    try:
        require_vehicle_access(db, route_data.vehicle_id, current_user)
        if (
            route_data.driver_id is not None
            and not is_manager(current_user)
            and route_data.driver_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign routes to other drivers",
            )
        route = route_svc.plan_route(db, route_data)
        return api_success(route, "Route planned")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[RouteListResponse])
def list_routes(
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List routes: managers see the fleet, others see their own vehicles."""
    if is_manager(current_user):
        routes, total = route_svc.list_routes(
            db, vehicle_id=vehicle_id, driver_id=driver_id, skip=skip, limit=limit
        )
        return api_success({"routes": routes, "total": total}, "Routes fetched")
    if vehicle_id is not None:
        require_vehicle_access(db, vehicle_id, current_user)
        routes, total = route_svc.list_routes(
            db, vehicle_id=vehicle_id, skip=skip, limit=limit
        )
        return api_success({"routes": routes, "total": total}, "Routes fetched")
    if driver_id is not None and driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot list other drivers' routes",
        )
    scope = owned_vehicle_ids(db, current_user)
    routes, total = route_svc.list_routes(
        db, driver_id=current_user.id, skip=skip, limit=limit
    )
    owned_routes, _ = route_svc.list_routes(
        db, vehicle_ids=scope, skip=skip, limit=limit
    )
    seen = {r.id for r in routes}
    combined = list(routes) + [r for r in owned_routes if r.id not in seen]
    return api_success(
        {"routes": combined, "total": len(combined)}, "Routes fetched"
    )


@router.get("/{route_id}", response_model=ApiResponse[RouteRead])
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single route by ID."""
    route = require_route_access(db, route_id, current_user)
    try:
        score = behavior_svc.compute_vehicle_score(db, route.vehicle_id)
        route.score = score.get("score")
    except Exception:
        pass
    return api_success(route, "Route fetched")


@router.get("/{route_id}/score", response_model=ApiResponse)
def get_route_score(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Computed driver behavior score 0-100 for a route's vehicle pings."""
    require_route_access(db, route_id, current_user)
    try:
        result = behavior_svc.compute_route_score(db, route_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return api_success(result, "Route score computed")


@router.post("/{route_id}/start", response_model=ApiResponse[RouteRead])
def start_route(
    route_id: int,
    started_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a planned route (mark as in-progress)."""
    try:
        require_route_access(db, route_id, current_user)
        route = route_svc.start_route(db, route_id, started_at)
        return api_success(route, "Route started")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{route_id}/complete", response_model=ApiResponse[RouteRead])
def complete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a route as completed."""
    try:
        require_route_access(db, route_id, current_user)
        route = route_svc.complete_route(db, route_id)
        return api_success(route, "Route completed")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/stops/{stop_id}/arrive", response_model=ApiResponse, status_code=status.HTTP_200_OK)
def mark_stop_arrived(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a delivery stop as arrived."""
    try:
        require_stop_access(db, stop_id, current_user)
        route_svc.mark_stop_arrived(db, stop_id)
        return api_success(None, f"Stop {stop_id} marked as arrived")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )