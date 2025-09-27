"""Repository for goal persistence operations."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.goal import Goal, GoalDependency
from aimi.db.models.goal_embedding import GoalEmbedding
from aimi.db.models.enums import GoalStatus, DependencyType

import logging

logger = logging.getLogger(__name__)


class GoalRepository:
    """Data access layer for Goal, GoalDependency, and GoalEmbedding models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # Goal CRUD operations
    async def create_goal(
        self,
        *,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        title: str,
        description: str | None = None,
        category: GoalCategory | None = None,
        priority: int = 3,
        estimated_duration_days: int | None = None,
        difficulty_level: int = 0,
        deadline: str | None = None,
    ) -> Goal:
        """Create and persist a new goal."""
        goal = Goal(
            user_id=user_id,
            chat_id=chat_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            estimated_duration_days=estimated_duration_days,
            difficulty_level=difficulty_level,
            deadline=deadline,
        )
        self._session.add(goal)
        await self._session.flush()

        logger.info(
            "goal_created",
            extra={
                "goal_id": str(goal.id),
                "user_id": str(goal.user_id),
                "title": goal.title,
            },
        )
        return goal

    async def get_by_id(self, goal_id: uuid.UUID) -> Goal | None:
        """Fetch a goal by primary key."""
        return await self._session.get(Goal, goal_id)

    async def get_user_goals(
        self,
        user_id: uuid.UUID,
        status: GoalStatus | None = None,
        statuses: list[GoalStatus] | None = None,
        limit: int | None = None,
        offset: int = 0
    ) -> list[Goal]:
        """Get goals for a specific user with optional filtering."""
        query = select(Goal).where(Goal.user_id == user_id)

        if status:
            query = query.where(Goal.status == status)
        elif statuses:
            query = query.where(Goal.status.in_(statuses))

        query = query.order_by(Goal.priority.desc(), Goal.created_at.desc())

        if limit:
            query = query.offset(offset).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update_goal(self, goal: Goal, **update_data) -> Goal:
        """Update goal fields."""
        for field, value in update_data.items():
            if hasattr(goal, field):
                setattr(goal, field, value)

        await self._session.flush()
        return goal


    # Goal Dependencies
    async def create_dependency(
        self,
        *,
        parent_goal_id: uuid.UUID,
        dependent_goal_id: uuid.UUID,
        dependency_type: DependencyType = DependencyType.REQUIRES,
        strength: int = 1,
        notes: str | None = None,
    ) -> GoalDependency:
        """Create a goal dependency relationship."""
        dependency = GoalDependency(
            parent_goal_id=parent_goal_id,
            dependent_goal_id=dependent_goal_id,
            dependency_type=dependency_type,
            strength=strength,
            notes=notes,
        )
        self._session.add(dependency)
        await self._session.flush()
        return dependency

    async def get_goal_dependencies(self, goal_id: uuid.UUID) -> list[GoalDependency]:
        """Get all dependencies for a goal (goals that this goal depends on)."""
        result = await self._session.execute(
            select(GoalDependency).where(GoalDependency.dependent_goal_id == goal_id)
        )
        return list(result.scalars().all())

    async def get_goal_dependents(self, goal_id: uuid.UUID) -> list[GoalDependency]:
        """Get all dependents for a goal (goals that depend on this goal)."""
        result = await self._session.execute(
            select(GoalDependency).where(GoalDependency.parent_goal_id == goal_id)
        )
        return list(result.scalars().all())

    async def delete_dependency(self, dependency: GoalDependency) -> None:
        """Delete a goal dependency."""
        await self._session.delete(dependency)

    # Goal Embeddings
    async def create_embedding(
        self,
        *,
        goal_id: uuid.UUID,
        summary_text: str,
        embedding: list[float],
        content_hash: str,
    ) -> GoalEmbedding:
        """Create goal embedding for semantic similarity."""
        goal_embedding = GoalEmbedding(
            goal_id=goal_id,
            summary_text=summary_text,
            embedding=embedding,
            content_hash=content_hash,
        )
        self._session.add(goal_embedding)
        await self._session.flush()
        return goal_embedding

    async def get_embedding_by_goal_id(self, goal_id: uuid.UUID) -> GoalEmbedding | None:
        """Get embedding for a specific goal."""
        result = await self._session.execute(
            select(GoalEmbedding).where(GoalEmbedding.goal_id == goal_id)
        )
        return result.scalar_one_or_none()

    async def update_embedding(
        self,
        embedding: GoalEmbedding,
        *,
        summary_text: str | None = None,
        embedding_vector: list[float] | None = None,
        content_hash: str | None = None,
    ) -> GoalEmbedding:
        """Update goal embedding."""
        if summary_text is not None:
            embedding.summary_text = summary_text
        if embedding_vector is not None:
            embedding.embedding = embedding_vector
        if content_hash is not None:
            embedding.content_hash = content_hash

        await self._session.flush()
        return embedding

    # Statistics and analytics
    async def get_goal_stats(self, user_id: uuid.UUID) -> dict:
        """Get goal statistics for user."""
        # Total goals
        total_stmt = select(func.count(Goal.id)).where(Goal.user_id == user_id)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Goals by status
        status_stmt = select(Goal.status, func.count(Goal.id)).where(
            Goal.user_id == user_id
        ).group_by(Goal.status)
        status_result = await self._session.execute(status_stmt)
        by_status = {status: count for status, count in status_result.fetchall()}

        # Goals by category
        category_stmt = select(Goal.category, func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.category.is_not(None)
        ).group_by(Goal.category)
        category_result = await self._session.execute(category_stmt)
        by_category = {category if category else None: count for category, count in category_result.fetchall()}

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category
        }


__all__ = ["GoalRepository"]