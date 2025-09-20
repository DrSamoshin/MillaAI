"""Common API schemas."""

from __future__ import annotations

from .health import HealthPayload
from .response import ErrorInfo, ErrorResponse, SuccessResponse

__all__: list[str] = ["ErrorInfo", "ErrorResponse", "SuccessResponse", "HealthPayload"]
