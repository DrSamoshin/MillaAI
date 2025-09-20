"""Database engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aimi.core.config import AppSettings, get_settings


@lru_cache
def get_engine(settings: AppSettings | None = None) -> AsyncEngine:
    """Return a cached async engine instance."""

    cfg = settings or get_settings()
    return create_async_engine(cfg.database_url, future=True)


@lru_cache
def get_session_factory(
    settings: AppSettings | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return configured async session factory."""

    engine = get_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session scope for background tasks."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session."""

    async with session_scope() as session:
        yield session


__all__ = ["get_engine", "get_session_factory", "session_scope", "get_db_session"]
