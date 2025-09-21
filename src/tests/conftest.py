from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aimi.api.app import app
from aimi.api.v1.deps import get_auth_service, get_db_session
from aimi.core.config import AppSettings
from aimi.db import Base
from aimi.services.auth import AuthService


@pytest.fixture
async def session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def api_client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncClient:
    async def override_session():
        async with session_factory() as session:
            yield session

    test_settings = AppSettings(jwt_secret="test-secret")

    def override_auth_service() -> AuthService:
        return AuthService(test_settings)

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_auth_service] = override_auth_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides = original_overrides
