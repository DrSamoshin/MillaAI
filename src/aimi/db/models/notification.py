"""Notification model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, TIMESTAMP, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from aimi.db.base import Base
from aimi.db.models.enums import NotificationStatus, NotificationType

if TYPE_CHECKING:
    from aimi.db.models.chat import Chat
    from aimi.db.models.goal import Goal
    from aimi.db.models.user import User


class Notification(Base):
    """Smart notification model for assistant messages."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chat_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional connection for context
    goal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Message content
    message: Mapped[str] = mapped_column(Text, nullable=False)

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(*[e.value for e in NotificationType], name="notificationtype"),
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_for: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    # Status tracking
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(*[e.value for e in NotificationStatus], name="notificationstatus"),
        nullable=False,
        default=NotificationStatus.PENDING.value,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Context for generation
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="notifications")
    chat: Mapped[Chat] = relationship("Chat", back_populates="notifications")
    goal: Mapped[Goal | None] = relationship("Goal", back_populates="notifications")


__all__ = ["Notification"]