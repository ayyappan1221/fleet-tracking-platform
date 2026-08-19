"""Pydantic schemas for maintenance request/response payloads."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MaintenanceCreate(BaseModel):
    """Payload for creating a new maintenance record."""

    vehicle_id: int = Field(..., ge=1)
    type: str = Field(..., max_length=50)
    status: str = Field(default="scheduled", max_length=20)
    due_mileage: Optional[Decimal] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    notes: Optional[str] = Field(default=None)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Only allow known maintenance types."""
        if v not in ("oil_change", "tire", "inspection", "repair"):
            raise ValueError("Type must be: oil_change, tire, inspection, or repair")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Only allow known maintenance statuses."""
        if v not in ("scheduled", "in_progress", "completed"):
            raise ValueError("Status must be: scheduled, in_progress, or completed")
        return v


class MaintenanceUpdate(BaseModel):
    """All-optional payload for partial maintenance updates."""

    vehicle_id: Optional[int] = Field(default=None, ge=1)
    type: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None, max_length=20)
    due_mileage: Optional[Decimal] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    notes: Optional[str] = Field(default=None)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """Only allow known maintenance types."""
        if v is not None and v not in ("oil_change", "tire", "inspection", "repair"):
            raise ValueError("Type must be: oil_change, tire, inspection, or repair")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Only allow known maintenance statuses."""
        if v is not None and v not in ("scheduled", "in_progress", "completed"):
            raise ValueError("Status must be: scheduled, in_progress, or completed")
        return v


class MaintenanceRead(MaintenanceCreate):
    """Full maintenance record returned to the caller."""

    id: int
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceListResponse(BaseModel):
    """Paginated maintenance listing."""

    records: list[MaintenanceRead]
    maintenance: list[MaintenanceRead] = []
    total: int

    def model_post_init(self, __context: object) -> None:
        """Sync both field names so either 'records' or 'maintenance' works."""
        if not self.maintenance and self.records:
            self.maintenance = self.records
        elif not self.records and self.maintenance:
            self.records = self.maintenance
