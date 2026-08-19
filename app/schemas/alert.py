"""Pydantic schemas for alert payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AlertCreate(BaseModel):
    """Payload for creating a new alert."""
    vehicle_id: Optional[int] = Field(default=None)
    type: str = Field(...)
    severity: str = Field(default="info")
    message: str = Field(..., min_length=1)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Only allow known alert types."""
        if v not in ("geofence", "maintenance", "speed", "low_fuel"):
            raise ValueError("Type must be: geofence, maintenance, speed, or low_fuel")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Only allow known severity levels."""
        if v not in ("info", "warning", "critical"):
            raise ValueError("Severity must be: info, warning, or critical")
        return v


class AlertRead(AlertCreate):
    """Alert record as persisted."""
    id: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Paginated alert listing."""
    alerts: list[AlertRead]
    total: int
