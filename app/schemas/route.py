"""Pydantic schemas for route planning and stop payloads."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class RouteStopBase(BaseModel):
    """A geographic point on a route, shared by create/read schemas."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=255)
    planned_arrival: Optional[datetime] = None


class RouteStopCreate(RouteStopBase):
    """Stop payload with an explicit stop order."""
    sequence: int = Field(..., ge=1)


class RouteStopRead(RouteStopBase):
    """Stop record as persisted, including arrival status."""
    id: int
    route_id: int
    sequence: int = Field(..., ge=1)
    actual_arrival: Optional[datetime] = None
    status: str = "pending"

    model_config = {"from_attributes": True}


class RouteBase(BaseModel):
    """Fields common to route create and read schemas."""
    vehicle_id: int = Field(..., ge=1)
    driver_id: Optional[int] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None


class RouteCreate(RouteBase):
    """Payload for planning a route: vehicle plus at least two stops."""
    stops: List[RouteStopCreate] = Field(default_factory=list, min_length=2)


class RouteStart(BaseModel):
    """Optional custom start timestamp for a route."""
    actual_start: Optional[datetime] = None


class RouteRead(RouteBase):
    """Full route record including computed distance and stops."""
    id: int
    distance_km: Decimal
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    stops: List[RouteStopRead] = []

    model_config = {"from_attributes": True}


class RouteListResponse(BaseModel):
    """Paginated route listing."""
    routes: List[RouteRead]
    total: int
