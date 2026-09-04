"""
backend/schemas/common.py
-------------------------
Common and generic schemas for pagination and API responses.
"""

from __future__ import annotations

import math
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page number (1-indexed)")
    limit: int = Field(..., description="Page size limit")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(cls, items: list[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        pages = math.ceil(total / limit) if limit > 0 else 1
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)


class MessageResponse(BaseModel):
    """Simple status/message response."""
    message: str
    status: str = "ok"
