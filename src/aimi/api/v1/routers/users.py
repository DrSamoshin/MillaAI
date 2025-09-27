"""User profile management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import get_current_user, get_db_session
from aimi.api.v1.schemas import SuccessResponse
from aimi.api.v1.schemas.auth import UserPayload
from aimi.api.v1.schemas.user import (
    EventStats,
    GoalStats,
    UserStatsResponse,
    UserAvailabilitySettings,
    UpdateUserAvailabilityRequest,
)
from aimi.api.v1.schemas.goals import MentalStateItem, MentalStateListResponse
from aimi.db.models import User
from aimi.repositories.users import UserRepository
from aimi.repositories.mental_state import MentalStateRepository


router = APIRouter(prefix="/users", tags=["users"])


class UserProfilePayload(UserPayload):
    """Extended user payload with availability settings."""
    availability: UserAvailabilitySettings


def _map_user(user: User) -> UserProfilePayload:
    return UserProfilePayload(
        id=str(user.id),
        email=user.email,
        name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
        role=user.role,
        availability=UserAvailabilitySettings(
            available_from=user.available_from,
            available_to=user.available_to,
            notification_enabled=user.notification_enabled,
        ),
    )


@router.get("/me/", response_model=SuccessResponse[UserProfilePayload])
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserProfilePayload]:
    return SuccessResponse(data=_map_user(current_user))


@router.get("/me/stats/", response_model=SuccessResponse[UserStatsResponse])
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[UserStatsResponse]:
    repo = UserRepository(session)

    goal_stats_data = await repo.get_goal_stats(current_user.id)
    event_stats_data = await repo.get_event_stats(current_user.id)

    stats = UserStatsResponse(
        goals=GoalStats(**goal_stats_data),
        events=EventStats(**event_stats_data)
    )

    return SuccessResponse(data=stats)


@router.patch("/me/availability/", response_model=SuccessResponse[UserAvailabilitySettings])
async def update_availability(
    request: UpdateUserAvailabilityRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[UserAvailabilitySettings]:
    repo = UserRepository(session)

    # Update only provided fields
    update_data = {}
    if request.available_from is not None:
        update_data["available_from"] = request.available_from
    if request.available_to is not None:
        update_data["available_to"] = request.available_to
    if request.notification_enabled is not None:
        update_data["notification_enabled"] = request.notification_enabled

    await repo.update_availability(current_user.id, **update_data)
    await session.commit()
    await session.refresh(current_user)

    return SuccessResponse(data=UserAvailabilitySettings(
        available_from=current_user.available_from,
        available_to=current_user.available_to,
        notification_enabled=current_user.notification_enabled,
    ))


@router.patch("/me/notifications/", response_model=SuccessResponse[dict[str, bool]])
async def update_notifications(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, bool]]:
    repo = UserRepository(session)
    await repo.update_availability(current_user.id, notification_enabled=enabled)
    await session.commit()

    return SuccessResponse(data={"notification_enabled": enabled})


@router.get("/me/mental-states/", response_model=SuccessResponse[MentalStateListResponse])
async def list_mental_states(
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[MentalStateListResponse]:
    """Get mental state history for current user."""
    repo = MentalStateRepository(session)

    mental_states, total = await repo.get_user_mental_states(
        current_user.id, limit=limit, offset=offset
    )

    mental_state_items = [
        MentalStateItem(
            mental_state_id=str(state.id),
            date=state.date.isoformat(),
            mood=state.mood if state.mood else None,
            readiness_level=state.readiness_level,
            notes=state.notes,
            question_asked_at=state.question_asked_at.isoformat(),
            responded_at=state.responded_at.isoformat() if state.responded_at else None,
        )
        for state in mental_states
    ]

    return SuccessResponse(data=MentalStateListResponse(
        mental_states=mental_state_items,
        total=total,
    ))


@router.delete("/me/", response_model=SuccessResponse[None])
async def delete_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[None]:
    repo = UserRepository(session)
    await repo.delete(current_user)
    await session.commit()
    return SuccessResponse(message="User deleted")
