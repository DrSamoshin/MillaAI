"""WebSocket connection manager for chat activity tracking."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for chat activity tracking."""

    def __init__(self):
        # Store active WebSocket connections by chat_id
        self.active_connections: dict[UUID, WebSocket] = {}

    async def connect(self, chat_id: UUID, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for a chat."""
        self.active_connections[chat_id] = websocket
        logger.info(f"Chat {chat_id} connected. Active chats: {len(self.active_connections)}")

    async def disconnect(self, chat_id: UUID) -> None:
        """Unregister WebSocket connection for a chat."""
        if chat_id in self.active_connections:
            del self.active_connections[chat_id]
            logger.info(f"Chat {chat_id} disconnected. Active chats: {len(self.active_connections)}")

    def is_active(self, chat_id: UUID) -> bool:
        """Check if chat has an active WebSocket connection."""
        return chat_id in self.active_connections

    async def send_to_chat(self, chat_id: UUID, message: dict[str, Any]) -> bool:
        """Send message to specific chat if it's active."""
        if chat_id not in self.active_connections:
            return False

        websocket = self.active_connections[chat_id]

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to chat {chat_id}: {e}")
            # Remove broken connection
            await self.disconnect(chat_id)
            return False

    def get_active_chats(self) -> list[UUID]:
        """Get list of all active chat IDs."""
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global singleton instance
connection_manager = ConnectionManager()


__all__ = ["ConnectionManager", "connection_manager"]