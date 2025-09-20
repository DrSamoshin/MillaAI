"""Redis-backed session cache implementation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis  # type: ignore[import-untyped]


class SessionCache:
    """Store recent conversation messages in Redis."""

    def __init__(
        self,
        redis: Redis,
        *,
        ttl_seconds: int = 600,
        max_messages: int = 30,
    ) -> None:
        if max_messages <= 0:
            raise ValueError("max_messages must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._max_messages = max_messages

    def _session_key(self, user_id: str) -> str:
        return f"session:{user_id}"

    def _meta_key(self, user_id: str) -> str:
        return f"session_meta:{user_id}"

    async def append(self, user_id: str, message: dict[str, Any]) -> None:
        """Append message to the session list and refresh TTL."""

        payload = json.dumps(message, ensure_ascii=True)
        now = datetime.now(timezone.utc).isoformat()
        session_key = self._session_key(user_id)
        meta_key = self._meta_key(user_id)

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(session_key, payload)
            pipe.ltrim(session_key, -self._max_messages, -1)
            pipe.hset(meta_key, mapping={"last_active_at": now})
            pipe.expire(session_key, self._ttl_seconds)
            pipe.expire(meta_key, self._ttl_seconds)
            await pipe.execute()

    async def fetch(self, user_id: str) -> list[dict[str, Any]]:
        """Return all cached messages for the session."""

        session_key = self._session_key(user_id)
        raw_messages = await self._redis.lrange(session_key, 0, -1)
        if not raw_messages:
            return []
        return [json.loads(entry) for entry in raw_messages]

    async def clear(self, user_id: str) -> None:
        """Remove session data for the user."""

        session_key = self._session_key(user_id)
        meta_key = self._meta_key(user_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(session_key)
            pipe.delete(meta_key)
            await pipe.execute()


__all__ = ["SessionCache"]
