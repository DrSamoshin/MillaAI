"""Conversation service placeholder.

Этот модуль будет отвечать за online-логику общения: запись сообщений,
подготовку контекста и вызов оркестратора. Пока он содержит только каркас,
чтобы было понятно, где появится реализация.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aimi.llm.client import ChatMessage, LLMClient


class MessageRepository(Protocol):
    """Интерфейс доступа к сохранению сообщений."""

    async def save(self, message: dict) -> None:  # pragma: no cover - placeholder
        ...


@dataclass(slots=True)
class ConversationService:
    """High-level entrypoint for chat interactions (initial implementation)."""

    message_repository: MessageRepository
    llm_client: LLMClient

    async def handle_incoming(self, *, user_id: str, message: str) -> dict[str, str]:
        """Handle an incoming message and return assistant response."""

        await self.message_repository.save(
            {"user_id": user_id, "role": "user", "content": message}
        )

        reply = await self.llm_client.generate(
            [ChatMessage(role="user", content=message)]
        )

        await self.message_repository.save(
            {"user_id": user_id, "role": "assistant", "content": reply}
        )

        return {"reply": reply, "model": self.llm_client.model_name}


__all__ = ["ConversationService", "MessageRepository"]
