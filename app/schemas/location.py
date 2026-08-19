"""Pydantic schemas for location tracking payloads."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    """Payload for recording a vehicle location."""

    vehicle_id: int = Field(..., ge=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed: Optional[float] = Field(default=None, ge=0)
    heading: Optional[float] = Field(default=None, ge=0, le=360)


class LocationRead(LocationCreate):
    """Persisted location record with id and timestamp."""

    id: int
    recorded_at: datetime

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    """Paginated location listing."""

    locations: list[LocationRead]
    total: int
