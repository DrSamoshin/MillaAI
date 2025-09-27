"""Repository for notification persistence operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.notification import Notification
from aimi.db.models.enums import NotificationStatus, NotificationType

import logging

logger = logging.getLogger(__name__)


class NotificationRepository:
    """Data access layer for Notification model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(
        self,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        message: str,
        notification_type: NotificationType,
        scheduled_for: datetime,
        goal_id: uuid.UUID | None = None,
        context: dict | None = None,
    ) -> Notification:
        """Create new notification."""
        notification = Notification(
            user_id=user_id,
            chat_id=chat_id,
            message=message,
            notification_type=notification_type,
            scheduled_for=scheduled_for,
            goal_id=goal_id,
            context=context,
            status=NotificationStatus.PENDING.value,
        )

        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        """Get notification by ID."""
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        status: NotificationStatus | None = None,
        limit: int | None = None,
    ) -> list[Notification]:
        """Get notifications for user, optionally filtered by status."""
        query = select(Notification).where(Notification.user_id == user_id)

        if status:
            query = query.where(Notification.status == status)

        query = query.order_by(Notification.scheduled_for.desc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_pending_notifications(
        self,
        user_id: uuid.UUID | None = None,
        limit: int | None = None,
    ) -> list[Notification]:
        """Get pending notifications, optionally for specific user."""
        now = datetime.utcnow()
        query = select(Notification).where(
            Notification.status == NotificationStatus.PENDING,
            Notification.scheduled_for <= now
        )

        if user_id:
            query = query.where(Notification.user_id == user_id)

        query = query.order_by(Notification.scheduled_for.asc())

        if limit:
            query = query.limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update_notification(
        self,
        notification: Notification,
        status: NotificationStatus | None = None,
        sent_at: datetime | None = None,
    ) -> Notification:
        """Update notification fields."""
        if status is not None:
            notification.status = status

        if sent_at is not None:
            notification.sent_at = sent_at

        await self._session.flush()
        await self._session.refresh(notification)
        return notification




__all__ = ["NotificationRepository"]