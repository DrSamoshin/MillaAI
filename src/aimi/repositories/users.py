"""Repository for user persistence operations."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.db.models import Event, Goal, User, UserRole
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
            role=role_enum.value,
        )
        self._session.add(user)
        await self._session.flush()
        logger.info(
            "user_created",
            extra={
                "user_id": str(user.id),
                "email": user.email,
                "apple_id": user.apple_id,
                "role": user.role,
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

    async def get_goal_stats(self, user_id: uuid.UUID) -> dict:
        """Get goal statistics for user."""

        # Total goals
        total_stmt = select(func.count(Goal.id)).where(Goal.user_id == user_id)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Goals by status
        status_stmt = select(Goal.status, func.count(Goal.id)).where(
            Goal.user_id == user_id
        ).group_by(Goal.status)
        status_result = await self._session.execute(status_stmt)
        by_status = dict(status_result.fetchall())

        # Goals by category
        category_stmt = select(Goal.category, func.count(Goal.id)).where(
            Goal.user_id == user_id,
            Goal.category.is_not(None)
        ).group_by(Goal.category)
        category_result = await self._session.execute(category_stmt)
        by_category = dict(category_result.fetchall())

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category
        }

    async def update_availability(
        self,
        user_id: uuid.UUID,
        **update_data
    ) -> None:
        """Update user availability settings."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        await self._session.flush()

    async def get_event_stats(self, user_id: uuid.UUID) -> dict:
        """Get event statistics for user."""

        # Total events
        total_stmt = select(func.count(Event.id)).where(Event.user_id == user_id)
        total_result = await self._session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Events by type
        type_stmt = select(Event.event_type, func.count(Event.id)).where(
            Event.user_id == user_id
        ).group_by(Event.event_type)
        type_result = await self._session.execute(type_stmt)
        by_type = dict(type_result.fetchall())

        # Events by status
        status_stmt = select(Event.status, func.count(Event.id)).where(
            Event.user_id == user_id
        ).group_by(Event.status)
        status_result = await self._session.execute(status_stmt)
        by_status = dict(status_result.fetchall())

        return {
            "total": total,
            "by_type": by_type,
            "by_status": by_status
        }


__all__ = ["UserRepository"]
