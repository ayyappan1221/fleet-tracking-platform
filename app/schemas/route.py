from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class RouteStopBase(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=255)
    planned_arrival: Optional[datetime] = None


class RouteStopCreate(RouteStopBase):
    sequence: int = Field(..., ge=1)


class RouteStopRead(RouteStopBase):
    id: int
    route_id: int
    actual_arrival: Optional[datetime] = None
    status: str = "pending"

    model_config = {"from_attributes": True}


class RouteBase(BaseModel):
    vehicle_id: int = Field(..., ge=1)
    driver_id: Optional[int] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None


class RouteCreate(RouteBase):
    stops: List[RouteStopCreate] = Field(default_factory=list, min_length=2)


class RouteStart(BaseModel):
    actual_start: Optional[datetime] = None


class RouteRead(RouteBase):
    id: int
    distance_km: Decimal
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    stops: List[RouteStopRead] = []

    model_config = {"from_attributes": True}


class RouteListResponse(BaseModel):
    routes: List[RouteRead]
    total: int
