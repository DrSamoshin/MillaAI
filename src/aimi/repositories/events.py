"""Repository for event persistence operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.event import Event
from aimi.db.models.enums import EventStatus, EventType

import logging

logger = logging.getLogger(__name__)


class EventRepository:
    """Data access layer for Event model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(
        self,
        user_id: uuid.UUID,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str | None = None,
        location: str | None = None,
        event_type: str = EventType.PERSONAL.value,
        goal_id: uuid.UUID | None = None,
    ) -> Event:
        """Create new event."""
        event = Event(
            user_id=user_id,
            title=title,
            description=description,
            location=location,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            goal_id=goal_id,
        )

        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        """Get event by ID."""
        result = await self._session.execute(
            select(Event).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_user_events(
        self,
        user_id: uuid.UUID,
        status: EventStatus | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Get events for user, optionally filtered by status."""
        query = select(Event).where(Event.user_id == user_id)

        if status:
            query = query.where(Event.status == status)

        query = query.order_by(Event.start_time.asc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_events(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Event]:
        """Get upcoming scheduled events for user."""
        now = datetime.utcnow()

        result = await self._session.execute(
            select(Event)
            .where(
                Event.user_id == user_id,
                Event.start_time >= now,
                Event.status == EventStatus.SCHEDULED.value
            )
            .order_by(Event.start_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_event(
        self,
        event: Event,
        status: EventStatus | None = None,
        goal_id: uuid.UUID | None = None,
    ) -> Event:
        """Update event fields."""
        if status is not None:
            event.status = status

        if goal_id is not None:
            event.goal_id = goal_id

        await self._session.flush()
        await self._session.refresh(event)
        return event


__all__ = ["EventRepository"]