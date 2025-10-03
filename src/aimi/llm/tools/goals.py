"""Goal management tools for LLM."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict
from uuid import UUID

from aimi.db.session import UnitOfWork
from aimi.db.models.enums import GoalStatus, GoalCategory, DependencyType
from aimi.llm.tools.helpers import GoalAnalysisHelpers

logger = logging.getLogger(__name__)


class GoalTools:
    """Tools for LLM to manage user goals using unified goals architecture."""

    def __init__(self, uow: UnitOfWork, user_id: UUID, chat_id: UUID):
        self.uow = uow
        self.user_id = user_id
        self.chat_id = chat_id
        self.analysis_helpers = GoalAnalysisHelpers()

    async def create_goal(
        self,
        title: str,
        description: str | None = None,
        priority: int = 3,
        category: str | None = None,
        deadline: str | None = None,
        estimated_duration_days: int | None = None,
        difficulty_level: int = 0,
        motivation: str | None = None,
        success_criteria: str | None = None,
    ) -> Dict[str, Any]:
        """Create a new goal for the user."""
        logger.info(f"Creating goal: {title}")
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

            # Validate category
            goal_category = None
            if category:
                try:
                    # Try to create enum from string (handles both 'learning' and 'LEARNING')
                    goal_category = GoalCategory(category)
                except ValueError:
                    valid_categories = [e.value for e in GoalCategory]
                    return {"error": f"Invalid category: {category}. Must be one of {valid_categories}"}

            # Create goal using repository
            goal = await self.uow.goals().create_goal(
                user_id=self.user_id,
                chat_id=self.chat_id,
                title=title,
                description=description,
                category=goal_category.value if goal_category else None,
                priority=priority,
                estimated_duration_days=estimated_duration_days,
                difficulty_level=difficulty_level,
                deadline=deadline_date,
                motivation=motivation,
                success_criteria=success_criteria,
            )

            logger.info(f"Created goal '{title}' for user {self.user_id}")

            # Prepare user-friendly message
            deadline_text = f" by {goal.deadline.strftime('%B %d, %Y')}" if goal.deadline else ""
            category_text = f" in {goal.category.value if hasattr(goal.category, 'value') else goal.category}" if goal.category else ""
            priority_text = f" (priority {goal.priority}/5)" if goal.priority != 3 else ""

            success_message = f"Created goal: {goal.title}{category_text}{priority_text}{deadline_text}"

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "description": goal.description,
                "priority": goal.priority,
                "category": goal.category.value if hasattr(goal.category, 'value') else goal.category if goal.category else None,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "estimated_duration_days": goal.estimated_duration_days,
                "difficulty_level": goal.difficulty_level,
                "motivation": goal.motivation,
                "success_criteria": goal.success_criteria,
                "status": goal.status if isinstance(goal.status, str) else goal.status.value,
                "created_at": goal.created_at.isoformat(),
                "success_message": success_message,
            }

        except Exception as e:
            logger.error(f"Failed to create goal: {e}", exc_info=True)
            try:
                await self.uow.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}", exc_info=True)
            return {"error": f"Failed to create goal: {str(e)}"}

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
    ) -> Dict[str, Any]:
        """Update goal status (todo -> done, etc)."""
        try:
            goal = await self.uow.goals().get_by_id(UUID(goal_id))
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Validate status
            try:
                status_enum = GoalStatus(status)
            except ValueError:
                valid_statuses = [e.value for e in GoalStatus]
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Update goal
            await self.uow.goals().update_goal(goal, status=status_enum.value)

            # Recalculate dependent goals status based on new status
            if status in ["done", "canceled"]:
                # Goal is finished - recalculate dependent goals
                await self.uow.goals().recalculate_dependent_goals_status(goal.id)
            elif status == "todo":
                # Goal is set to TODO - check if it should be blocked based on dependencies
                await self.uow.goals().recalculate_goal_status_after_dependency_change(goal.id)

            logger.info(f"Updated goal '{goal.title}' status to {status} for user {self.user_id}")

            # Prepare user-friendly message
            status_text = "completed" if status == "done" else "canceled" if status == "canceled" else status
            success_message = f"Updated goal '{goal.title}' status to {status_text}"

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "status": status,
                "updated_at": goal.updated_at.isoformat(),
                "success_message": success_message,
            }

        except Exception as e:
            logger.error(f"Failed to update goal status: {e}")
            await self.uow.rollback()
            return {"error": f"Failed to update goal status: {str(e)}"}

    async def create_goal_dependency(
        self,
        parent_goal_id: str,
        dependent_goal_id: str,
        dependency_type: str = "requires",
        strength: int = 1,
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
            parent_goal = await self.uow.goals().get_by_id(UUID(parent_goal_id))
            dependent_goal = await self.uow.goals().get_by_id(UUID(dependent_goal_id))

            if not parent_goal or parent_goal.user_id != self.user_id:
                return {"error": f"Parent goal {parent_goal_id} not found or not owned by user"}

            if not dependent_goal or dependent_goal.user_id != self.user_id:
                return {"error": f"Dependent goal {dependent_goal_id} not found or not owned by user"}

            # Create dependency using repository
            dependency = await self.uow.goals().create_dependency(
                parent_goal_id=UUID(parent_goal_id),
                dependent_goal_id=UUID(dependent_goal_id),
                dependency_type=dependency_type_enum.value,
                strength=strength,
            )

            logger.info(f"Created goal dependency: {parent_goal_id} -> {dependent_goal_id}")

            # Prepare user-friendly message
            success_message = f"Created dependency: '{dependent_goal.title}' {dependency_type} '{parent_goal.title}'"

            return {
                "dependency_id": str(dependency.id),
                "parent_goal_id": parent_goal_id,
                "parent_goal_title": parent_goal.title,
                "dependent_goal_id": dependent_goal_id,
                "dependent_goal_title": dependent_goal.title,
                "dependency_type": dependency_type,
                "strength": strength,
                "created_at": dependency.created_at.isoformat(),
                "success_message": success_message,
            }

        except Exception as e:
            logger.error(f"Failed to create goal dependency: {e}")
            await self.uow.rollback()
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
            goals = await self.uow.goals().get_user_goals(
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
                    "category": goal.category.value if hasattr(goal.category, 'value') else goal.category if goal.category else None,
                    "deadline": goal.deadline.isoformat() if goal.deadline else None,
                    "estimated_duration_days": goal.estimated_duration_days,
                    "difficulty_level": goal.difficulty_level,
                    "status": goal.status if isinstance(goal.status, str) else goal.status.value,
                    "created_at": goal.created_at.isoformat(),
                    "updated_at": goal.updated_at.isoformat(),
                }

                # Add dependencies if requested
                if include_dependencies:
                    dependencies = await self.uow.goals().get_goal_dependencies(goal.id)
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

    async def get_goal_by_id(self, goal_id: str) -> Dict[str, Any]:
        """Get a specific goal by UUID."""
        try:
            goal = await self.uow.goals().get_by_id(UUID(goal_id))
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "description": goal.description,
                "priority": goal.priority,
                "category": goal.category.value if hasattr(goal.category, 'value') else goal.category if goal.category else None,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "estimated_duration_days": goal.estimated_duration_days,
                "difficulty_level": goal.difficulty_level,
                "motivation": goal.motivation,
                "success_criteria": goal.success_criteria,
                "status": goal.status if isinstance(goal.status, str) else goal.status.value,
                "created_at": goal.created_at.isoformat(),
                "updated_at": goal.updated_at.isoformat(),
            }

        except ValueError:
            return {"error": f"Invalid goal_id format: {goal_id}. Must be a valid UUID"}
        except Exception as e:
            logger.error(f"Failed to get goal by id: {e}")
            return {"error": f"Failed to get goal by id: {str(e)}"}

    async def get_available_goals(self) -> Dict[str, Any]:
        """Get goals that are available for work (status=todo)."""
        try:
            # Get all TODO goals - they are already available by definition
            goals = await self.uow.goals().get_user_goals(
                user_id=self.user_id,
                status=GoalStatus.TODO.value,
            )

            available_goals = []
            for goal in goals:
                available_goals.append({
                    "goal_id": str(goal.id),
                    "title": goal.title,
                    "description": goal.description,
                    "priority": goal.priority,
                    "category": goal.category,
                    "deadline": goal.deadline.isoformat() if goal.deadline else None,
                    "difficulty_level": goal.difficulty_level,
                    "estimated_duration_days": goal.estimated_duration_days,
                    "motivation": goal.motivation,
                    "success_criteria": goal.success_criteria,
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


    async def update_goal_title(
        self,
        goal_id: str,
        title: str,
    ) -> Dict[str, Any]:
        """Update goal title."""
        try:
            goal = await self.uow.goals().update_goal_title(UUID(goal_id), title)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_title = goal.title
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal title for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "title": goal_title,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal title to '{goal_title}'",
            }

        except Exception as e:
            logger.error(f"Failed to update goal title: {e}")
            return {"error": f"Failed to update goal title: {str(e)}"}

    async def update_goal_description(
        self,
        goal_id: str,
        description: str | None,
    ) -> Dict[str, Any]:
        """Update goal description."""
        try:
            goal = await self.uow.goals().update_goal_description(UUID(goal_id), description)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_description = goal.description
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal description for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "description": goal_description,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal description",
            }

        except Exception as e:
            logger.error(f"Failed to update goal description: {e}")
            return {"error": f"Failed to update goal description: {str(e)}"}

    async def update_goal_priority(
        self,
        goal_id: str,
        priority: int,
    ) -> Dict[str, Any]:
        """Update goal priority."""
        try:
            goal = await self.uow.goals().update_goal_priority(UUID(goal_id), priority)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_priority = goal.priority
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal priority for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "priority": goal_priority,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal priority to {goal_priority}/5",
            }

        except Exception as e:
            logger.error(f"Failed to update goal priority: {e}")
            return {"error": f"Failed to update goal priority: {str(e)}"}

    async def update_goal_deadline(
        self,
        goal_id: str,
        deadline: str | None,
    ) -> Dict[str, Any]:
        """Update goal deadline."""
        try:
            goal = await self.uow.goals().update_goal_deadline(UUID(goal_id), deadline)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_deadline = goal.deadline.isoformat() if goal.deadline else None
            goal_updated_at = goal.updated_at.isoformat()
            deadline_text = goal.deadline.strftime('%B %d, %Y') if goal.deadline else "removed"

            logger.info(f"Updated goal deadline for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "deadline": goal_deadline,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal deadline to {deadline_text}",
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to update goal deadline: {e}")
            return {"error": f"Failed to update goal deadline: {str(e)}"}

    async def update_goal_category(
        self,
        goal_id: str,
        category: str | None,
    ) -> Dict[str, Any]:
        """Update goal category."""
        try:
            # Validate and convert category
            goal_category = None
            if category:
                try:
                    goal_category = GoalCategory(category)
                except ValueError:
                    valid_categories = [e.value for e in GoalCategory]
                    return {"error": f"Invalid category: {category}. Must be one of {valid_categories}"}

            goal = await self.uow.goals().update_goal_category(UUID(goal_id), goal_category)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_category_value = goal.category.value if goal.category else None
            goal_updated_at = goal.updated_at.isoformat()
            category_text = goal.category.value if goal.category else "none"

            logger.info(f"Updated goal category for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "category": goal_category_value,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal category to {category_text}",
            }

        except Exception as e:
            logger.error(f"Failed to update goal category: {e}")
            return {"error": f"Failed to update goal category: {str(e)}"}

    async def update_goal_motivation(
        self,
        goal_id: str,
        motivation: str | None,
    ) -> Dict[str, Any]:
        """Update goal motivation."""
        try:
            goal = await self.uow.goals().update_goal_motivation(UUID(goal_id), motivation)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_motivation = goal.motivation
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal motivation for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "motivation": goal_motivation,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal motivation",
            }

        except Exception as e:
            logger.error(f"Failed to update goal motivation: {e}")
            return {"error": f"Failed to update goal motivation: {str(e)}"}

    async def update_goal_success_criteria(
        self,
        goal_id: str,
        success_criteria: str | None,
    ) -> Dict[str, Any]:
        """Update goal success criteria."""
        try:
            goal = await self.uow.goals().update_goal_success_criteria(UUID(goal_id), success_criteria)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_success_criteria = goal.success_criteria
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal success criteria for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "success_criteria": goal_success_criteria,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal success criteria",
            }

        except Exception as e:
            logger.error(f"Failed to update goal success criteria: {e}")
            return {"error": f"Failed to update goal success criteria: {str(e)}"}

    async def update_goal_difficulty(
        self,
        goal_id: str,
        difficulty_level: int,
    ) -> Dict[str, Any]:
        """Update goal difficulty level."""
        try:
            goal = await self.uow.goals().update_goal_difficulty(UUID(goal_id), difficulty_level)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_difficulty_level = goal.difficulty_level
            goal_updated_at = goal.updated_at.isoformat()

            logger.info(f"Updated goal difficulty for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "difficulty_level": goal_difficulty_level,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal difficulty to {goal_difficulty_level}/10",
            }

        except Exception as e:
            logger.error(f"Failed to update goal difficulty: {e}")
            return {"error": f"Failed to update goal difficulty: {str(e)}"}

    async def update_goal_duration(
        self,
        goal_id: str,
        estimated_duration_days: int | None,
    ) -> Dict[str, Any]:
        """Update goal estimated duration."""
        try:
            goal = await self.uow.goals().update_goal_duration(UUID(goal_id), estimated_duration_days)
            if not goal or goal.user_id != self.user_id:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Access attributes immediately after DB operation to avoid lazy loading issues
            goal_id_str = str(goal.id)
            goal_estimated_duration_days = goal.estimated_duration_days
            goal_updated_at = goal.updated_at.isoformat()
            duration_text = f"{goal.estimated_duration_days} days" if goal.estimated_duration_days else "not set"

            logger.info(f"Updated goal duration for user {self.user_id}")

            return {
                "goal_id": goal_id_str,
                "estimated_duration_days": goal_estimated_duration_days,
                "updated_at": goal_updated_at,
                "success_message": f"Updated goal duration to {duration_text}",
            }

        except Exception as e:
            logger.error(f"Failed to update goal duration: {e}")
            return {"error": f"Failed to update goal duration: {str(e)}"}

__all__ = ["GoalTools"]