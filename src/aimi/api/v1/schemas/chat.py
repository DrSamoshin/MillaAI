"""Schemas for chat endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload submitted when a user sends a chat message."""

    user_id: str | None = Field(
        default=None,
        description="Identifier of the user sending the message; defaults to the authenticated user.",
    )
    message: str = Field(..., description="User message content.")


class ChatResponsePayload(BaseModel):
    """Payload returned after the assistant generates a reply."""

    reply: str = Field(..., description="Assistant response text.")
    model: str = Field(..., description="LLM model used to generate the reply.")


__all__: list[str] = ["ChatRequest", "ChatResponsePayload"]
