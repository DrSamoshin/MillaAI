"""Embedding service stub."""

from __future__ import annotations

from typing import Iterable


class EmbeddingService:
    """Placeholder for vector generation logic."""

    async def encode(
        self, texts: Iterable[str]
    ) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError


__all__ = ["EmbeddingService"]
