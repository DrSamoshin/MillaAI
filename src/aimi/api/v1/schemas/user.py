"""Schemas for user profile endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from aimi.api.v1.schemas.auth import UserPayload


class UserProfileResponse(BaseModel):
    user: UserPayload


class DeleteUserResponse(BaseModel):
    message: str = Field(default="User deleted")


__all__ = [
    "UserProfileResponse",
    "DeleteUserResponse",
]
