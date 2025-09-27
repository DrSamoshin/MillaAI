"""Repository for chat persistence operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.chat import Chat

import logging

logger = logging.getLogger(__name__)


class ChatRepository:
    """Data access layer for Chat model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, chat_id: uuid.UUID) -> Chat | None:
        """Get chat by ID."""
        result = await self._session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()

    async def get_user_chat_by_id(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> Chat | None:
        """Get chat by ID if it belongs to user."""
        result = await self._session.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_chat(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        model: str = "gpt-4",
        settings: dict | None = None,
    ) -> Chat:
        """Create new chat."""
        chat = Chat(
            id=chat_id,
            user_id=user_id,
            title=title,
            model=model,
            settings=settings or {"temperature": 0.7},
        )
        self._session.add(chat)
        await self._session.flush()
        await self._session.refresh(chat)
        return chat

    async def delete_chat(self, chat_id: uuid.UUID) -> bool:
        """Delete chat by ID."""
        result = await self._session.execute(
            delete(Chat).where(Chat.id == chat_id)
        )
        return result.rowcount > 0

    async def update_last_activity(self, chat_id: uuid.UUID, last_seq: int, last_active_at: datetime) -> None:
        """Update chat's last activity metadata."""
        await self._session.execute(
            update(Chat).where(Chat.id == chat_id).values(
                last_seq=last_seq,
                last_active_at=last_active_at,
            )
        )

    async def get_user_chats(self, user_id: uuid.UUID) -> list[Chat]:
        """Get all chats for user."""
        result = await self._session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.last_active_at.desc())
        )
        return list(result.scalars().all())


__all__ = ["ChatRepository"]