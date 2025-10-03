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
from aimi.db.uow import UnitOfWork


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



@asynccontextmanager
async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    """Provide a Unit of Work context manager."""

    async with session_scope() as session:
        uow = UnitOfWork(session)
        yield uow


async def get_uow_dependency() -> AsyncGenerator[UnitOfWork, None]:
    """FastAPI dependency that yields a Unit of Work."""

    async with get_unit_of_work() as uow:
        yield uow


__all__ = [
    "get_engine",
    "get_session_factory",
    "session_scope",
    "get_unit_of_work",
    "get_uow_dependency",
    "UnitOfWork"
]
