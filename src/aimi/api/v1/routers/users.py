"""User profile management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import get_current_user, get_db_session
from aimi.api.v1.schemas import SuccessResponse
from aimi.api.v1.schemas.auth import UserPayload
from aimi.api.v1.schemas.user import DeleteUserResponse, UserProfileResponse
from aimi.db.models import User
from aimi.repositories.users import UserRepository


router = APIRouter(prefix="/users", tags=["users"])


def _map_user(user: User) -> UserPayload:
    return UserPayload(
        id=str(user.id),
        email=user.email,
        name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
        role=user.role,
    )


@router.get("/me/", response_model=SuccessResponse[UserProfileResponse])
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserProfileResponse]:
    return SuccessResponse(data=UserProfileResponse(user=_map_user(current_user)))


@router.delete("/me/", response_model=SuccessResponse[DeleteUserResponse])
async def delete_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[DeleteUserResponse]:
    repo = UserRepository(session)
    await repo.delete(current_user)
    await session.commit()
    # TODO: cascade delete related data (messages, events, vectors, etc.)
    return SuccessResponse(data=DeleteUserResponse())
