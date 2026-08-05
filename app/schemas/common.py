"""Shared response envelope model + helpers used by every endpoint."""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API envelope: { success, data, message }."""

    success: bool = True
    data: Optional[T] = None
    message: str = ""