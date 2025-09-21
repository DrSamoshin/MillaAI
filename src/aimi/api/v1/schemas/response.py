"""Pydantic schemas for API responses."""

from __future__ import annotations

from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field


PayloadT = TypeVar("PayloadT")


class SuccessResponse(BaseModel, Generic[PayloadT]):
    """Envelope for successful responses."""

    status: Literal["success"] = Field(default="success", frozen=True)
    data: PayloadT


class ErrorInfo(BaseModel):
    """Structured information describing an API error."""

    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: Optional[Any] = Field(default=None, description="Optional error context.")


class ErrorResponse(BaseModel):
    """Envelope for error responses."""

    status: Literal["error"] = Field(default="error", frozen=True)
    error: ErrorInfo


__all__ = ["SuccessResponse", "ErrorInfo", "ErrorResponse"]
