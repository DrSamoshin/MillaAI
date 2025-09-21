"""Security helpers for JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from aimi.core.config import AppSettings


def _expiry(seconds: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def create_access_token(*, subject: str, settings: AppSettings) -> str:
    payload = {
        "sub": subject,
        "type": "access",
        "exp": _expiry(settings.jwt_access_expires_seconds),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, subject: str, settings: AppSettings) -> str:
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": _expiry(settings.jwt_refresh_expires_seconds),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(*, token: str, settings: AppSettings) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = ["create_access_token", "create_refresh_token", "decode_token"]
