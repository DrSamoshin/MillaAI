"""Goal model."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, CheckConstraint, Date, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from aimi.db.base import Base
from aimi.db.models.enums import DependencyType, GoalCategory, GoalStatus

if TYPE_CHECKING:
    from aimi.db.models.chat import Chat
    from aimi.db.models.event import Event
    from aimi.db.models.goal_embedding import GoalEmbedding
    from aimi.db.models.notification import Notification
    from aimi.db.models.user import User


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

    # New fields from migration
    category: Mapped[GoalCategory | None] = mapped_column(Enum(*[e.value for e in GoalCategory], name="goalcategory"), nullable=True)

    status: Mapped[GoalStatus] = mapped_column(
        Enum(*[e.value for e in GoalStatus], name="goalstatus"),
        nullable=False,
        default=GoalStatus.TODO.value,
        index=True,
    )

    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Planning fields
    estimated_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    events: Mapped[list[Event]] = relationship("Event", back_populates="goal")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="goal")
    embedding: Mapped[GoalEmbedding | None] = relationship("GoalEmbedding", back_populates="goal", uselist=False, cascade="all, delete-orphan")

    # Graph relationships
    dependent_goals: Mapped[list["GoalDependency"]] = relationship(
        "GoalDependency", foreign_keys="GoalDependency.parent_goal_id", back_populates="parent_goal"
    )
    dependency_goals: Mapped[list["GoalDependency"]] = relationship(
        "GoalDependency", foreign_keys="GoalDependency.dependent_goal_id", back_populates="dependent_goal"
    )


class GoalDependency(Base):
    """Goal dependency model for graph relationships."""

    __tablename__ = "goal_dependencies"
    __table_args__ = (
        CheckConstraint("parent_goal_id != dependent_goal_id", name="no_self_dependency"),
        CheckConstraint("strength BETWEEN 1 AND 5", name="valid_strength"),
        UniqueConstraint("parent_goal_id", "dependent_goal_id", name="unique_goal_dependency"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    parent_goal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dependent_goal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(*[e.value for e in DependencyType], name="dependencytype"),
        nullable=False,
        default=DependencyType.REQUIRES.value,
    )

    # Strength of the dependency (1-5)
    strength: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Optional notes about why this dependency exists
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    parent_goal: Mapped["Goal"] = relationship(
        "Goal",
        foreign_keys=[parent_goal_id],
        back_populates="dependent_goals"
    )
    dependent_goal: Mapped["Goal"] = relationship(
        "Goal",
        foreign_keys=[dependent_goal_id],
        back_populates="dependency_goals"
    )


__all__ = ["Goal", "GoalDependency"]