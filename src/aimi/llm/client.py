"""LLM client abstraction placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str
    content: str


class LLMClient:
    """Interface for chat completion models."""

    async def generate(self, messages: list[ChatMessage]) -> str:  # pragma: no cover
        raise NotImplementedError


__all__ = ["LLMClient", "ChatMessage"]
