"""Repository for user persistence operations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models import User


class UserRepository:
    """Data access layer for the `User` model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        display_name: str,
        timezone: str,
        locale: str,
        email: str | None = None,
        apple_id: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> User:
        """Create and persist a new user entity."""

        user = User(
            email=email,
            apple_id=apple_id,
            display_name=display_name,
            timezone=timezone,
            locale=locale,
            profile=profile or {},
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key."""

        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address."""

        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_apple_id(self, apple_id: str) -> User | None:
        """Fetch a user by associated Apple identifier."""

        stmt = select(User).where(User.apple_id == apple_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


__all__ = ["UserRepository"]
