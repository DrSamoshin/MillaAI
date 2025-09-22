"""New chat endpoints with proper chat support."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import get_auth_service, get_current_user, get_db_session
from aimi.api.v1.schemas import SuccessResponse
from aimi.db.models import User
from aimi.db.models.chat import Chat
from aimi.repositories.users import UserRepository
from aimi.services.auth import AuthService
from aimi.services.chat import ChatService
from aimi.services.connection_manager import connection_manager
from aimi.services.deps import get_chat_service

router = APIRouter(prefix="/chats", tags=["chats"])
ws_router = APIRouter(prefix="/ws", tags=["chats"])


class CreateChatRequest(BaseModel):
    """Request to create a new chat."""
    title: str | None = None
    model: str = "gpt-4"
    settings: dict | None = None


class CreateChatResponse(BaseModel):
    """Response with created chat info."""
    chat_id: str
    title: str | None
    model: str
    settings: dict


class SendMessageRequest(BaseModel):
    """Request to send message."""
    content: str
    client_msg_id: str | None = None


class SendMessageResponse(BaseModel):
    """Response with user and assistant messages."""
    user_message: dict
    assistant_message: dict
    status: str
    model: str


class ChatListItem(BaseModel):
    """Chat item in list."""
    chat_id: str
    title: str | None
    model: str
    settings: dict
    last_seq: int | None
    last_active_at: str | None
    created_at: str


class ChatListResponse(BaseModel):
    """Response with list of user's chats."""
    chats: list[ChatListItem]
    total: int


class MessageItem(BaseModel):
    """Message item in history."""
    id: str
    seq: int
    role: str
    content: str
    created_at: str
    truncated: bool
    from_summary: bool


class MessageHistoryResponse(BaseModel):
    """Response with chat message history."""
    messages: list[MessageItem]
    total: int
    has_more: bool


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
    except Exception as exc:
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


@router.post("/", response_model=SuccessResponse[CreateChatResponse])
async def create_chat(
    request: CreateChatRequest = ...,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> SuccessResponse[CreateChatResponse]:
    """Create a new chat."""
    chat_id = uuid4()

    # Set default settings if not provided
    settings = request.settings or {"temperature": 0.7}

    # Use ChatService to ensure chat exists (this will create it)
    await chat_service._ensure_chat_exists(
        chat_id=chat_id,
        user_id=current_user.id,
        title=request.title,
        model=request.model,
        settings=settings,
    )

    return SuccessResponse(data=CreateChatResponse(
        chat_id=str(chat_id),
        title=request.title,
        model=request.model,
        settings=settings,
    ))


@router.get("/", response_model=SuccessResponse[ChatListResponse])
async def list_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ChatListResponse]:
    """Get all chats for current user."""
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == current_user.id)
        .order_by(Chat.last_active_at.desc().nulls_last(), Chat.created_at.desc())
    )
    chats = result.scalars().all()

    chat_items = [
        ChatListItem(
            chat_id=str(chat.id),
            title=chat.title,
            model=chat.model,
            settings=chat.settings,
            last_seq=chat.last_seq,
            last_active_at=chat.last_active_at.isoformat() if chat.last_active_at else None,
            created_at=chat.created_at.isoformat(),
        )
        for chat in chats
    ]

    return SuccessResponse(data=ChatListResponse(
        chats=chat_items,
        total=len(chat_items),
    ))


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> SuccessResponse[dict]:
    """Delete a chat and all its messages."""
    success = await chat_service.delete_chat(chat_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found or not owned by user"
        )

    return SuccessResponse(data={"deleted": True, "chat_id": str(chat_id)})


@router.get("/{chat_id}/messages", response_model=SuccessResponse[MessageHistoryResponse])
async def get_chat_messages(
    chat_id: UUID = Path(...),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> SuccessResponse[MessageHistoryResponse]:
    """Get message history for a chat."""
    result = await chat_service.get_chat_messages(
        chat_id=chat_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return SuccessResponse(data=MessageHistoryResponse(**result))


@router.post("/{chat_id}/send", response_model=SuccessResponse[SendMessageResponse])
async def send_message(
    chat_id: UUID = Path(...),
    request: SendMessageRequest = ...,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> SuccessResponse[SendMessageResponse]:
    """Send message to chat via REST API."""
    result = await chat_service.send_message(
        chat_id=chat_id,
        content=request.content,
        client_msg_id=request.client_msg_id,
        user_id=current_user.id,
    )

    return SuccessResponse(data=SendMessageResponse(**result))


@ws_router.websocket("/chat/{chat_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: UUID = Path(...),
    current_user: User = Depends(_get_current_user_ws),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    # Register connection in manager
    await connection_manager.connect(chat_id, websocket)

    try:
        while True:
            # Receive message
            message_data = await websocket.receive_json()

            if not isinstance(message_data, dict) or "content" not in message_data:
                await websocket.send_json({
                    "status": "error",
                    "error": {
                        "code": "invalid_message_format",
                        "message": "Message must be JSON with 'content' field",
                    }
                })
                continue

            content = message_data["content"].strip()
            if not content:
                continue

            client_msg_id = message_data.get("client_msg_id")

            try:
                # Send "thinking" message for long processing
                await websocket.send_json({
                    "status": "thinking",
                    "message": "Обрабатываю ваш запрос..."
                })

                # Process message
                result = await chat_service.send_message(
                    chat_id=chat_id,
                    content=content,
                    client_msg_id=client_msg_id,
                    user_id=current_user.id,
                )

                # Send response
                await websocket.send_json({
                    "status": "success",
                    "data": result,
                })

            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "error": {
                        "code": "message_processing_failed",
                        "message": "Failed to process message",
                        "details": {"reason": str(e)},
                    }
                })

    except WebSocketDisconnect:
        # Unregister connection when disconnected
        await connection_manager.disconnect(chat_id)


def _extract_token(websocket: WebSocket) -> str | None:
    """Pull bearer token from the Authorization header."""
    authorization = websocket.headers.get("Authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


__all__ = ["router", "ws_router"]