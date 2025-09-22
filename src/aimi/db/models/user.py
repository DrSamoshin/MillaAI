"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aimi.db.base import Base

if TYPE_CHECKING:
    from aimi.db.models.chat import Chat
    from aimi.db.models.goals import Goal, MentalState


class UserRole(PyEnum):
    """Available user roles."""

    USER = "user"
    ADMIN = "admin"


class User(Base):
    """Persisted application user."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    apple_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=text("'user'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    chats: Mapped[list[Chat]] = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    mental_states: Mapped[list[MentalState]] = relationship("MentalState", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"User(id={self.id!s}, email={self.email!r})"


__all__ = ["User", "UserRole"]
