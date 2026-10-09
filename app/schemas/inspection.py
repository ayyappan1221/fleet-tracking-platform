"""Pydantic schemas for vehicle inspection payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InspectionCreate(BaseModel):
    """Payload for recording a vehicle inspection."""

    vehicle_id: int = Field(..., ge=1)
    type: str = Field(default="pre_trip", max_length=20)
    passed: bool = True
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Only allow known inspection types."""
        if v not in ("pre_trip", "post_trip"):
            raise ValueError("Type must be: pre_trip or post_trip")
        return v


class InspectionRead(InspectionCreate):
    """Persisted inspection record."""

    id: int
    inspector_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionListResponse(BaseModel):
    """Paginated inspection listing."""

    inspections: list[InspectionRead]
    total: int
