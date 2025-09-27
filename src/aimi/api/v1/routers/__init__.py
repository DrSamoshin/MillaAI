"""API routers."""

from __future__ import annotations

from .chat import router as chat_router
from .auth import router as auth_router
from .health import router as health_router
from .users import router as users_router
from .admin import router as admin_router
from .goals import router as goals_router

__all__: list[str] = [
    "chat_router",
    "health_router",
    "auth_router",
    "users_router",
    "admin_router",
    "goals_router",
]
