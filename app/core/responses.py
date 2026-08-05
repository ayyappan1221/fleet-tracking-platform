"""
Response helpers.

Every endpoint returns one consistent JSON envelope:
    {"success": bool, "data": ..., "message": str}
"""
from typing import Any, Optional


def api_success(data: Any = None, message: str = "") -> dict:
    """Wrap a successful payload in the standard envelope."""
    return {"success": True, "data": data, "message": message}


def api_error(message: str, data: Any = None) -> dict:
    """Build an error body (used by exception handlers)."""
    return {"success": False, "data": data, "message": message}