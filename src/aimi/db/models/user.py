"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from aimi.db.base import Base


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
    timezone: Mapped[str] = mapped_column(
        String(64), default="UTC", server_default=text("'UTC'")
    )
    locale: Mapped[str] = mapped_column(
        String(32), default="en_US", server_default=text("'en_US'")
    )
    profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"User(id={self.id!s}, email={self.email!r})"


__all__ = ["User"]
