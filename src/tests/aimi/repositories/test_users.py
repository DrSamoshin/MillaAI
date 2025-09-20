from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aimi.core.config import get_settings
from aimi.db import Base


@pytest.fixture(scope="module")
async def db_engine() -> AsyncEngine:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - environment guard
        await engine.dispose()
        pytest.skip(f"Database unavailable: {exc}")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncSession:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


# Skipping repository tests until transactional test harness is ready.
pytestmark = pytest.mark.skip(reason="Repository tests temporarily disabled")
