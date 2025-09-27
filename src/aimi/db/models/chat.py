"""Chat ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from aimi.db.base import Base

if TYPE_CHECKING:
    from aimi.db.models.goal import Goal
    from aimi.db.models.message import Message
    from aimi.db.models.notification import Notification
    from aimi.db.models.user import User


class Chat(Base):
    """Persisted chat conversation."""

    __tablename__ = "chats"
    __table_args__ = (
        Index("ix_chats_user_id", "user_id"),
        Index("ix_chats_last_active_at", "last_active_at"),
        Index("ix_chats_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", order_by="Message.seq"
    )
    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="chat", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="chat", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Chat(id={self.id!s}, user_id={self.user_id!s}, title={self.title!r})"


__all__ = ["Chat"]