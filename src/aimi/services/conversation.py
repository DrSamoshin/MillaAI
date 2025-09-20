"""Conversation service placeholder.

Этот модуль будет отвечать за online-логику общения: запись сообщений,
подготовку контекста и вызов оркестратора. Пока он содержит только каркас,
чтобы было понятно, где появится реализация.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from aimi.llm.client import ChatMessage, LLMClient
from aimi.memory.cache.session import SessionCache


class MessageRepository(Protocol):
    """Интерфейс доступа к сохранению сообщений."""

    async def save(self, message: dict) -> None:  # pragma: no cover - placeholder
        ...


@dataclass(slots=True)
class ConversationService:
    """High-level entrypoint for chat interactions (initial implementation)."""

    message_repository: MessageRepository
    llm_client: LLMClient
    session_cache: SessionCache | None = None

    async def handle_incoming(self, *, user_id: str, message: str) -> dict[str, str]:
        """Handle an incoming message and return assistant response."""

        occurred_at = datetime.now(timezone.utc).isoformat()
        user_payload = {
            "user_id": user_id,
            "role": "user",
            "content": message,
            "occurred_at": occurred_at,
        }
        await self.message_repository.save(user_payload)

        if self.session_cache is not None:
            await self.session_cache.append(
                user_id,
                {
                    "message_id": str(uuid4()),
                    "role": "user",
                    "content": message,
                    "occurred_at": occurred_at,
                },
            )
            history = await self.session_cache.fetch(user_id)
        else:
            history = [
                {
                    "role": "user",
                    "content": message,
                }
            ]

        prompt_messages = [
            ChatMessage(
                role=entry.get("role", "user"),
                content=str(entry.get("content", "")),
            )
            for entry in history
            if entry.get("content")
        ]
        if not prompt_messages:
            prompt_messages = [ChatMessage(role="user", content=message)]

        reply = await self.llm_client.generate(prompt_messages)

        assistant_payload = {
            "user_id": user_id,
            "role": "assistant",
            "content": reply,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.message_repository.save(assistant_payload)

        if self.session_cache is not None:
            await self.session_cache.append(
                user_id,
                {
                    "message_id": str(uuid4()),
                    "role": "assistant",
                    "content": reply,
                    "occurred_at": assistant_payload["occurred_at"],
                },
            )

        return {"reply": reply, "model": self.llm_client.model_name}


__all__ = ["ConversationService", "MessageRepository"]
