"""Notification management tools for LLM."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.repositories.notifications import NotificationRepository
from aimi.repositories.goals import GoalRepository
from aimi.db.models.enums import NotificationStatus, NotificationType

logger = logging.getLogger(__name__)


class NotificationTools:
    """Tools for LLM to manage user notifications."""

    def __init__(self, db_session: AsyncSession, user_id: UUID, chat_id: UUID):
        self.db = db_session
        self.user_id = user_id
        self.chat_id = chat_id
        self.repo = NotificationRepository(db_session)
        self.goal_repo = GoalRepository(db_session)

    async def create_notification(
        self,
        message: str,
        scheduled_for: str,
        notification_type: str = "reminder",
        goal_id: str | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Create a scheduled notification."""
        try:
            # Parse scheduled time
            try:
                scheduled_dt = datetime.fromisoformat(scheduled_for)
            except ValueError:
                return {"error": f"Invalid scheduled_for format: {scheduled_for}. Use ISO format"}

            # Validate notification type
            try:
                notification_type_enum = NotificationType(notification_type)
            except ValueError:
                valid_types = [e.value for e in NotificationType]
                return {"error": f"Invalid notification_type: {notification_type}. Must be one of {valid_types}"}

            # Validate goal if provided
            goal_uuid = None
            if goal_id:
                goal = await self.goal_repo.get_by_id(UUID(goal_id))
                if not goal or goal.user_id != self.user_id:
                    return {"error": f"Goal {goal_id} not found or not owned by user"}
                goal_uuid = UUID(goal_id)

            # Create notification using repository
            notification = await self.repo.create_notification(
                user_id=self.user_id,
                chat_id=self.chat_id,
                message=message,
                notification_type=notification_type_enum,
                scheduled_for=scheduled_dt,
                goal_id=goal_uuid,
                context=context,
            )

            await self.db.commit()

            logger.info(f"Created notification for user {self.user_id} scheduled for {scheduled_for}")

            return {
                "notification_id": str(notification.id),
                "message": notification.message,
                "notification_type": notification.notification_type,
                "scheduled_for": notification.scheduled_for.isoformat(),
                "status": notification.status,
                "goal_id": str(notification.goal_id) if notification.goal_id else None,
                "context": notification.context,
                "created_at": notification.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            await self.db.rollback()
            return {"error": f"Failed to create notification: {str(e)}"}

    async def update_notification_status(
        self,
        notification_id: str,
        status: str,
    ) -> Dict[str, Any]:
        """Update notification status."""
        try:
            # Validate status
            try:
                status_enum = NotificationStatus(status)
            except ValueError:
                valid_statuses = [e.value for e in NotificationStatus]
                return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Get notification
            notification = await self.repo.get_by_id(UUID(notification_id))
            if not notification or notification.user_id != self.user_id:
                return {"error": f"Notification {notification_id} not found or not owned by user"}

            # Update status
            sent_at = datetime.utcnow() if status_enum == NotificationStatus.SENT else None
            await self.repo.update_notification(
                notification,
                status=status_enum,
                sent_at=sent_at
            )
            await self.db.commit()

            logger.info(f"Updated notification {notification_id} status to {status}")

            return {
                "notification_id": str(notification.id),
                "message": notification.message,
                "status": status,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
            await self.db.rollback()
            return {"error": f"Failed to update notification status: {str(e)}"}

    async def get_user_notifications(
        self,
        status: str | None = None,
        limit: int | None = 50,
    ) -> Dict[str, Any]:
        """Get notifications for the user, optionally filtered by status."""
        try:
            # Parse status filter
            status_enum = None
            if status:
                try:
                    status_enum = NotificationStatus(status)
                except ValueError:
                    valid_statuses = [e.value for e in NotificationStatus]
                    return {"error": f"Invalid status: {status}. Must be one of {valid_statuses}"}

            # Get notifications using repository
            notifications = await self.repo.get_user_notifications(
                user_id=self.user_id,
                status=status_enum,
                limit=limit
            )

            notifications_data = []
            for notification in notifications:
                # Get goal title if linked
                goal_title = None
                if notification.goal_id:
                    goal = await self.goal_repo.get_by_id(notification.goal_id)
                    if goal:
                        goal_title = goal.title

                notifications_data.append({
                    "notification_id": str(notification.id),
                    "message": notification.message,
                    "notification_type": notification.notification_type,
                    "status": notification.status,
                    "scheduled_for": notification.scheduled_for.isoformat(),
                    "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                    "goal_id": str(notification.goal_id) if notification.goal_id else None,
                    "goal_title": goal_title,
                    "context": notification.context,
                    "created_at": notification.created_at.isoformat(),
                })

            return {
                "notifications": notifications_data,
                "total": len(notifications_data),
                "filter_status": status,
            }

        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return {"error": f"Failed to get user notifications: {str(e)}"}

    async def get_pending_notifications(
        self,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get pending notifications that are ready to be sent."""
        try:
            # Get pending notifications using repository
            notifications = await self.repo.get_pending_notifications(
                user_id=self.user_id,
                limit=limit
            )

            notifications_data = []
            for notification in notifications:
                # Get goal title if linked
                goal_title = None
                if notification.goal_id:
                    goal = await self.goal_repo.get_by_id(notification.goal_id)
                    if goal:
                        goal_title = goal.title

                notifications_data.append({
                    "notification_id": str(notification.id),
                    "message": notification.message,
                    "notification_type": notification.notification_type,
                    "scheduled_for": notification.scheduled_for.isoformat(),
                    "goal_id": str(notification.goal_id) if notification.goal_id else None,
                    "goal_title": goal_title,
                    "context": notification.context,
                })

            return {
                "pending_notifications": notifications_data,
                "total": len(notifications_data),
            }

        except Exception as e:
            logger.error(f"Failed to get pending notifications: {e}")
            return {"error": f"Failed to get pending notifications: {str(e)}"}


__all__ = ["NotificationTools"]