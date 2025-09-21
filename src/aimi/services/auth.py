"""Auth service for Apple Sign In and token issuance."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.core.config import AppSettings
from aimi.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from aimi.repositories.users import UserRepository


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(slots=True)
class AuthResult:
    user_id: uuid.UUID
    email: str | None
    display_name: str
    is_active: bool
    role: str
    created_at: datetime
    tokens: TokenPair


class AuthService:
    """Handle user registration/login and JWT operations."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def apple_sign_in(
        self,
        *,
        session: AsyncSession,
        apple_id: str,
        name: str | None,
        email: str | None,
    ) -> AuthResult:
        repo = UserRepository(session)
        user = await repo.get_by_apple_id(apple_id)
        if user is None:
            resolved_name = (name or "").strip() or email or apple_id
            user = await repo.create(
                display_name=resolved_name,
                email=email,
                apple_id=apple_id,
            )
            await session.commit()
            await session.refresh(user)
        else:
            # Existing user stays unchanged; no field updates on repeat sign-in.
            await session.refresh(user)

        access = create_access_token(subject=str(user.id), settings=self._settings)
        refresh = create_refresh_token(subject=str(user.id), settings=self._settings)
        return AuthResult(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            role=user.role.value,
            created_at=_ensure_datetime(user.created_at),
            tokens=TokenPair(access_token=access, refresh_token=refresh),
        )

    async def refresh_tokens(self, *, token: str, session: AsyncSession) -> AuthResult:
        payload = decode_token(token=token, settings=self._settings)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("Missing subject")

        user_id = self._parse_subject(subject)

        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        access = create_access_token(subject=str(user.id), settings=self._settings)
        refresh = create_refresh_token(subject=str(user.id), settings=self._settings)
        await session.refresh(user)
        return AuthResult(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            role=user.role.value,
            created_at=_ensure_datetime(user.created_at),
            tokens=TokenPair(access_token=access, refresh_token=refresh),
        )

    def parse_access_token(self, token: str) -> uuid.UUID:
        payload = decode_token(token=token, settings=self._settings)
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("Missing subject")
        return self._parse_subject(subject)

    @staticmethod
    def _parse_subject(subject: str) -> uuid.UUID:
        try:
            return uuid.UUID(subject)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid subject") from exc


def _ensure_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


__all__ = ["AuthService", "AuthResult", "TokenPair"]
