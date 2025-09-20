"""Session cache helpers (placeholder)."""

from __future__ import annotations

from typing import Any


class SessionCache:
    """Обёртка над Redis/ин-memory. Реализация появится позже."""

    async def append(
        self, user_id: str, message: dict[str, Any]
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    async def fetch(self, user_id: str) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    async def clear(self, user_id: str) -> None:  # pragma: no cover
        raise NotImplementedError


__all__ = ["SessionCache"]
