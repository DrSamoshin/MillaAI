"""Redis client utilities."""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis  # type: ignore[import-untyped]

from aimi.core.config import get_settings


def create_redis_client() -> Redis:
    """Instantiate an async Redis client using application settings."""

    settings = get_settings()
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


@lru_cache
def get_redis_client() -> Redis:
    """Return cached Redis client instance."""

    return create_redis_client()


__all__ = ["create_redis_client", "get_redis_client"]
