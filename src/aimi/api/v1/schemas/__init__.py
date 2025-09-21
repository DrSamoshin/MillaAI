"""Common API schemas."""

from __future__ import annotations

from .chat import ChatRequest, ChatResponsePayload
from .health import HealthPayload
from .response import ErrorInfo, ErrorResponse, SuccessResponse
from .auth import (
    AppleSignInRequest,
    AuthResponsePayload,
    RefreshRequest,
    RefreshResponsePayload,
    TokenPayload,
    UserPayload,
)
from .user import UserProfileResponse, DeleteUserResponse

__all__: list[str] = [
    "ChatRequest",
    "ChatResponsePayload",
    "ErrorInfo",
    "ErrorResponse",
    "SuccessResponse",
    "HealthPayload",
    "AppleSignInRequest",
    "AuthResponsePayload",
    "RefreshRequest",
    "RefreshResponsePayload",
    "TokenPayload",
    "UserPayload",
    "UserProfileResponse",
    "DeleteUserResponse",
]
