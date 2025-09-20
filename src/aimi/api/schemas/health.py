"""Schemas specific to the health endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthPayload(BaseModel):
    """Payload describing service health state."""

    status: Literal["ok"] = Field(default="ok")
    version: str = Field(..., description="Application version.")


__all__ = ["HealthPayload"]
