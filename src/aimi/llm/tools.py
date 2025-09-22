"""LLM tools for goal and task management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.goals import Goal, Task, MentalState

logger = logging.getLogger(__name__)


class GoalManagementTools:
    """Tools for LLM to manage user goals and tasks."""

    def __init__(self, db_session: AsyncSession, user_id: UUID, chat_id: UUID):
        self.db = db_session
        self.user_id = user_id
        self.chat_id = chat_id

    async def create_goal(
        self,
        title: str,
        description: str | None = None,
        priority: int = 1,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        """Create a new goal for the user.

        Args:
            title: Goal title
            description: Detailed description of the goal
            priority: Priority level (1-5, where 5 is highest)
            deadline: Deadline in YYYY-MM-DD format

        Returns:
            Created goal information
        """
        try:
            # Parse deadline if provided
            deadline_date = None
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline).date()
                except ValueError:
                    return {"error": f"Invalid deadline format: {deadline}. Use YYYY-MM-DD"}

            # Create goal
            goal = Goal(
                user_id=self.user_id,
                chat_id=self.chat_id,
                title=title,
                description=description,
                priority=max(1, min(5, priority)),  # Clamp between 1-5
                deadline=deadline_date,
            )

            self.db.add(goal)
            await self.db.flush()
            await self.db.refresh(goal)
            await self.db.commit()

            logger.info(f"Created goal '{title}' for user {self.user_id}")

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "description": goal.description,
                "priority": goal.priority,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "status": goal.status,
                "created_at": goal.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            return {"error": f"Failed to create goal: {str(e)}"}

    async def create_task(
        self,
        goal_id: str,
        title: str,
        description: str | None = None,
        due_date: str | None = None,
        reminder_at: str | None = None,
    ) -> dict[str, Any]:
        """Create a task for a specific goal.

        Args:
            goal_id: ID of the goal this task belongs to
            title: Task title
            description: Task description
            due_date: Due date in ISO format
            reminder_at: Reminder time in ISO format

        Returns:
            Created task information
        """
        try:
            # Verify goal exists and belongs to user
            result = await self.db.execute(
                select(Goal).where(
                    Goal.id == UUID(goal_id),
                    Goal.user_id == self.user_id
                )
            )
            goal = result.scalar_one_or_none()

            if not goal:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Parse dates if provided
            due_date_dt = None
            reminder_at_dt = None

            if due_date:
                try:
                    due_date_dt = datetime.fromisoformat(due_date)
                except ValueError:
                    return {"error": f"Invalid due_date format: {due_date}"}

            if reminder_at:
                try:
                    reminder_at_dt = datetime.fromisoformat(reminder_at)
                except ValueError:
                    return {"error": f"Invalid reminder_at format: {reminder_at}"}

            # Create task
            task = Task(
                goal_id=UUID(goal_id),
                title=title,
                description=description,
                due_date=due_date_dt,
                reminder_at=reminder_at_dt,
            )

            self.db.add(task)
            await self.db.flush()
            await self.db.refresh(task)
            await self.db.commit()

            logger.info(f"Created task '{title}' for goal '{goal.title}'")

            return {
                "task_id": str(task.id),
                "goal_id": goal_id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "reminder_at": task.reminder_at.isoformat() if task.reminder_at else None,
                "created_at": task.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return {"error": f"Failed to create task: {str(e)}"}

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update goal status.

        Args:
            goal_id: Goal ID
            status: New status (active, completed, paused, cancelled)

        Returns:
            Updated goal information
        """
        try:
            valid_statuses = {"active", "completed", "paused", "cancelled"}
            if status not in valid_statuses:
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Find and update goal
            result = await self.db.execute(
                select(Goal).where(
                    Goal.id == UUID(goal_id),
                    Goal.user_id == self.user_id
                )
            )
            goal = result.scalar_one_or_none()

            if not goal:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            goal.status = status
            goal.updated_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Updated goal '{goal.title}' status to '{status}'")

            return {
                "goal_id": str(goal.id),
                "title": goal.title,
                "status": goal.status,
                "updated_at": goal.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to update goal status: {e}")
            return {"error": f"Failed to update goal status: {str(e)}"}

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status (pending, in_progress, completed, cancelled)

        Returns:
            Updated task information
        """
        try:
            valid_statuses = {"pending", "in_progress", "completed", "cancelled"}
            if status not in valid_statuses:
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Find and update task
            result = await self.db.execute(
                select(Task)
                .join(Goal)
                .where(
                    Task.id == UUID(task_id),
                    Goal.user_id == self.user_id
                )
            )
            task = result.scalar_one_or_none()

            if not task:
                return {"error": f"Task {task_id} not found or not owned by user"}

            task.status = status
            if status == "completed":
                task.completed_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Updated task '{task.title}' status to '{status}'")

            return {
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return {"error": f"Failed to update task status: {str(e)}"}

    async def get_active_goals(self) -> dict[str, Any]:
        """Get all active goals for the user.

        Returns:
            List of active goals with their tasks
        """
        try:
            result = await self.db.execute(
                select(Goal)
                .where(
                    Goal.user_id == self.user_id,
                    Goal.status == "active"
                )
                .order_by(Goal.priority.desc(), Goal.created_at.desc())
            )
            goals = result.scalars().all()

            goals_data = []
            for goal in goals:
                # Get tasks for this goal
                tasks_result = await self.db.execute(
                    select(Task)
                    .where(Task.goal_id == goal.id)
                    .order_by(Task.created_at.asc())
                )
                tasks = tasks_result.scalars().all()

                goals_data.append({
                    "goal_id": str(goal.id),
                    "title": goal.title,
                    "description": goal.description,
                    "priority": goal.priority,
                    "deadline": goal.deadline.isoformat() if goal.deadline else None,
                    "status": goal.status,
                    "created_at": goal.created_at.isoformat(),
                    "tasks": [
                        {
                            "task_id": str(task.id),
                            "title": task.title,
                            "description": task.description,
                            "status": task.status,
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "reminder_at": task.reminder_at.isoformat() if task.reminder_at else None,
                        }
                        for task in tasks
                    ]
                })

            return {
                "goals": goals_data,
                "total": len(goals_data)
            }

        except Exception as e:
            logger.error(f"Failed to get active goals: {e}")
            return {"error": f"Failed to get active goals: {str(e)}"}

    async def record_mental_state(
        self,
        mood: str | None = None,
        energy_level: int | None = None,
        confidence_level: int | None = None,
        detected_emotions: list[str] | None = None,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Record user's mental state analysis.

        Args:
            mood: Current mood (happy, sad, stressed, motivated, etc.)
            energy_level: Energy level 1-10
            confidence_level: Confidence level 1-10
            detected_emotions: List of detected emotions
            context: Context that led to this state

        Returns:
            Recorded mental state information
        """
        try:
            # Validate levels
            if energy_level is not None and not (1 <= energy_level <= 10):
                return {"error": "Energy level must be between 1-10"}

            if confidence_level is not None and not (1 <= confidence_level <= 10):
                return {"error": "Confidence level must be between 1-10"}

            mental_state = MentalState(
                user_id=self.user_id,
                chat_id=self.chat_id,
                mood=mood,
                energy_level=energy_level,
                confidence_level=confidence_level,
                detected_emotions=detected_emotions,
                context=context,
                analysis_source="realtime",  # Since this is called during chat
            )

            self.db.add(mental_state)
            await self.db.flush()
            await self.db.refresh(mental_state)
            await self.db.commit()

            logger.info(f"Recorded mental state for user {self.user_id}: {mood}")

            return {
                "mental_state_id": str(mental_state.id),
                "mood": mental_state.mood,
                "energy_level": mental_state.energy_level,
                "confidence_level": mental_state.confidence_level,
                "detected_emotions": mental_state.detected_emotions,
                "context": mental_state.context,
                "created_at": mental_state.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to record mental state: {e}")
            return {"error": f"Failed to record mental state: {str(e)}"}


__all__ = ["GoalManagementTools"]