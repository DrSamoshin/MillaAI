"""Event model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from aimi.db.base import Base
from aimi.db.models.enums import EventStatus, EventType

if TYPE_CHECKING:
    from aimi.db.models.goal import Goal
    from aimi.db.models.user import User


class Event(Base):
    """Calendar event model."""

    __tablename__ = "events"

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

    # Optional connection to goal
    goal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Event details
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Event type and status
    event_type: Mapped[EventType] = mapped_column(
        Enum(*[e.value for e in EventType], name="eventtype"),
        nullable=False,
        default=EventType.PERSONAL.value,
    )

    status: Mapped[EventStatus] = mapped_column(
        Enum(*[e.value for e in EventStatus], name="eventstatus"),
        nullable=False,
        default=EventStatus.SCHEDULED.value,
        index=True,
    )

    # Timing
    start_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    end_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="events")
    goal: Mapped[Goal | None] = relationship("Goal", back_populates="events")


__all__ = ["Event"]