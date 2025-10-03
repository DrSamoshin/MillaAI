"""Repository for goal persistence operations."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.goal import Goal, GoalDependency
from aimi.db.models.goal_embedding import GoalEmbedding
from aimi.db.models.enums import GoalStatus, GoalCategory, DependencyType

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
        motivation: str | None = None,
        success_criteria: str | None = None,
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
            motivation=motivation,
            success_criteria=success_criteria,
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
        statuses: list[GoalStatus | str] | None = None,
        limit: int | None = None,
        offset: int = 0
    ) -> list[Goal]:
        """Get goals for a specific user with optional filtering."""
        query = select(Goal).where(Goal.user_id == user_id)

        if status:
            query = query.where(Goal.status == status.value)
        elif statuses:
            # Handle both enum objects and string values
            status_values = []
            for s in statuses:
                if hasattr(s, 'value'):
                    status_values.append(s.value)
                else:
                    status_values.append(s)
            query = query.where(Goal.status.in_(status_values))

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

    # Specific field update methods
    async def update_goal_title(self, goal_id: uuid.UUID, title: str) -> Goal | None:
        """Update goal title."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.title = title.strip()
        await self._session.flush()
        logger.info(f"Updated goal title: {goal_id}")
        return goal

    async def update_goal_description(self, goal_id: uuid.UUID, description: str | None) -> Goal | None:
        """Update goal description."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.description = description.strip() if description else None
        await self._session.flush()
        logger.info(f"Updated goal description: {goal_id}")
        return goal

    async def update_goal_priority(self, goal_id: uuid.UUID, priority: int) -> Goal | None:
        """Update goal priority with validation."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        # Validate priority range
        priority = max(1, min(5, priority))
        goal.priority = priority
        await self._session.flush()
        logger.info(f"Updated goal priority to {priority}: {goal_id}")
        return goal

    async def update_goal_category(self, goal_id: uuid.UUID, category: GoalCategory | None) -> Goal | None:
        """Update goal category."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.category = category
        await self._session.flush()
        logger.info(f"Updated goal category to {category}: {goal_id}")
        return goal

    async def update_goal_deadline(self, goal_id: uuid.UUID, deadline: str | None) -> Goal | None:
        """Update goal deadline."""
        from datetime import date

        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        deadline_date = None
        if deadline:
            try:
                deadline_date = date.fromisoformat(deadline)
            except ValueError:
                raise ValueError(f"Invalid deadline format: {deadline}. Use YYYY-MM-DD")

        goal.deadline = deadline_date
        await self._session.flush()
        logger.info(f"Updated goal deadline to {deadline}: {goal_id}")
        return goal

    async def update_goal_motivation(self, goal_id: uuid.UUID, motivation: str | None) -> Goal | None:
        """Update goal motivation."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.motivation = motivation.strip() if motivation else None
        await self._session.flush()
        logger.info(f"Updated goal motivation: {goal_id}")
        return goal

    async def update_goal_success_criteria(self, goal_id: uuid.UUID, success_criteria: str | None) -> Goal | None:
        """Update goal success criteria."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.success_criteria = success_criteria.strip() if success_criteria else None
        await self._session.flush()
        logger.info(f"Updated goal success criteria: {goal_id}")
        return goal

    async def update_goal_difficulty(self, goal_id: uuid.UUID, difficulty_level: int) -> Goal | None:
        """Update goal difficulty level with validation."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        # Validate difficulty range
        difficulty_level = max(0, min(10, difficulty_level))
        goal.difficulty_level = difficulty_level
        await self._session.flush()
        logger.info(f"Updated goal difficulty to {difficulty_level}: {goal_id}")
        return goal

    async def update_goal_duration(self, goal_id: uuid.UUID, estimated_duration_days: int | None) -> Goal | None:
        """Update goal estimated duration."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        # Validate duration
        if estimated_duration_days is not None:
            estimated_duration_days = max(1, estimated_duration_days)

        goal.estimated_duration_days = estimated_duration_days
        await self._session.flush()
        logger.info(f"Updated goal duration to {estimated_duration_days}: {goal_id}")
        return goal


    # Goal Dependencies
    async def create_dependency(
        self,
        *,
        parent_goal_id: uuid.UUID,
        dependent_goal_id: uuid.UUID,
        dependency_type: str = DependencyType.REQUIRES.value,
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

        # Recalculate status of the dependent goal
        await self.recalculate_goal_status_after_dependency_change(dependent_goal_id)

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
        dependent_goal_id = dependency.dependent_goal_id
        await self._session.delete(dependency)
        await self._session.flush()

        # Recalculate status of the dependent goal after removing dependency
        await self.recalculate_goal_status_after_dependency_change(dependent_goal_id)

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

    # Dependency status management
    async def recalculate_goal_status_after_dependency_change(self, goal_id: uuid.UUID) -> None:
        """Recalculate goal status after dependency changes."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return

        # Check all REQUIRES dependencies
        dependencies = await self.get_goal_dependencies(goal_id)
        should_block = False

        for dep in dependencies:
            # Only REQUIRES dependencies can block a goal
            if dep.dependency_type == DependencyType.REQUIRES.value:
                parent_goal = await self.get_by_id(dep.parent_goal_id)
                if parent_goal and parent_goal.status not in [GoalStatus.DONE.value, GoalStatus.CANCELED.value]:
                    should_block = True
                    break

        # Update status based on dependencies
        if should_block and goal.status == GoalStatus.TODO.value:
            # Block the goal
            await self.update_goal(goal, status=GoalStatus.BLOCKED.value)
            logger.info(f"Blocked goal '{goal.title}' due to incomplete dependencies")
        elif not should_block and goal.status == GoalStatus.BLOCKED.value:
            # Unblock the goal
            await self.update_goal(goal, status=GoalStatus.TODO.value)
            logger.info(f"Unblocked goal '{goal.title}' - all dependencies satisfied")

    async def recalculate_dependent_goals_status(self, parent_goal_id: uuid.UUID) -> None:
        """Recalculate status of goals that depend on the given goal."""
        parent_goal = await self.get_by_id(parent_goal_id)
        if not parent_goal:
            return

        # Find all goals that depend on this goal
        dependents = await self.get_goal_dependents(parent_goal_id)

        for dependency in dependents:
            # Only process REQUIRES dependencies
            if dependency.dependency_type == DependencyType.REQUIRES.value:
                dependent_goal = await self.get_by_id(dependency.dependent_goal_id)

                if dependent_goal:
                    # Check if the dependent goal should be unblocked/blocked
                    await self.recalculate_goal_status_after_dependency_change(dependent_goal.id)


__all__ = ["GoalRepository"]