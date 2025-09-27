"""Message ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from aimi.db.base import Base
from aimi.db.models.enums import MessageRole

if TYPE_CHECKING:
    from aimi.db.models.chat import Chat


class Message(Base):
    """Persisted chat message."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_chat_id_seq", "chat_id", "seq"),
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
        Index("ix_messages_request_id", "request_id"),
        Index("ix_messages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        Enum(*[e.value for e in MessageRole], name="messagerole"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Message(id={self.id!s}, chat_id={self.chat_id!s}, seq={self.seq}, role={self.role})"


__all__ = ["Message"]