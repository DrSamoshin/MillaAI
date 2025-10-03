"""New chat endpoints with proper chat support."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException

from aimi.api.v1.deps import get_auth_service, get_current_user, get_uow_dependency
from aimi.db.session import UnitOfWork, get_unit_of_work
from aimi.api.v1.schemas import SuccessResponse
from aimi.api.v1.schemas.chat import (
    ChatListItem,
    ChatListResponse,
    CreateChatRequest,
    CreateChatResponse,
    MessageHistoryResponse,
    MessageItem,
    SendMessageRequest,
    SendMessageResponse,
)
from aimi.db.models import Chat, User, MessageRole
from aimi.services.auth import AuthService
from aimi.services.chat import ChatService
from aimi.services.connection_manager import connection_manager
from aimi.services.deps import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])
ws_router = APIRouter(prefix="/ws", tags=["chats"])


async def _get_current_user_ws(
    websocket: WebSocket,
    uow: UnitOfWork = Depends(get_uow_dependency),
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

    user = await uow.users().get_by_id(user_id)
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
    uow: UnitOfWork = Depends(get_uow_dependency),
) -> SuccessResponse[CreateChatResponse]:
    """Create a new chat."""
    chat_id = uuid4()

    # Set default settings if not provided
    settings = request.settings or {"temperature": 0.7}

    # Use ChatService to ensure chat exists (this will create it)
    await chat_service._ensure_chat_exists(
        uow=uow,
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
    uow: UnitOfWork = Depends(get_uow_dependency),
) -> SuccessResponse[ChatListResponse]:
    """Get all chats for current user."""
    chats = await uow.chats().get_user_chats(current_user.id)

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
    uow: UnitOfWork = Depends(get_uow_dependency),
) -> SuccessResponse[dict]:
    """Delete a chat and all its messages."""
    success = await chat_service.delete_chat(uow, chat_id, current_user.id)

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
    uow: UnitOfWork = Depends(get_uow_dependency),
) -> SuccessResponse[MessageHistoryResponse]:
    """Get message history for a chat."""
    result = await chat_service.get_chat_messages(
        uow=uow,
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
    uow: UnitOfWork = Depends(get_uow_dependency),
) -> SuccessResponse[SendMessageResponse]:
    """Send message to chat via REST API."""
    messages = await chat_service.send_message(
        uow=uow,
        chat_id=chat_id,
        content=request.content,
        client_msg_id=request.client_msg_id,
        user_id=current_user.id,
    )

    # Convert last assistant message for REST response (backward compatibility)
    assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT.value]
    last_message = assistant_messages[-1] if assistant_messages else messages[-1]

    result_dict = {
        "id": str(last_message.id),
        "seq": last_message.seq,
        "role": last_message.role,
        "content": last_message.content,
        "created_at": last_message.created_at.isoformat(),
        "request_id": str(last_message.request_id) if last_message.request_id else None,
    }

    return SuccessResponse(data=SendMessageResponse(**result_dict))


@ws_router.websocket("/chat/{chat_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: UUID = Path(...),
    current_user: User = Depends(_get_current_user_ws),
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """WebSocket endpoint for real-time chat."""
    logger.info(f"[WS] WebSocket connected for chat {chat_id}, user {current_user.id}")
    await websocket.accept()

    # Register connection in manager
    await connection_manager.connect(chat_id, websocket)

    try:
        while True:
            # Receive message
            logger.info(f"[WS] Waiting for message...")
            message_data = await websocket.receive_json()
            logger.info(f"[WS] Received message data: {message_data}")

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
                logger.info(f"[WS] Processing message from user {current_user.id} in chat {chat_id}: '{content[:50]}...'")

                # Step 1: Save user message and return immediately
                async with get_unit_of_work() as uow:
                    logger.info(f"[WS] Saving user message...")
                    user_msg = await chat_service.save_user_message(
                        uow=uow,
                        chat_id=chat_id,
                        content=content,
                        client_msg_id=client_msg_id,
                        user_id=current_user.id,
                    )
                    logger.info(f"[WS] User message saved with seq: {user_msg.seq}")

                # Send user message immediately
                user_message_dict = {
                    "id": str(user_msg.id),
                    "seq": user_msg.seq,
                    "role": user_msg.role,
                    "content": user_msg.content,
                    "created_at": user_msg.created_at.isoformat(),
                    "request_id": str(user_msg.request_id) if user_msg.request_id else client_msg_id,
                    "chat_id": str(user_msg.chat_id),
                }
                await websocket.send_json(user_message_dict)
                logger.info(f"[WS] Sent user message immediately")

                # Step 2: Generate assistant response
                async with get_unit_of_work() as uow:
                    logger.info(f"[WS] Generating assistant response...")
                    assistant_messages = await chat_service.generate_assistant_response(
                        uow=uow,
                        chat_id=chat_id,
                        user_content=content,
                        user_id=current_user.id,
                    )
                    logger.info(f"[WS] Generated {len(assistant_messages)} assistant messages")

                # Send all assistant messages
                for i, message in enumerate(assistant_messages):
                    logger.info(f"[WS] Sending assistant message {i+1}/{len(assistant_messages)}: role={message.role}")

                    message_dict = {
                        "id": str(message.id),
                        "seq": message.seq,
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                        "request_id": client_msg_id,  # Link to original request
                        "chat_id": str(message.chat_id),
                    }

                    await websocket.send_json(message_dict)
                    logger.info(f"[WS] Successfully sent assistant message {i+1} to client")

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