"""Mental state model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from aimi.db.base import Base
from aimi.db.models.enums import MentalStateMood

if TYPE_CHECKING:
    from aimi.db.models.user import User


class MentalState(Base):
    """Daily mental state polling model."""

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

    # Daily polling data
    date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    # User responses
    mood: Mapped[MentalStateMood | None] = mapped_column(
        Enum(*[e.value for e in MentalStateMood], name="mentalstatemood"),
        nullable=True,
    )

    readiness_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Polling metadata
    question_asked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mental_states")


__all__ = ["MentalState"]