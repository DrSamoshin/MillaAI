"""Goals endpoints - unified goals graph architecture."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import get_current_user, get_db_session
from aimi.repositories.goals import GoalRepository
from aimi.api.v1.schemas import SuccessResponse
from aimi.api.v1.schemas.goals import (
    UpdateGoalRequest,
    GoalItem,
    GoalListResponse,
    GoalDependencyItem,
)
from aimi.db.models import User

router = APIRouter(prefix="/goals", tags=["goals"])


def _map_goal_dependency(dep) -> GoalDependencyItem:
    """Map GoalDependency model to schema."""
    return GoalDependencyItem(
        dependency_id=str(dep.id),
        parent_goal_id=str(dep.parent_goal_id),
        dependent_goal_id=str(dep.dependent_goal_id),
        dependency_type=dep.dependency_type,
        strength=dep.strength,
        notes=dep.notes,
        created_at=dep.created_at.isoformat(),
    )


def _map_goal(goal, dependencies: list = None) -> GoalItem:
    """Map Goal model to schema."""
    return GoalItem(
        goal_id=str(goal.id),
        title=goal.title,
        description=goal.description,
        status=goal.status,
        category=goal.category if goal.category else None,
        priority=goal.priority,
        estimated_duration_days=goal.estimated_duration_days,
        difficulty_level=goal.difficulty_level,
        deadline=goal.deadline,
        created_at=goal.created_at.isoformat(),
        updated_at=goal.updated_at.isoformat(),
        dependencies=[_map_goal_dependency(dep) for dep in dependencies or []],
    )


@router.get("/", response_model=SuccessResponse[GoalListResponse])
async def list_goals(
    status: str | None = Query(None, description="Filter by status (todo, blocked, done, canceled)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[GoalListResponse]:
    """Get all goals for current user."""
    repo = GoalRepository(session)

    # Convert status string to enum if provided
    status_enum = None
    if status:
        from aimi.db.models.enums import GoalStatus
        try:
            status_enum = GoalStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    goals = await repo.get_user_goals(current_user.id, status=status_enum)

    # Get dependencies for all goals
    goal_items = []
    for goal in goals:
        dependencies = await repo.get_goal_dependencies(goal.id)
        goal_items.append(_map_goal(goal, dependencies))

    return SuccessResponse(data=GoalListResponse(
        goals=goal_items,
        total=len(goal_items),
    ))



@router.patch("/{goal_id}", response_model=SuccessResponse[GoalItem])
async def update_goal_status(
    goal_id: UUID,
    request: UpdateGoalRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[GoalItem]:
    """Update goal status and other fields."""
    repo = GoalRepository(session)

    goal = await repo.get_by_id(goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    goal = await repo.update_goal(goal, **update_data)

    await session.commit()
    await session.refresh(goal)

    # Get dependencies
    dependencies = await repo.get_goal_dependencies(goal.id)

    return SuccessResponse(data=_map_goal(goal, dependencies))




__all__ = ["router"]