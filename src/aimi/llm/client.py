"""LLM client abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ChatMessage:
    """Generic chat message data structure."""

    role: str
    content: str


class LLMClient(ABC):
    """Interface for chat completion models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the underlying model."""

    @abstractmethod
    async def generate(self, messages: list[ChatMessage]) -> str:  # pragma: no cover
        """Generate assistant reply for the provided messages."""


__all__ = ["LLMClient", "ChatMessage"]
