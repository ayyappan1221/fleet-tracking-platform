"""Pydantic schemas for vehicle request/response payloads."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class VehicleBase(BaseModel):
    """Fields common to vehicle create and read schemas."""
    license_plate: str = Field(..., min_length=1, max_length=20)
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=2030)
    vin: str = Field(..., min_length=1, max_length=50)
    fleet_id: Optional[str] = Field(default=None, max_length=50)

    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        """Normalize plate: trim and uppercase."""
        if not v.strip():
            raise ValueError("License plate cannot be empty")
        return v.strip().upper()

    @field_validator("vin")
    @classmethod
    def validate_vin(cls, v: str) -> str:
        """Reject VINs that are unreasonably short."""
        if len(v) < 5:
            raise ValueError("VIN is too short (minimum 5 characters)")
        return v.strip()


class VehicleCreate(VehicleBase):
    """Payload for creating a new vehicle."""


class VehicleUpdate(BaseModel):
    """All-optional payload for partial vehicle updates."""
    license_plate: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1900, le=2030)
    vin: Optional[str] = None
    fleet_id: Optional[str] = None
    current_mileage: Optional[Decimal] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Only allow known vehicle statuses."""
        if v is not None and v not in ("active", "inactive", "repair"):
            raise ValueError("Status must be: active, inactive, or repair")
        return v


class VehicleRead(VehicleBase):
    """Full vehicle record returned to the caller."""
    id: int
    owner_id: int
    status: str
    current_mileage: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleListResponse(BaseModel):
    """Paginated vehicle listing."""
    vehicles: list[VehicleRead]
    total: int
