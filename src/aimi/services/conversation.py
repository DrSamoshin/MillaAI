"""Conversation service placeholder.

Этот модуль будет отвечать за online-логику общения: запись сообщений,
подготовку контекста и вызов оркестратора. Пока он содержит только каркас,
чтобы было понятно, где появится реализация.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class MessageRepository(Protocol):
    """Интерфейс доступа к сохранению сообщений."""

    async def save(self, message: dict) -> None:  # pragma: no cover - placeholder
        ...


@dataclass
class ConversationService:
    """High-level entrypoint for chat interactions (skeleton)."""

    message_repository: MessageRepository

    async def handle_incoming(self, payload: dict) -> dict:
        """Handle an incoming message and return assistant response.

        Реальная логика появится на последующих этапах: пока просто сохраняем входные данные
        и возвращаем заглушку.
        """

        await self.message_repository.save(payload)
        return {"reply": "Aimi is not ready yet."}


__all__ = ["ConversationService", "MessageRepository"]
