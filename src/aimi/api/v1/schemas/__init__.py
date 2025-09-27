"""Common API schemas."""

from __future__ import annotations

from .chat import (
    ChatRequest,
    ChatResponsePayload,
    CreateChatRequest,
    CreateChatResponse,
    SendMessageRequest,
    SendMessageResponse,
    ChatListItem,
    ChatListResponse,
    MessageItem,
    MessageHistoryResponse,
)
from .goals import (
    GoalDependencyItem,
    GoalItem,
    CreateGoalRequest,
    UpdateGoalRequest,
    GoalListResponse,
    MentalStateItem,
    MentalStateListResponse,
)
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
from .user import (
    UserStatsResponse,
    UserAvailabilitySettings,
    UpdateUserAvailabilityRequest,
)

__all__: list[str] = [
    # Chat schemas
    "ChatRequest",
    "ChatResponsePayload",
    "CreateChatRequest",
    "CreateChatResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "ChatListItem",
    "ChatListResponse",
    "MessageItem",
    "MessageHistoryResponse",
    # Goals schemas
    "GoalDependencyItem",
    "GoalItem",
    "CreateGoalRequest",
    "UpdateGoalRequest",
    "GoalListResponse",
    "MentalStateItem",
    "MentalStateListResponse",
    # Response schemas
    "ErrorInfo",
    "ErrorResponse",
    "SuccessResponse",
    # Health schemas
    "HealthPayload",
    # Auth schemas
    "AppleSignInRequest",
    "AuthResponsePayload",
    "RefreshRequest",
    "RefreshResponsePayload",
    "TokenPayload",
    "UserPayload",
    # User schemas
    "UserStatsResponse",
    "UserAvailabilitySettings",
    "UpdateUserAvailabilityRequest",
]
