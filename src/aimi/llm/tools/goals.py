"""Goal management tools for LLM."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.repositories.goals import GoalRepository
from aimi.db.models.enums import GoalStatus, GoalCategory, DependencyType

logger = logging.getLogger(__name__)


class GoalTools:
    """Tools for LLM to manage user goals using unified goals architecture."""

    def __init__(self, db_session: AsyncSession, user_id: UUID, chat_id: UUID):
        self.db = db_session
        self.user_id = user_id
        self.chat_id = chat_id
        self.repo = GoalRepository(db_session)

    async def create_goal(
        self,
        title: str,
        description: str | None = None,
        priority: int = 3,
        category: str | None = None,
        deadline: str | None = None,
        estimated_duration_days: int | None = None,
        difficulty_level: int = 0,
    ) -> Dict[str, Any]:
        """Create a new goal for the user."""
        logger.info(f"create_goal called with title: {title}, db_session: {self.db}")
        try:
            # Parse deadline if provided
            deadline_date = None
            if deadline:
                try:
                    deadline_date = date.fromisoformat(deadline)
                except ValueError:
                    return {"error": f"Invalid deadline format: {deadline}. Use YYYY-MM-DD"}

            # Validate priority and difficulty
            priority = max(1, min(5, priority))
            difficulty_level = max(0, min(10, difficulty_level))

            # Validate and convert category
            goal_category = None
            if category:
                try:
                    # Try to create enum from string (handles both 'learning' and 'LEARNING')
                    goal_category = GoalCategory(category)
                except ValueError:
                    valid_categories = [e.value for e in GoalCategory]
                    return {"error": f"Invalid category: {category}. Must be one of {valid_categories}"}

            # Create goal using repository
            logger.info(f"About to call repo.create_goal")
            goal = await self.repo.create_goal(
                user_id=self.user_id,
                chat_id=self.chat_id,
                title=title,
                description=description,
                category=goal_category,
                priority=priority,
                estimated_duration_days=estimated_duration_days,
                difficulty_level=difficulty_level,
                deadline=deadline_date,
            )
            logger.info(f"Goal created by repository")

            logger.info(f"About to commit transaction")
            await self.db.commit()
            logger.info(f"Transaction committed successfully")

            logger.info(f"Created goal '{title}' for user {self.user_id}")

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "description": goal.description,
                "priority": goal.priority,
                "category": goal.category if goal.category else None,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "estimated_duration_days": goal.estimated_duration_days,
                "difficulty_level": goal.difficulty_level,
                "status": goal.status,
                "created_at": goal.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            await self.db.rollback()
            return {"error": f"Failed to create goal: {str(e)}"}

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        """Update goal status (todo -> done, etc)."""
        try:
            goal = await self.repo.get_by_id(UUID(goal_id))
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Validate status
            try:
                status_enum = GoalStatus(status)
            except ValueError:
                valid_statuses = [e.value for e in GoalStatus]
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Update goal
            await self.repo.update_goal(goal, status=status_enum)
            await self.db.commit()

            logger.info(f"Updated goal '{goal.title}' status to {status} for user {self.user_id}")

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "status": status,
                "updated_at": goal.updated_at.isoformat(),
                "notes": notes,
            }

        except Exception as e:
            logger.error(f"Failed to update goal status: {e}")
            await self.db.rollback()
            return {"error": f"Failed to update goal status: {str(e)}"}

    async def create_goal_dependency(
        self,
        parent_goal_id: str,
        dependent_goal_id: str,
        dependency_type: str = "requires",
        strength: int = 1,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        """Create dependency relationship between goals."""
        try:
            # Validate dependency type
            try:
                dependency_type_enum = DependencyType(dependency_type)
            except ValueError:
                valid_types = [e.value for e in DependencyType]
                return {"error": f"Invalid dependency_type: {dependency_type}. Must be one of {valid_types}"}

            # Validate strength
            strength = max(1, min(5, strength))

            # Verify both goals exist and belong to user
            parent_goal = await self.repo.get_by_id(UUID(parent_goal_id))
            dependent_goal = await self.repo.get_by_id(UUID(dependent_goal_id))

            if not parent_goal or parent_goal.user_id != self.user_id:
                return {"error": f"Parent goal {parent_goal_id} not found or not owned by user"}

            if not dependent_goal or dependent_goal.user_id != self.user_id:
                return {"error": f"Dependent goal {dependent_goal_id} not found or not owned by user"}

            # Create dependency using repository
            dependency = await self.repo.create_dependency(
                parent_goal_id=UUID(parent_goal_id),
                dependent_goal_id=UUID(dependent_goal_id),
                dependency_type=dependency_type_enum,
                strength=strength,
                notes=notes,
            )

            await self.db.commit()

            logger.info(f"Created goal dependency: {parent_goal_id} -> {dependent_goal_id}")

            return {
                "dependency_id": str(dependency.id),
                "parent_goal_id": parent_goal_id,
                "parent_goal_title": parent_goal.title,
                "dependent_goal_id": dependent_goal_id,
                "dependent_goal_title": dependent_goal.title,
                "dependency_type": dependency_type,
                "strength": strength,
                "notes": notes,
                "created_at": dependency.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create goal dependency: {e}")
            await self.db.rollback()
            return {"error": f"Failed to create goal dependency: {str(e)}"}

    async def get_user_goals(
        self,
        status: str | None = None,
        include_dependencies: bool = True,
    ) -> Dict[str, Any]:
        """Get goals for the user, optionally filtered by status."""
        try:
            # Parse status filter
            status_enum = None
            if status:
                try:
                    status_enum = GoalStatus(status)
                except ValueError:
                    valid_statuses = [e.value for e in GoalStatus]
                    return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Get goals using repository
            goals = await self.repo.get_user_goals(
                user_id=self.user_id,
                status=status_enum
            )

            goals_data = []
            for goal in goals:
                goal_data = {
                    "goal_id": str(goal.id),
                    "title": goal.title,
                    "description": goal.description,
                    "priority": goal.priority,
                    "category": goal.category if goal.category else None,
                    "deadline": goal.deadline.isoformat() if goal.deadline else None,
                    "estimated_duration_days": goal.estimated_duration_days,
                    "difficulty_level": goal.difficulty_level,
                    "status": goal.status,
                    "created_at": goal.created_at.isoformat(),
                    "updated_at": goal.updated_at.isoformat(),
                }

                # Add dependencies if requested
                if include_dependencies:
                    dependencies = await self.repo.get_goal_dependencies(goal.id)
                    goal_data["dependencies"] = [
                        {
                            "dependency_id": str(dep.id),
                            "parent_goal_id": str(dep.parent_goal_id),
                            "dependency_type": dep.dependency_type,
                            "strength": dep.strength,
                            "notes": dep.notes,
                        }
                        for dep in dependencies
                    ]

                goals_data.append(goal_data)

            return {
                "goals": goals_data,
                "total": len(goals_data),
                "filter_status": status,
            }

        except Exception as e:
            logger.error(f"Failed to get user goals: {e}")
            return {"error": f"Failed to get user goals: {str(e)}"}

    async def get_available_goals(self) -> Dict[str, Any]:
        """Get goals that are available for work (status=todo and no blocked dependencies)."""
        try:
            # Get all TODO goals
            goals = await self.repo.get_user_goals(
                user_id=self.user_id,
                status=GoalStatus.TODO.value
            )

            available_goals = []
            for goal in goals:
                # Check if goal has any incomplete dependencies
                dependencies = await self.repo.get_goal_dependencies(goal.id)
                is_blocked = False

                for dep in dependencies:
                    parent_goal = await self.repo.get_by_id(dep.parent_goal_id)
                    if parent_goal and parent_goal.status != GoalStatus.DONE:
                        is_blocked = True
                        break

                if not is_blocked:
                    available_goals.append({
                        "goal_id": str(goal.id),
                        "title": goal.title,
                        "description": goal.description,
                        "priority": goal.priority,
                        "category": goal.category if goal.category else None,
                        "deadline": goal.deadline.isoformat() if goal.deadline else None,
                        "difficulty_level": goal.difficulty_level,
                        "estimated_duration_days": goal.estimated_duration_days,
                    })

            # Sort by priority (high to low) then by deadline (soonest first)
            available_goals.sort(
                key=lambda g: (
                    -g["priority"],  # Higher priority first
                    g["deadline"] or "9999-12-31"  # Earlier deadline first
                )
            )

            return {
                "available_goals": available_goals,
                "total": len(available_goals),
            }

        except Exception as e:
            logger.error(f"Failed to get available goals: {e}")
            return {"error": f"Failed to get available goals: {str(e)}"}

    async def get_active_goals(self) -> Dict[str, Any]:
        """Get active goals (TODO and BLOCKED status) for conversation context."""
        try:
            logger.info(f"Getting active goals for user {self.user_id}")
            goals = await self.repo.get_user_goals(
                user_id=self.user_id,
                statuses=[GoalStatus.TODO, GoalStatus.BLOCKED]
            )
            logger.info(f"Successfully got {len(goals)} active goals")

            if not goals:
                return {"success": True, "goals": [], "message": "No active goals"}

            goal_list = []
            for goal in goals:
                goal_list.append({
                    "id": str(goal.id),
                    "title": goal.title,
                    "description": goal.description,
                    "status": goal.status,
                    "category": goal.category if goal.category else None,
                    "priority": goal.priority,
                    "difficulty_level": goal.difficulty_level,
                    "deadline": goal.deadline.isoformat() if goal.deadline else None,
                    "estimated_duration_days": goal.estimated_duration_days,
                })

            return {
                "success": True,
                "goals": goal_list,
                "count": len(goal_list),
                "message": f"Found {len(goal_list)} active goals"
            }

        except Exception as e:
            logger.error(f"Error getting active goals for user {self.user_id}: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["GoalTools"]