"""Chat service with WebSocket activity tracking and Redis cache."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models import Chat, Message, MessageRole
from aimi.llm.client import ChatMessage, LLMClient
from aimi.repositories.chats import ChatRepository
from aimi.repositories.messages import MessageRepository
from aimi.services.connection_manager import connection_manager
from aimi.services.conversation import ConversationOrchestrator

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations with Redis cache and WebSocket activity tracking.

    Focused on CRUD operations, message persistence, and chat management.
    LLM orchestration is handled by ConversationOrchestrator.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis: Redis,
        llm_client: LLMClient,
    ):
        self.db = db_session
        self.redis = redis
        self.llm_client = llm_client
        self.chat_repo = ChatRepository(db_session)
        self.message_repo = MessageRepository(db_session)

    async def send_message(
        self,
        chat_id: UUID,
        content: str,
        client_msg_id: str | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send message and generate response using ConversationOrchestrator."""
        # 1. Ensure chat exists (auto-create if needed)
        await self._ensure_chat_exists(chat_id, user_id)

        # 2. Save user message
        user_msg = await self._save_message(
            chat_id=chat_id,
            role=MessageRole.USER.value,
            content=content,
            client_msg_id=client_msg_id,
        )

        try:
            # 3. Build conversation context
            context = await self._build_context(chat_id, content)

            # 4. Use ConversationOrchestrator for enhanced response generation
            if user_id:
                orchestrator = ConversationOrchestrator(
                    db_session=self.db,
                    llm_client=self.llm_client,
                    user_id=user_id,
                    chat_id=chat_id
                )

                # Generate response with tool support
                orchestration_result = await orchestrator.generate_response(
                    messages=context[1:],  # Skip system message from context
                    user_message=content
                )

                reply = orchestration_result["content"]
                tool_calls = orchestration_result.get("tool_calls", [])
                tool_results = orchestration_result.get("tool_results", [])

                # Log tool usage for debugging
                if tool_calls:
                    logger.info(f"LLM made {len(tool_calls)} tool calls for chat {chat_id}")
                if tool_results:
                    logger.info(f"Tool results: {tool_results}")

            else:
                # Fallback for cases without user_id
                reply = await self.llm_client.generate(context)
                tool_calls = []
                tool_results = []

            # 5. Save assistant response
            assistant_msg = await self._save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT.value,
                content=reply,
            )

            # 6. Handle notification if chat is inactive
            is_active = self._is_chat_active(chat_id)
            if not is_active:
                await self._send_push_notification(chat_id, reply)

            return {
                "user_message": self._message_to_dict(user_msg),
                "assistant_message": self._message_to_dict(assistant_msg),
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "status": "delivered" if is_active else "push_sent",
                "model": self.llm_client.model_name,
            }

        except Exception as e:
            logger.error(f"Error generating response for chat {chat_id}: {e}")
            # Send error response
            error_msg = await self._save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT.value,
                content="I encountered an error while processing your request. Please try again.",
            )

            return {
                "user_message": self._message_to_dict(user_msg),
                "assistant_message": self._message_to_dict(error_msg),
                "tool_calls": [],
                "tool_results": [],
                "status": "error",
                "model": self.llm_client.model_name,
            }

    # Note: Activity tracking now handled by ConnectionManager
    # No longer need mark_chat_active/inactive methods

    def _is_chat_active(self, chat_id: UUID) -> bool:
        """Check if chat has active WebSocket connection."""
        return connection_manager.is_active(chat_id)

    async def _ensure_chat_exists(
        self,
        chat_id: UUID,
        user_id: UUID | None = None,
        title: str | None = None,
        model: str = "gpt-4",
        settings: dict | None = None,
    ) -> None:
        """Ensure chat exists, create if needed."""
        # Check if chat already exists
        existing_chat = await self.chat_repo.get_by_id(chat_id)

        if existing_chat:
            return  # Chat already exists

        # Need user_id to create chat
        if not user_id:
            raise ValueError("user_id required to create new chat")

        # Create new chat using repository
        await self.chat_repo.create_chat(
            chat_id=chat_id,
            user_id=user_id,
            title=title,
            model=model,
            settings=settings,
        )
        await self.db.commit()

        if title:
            logger.info(f"Created chat '{title}' {chat_id} for user {user_id}")
        else:
            logger.info(f"Auto-created chat {chat_id} for user {user_id}")

    async def delete_chat(self, chat_id: UUID, user_id: UUID) -> bool:
        """Delete chat and all its messages."""
        # Check if chat exists and belongs to user
        chat = await self.chat_repo.get_user_chat_by_id(chat_id, user_id)

        if not chat:
            return False

        # Delete all messages first (due to foreign key constraint)
        await self.message_repo.delete_chat_messages(chat_id)

        # Delete chat
        deleted = await self.chat_repo.delete_chat(chat_id)
        if not deleted:
            return False

        await self.db.commit()

        # Clean Redis cache
        await self.redis.delete(f"chat:{chat_id}:messages")
        await self.redis.delete(f"chat:{chat_id}:meta")

        # Disconnect any active WebSocket
        await connection_manager.disconnect(chat_id)

        logger.info(f"Deleted chat {chat_id} for user {user_id}")
        return True

    async def get_chat_messages(
        self,
        chat_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get message history for a chat with pagination."""
        # First verify chat exists and belongs to user
        chat = await self.chat_repo.get_user_chat_by_id(chat_id, user_id)

        if not chat:
            raise ValueError("Chat not found or not owned by user")

        # Try to get messages from Redis cache first (last 100 messages)
        cached_messages = await self.redis.zrange(f"chat:{chat_id}:messages", 0, -1)

        messages = []
        total_messages = 0

        if cached_messages and offset == 0:
            # Use Redis cache for recent messages (no offset)
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    messages.append({
                        "id": msg_data["id"],
                        "seq": msg_data["seq"],
                        "role": msg_data["role"],
                        "content": msg_data["content"],
                        "created_at": msg_data["created_at"],
                    })
                except (json.JSONDecodeError, KeyError):
                    continue

            # Apply limit to cached messages
            if limit < len(messages):
                messages = messages[-limit:]  # Get latest messages
                has_more = True
            else:
                has_more = False

            total_messages = len(messages)

        else:
            # Fallback to PostgreSQL for pagination or cache miss
            db_messages, total_messages = await self.message_repo.get_chat_messages(
                chat_id=chat_id,
                limit=limit,
                offset=offset
            )

            messages = [
                {
                    "id": str(msg.id),
                    "seq": msg.seq,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in reversed(db_messages)  # Reverse to get chronological order
            ]

            has_more = offset + limit < total_messages

        return {
            "messages": messages,
            "total": total_messages,
            "has_more": has_more,
        }

    async def _save_message(
        self,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        client_msg_id: str | None = None,
    ) -> Message:
        """Save message to database and Redis cache."""
        # Check for duplicate if client_msg_id provided
        if client_msg_id:
            existing_msg = await self.message_repo.get_by_request_id(
                chat_id, UUID(client_msg_id)
            )
            if existing_msg:
                return existing_msg

        # Get next sequence number
        next_seq = await self.message_repo.get_next_sequence(chat_id)

        # Create message using repository
        message = await self.message_repo.create_message(
            chat_id=chat_id,
            role=role,
            content=content,
            seq=next_seq,
            request_id=UUID(client_msg_id) if client_msg_id else None,
        )

        # Save to Redis cache
        await self._add_message_to_cache(chat_id, message)

        # Update chat metadata
        await self.chat_repo.update_last_activity(
            chat_id=chat_id,
            last_seq=next_seq,
            last_active_at=message.created_at,
        )

        await self.db.commit()
        return message

    async def _add_message_to_cache(self, chat_id: UUID, message: Message) -> None:
        """Add message to Redis sorted set cache."""
        message_json = json.dumps({
            "id": str(message.id),
            "seq": message.seq,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        })

        # Add to sorted set by seq
        await self.redis.zadd(f"chat:{chat_id}:messages", {message_json: message.seq})

        # Keep only last 100 messages
        await self.redis.zremrangebyrank(f"chat:{chat_id}:messages", 0, -101)

        # Update metadata
        await self.redis.hset(
            f"chat:{chat_id}:meta",
            mapping={
                "max_seq": str(message.seq),
                "last_active_at": message.created_at.isoformat(),
                "message_count": await self.redis.zcard(f"chat:{chat_id}:messages"),
            },
        )

    async def _build_context(self, chat_id: UUID, user_message: str) -> list[ChatMessage]:
        """Build basic conversation context for LLM."""
        # Get last 20 messages from Redis cache for context
        cached_messages = await self.redis.zrange(f"chat:{chat_id}:messages", -20, -1)

        messages = []
        if cached_messages:
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    messages.append(ChatMessage(
                        role=msg_data["role"],
                        content=msg_data["content"],
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue

        # Add basic system message (ConversationOrchestrator handles enhanced context)
        system_msg = ChatMessage(
            role="system",
            content="You are Aimi, a helpful AI assistant focused on helping users achieve their goals.",
        )

        return [system_msg] + messages

    async def get_conversation_starter(self, chat_id: UUID, user_id: UUID) -> str:
        """Get a personalized conversation starter for the chat."""
        try:
            orchestrator = ConversationOrchestrator(
                db_session=self.db,
                llm_client=self.llm_client,
                user_id=user_id,
                chat_id=chat_id
            )
            return await orchestrator.get_conversation_starter()
        except Exception as e:
            logger.error(f"Error getting conversation starter: {e}")
            return "Hello! How can I help you achieve your goals today?"

    async def _send_push_notification(self, chat_id: UUID, content: str) -> None:
        """Send push notification (stub implementation)."""
        # Get chat info for notification
        chat = await self.chat_repo.get_by_id(chat_id)

        if not chat:
            return

        # Truncate content for notification
        preview = content[:100] + "..." if len(content) > 100 else content

        logger.info(
            f"PUSH NOTIFICATION: Chat '{chat.title or 'Untitled'}' - {preview} (user_id: {chat.user_id})"
        )

        # TODO: Implement actual push notification service
        # await push_service.send_notification(
        #     user_id=chat.user_id,
        #     title=f"New message in '{chat.title or 'Chat'}'",
        #     body=preview
        # )

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """Convert message model to dictionary."""
        return {
            "id": str(message.id),
            "seq": message.seq,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "request_id": str(message.request_id) if message.request_id else None,
        }


__all__ = ["ChatService"]