"""Repository for user persistence operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models import User, UserRole
import logging


logger = logging.getLogger(__name__)


class UserRepository:
    """Data access layer for the `User` model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        display_name: str,
        email: str | None = None,
        apple_id: str | None = None,
        role: UserRole | str = UserRole.USER,
    ) -> User:
        """Create and persist a new user entity."""

        role_enum = UserRole(role) if isinstance(role, str) else role
        user = User(
            email=email,
            apple_id=apple_id,
            display_name=display_name,
            role=role_enum,
        )
        self._session.add(user)
        await self._session.flush()
        logger.info(
            "user_created",
            extra={
                "user_id": str(user.id),
                "email": user.email,
                "apple_id": user.apple_id,
                "role": user.role.value,
            },
        )
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

    async def delete(self, user: User) -> None:
        """Remove user record."""

        await self._session.delete(user)


__all__ = ["UserRepository"]
