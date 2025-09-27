"""Goal embedding model for semantic similarity search."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import pgvector.sqlalchemy

from aimi.db.base import Base

if TYPE_CHECKING:
    from aimi.db.models.goal import Goal


class GoalEmbedding(Base):
    """Vector embeddings for goals to enable semantic similarity search."""

    __tablename__ = "goal_embeddings"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    goal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Summary text generated from chat context when goal was created/updated
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    # OpenAI embedding vector (1536 dimensions) of the summary_text
    embedding: Mapped[pgvector.sqlalchemy.Vector] = mapped_column(
        pgvector.sqlalchemy.Vector(1536),
        nullable=False,
    )

    # Hash of content used to generate embedding (for change detection)
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

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
    goal: Mapped["Goal"] = relationship("Goal", back_populates="embedding")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"GoalEmbedding(id={self.id!s}, goal_id={self.goal_id!s})"


__all__ = ["GoalEmbedding"]