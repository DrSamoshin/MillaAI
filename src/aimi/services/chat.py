"""Chat service with WebSocket activity tracking and Redis cache.

IMPORTANT: Do not use emojis in any user-facing content or system messages.
Keep all communication clean and professional without emoji characters.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis

from aimi.core.config import get_settings
from aimi.db.models import Chat, Message, MessageRole
from aimi.db.session import UnitOfWork
from aimi.llm.client import ChatMessage, LLMClient
from aimi.services.connection_manager import connection_manager
from aimi.services.conversation import ConversationOrchestrator
from aimi.services.notification import NotificationService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations with Redis cache and WebSocket activity tracking.

    Focused on CRUD operations, message persistence, and chat management.
    LLM orchestration is handled by ConversationOrchestrator.
    """

    def __init__(
        self,
        redis: Redis,
        llm_client: LLMClient,
        notification_service: NotificationService | None = None,
    ):
        self.redis = redis
        self.llm_client = llm_client
        self.notification_service = notification_service or NotificationService()

    async def save_user_message(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        content: str,
        client_msg_id: str | None = None,
        user_id: UUID | None = None,
    ) -> Message:
        """Save user message and return it immediately."""
        logger.info(f"[CHAT] Saving user message for chat {chat_id}")

        # Ensure chat exists (auto-create if needed)
        await self._ensure_chat_exists(uow, chat_id, user_id)

        # Save user message
        user_msg = await self._save_message(
            uow=uow,
            chat_id=chat_id,
            role=MessageRole.USER.value,
            content=content,
            client_msg_id=client_msg_id,
        )

        logger.info(f"[CHAT] Saved user message with ID: {user_msg.id}, seq: {user_msg.seq}")
        return user_msg

    async def generate_assistant_response(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        user_content: str,
        user_id: UUID | None = None,
    ) -> list[Message]:
        """Generate and save assistant response messages."""
        logger.info(f"[CHAT] Generating assistant response for chat {chat_id}")

        try:
            # Get conversation history for context
            history = await self._get_conversation_history(chat_id, uow)
            logger.info(f"[CHAT] Got {len(history)} messages from history")

            # Use ConversationOrchestrator for response generation
            orchestrator = ConversationOrchestrator(
                uow=uow,
                llm_client=self.llm_client,
                user_id=user_id,
                chat_id=chat_id
            )

            # Generate response with history (includes user content)
            generated_messages = await orchestrator.generate_response(history)
            logger.info(f"[CHAT] Orchestrator returned {len(generated_messages)} generated messages")

            # Save all generated messages to database
            saved_messages = []
            for i, message in enumerate(generated_messages):
                logger.info(f"[CHAT] Saving message {i+1}/{len(generated_messages)}: role={message.role}")
                saved_msg = await self._save_message(
                    uow=uow,
                    chat_id=chat_id,
                    role=message.role,
                    content=message.content,
                )
                saved_messages.append(saved_msg)
                logger.info(f"[CHAT] Saved message {i+1} with ID: {saved_msg.id}")

            # Handle notification if chat is inactive
            assistant_messages = [msg for msg in saved_messages if msg.role == MessageRole.ASSISTANT.value]
            if assistant_messages:
                assistant_msg = assistant_messages[-1]
                is_active = self._is_chat_active(chat_id)
                if not is_active:
                    await self.notification_service.send_push_notification(uow, chat_id, assistant_msg.content)

            logger.info(f"[CHAT] Generated {len(saved_messages)} assistant messages")
            return saved_messages

        except Exception as e:
            logger.error(f"Error generating response for chat {chat_id}: {e}", exc_info=True)
            # Send error response
            error_msg = await self._save_message(
                uow=uow,
                chat_id=chat_id,
                role=MessageRole.ASSISTANT.value,
                content="I encountered an error while processing your request. Please try again.",
            )
            return [error_msg]

    async def send_message(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        content: str,
        client_msg_id: str | None = None,
        user_id: UUID | None = None,
    ) -> list[Message]:
        """Send message and generate response using ConversationOrchestrator.

        This method is kept for backward compatibility with REST API.
        """
        logger.info(f"[CHAT] Starting send_message for chat {chat_id}, user {user_id}")
        logger.info(f"[CHAT] Message content: '{content[:100]}...'")

        # Save user message
        user_msg = await self.save_user_message(uow, chat_id, content, client_msg_id, user_id)

        # Generate assistant response
        assistant_messages = await self.generate_assistant_response(uow, chat_id, content, user_id)

        # Return all messages in order: user_msg + assistant_messages
        all_messages = [user_msg] + assistant_messages
        logger.info(f"[CHAT] Returning {len(all_messages)} total messages")
        return all_messages

    # Note: Activity tracking now handled by ConnectionManager
    # No longer need mark_chat_active/inactive methods

    def _is_chat_active(self, chat_id: UUID) -> bool:
        """Check if chat has active WebSocket connection."""
        return connection_manager.is_active(chat_id)

    async def _ensure_chat_exists(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        user_id: UUID | None = None,
        title: str | None = None,
        model: str = "gpt-4",
        settings: dict | None = None,
    ) -> None:
        """Ensure chat exists, create if needed."""
        # Check if chat already exists
        existing_chat = await uow.chats().get_by_id(chat_id)

        if existing_chat:
            return  # Chat already exists

        # Need user_id to create chat
        if not user_id:
            raise ValueError("user_id required to create new chat")

        # Create new chat using repository
        await uow.chats().create_chat(
            chat_id=chat_id,
            user_id=user_id,
            title=title,
            model=model,
            settings=settings,
        )
        await uow.commit()

        if title:
            logger.info(f"Created chat '{title}' {chat_id} for user {user_id}")
        else:
            logger.info(f"Auto-created chat {chat_id} for user {user_id}")

    async def delete_chat(self, uow: UnitOfWork, chat_id: UUID, user_id: UUID) -> bool:
        """Delete chat and all its messages."""
        # Check if chat exists and belongs to user
        chat = await uow.chats().get_user_chat_by_id(chat_id, user_id)

        if not chat:
            return False

        # Delete all messages first (due to foreign key constraint)
        await uow.messages().delete_chat_messages(chat_id)

        # Delete chat
        deleted = await uow.chats().delete_chat(chat_id)
        if not deleted:
            return False

        await uow.commit()

        # Clean Redis cache
        await self.redis.delete(f"chat:{chat_id}:messages")
        await self.redis.delete(f"chat:{chat_id}:meta")

        # Disconnect any active WebSocket
        await connection_manager.disconnect(chat_id)

        logger.info(f"Deleted chat {chat_id} for user {user_id}")
        return True

    async def send_assistant_message(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        content: str,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send message from assistant/system without LLM processing."""
        # 1. Ensure chat exists (auto-create if needed)
        await self._ensure_chat_exists(uow, chat_id, user_id)

        # 2. Save assistant message directly
        assistant_msg = await self._save_message(
            uow=uow,
            chat_id=chat_id,
            role=MessageRole.ASSISTANT.value,
            content=content,
        )

        # 3. Prepare message data BEFORE any commits to avoid lazy loading issues
        assistant_message_data = self._message_to_dict(assistant_msg)

        # 4. Handle notification if chat is inactive
        is_active = self._is_chat_active(chat_id)
        if not is_active:
            await self.notification_service.send_push_notification(uow, chat_id, content)

        return {
            "assistant_message": assistant_message_data,
            "status": "delivered" if is_active else "push_sent",
        }

    async def get_chat_messages(
        self,
        uow: UnitOfWork,
        chat_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get message history for a chat with pagination (direct PostgreSQL access for UI)."""
        # First verify chat exists and belongs to user
        chat = await uow.chats().get_user_chat_by_id(chat_id, user_id)

        if not chat:
            raise ValueError("Chat not found or not owned by user")

        # Always go to PostgreSQL for UI - no Redis cache
        db_messages, total_messages = await uow.messages().get_chat_messages(
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
        uow: UnitOfWork,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        client_msg_id: str | None = None,
    ) -> Message:
        """Save message to database and Redis cache."""
        # Check for duplicate if client_msg_id provided
        if client_msg_id:
            existing_msg = await uow.messages().get_by_request_id(
                chat_id, UUID(client_msg_id)
            )
            if existing_msg:
                return existing_msg

        # Get next sequence number
        next_seq = await uow.messages().get_next_sequence(chat_id)

        # Create message using repository
        message = await uow.messages().create_message(
            chat_id=chat_id,
            role=role,
            content=content,
            seq=next_seq,
            request_id=UUID(client_msg_id) if client_msg_id else None,
        )

        # Save to Redis cache
        await self._add_message_to_cache(chat_id, message)

        # Ensure all attributes are loaded BEFORE commit
        # This prevents lazy loading issues after session is closed
        _ = message.id, message.seq, message.role, message.content, message.created_at
        if message.request_id:
            _ = message.request_id

        # Update chat metadata
        await uow.chats().update_last_activity(
            chat_id=chat_id,
            last_seq=next_seq,
            last_active_at=message.created_at,
        )

        await uow.commit()
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

    async def _get_conversation_history(self, chat_id: UUID, uow: UnitOfWork) -> list[ChatMessage]:
        """Get conversation history for LLM context (Redis cache with PostgreSQL fallback)."""
        settings = get_settings()
        limit = settings.llm_context_message_limit

        messages = []

        # Try Redis cache first
        cached_messages = await self.redis.zrange(f"chat:{chat_id}:messages", -limit, -1)

        if cached_messages:
            # Use Redis cache
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    role = msg_data["role"]
                    messages.append(ChatMessage(
                        role=role,
                        content=msg_data["content"],
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue
        else:
            # Fallback to PostgreSQL via get_chat_messages
            try:
                # We need to get user_id from chat for fallback
                chat = await uow.chats().get_by_id(chat_id)
                if chat:
                    chat_messages_result = await self.get_chat_messages(
                        uow=uow,
                        chat_id=chat_id,
                        user_id=chat.user_id,
                        limit=limit,
                        offset=0
                    )

                    for msg in chat_messages_result["messages"]:
                        role = msg["role"]
                        messages.append(ChatMessage(
                            role=role,
                            content=msg["content"],
                        ))
            except Exception as e:
                logger.warning(f"Failed to get conversation history from DB for chat {chat_id}: {e}")

        return messages


    async def get_conversation_starter(self, uow: UnitOfWork, chat_id: UUID, user_id: UUID) -> str:
        """Get a personalized conversation starter for the chat."""
        try:
            context_service = ContextService(uow, user_id, chat_id)
            return await context_service.get_conversation_starter()
        except Exception as e:
            logger.error(f"Error getting conversation starter: {e}")
            return "Hello! How can I help you achieve your goals today?"


    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """Convert message model to dictionary.

        Note: This assumes message attributes have been eagerly loaded
        to prevent lazy loading issues after session closure.
        """
        try:
            return {
                "id": str(message.id),
                "seq": message.seq,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "request_id": str(message.request_id) if message.request_id else None,
            }
        except Exception as e:
            logger.error(f"Error converting message to dict: {e}")
            # Return a safe fallback without accessing any model attributes
            return {
                "id": "unknown",
                "seq": 0,
                "role": "user",
                "content": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "request_id": None,
            }


__all__ = ["ChatService"]