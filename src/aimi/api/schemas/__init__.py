"""Common API schemas."""

from __future__ import annotations

from .chat import ChatRequest, ChatResponsePayload
from .health import HealthPayload
from .response import ErrorInfo, ErrorResponse, SuccessResponse

__all__: list[str] = [
    "ChatRequest",
    "ChatResponsePayload",
    "ErrorInfo",
    "ErrorResponse",
    "SuccessResponse",
    "HealthPayload",
]
