"""Goal tracking models."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, TIMESTAMP, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from aimi.db.base import Base

if TYPE_CHECKING:
    from aimi.db.models import User
    from aimi.db.models.chat import Chat


class GoalStatus(enum.Enum):
    """Goal status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskStatus(enum.Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Goal(Base):
    """Goal model for user objectives."""

    __tablename__ = "goals"

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

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        index=True,
    )

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="goals")
    chat: Mapped[Chat] = relationship("Chat", back_populates="goals")
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="goal", cascade="all, delete-orphan")


class Task(Base):
    """Task model for goal breakdown."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    goal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )

    due_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    reminder_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    goal: Mapped[Goal] = relationship("Goal", back_populates="tasks")


class MentalState(Base):
    """Mental state analysis model."""

    __tablename__ = "mental_states"

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

    mood: Mapped[str | None] = mapped_column(String(50), nullable=True)
    energy_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_emotions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="summary",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mental_states")
    chat: Mapped[Chat] = relationship("Chat", back_populates="mental_states")


__all__ = ["Goal", "Task", "MentalState", "GoalStatus", "TaskStatus"]