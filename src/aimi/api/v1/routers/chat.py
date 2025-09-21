"""Chat endpoints (REST + WebSocket)."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.exceptions import WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import (
    get_auth_service,
    get_conversation_service,
    get_current_user,
    get_db_session,
)
from aimi.api.v1.schemas import ChatRequest, ChatResponsePayload, SuccessResponse
from aimi.core.errors import BaseAppError
from aimi.db.models import User
from aimi.repositories.users import UserRepository
from aimi.services.auth import AuthService
from aimi.services.conversation import ConversationService

router = APIRouter(prefix="/chat", tags=["chat"])
ws_router = APIRouter(prefix="/ws", tags=["chat"])


@router.post("/send/", response_model=SuccessResponse[ChatResponsePayload])
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> SuccessResponse[ChatResponsePayload]:
    """Handle chat message submitted via REST."""

    user_id = str(current_user.id)
    raw_result = await service.handle_incoming(user_id=user_id, message=payload.message)
    response = ChatResponsePayload.model_validate(raw_result)
    return SuccessResponse(data=response)


async def _get_current_user_ws(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Authenticate WebSocket connection using bearer token."""

    token = _extract_token(websocket)
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing bearer token",
        )

    try:
        user_id = auth_service.parse_access_token(token)
    except Exception as exc:  # pragma: no cover - invalid token path
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        ) from exc

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found",
        )
    return user


@ws_router.websocket("/chat")
async def chat_ws(
    websocket: WebSocket,
    current_user: User = Depends(_get_current_user_ws),
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Bi-directional chat endpoint using WebSocket."""

    await websocket.accept()
    user_id = str(current_user.id)
    try:
        while True:
            message = await websocket.receive_text()
            message = message.strip()
            if not message:
                continue

            try:
                raw_result = await service.handle_incoming(
                    user_id=user_id,
                    message=message,
                )
            except BaseAppError as exc:
                await websocket.send_json(
                    {
                        "status": "error",
                        "error": {
                            "code": exc.code,
                            "message": exc.message,
                            "details": exc.details,
                        },
                    }
                )
                continue
            except Exception as exc:  # pragma: no cover - runtime safeguard
                await websocket.send_json(
                    {
                        "status": "error",
                        "error": {
                            "code": "chat.ws_internal_error",
                            "message": "Failed to process message.",
                            "details": {"reason": str(exc)},
                        },
                    }
                )
                continue

            await websocket.send_json(
                {
                    "status": "success",
                    "reply": raw_result.get("reply", ""),
                    "model": raw_result.get("model", ""),
                }
            )
    except WebSocketDisconnect:
        return


def _extract_token(websocket: WebSocket) -> str | None:
    """Pull bearer token from the Authorization header."""

    authorization = websocket.headers.get("Authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


__all__ = ["router", "ws_router", "chat_ws", "send_message"]
