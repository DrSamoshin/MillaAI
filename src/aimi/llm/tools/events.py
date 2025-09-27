"""Event management tools for LLM."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from aimi.db.models.enums import EventStatus
from aimi.db.models.event import Event
from aimi.db.models.goal import Goal

logger = logging.getLogger(__name__)


class EventTools:
    """Tools for LLM to manage user events."""

    def __init__(self, db_session: AsyncSession, user_id: UUID, chat_id: UUID):
        self.db = db_session
        self.user_id = user_id
        self.chat_id = chat_id

    async def create_event(
        self,
        title: str,
        start_time: str,
        description: str | None = None,
        end_time: str | None = None,
        location: str | None = None,
        event_type: str = "personal",
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        try:
            # Parse start time
            try:
                start_time_dt = datetime.fromisoformat(start_time)
            except ValueError:
                return {"error": f"Invalid start_time format: {start_time}. Use ISO format"}

            # Parse end time if provided
            end_time_dt = None
            if end_time:
                try:
                    end_time_dt = datetime.fromisoformat(end_time)
                except ValueError:
                    return {"error": f"Invalid end_time format: {end_time}. Use ISO format"}

                # Validate that end time is after start time
                if end_time_dt <= start_time_dt:
                    return {"error": "End time must be after start time"}

            # Validate event type
            valid_types = {"work", "meeting", "break", "focus_time", "deadline", "personal"}
            if event_type not in valid_types:
                return {"error": f"Invalid event_type: {event_type}. Must be one of {valid_types}"}

            # Create event
            event = Event(
                user_id=self.user_id,
                title=title,
                description=description,
                location=location,
                event_type=event_type,
                status=EventStatus.SCHEDULED.value,
                start_time=start_time_dt,
                end_time=end_time_dt,
            )

            self.db.add(event)
            await self.db.flush()
            await self.db.refresh(event)
            await self.db.commit()

            logger.info(f"Created event '{title}' for user {self.user_id}")

            return {
                "event_id": str(event.id),
                "title": event.title,
                "description": event.description,
                "location": event.location,
                "event_type": event.event_type,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "status": event.status,
                "created_at": event.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return {"error": f"Failed to create event: {str(e)}"}

    async def link_event_to_goal(self, event_id: str, goal_id: str) -> Dict[str, Any]:
        """Connect an event to a goal."""
        try:
            # Verify event exists and belongs to user
            event_result = await self.db.execute(
                select(Event).where(
                    Event.id == UUID(event_id),
                    Event.user_id == self.user_id
                )
            )
            event = event_result.scalar_one_or_none()

            if not event:
                return {"error": f"Event {event_id} not found or not owned by user"}

            # Verify goal exists and belongs to user
            goal_result = await self.db.execute(
                select(Goal).where(
                    Goal.id == UUID(goal_id),
                    Goal.user_id == self.user_id
                )
            )
            goal = goal_result.scalar_one_or_none()

            if not goal:
                return {"error": f"Goal {goal_id} not found or not owned by user"}

            # Link event to goal
            event.goal_id = UUID(goal_id)
            await self.db.commit()

            logger.info(f"Linked event '{event.title}' to goal '{goal.title}'")

            return {
                "event_id": str(event.id),
                "goal_id": str(goal.id),
                "event_title": event.title,
                "goal_title": goal.title,
            }

        except Exception as e:
            logger.error(f"Failed to link event to goal: {e}")
            return {"error": f"Failed to link event to goal: {str(e)}"}

    async def link_event_to_task(self, event_id: str, task_id: str) -> Dict[str, Any]:
        """Connect an event to a task."""
        try:
            # Verify event exists and belongs to user
            event_result = await self.db.execute(
                select(Event).where(
                    Event.id == UUID(event_id),
                    Event.user_id == self.user_id
                )
            )
            event = event_result.scalar_one_or_none()

            if not event:
                return {"error": f"Event {event_id} not found or not owned by user"}

            # Verify task exists and belongs to user (through goal)
            task_result = await self.db.execute(
                select(Task, Goal.title.label("goal_title"))
                .join(Goal)
                .where(
                    Task.id == UUID(task_id),
                    Goal.user_id == self.user_id
                )
            )
            task_data = task_result.first()

            if not task_data:
                return {"error": f"Task {task_id} not found or not owned by user"}

            task, goal_title = task_data

            # Link event to task
            event.task_id = UUID(task_id)
            await self.db.commit()

            logger.info(f"Linked event '{event.title}' to task '{task.title}'")

            return {
                "event_id": str(event.id),
                "task_id": str(task.id),
                "event_title": event.title,
                "task_title": task.title,
                "goal_title": goal_title,
            }

        except Exception as e:
            logger.error(f"Failed to link event to task: {e}")
            return {"error": f"Failed to link event to task: {str(e)}"}

    async def update_event_status(self, event_id: str, status: str) -> Dict[str, Any]:
        """Update event status."""
        try:
            # Validate status
            valid_statuses = {e.value for e in EventStatus}
            if status not in valid_statuses:
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Find event
            result = await self.db.execute(
                select(Event).where(
                    Event.id == UUID(event_id),
                    Event.user_id == self.user_id
                )
            )
            event = result.scalar_one_or_none()

            if not event:
                return {"error": f"Event {event_id} not found or not owned by user"}

            event.status = EventStatus(status)
            await self.db.commit()

            logger.info(f"Updated event '{event.title}' status to '{status}'")

            return {
                "event_id": str(event.id),
                "title": event.title,
                "status": event.status,
            }

        except Exception as e:
            logger.error(f"Failed to update event status: {e}")
            return {"error": f"Failed to update event status: {str(e)}"}

    async def get_upcoming_events(self, limit: int = 10) -> Dict[str, Any]:
        """Get upcoming events for the user."""
        try:
            now = datetime.utcnow()

            result = await self.db.execute(
                select(Event, Goal.title.label("goal_title"), Task.title.label("task_title"))
                .outerjoin(Goal, Event.goal_id == Goal.id)
                .outerjoin(Task, Event.task_id == Task.id)
                .where(
                    Event.user_id == self.user_id,
                    Event.start_time >= now,
                    Event.status == EventStatus.SCHEDULED
                )
                .order_by(Event.start_time.asc())
                .limit(limit)
            )

            events_data = []
            for event, goal_title, task_title in result.all():
                events_data.append({
                    "event_id": str(event.id),
                    "title": event.title,
                    "description": event.description,
                    "location": event.location,
                    "event_type": event.event_type,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat() if event.end_time else None,
                    "status": event.status,
                    "goal_id": str(event.goal_id) if event.goal_id else None,
                    "goal_title": goal_title,
                    "task_id": str(event.task_id) if event.task_id else None,
                    "task_title": task_title,
                })

            return {
                "events": events_data,
                "total": len(events_data)
            }

        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return {"error": f"Failed to get upcoming events: {str(e)}"}

    async def get_user_events(
        self,
        status: str | None = None,
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """Get events for the user, optionally filtered by status."""
        try:
            # Parse status filter
            status_enum = None
            if status:
                try:
                    status_enum = EventStatus(status)
                except ValueError:
                    valid_statuses = [e.value for e in EventStatus]
                    return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Get events using repository
            events = await self.repo.get_user_events(
                user_id=self.user_id,
                status=status_enum,
                limit=limit
            )

            events_data = []
            for event in events:
                # Get goal title if linked
                goal_title = None
                if event.goal_id:
                    goal = await self.goal_repo.get_by_id(event.goal_id)
                    if goal:
                        goal_title = goal.title

                events_data.append({
                    "event_id": str(event.id),
                    "title": event.title,
                    "description": event.description,
                    "location": event.location,
                    "event_type": event.event_type,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "status": event.status,
                    "goal_id": str(event.goal_id) if event.goal_id else None,
                    "goal_title": goal_title,
                    "created_at": event.created_at.isoformat(),
                })

            return {
                "events": events_data,
                "total": len(events_data),
                "filter_status": status,
            }

        except Exception as e:
            logger.error(f"Failed to get user events: {e}")
            return {"error": f"Failed to get user events: {str(e)}"}


__all__ = ["EventTools"]