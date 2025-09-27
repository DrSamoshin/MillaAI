"""Schemas for chat endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload submitted when a user sends a chat message."""

    message: str = Field(
        ...,
        description="User message content.",
        min_length=1,
    )


class ChatResponsePayload(BaseModel):
    """Payload returned after the assistant generates a reply."""

    reply: str = Field(..., description="Assistant response text.")
    model: str = Field(..., description="LLM model used to generate the reply.")


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
    request_id: str | None
    created_at: str


class MessageHistoryResponse(BaseModel):
    """Response with chat message history."""
    messages: list[MessageItem]
    total: int
    has_more: bool


__all__ = [
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
]
