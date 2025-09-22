"""Chat-related ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import ForeignKey

from aimi.db.base import Base

from pgvector.sqlalchemy import Vector

if TYPE_CHECKING:
    from aimi.db.models import User
    from aimi.db.models.goals import Goal, MentalState


class MessageRole(PyEnum):
    """Available message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


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
    mental_states: Mapped[list[MentalState]] = relationship("MentalState", back_populates="chat", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Chat(id={self.id!s}, user_id={self.user_id!s}, title={self.title!r})"


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
        String(20), nullable=False
    )  # Using String instead of Enum for flexibility
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    truncated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    from_summary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Message(id={self.id!s}, chat_id={self.chat_id!s}, seq={self.seq}, role={self.role.value})"


class Summary(Base):
    """Persisted chat summary with vector embedding."""

    __tablename__ = "summaries"
    __table_args__ = (
        Index("ix_summaries_chat_id", "chat_id"),
        Index("ix_summaries_start_seq", "start_seq"),
        Index("ix_summaries_created_at", "created_at"),
        # Vector index will be created in migration
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False
    )
    start_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Vector field for semantic search
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Summary(id={self.id!s}, chat_id={self.chat_id!s}, range={self.start_seq}-{self.end_seq})"


class Device(Base):
    """Persisted user device for push notifications."""

    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_user_id", "user_id"),
        Index("ix_devices_device_token", "device_token"),
        Index("ix_devices_last_seen", "last_seen"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    device_token: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "ios", "android", "web"
    locale: Mapped[str | None] = mapped_column(String(10))
    timezone: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Device(id={self.id!s}, user_id={self.user_id!s}, platform={self.platform})"


__all__ = ["Chat", "Message", "MessageRole", "Summary", "Device"]