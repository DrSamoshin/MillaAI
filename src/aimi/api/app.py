"""FastAPI application factory for Aimi."""

from __future__ import annotations

from fastapi import FastAPI

from .exceptions import register_exception_handlers
from .routers import chat_router, health_router


def create_app() -> FastAPI:
    """Create and return a FastAPI application."""

    app = FastAPI(title="Aimi", version="0.1.0")
    app.include_router(health_router)
    app.include_router(chat_router)
    register_exception_handlers(app)
    return app


app = create_app()

__all__ = ["create_app", "app"]
