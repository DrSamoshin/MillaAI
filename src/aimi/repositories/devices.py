"""Repository for device persistence operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.device import Device

import logging

logger = logging.getLogger(__name__)


class DeviceRepository:
    """Data access layer for Device model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_devices(self, user_id: uuid.UUID) -> list[Device]:
        """Get all devices for user."""
        result = await self._session.execute(
            select(Device)
            .where(Device.user_id == user_id)
            .order_by(Device.last_seen.desc())
        )
        return list(result.scalars().all())


__all__ = ["DeviceRepository"]