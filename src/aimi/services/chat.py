"""Chat service with WebSocket activity tracking and Redis cache."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models.chat import Chat, Message, MessageRole
from aimi.llm.client import ChatMessage, LLMClient
from aimi.llm.tools import GoalManagementTools
from aimi.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations with Redis cache and WebSocket activity tracking."""

    def __init__(
        self,
        db_session: AsyncSession,
        redis: Redis,
        llm_client: LLMClient,
    ):
        self.db = db_session
        self.redis = redis
        self.llm_client = llm_client

    async def send_message(
        self,
        chat_id: UUID,
        content: str,
        client_msg_id: str | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send message and generate response."""
        # 1. Ensure chat exists (auto-create if needed)
        await self._ensure_chat_exists(chat_id, user_id)

        # 2. Save user message
        user_msg = await self._save_message(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=content,
            client_msg_id=client_msg_id,
        )

        # 2. Check if need "thinking" message for long processing
        thinking_task = None
        try:
            # 3. Build context and generate response
            context = await self._build_context(chat_id, content)

            # 4. Check for goal extraction before generating response
            await self._process_goal_extraction(chat_id, content, user_id)

            # Generate response
            reply = await self.llm_client.generate(context)

            # 4. Save assistant response
            assistant_msg = await self._save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=reply,
            )

            # 5. Check if chat is active and handle notification
            is_active = self._is_chat_active(chat_id)

            if not is_active:
                await self._send_push_notification(chat_id, reply)

            return {
                "user_message": self._message_to_dict(user_msg),
                "assistant_message": self._message_to_dict(assistant_msg),
                "status": "delivered" if is_active else "push_sent",
                "model": self.llm_client.model_name,
            }

        except Exception as e:
            logger.error(f"Error generating response for chat {chat_id}: {e}")
            # Send error response
            error_msg = await self._save_message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content="Извините, произошла ошибка при генерации ответа. Попробуйте еще раз.",
            )

            return {
                "user_message": self._message_to_dict(user_msg),
                "assistant_message": self._message_to_dict(error_msg),
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
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return  # Chat already exists

        # Need user_id to create chat
        if not user_id:
            raise ValueError("user_id required to create new chat")

        # Create new chat
        new_chat = Chat(
            id=chat_id,
            user_id=user_id,
            title=title,
            model=model,
            settings=settings or {"temperature": 0.7},
        )

        self.db.add(new_chat)
        await self.db.flush()
        await self.db.commit()

        if title:
            logger.info(f"Created chat '{title}' {chat_id} for user {user_id}")
        else:
            logger.info(f"Auto-created chat {chat_id} for user {user_id}")

    async def delete_chat(self, chat_id: UUID, user_id: UUID) -> bool:
        """Delete chat and all its messages."""
        # Check if chat exists and belongs to user
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()

        if not chat:
            return False

        # Delete all messages first (due to foreign key constraint)
        await self.db.execute(
            delete(Message).where(Message.chat_id == chat_id)
        )

        # Delete chat
        await self.db.execute(
            delete(Chat).where(Chat.id == chat_id)
        )

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
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()

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
                        "truncated": msg_data["truncated"],
                        "from_summary": msg_data["from_summary"],
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
            count_result = await self.db.execute(
                select(func.count(Message.id)).where(Message.chat_id == chat_id)
            )
            total_messages = count_result.scalar() or 0

            db_result = await self.db.execute(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.seq.desc())
                .offset(offset)
                .limit(limit)
            )
            db_messages = db_result.scalars().all()

            messages = [
                {
                    "id": str(msg.id),
                    "seq": msg.seq,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "truncated": msg.truncated,
                    "from_summary": msg.from_summary,
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
            existing = await self.db.execute(
                select(Message).where(
                    Message.chat_id == chat_id,
                    Message.request_id == UUID(client_msg_id),
                )
            )
            existing_msg = existing.scalar_one_or_none()
            if existing_msg:
                return existing_msg

        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(Message.seq), 0) + 1).where(
                Message.chat_id == chat_id
            )
        )
        next_seq = result.scalar() or 1

        # Create message
        message = Message(
            chat_id=chat_id,
            seq=next_seq,
            role=role.value,
            content=content,
            request_id=UUID(client_msg_id) if client_msg_id else None,
        )

        # Save to database
        self.db.add(message)
        await self.db.flush()  # Get ID without committing
        await self.db.refresh(message)

        # Save to Redis cache
        await self._add_message_to_cache(chat_id, message)

        # Update chat metadata
        await self.db.execute(
            update(Chat).where(Chat.id == chat_id).values(
                last_seq=next_seq,
                last_active_at=message.created_at,
            )
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
            "truncated": message.truncated,
            "from_summary": message.from_summary,
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
        """Build conversation context for LLM."""
        # Get last 100 messages from Redis cache
        cached_messages = await self.redis.zrange(f"chat:{chat_id}:messages", 0, -1)

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

        # Add current user message
        messages.append(ChatMessage(role="user", content=user_message))

        # Add system message at the beginning
        system_msg = ChatMessage(
            role="system",
            content="You are a helpful AI assistant. Keep responses concise (max 500 words). If the response would be very long, consider splitting it into multiple messages.",
        )

        return [system_msg] + messages

    async def _process_goal_extraction(self, chat_id: UUID, user_message: str, user_id: UUID) -> None:
        """Extract and process goals from user message using LLM."""
        try:
            # Use a simple prompt to check if message contains goal intentions
            goal_extraction_prompt = [
                ChatMessage(
                    role="system",
                    content="""You are a goal extraction assistant. Analyze the user's message and determine if they are expressing a goal, intention, or something they want to achieve.

If you detect a goal, respond with JSON in this format:
{"has_goal": true, "title": "goal title", "description": "detailed description", "priority": 1-5, "needs_clarification": true/false, "clarification_questions": ["question1", "question2"]}

If no goal is detected, respond with:
{"has_goal": false}

Examples of goals:
- "I want to learn Python"
- "I need to lose weight"
- "I should start exercising"
- "I'm planning to read more books"
- "I want to improve my Spanish"

Respond only with valid JSON."""
                ),
                ChatMessage(role="user", content=user_message)
            ]

            # Get goal extraction result
            extraction_result = await self.llm_client.generate(goal_extraction_prompt)

            try:
                goal_data = json.loads(extraction_result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse goal extraction result: {extraction_result}")
                return

            if not goal_data.get("has_goal", False):
                return

            # Create goal management tools instance
            goal_tools = GoalManagementTools(self.db, user_id, chat_id)

            # If goal needs clarification, we'll create it with basic info for now
            # In a more advanced implementation, we could store pending goals and ask clarification
            goal_result = await goal_tools.create_goal(
                title=goal_data.get("title", "User Goal"),
                description=goal_data.get("description"),
                priority=goal_data.get("priority", 3),
            )

            if "error" not in goal_result:
                logger.info(f"Auto-created goal '{goal_result['title']}' for user {user_id}")

                # Optionally, we could break down the goal into tasks here
                # For now, we'll just log the successful creation

        except Exception as e:
            logger.error(f"Error in goal extraction: {e}")
            # Don't fail the main chat flow if goal extraction fails

    async def _send_push_notification(self, chat_id: UUID, content: str) -> None:
        """Send push notification (stub implementation)."""
        # Get chat info for notification
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()

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
            "truncated": message.truncated,
            "from_summary": message.from_summary,
        }


__all__ = ["ChatService"]