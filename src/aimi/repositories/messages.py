"""Repository for message persistence operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.message import Message
from aimi.db.models.enums import MessageRole

import logging

logger = logging.getLogger(__name__)


class MessageRepository:
    """Data access layer for Message model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_message(
        self,
        chat_id: uuid.UUID,
        role: MessageRole,
        content: str,
        seq: int,
        request_id: uuid.UUID | None = None,
    ) -> Message:
        """Create new message."""
        message = Message(
            chat_id=chat_id,
            seq=seq,
            role=role,
            content=content,
            request_id=request_id,
        )
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    async def get_by_request_id(self, chat_id: uuid.UUID, request_id: uuid.UUID) -> Message | None:
        """Get message by request ID to check for duplicates."""
        result = await self._session.execute(
            select(Message).where(
                Message.chat_id == chat_id,
                Message.request_id == request_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_next_sequence(self, chat_id: uuid.UUID) -> int:
        """Get next sequence number for a chat."""
        result = await self._session.execute(
            select(func.coalesce(func.max(Message.seq), 0) + 1).where(
                Message.chat_id == chat_id
            )
        )
        return result.scalar() or 1

    async def get_chat_messages(
        self,
        chat_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Message], int]:
        """Get messages for a chat with pagination."""
        # Get total count
        count_result = await self._session.execute(
            select(func.count(Message.id)).where(Message.chat_id == chat_id)
        )
        total_count = count_result.scalar() or 0

        # Get messages
        result = await self._session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.seq.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = list(result.scalars().all())

        return messages, total_count

    async def delete_chat_messages(self, chat_id: uuid.UUID) -> int:
        """Delete all messages for a chat."""
        result = await self._session.execute(
            delete(Message).where(Message.chat_id == chat_id)
        )
        return result.rowcount

    async def get_user_messages(self, user_id: uuid.UUID) -> list[Message]:
        """Get all messages for user across all chats."""
        # Get messages through chat relationship
        result = await self._session.execute(
            select(Message)
            .join(Message.chat)
            .where(Message.chat.has(user_id=user_id))
            .order_by(Message.created_at.desc())
        )
        return list(result.scalars().all())


__all__ = ["MessageRepository"]