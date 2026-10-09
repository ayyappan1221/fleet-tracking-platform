"""Pydantic schemas for fuel log payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FuelCreate(BaseModel):
    """Payload for logging a fuel fill-up."""

    vehicle_id: int = Field(..., ge=1)
    liters: float = Field(..., gt=0)
    cost: float = Field(default=0, ge=0)
    odometer_km: float = Field(..., ge=0)
    note: Optional[str] = Field(default=None, max_length=2000)


class FuelRead(FuelCreate):
    """Persisted fuel log record."""

    id: int
    filled_at: datetime

    model_config = {"from_attributes": True}


class FuelListResponse(BaseModel):
    """Paginated fuel log listing."""

    fuel_logs: list[FuelRead]
    total: int


class FuelEfficiency(BaseModel):
    """Fuel efficiency stats computed from odometer deltas."""

    fills: int
    total_liters: float
    total_cost: float
    total_km: float
    km_per_liter: Optional[float] = None
    cost_per_km: Optional[float] = None
