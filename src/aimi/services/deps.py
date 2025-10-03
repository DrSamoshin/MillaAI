"""Service dependencies for dependency injection."""

from __future__ import annotations

from fastapi import Depends
from redis.asyncio import Redis

from aimi.api.v1.deps import get_llm_client, get_redis
from aimi.llm.client import LLMClient
from aimi.services.chat import ChatService


async def get_chat_service(
    redis: Redis = Depends(get_redis),
    llm_client: LLMClient = Depends(get_llm_client),
) -> ChatService:
    """Get ChatService instance."""
    return ChatService(
        redis=redis,
        llm_client=llm_client,
    )


__all__ = ["get_chat_service"]