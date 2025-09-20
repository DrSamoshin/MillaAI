"""API routers."""

from __future__ import annotations

from .chat import router as chat_router
from .health import router as health_router

__all__: list[str] = ["chat_router", "health_router"]
