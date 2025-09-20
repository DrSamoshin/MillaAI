from __future__ import annotations

from typing import Any

import pytest

from aimi.llm.client import ChatMessage, LLMClient
from aimi.services.conversation import ConversationService


class StubRepository:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    async def save(self, message: dict[str, Any]) -> None:
        self.saved.append(message)


class RecordingLLM(LLMClient):
    def __init__(self, reply_text: str) -> None:
        self.reply_text = reply_text
        self.seen: list[ChatMessage] = []

    @property
    def model_name(self) -> str:
        return "stub-model"

    async def generate(self, messages: list[ChatMessage]) -> str:
        self.seen = messages
        return self.reply_text


class StubSessionCache:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def append(self, user_id: str, message: dict[str, Any]) -> None:
        self.entries.append(message)

    async def fetch(self, user_id: str) -> list[dict[str, Any]]:
        return list(self.entries)

    async def clear(self, user_id: str) -> None:  # pragma: no cover - not used here
        self.entries.clear()


@pytest.mark.asyncio
async def test_handle_incoming_records_history_and_uses_cache() -> None:
    repository = StubRepository()
    llm = RecordingLLM("assistant reply")
    cache = StubSessionCache()
    service = ConversationService(
        message_repository=repository,
        llm_client=llm,
        session_cache=cache,
    )

    result = await service.handle_incoming(user_id="user-1", message="Hello")

    assert result == {"reply": "assistant reply", "model": "stub-model"}
    assert len(repository.saved) == 2
    assert repository.saved[0]["role"] == "user"
    assert repository.saved[1]["role"] == "assistant"

    assert len(cache.entries) == 2
    assert cache.entries[0]["role"] == "user"
    assert cache.entries[1]["role"] == "assistant"

    assert [msg.content for msg in llm.seen] == ["Hello"]


@pytest.mark.asyncio
async def test_handle_incoming_without_cache_behaves_normally() -> None:
    repository = StubRepository()
    llm = RecordingLLM("echo")
    service = ConversationService(
        message_repository=repository,
        llm_client=llm,
        session_cache=None,
    )

    result = await service.handle_incoming(user_id="user-2", message="Ping")

    assert result == {"reply": "echo", "model": "stub-model"}
    assert len(repository.saved) == 2
    assert repository.saved[0]["role"] == "user"
    assert repository.saved[1]["role"] == "assistant"
