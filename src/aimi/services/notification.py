"""Notification service for push notifications and message delivery.

IMPORTANT: Do not use emojis in notifications or any user-facing content.
Keep all messages clean and professional without emoji characters.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from aimi.db.session import UnitOfWork
from aimi.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling push notifications and message delivery.

    Handles delivery of messages when users are not actively connected
    to WebSocket and manages push notification sending.
    """

    def __init__(self):
        pass

    async def send_push_notification(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        content: str,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send push notification for message delivery."""
        try:
            # Get chat info for notification context
            chat = await uow.chats().get_by_id(chat_id)

            if not chat:
                logger.error(f"Chat {chat_id} not found for push notification")
                return {"error": "Chat not found", "status": "failed"}

            # Truncate content for notification preview
            preview = content[:100] + "..." if len(content) > 100 else content

            # Check if chat has active WebSocket connection
            is_active = connection_manager.is_active(chat_id)

            if is_active:
                logger.info(f"Chat {chat_id} is active, no push notification needed")
                return {"status": "delivered_via_websocket"}

            # Log push notification (TODO: implement actual push service)
            logger.info(
                f"PUSH NOTIFICATION: Chat '{chat.title or 'Untitled'}' - {preview} (user_id: {chat.user_id})"
            )

            # TODO: Implement actual push notification service integration
            # await push_service.send_notification(
            #     user_id=chat.user_id,
            #     title=f"New message in '{chat.title or 'Chat'}'",
            #     body=preview,
            #     data={
            #         "chat_id": str(chat_id),
            #         "type": "chat_message"
            #     }
            # )

            return {
                "status": "push_sent",
                "chat_id": str(chat_id),
                "user_id": str(chat.user_id),
                "preview": preview,
                "sent_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send push notification for chat {chat_id}: {e}", exc_info=True)
            return {"error": f"Failed to send push notification: {str(e)}", "status": "failed"}

    async def notify_user_message(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        message_content: str,
        notification_type: str = "chat_message",
    ) -> dict[str, Any]:
        """Notify user about a new message with appropriate delivery method."""
        try:
            # Check if user is actively connected
            is_active = connection_manager.is_active(chat_id)

            if is_active:
                # User is active, message will be delivered via WebSocket
                logger.info(f"User active for chat {chat_id}, message delivered via WebSocket")
                return {"status": "delivered_via_websocket", "chat_id": str(chat_id)}
            else:
                # User is not active, send push notification
                result = await self.send_push_notification(uow, chat_id, message_content)
                return result

        except Exception as e:
            logger.error(f"Failed to notify user for chat {chat_id}: {e}", exc_info=True)
            return {"error": f"Failed to notify user: {str(e)}", "status": "failed"}

    async def send_scheduled_notification(
        self,
        uow: UnitOfWork,
        notification_id: UUID,
    ) -> dict[str, Any]:
        """Send a scheduled notification (for background workers)."""
        try:
            # Get notification details
            notification = await uow.notifications().get_by_id(notification_id)

            if not notification:
                logger.error(f"Notification {notification_id} not found")
                return {"error": "Notification not found", "status": "failed"}

            # Get user's active chat or create system chat
            # TODO: Implement logic to find or create appropriate chat for notifications

            # For now, log the scheduled notification
            logger.info(
                f"SCHEDULED NOTIFICATION: {notification.notification_type.value} - "
                f"{notification.message} (user_id: {notification.user_id})"
            )

            # Update notification status to sent
            await uow.notifications().update_notification(
                notification,
                status="sent",
                sent_at=datetime.utcnow()
            )
            await uow.commit()

            return {
                "status": "sent",
                "notification_id": str(notification_id),
                "user_id": str(notification.user_id),
                "sent_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to send scheduled notification {notification_id}: {e}", exc_info=True)
            await uow.rollback()
            return {"error": f"Failed to send scheduled notification: {str(e)}", "status": "failed"}


__all__ = ["NotificationService"]