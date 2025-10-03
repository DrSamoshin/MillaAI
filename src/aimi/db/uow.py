"""Unit of Work implementation for transaction and repository management."""

from __future__ import annotations

from types import TracebackType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.repositories.chats import ChatRepository
from aimi.repositories.devices import DeviceRepository
from aimi.repositories.events import EventRepository
from aimi.repositories.goals import GoalRepository
from aimi.repositories.mental_states import MentalStateRepository
from aimi.repositories.messages import MessageRepository
from aimi.repositories.notifications import NotificationRepository
from aimi.repositories.users import UserRepository


class UnitOfWork:
    """Unit of Work for managing database session and repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repositories: dict[str, Any] = {}

    async def __aenter__(self) -> UnitOfWork:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit with automatic rollback on exception."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush changes to the database without committing."""
        await self._session.flush()

    def users(self) -> UserRepository:
        """Get or create UserRepository instance."""
        if 'users' not in self._repositories:
            self._repositories['users'] = UserRepository(self._session)
        return self._repositories['users']

    def goals(self) -> GoalRepository:
        """Get or create GoalRepository instance."""
        if 'goals' not in self._repositories:
            self._repositories['goals'] = GoalRepository(self._session)
        return self._repositories['goals']

    def messages(self) -> MessageRepository:
        """Get or create MessageRepository instance."""
        if 'messages' not in self._repositories:
            self._repositories['messages'] = MessageRepository(self._session)
        return self._repositories['messages']

    def chats(self) -> ChatRepository:
        """Get or create ChatRepository instance."""
        if 'chats' not in self._repositories:
            self._repositories['chats'] = ChatRepository(self._session)
        return self._repositories['chats']

    def events(self) -> EventRepository:
        """Get or create EventRepository instance."""
        if 'events' not in self._repositories:
            self._repositories['events'] = EventRepository(self._session)
        return self._repositories['events']

    def notifications(self) -> NotificationRepository:
        """Get or create NotificationRepository instance."""
        if 'notifications' not in self._repositories:
            self._repositories['notifications'] = NotificationRepository(self._session)
        return self._repositories['notifications']

    def devices(self) -> DeviceRepository:
        """Get or create DeviceRepository instance."""
        if 'devices' not in self._repositories:
            self._repositories['devices'] = DeviceRepository(self._session)
        return self._repositories['devices']

    def mental_states(self) -> MentalStateRepository:
        """Get or create MentalStateRepository instance."""
        if 'mental_states' not in self._repositories:
            self._repositories['mental_states'] = MentalStateRepository(self._session)
        return self._repositories['mental_states']


__all__ = ["UnitOfWork"]