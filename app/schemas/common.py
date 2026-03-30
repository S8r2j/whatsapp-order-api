"""
Shared Pydantic schemas used across multiple modules.

Includes pagination wrappers and the standard API error response format.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated list response."""

    items: List[DataT]
    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page number (1-based)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Structured error response returned for all non-2xx responses."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[object] = Field(None, description="Additional structured details")
    request_id: Optional[str] = Field(None, description="Request trace ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Envelope wrapping ErrorDetail."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Response for the /health liveness endpoint."""

    status: str = "ok"
    environment: str
    version: str = "0.1.0"
