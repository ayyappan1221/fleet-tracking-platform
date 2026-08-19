"""Pydantic schemas for geofence request/response payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GeofenceCreate(BaseModel):
    """Payload for creating a new geofence."""

    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="inclusion")
    coordinates: str = Field(..., min_length=1)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Only allow inclusion or exclusion type."""
        if v not in ("inclusion", "exclusion"):
            raise ValueError("Type must be: inclusion or exclusion")
        return v


class GeofenceUpdate(BaseModel):
    """All-optional payload for partial geofence updates."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """Only allow inclusion or exclusion type."""
        if v is not None and v not in ("inclusion", "exclusion"):
            raise ValueError("Type must be: inclusion or exclusion")
        return v


class GeofenceRead(GeofenceCreate):
    """Full geofence record returned to the caller."""

    id: int
    owner_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GeofenceListResponse(BaseModel):
    """Paginated geofence listing."""

    geofences: list[GeofenceRead]
    total: int
