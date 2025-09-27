"""Repository for mental state persistence operations."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.mental_state import MentalState

import logging

logger = logging.getLogger(__name__)


class MentalStateRepository:
    """Data access layer for MentalState model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_mental_states(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MentalState], int]:
        """Get mental state history for user with pagination."""
        # Get total count
        count_stmt = select(func.count(MentalState.id)).where(MentalState.user_id == user_id)
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get records
        query = select(MentalState).where(MentalState.user_id == user_id).order_by(
            MentalState.question_asked_at.desc()
        ).offset(offset).limit(limit)

        result = await self._session.execute(query)
        mental_states = list(result.scalars().all())

        return mental_states, total


__all__ = ["MentalStateRepository"]