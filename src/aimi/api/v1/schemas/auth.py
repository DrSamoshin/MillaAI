"""Schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class AppleSignInRequest(BaseModel):
    apple_id: str = Field(..., description="Stable Apple user identifier")
    name: Optional[str] = Field(
        default=None, description="Display name extracted from Apple profile"
    )
    email: Optional[str] = Field(
        default=None,
        description="User email provided by Apple",
        pattern=EMAIL_REGEX,
    )
    identity_token: Optional[str] = Field(
        default=None, description="Identity token returned by Apple"
    )


class TokenPayload(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="Bearer", frozen=True)
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class UserPayload(BaseModel):
    id: str
    email: Optional[str]
    name: str
    is_active: bool
    created_at: datetime
    role: str


class AuthResponsePayload(BaseModel):
    user: UserPayload
    token: TokenPayload


class RefreshResponsePayload(BaseModel):
    user: UserPayload
    token: TokenPayload


class RefreshRequest(BaseModel):
    refresh_token: str


__all__ = [
    "AppleSignInRequest",
    "TokenPayload",
    "UserPayload",
    "AuthResponsePayload",
    "RefreshResponsePayload",
    "RefreshRequest",
]
