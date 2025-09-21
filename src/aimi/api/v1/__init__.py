"""Versioned API routers."""

from __future__ import annotations

from fastapi import APIRouter

from .routers.admin import router as admin_router
from .routers.auth import router as auth_router
from .routers.chat import router as chat_router, ws_router as chat_ws_router
from .routers.health import router as health_router
from .routers.users import router as users_router


api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(chat_ws_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_router)


__all__ = ["api_router"]
