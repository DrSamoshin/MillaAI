"""Repository for mental state persistence operations."""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.mental_state import MentalState
from aimi.db.models.enums import MentalStateMood

import logging

logger = logging.getLogger(__name__)


class MentalStateRepository:
    """Data access layer for MentalState model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_mental_state(
        self,
        user_id: uuid.UUID,
        date: datetime,
        mood: MentalStateMood | None = None,
        readiness_level: int | None = None,
        notes: str | None = None,
        responded_at: datetime | None = None,
    ) -> MentalState:
        """Create new mental state entry."""
        mental_state = MentalState(
            user_id=user_id,
            date=date,
            mood=mood,
            readiness_level=readiness_level,
            notes=notes,
            responded_at=responded_at,
        )

        self._session.add(mental_state)
        await self._session.flush()
        await self._session.refresh(mental_state)
        return mental_state

    async def get_by_id(self, mental_state_id: uuid.UUID) -> MentalState | None:
        """Get mental state by ID."""
        result = await self._session.execute(
            select(MentalState).where(MentalState.id == mental_state_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_date(
        self,
        user_id: uuid.UUID,
        target_date: date
    ) -> MentalState | None:
        """Get mental state for user on specific date."""
        # Convert date to datetime range for the day
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())

        result = await self._session.execute(
            select(MentalState).where(
                and_(
                    MentalState.user_id == user_id,
                    MentalState.date >= start_of_day,
                    MentalState.date <= end_of_day
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_mental_states(
        self,
        user_id: uuid.UUID,
        limit: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[MentalState]:
        """Get mental states for user with optional date filtering."""
        query = select(MentalState).where(MentalState.user_id == user_id)

        if start_date:
            query = query.where(MentalState.date >= start_date)
        if end_date:
            query = query.where(MentalState.date <= end_date)

        query = query.order_by(MentalState.date.desc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_unanswered_polls(
        self,
        user_id: uuid.UUID | None = None,
        limit: int | None = None,
    ) -> list[MentalState]:
        """Get mental state entries that haven't been responded to yet."""
        query = select(MentalState).where(MentalState.responded_at.is_(None))

        if user_id:
            query = query.where(MentalState.user_id == user_id)

        query = query.order_by(MentalState.question_asked_at.asc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update_mental_state(
        self,
        mental_state: MentalState,
        mood: MentalStateMood | None = None,
        readiness_level: int | None = None,
        notes: str | None = None,
        responded_at: datetime | None = None,
    ) -> MentalState:
        """Update mental state fields."""
        if mood is not None:
            mental_state.mood = mood

        if readiness_level is not None:
            mental_state.readiness_level = readiness_level

        if notes is not None:
            mental_state.notes = notes

        if responded_at is not None:
            mental_state.responded_at = responded_at

        await self._session.flush()
        await self._session.refresh(mental_state)
        return mental_state


__all__ = ["MentalStateRepository"]