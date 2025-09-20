from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from aimi.memory.cache.session import SessionCache


@pytest.mark.asyncio
async def test_append_enforces_limit_and_preserves_order() -> None:
    client = FakeRedis()
    cache = SessionCache(client, ttl_seconds=600, max_messages=3)

    for index in range(5):
        await cache.append(
            "user-1",
            {"message_id": str(index), "role": "user", "content": f"msg-{index}"},
        )

    history = await cache.fetch("user-1")
    assert [item["content"] for item in history] == ["msg-2", "msg-3", "msg-4"]


@pytest.mark.asyncio
async def test_append_updates_ttl() -> None:
    client = FakeRedis()
    cache = SessionCache(client, ttl_seconds=600, max_messages=5)

    await cache.append(
        "user-2",
        {"message_id": "1", "role": "user", "content": "hello"},
    )

    ttl = await client.ttl("session:user-2")
    # TTL can diminish between calls, so we only check bounds.
    assert 0 < ttl <= 600
    meta_ttl = await client.ttl("session_meta:user-2")
    assert 0 < meta_ttl <= 600


@pytest.mark.asyncio
async def test_clear_removes_session_keys() -> None:
    client = FakeRedis()
    cache = SessionCache(client)

    await cache.append(
        "user-3",
        {"message_id": "1", "role": "user", "content": "cleanup"},
    )

    await cache.clear("user-3")

    assert await client.exists("session:user-3") == 0
    assert await client.exists("session_meta:user-3") == 0
