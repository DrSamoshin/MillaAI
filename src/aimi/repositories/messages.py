"""Repository stubs for chat messages."""

from __future__ import annotations


class InMemoryMessageRepository:
    """Временный репозиторий, который просто собирает сообщения в списке."""

    def __init__(self) -> None:
        self._storage: list[dict] = []

    async def save(self, message: dict) -> None:  # pragma: no cover - placeholder
        self._storage.append(message)


__all__ = ["InMemoryMessageRepository"]
