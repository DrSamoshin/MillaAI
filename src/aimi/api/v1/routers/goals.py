"""Goals and tasks endpoints - read-only access."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.api.v1.deps import get_current_user, get_db_session
from aimi.api.v1.schemas import SuccessResponse
from aimi.db.models import User
from aimi.db.models.goals import Goal, Task, MentalState

router = APIRouter(prefix="/goals", tags=["goals"])


class TaskItem(BaseModel):
    """Task item in goal."""
    task_id: str
    title: str
    description: str | None
    status: str
    due_date: str | None
    reminder_at: str | None
    created_at: str
    completed_at: str | None


class GoalItem(BaseModel):
    """Goal item with tasks."""
    goal_id: str
    title: str
    description: str | None
    status: str
    priority: int
    deadline: str | None
    created_at: str
    updated_at: str
    tasks: list[TaskItem]


class GoalListResponse(BaseModel):
    """Response with list of goals."""
    goals: list[GoalItem]
    total: int


class MentalStateItem(BaseModel):
    """Mental state record."""
    mental_state_id: str
    mood: str | None
    energy_level: int | None
    confidence_level: int | None
    detected_emotions: list[str] | None
    context: str | None
    analysis_source: str
    created_at: str


class MentalStateListResponse(BaseModel):
    """Response with mental state history."""
    mental_states: list[MentalStateItem]
    total: int


@router.get("/", response_model=SuccessResponse[GoalListResponse])
async def list_goals(
    status: str | None = Query(None, description="Filter by status (active, completed, paused, cancelled)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[GoalListResponse]:
    """Get all goals for current user."""
    query = select(Goal).where(Goal.user_id == current_user.id)

    if status:
        query = query.where(Goal.status == status)

    query = query.order_by(Goal.priority.desc(), Goal.created_at.desc())

    result = await db.execute(query)
    goals = result.scalars().all()

    # Build response with tasks
    goal_items = []
    for goal in goals:
        # Get tasks for this goal
        tasks_result = await db.execute(
            select(Task)
            .where(Task.goal_id == goal.id)
            .order_by(Task.created_at.asc())
        )
        tasks = tasks_result.scalars().all()

        task_items = [
            TaskItem(
                task_id=str(task.id),
                title=task.title,
                description=task.description,
                status=task.status,
                due_date=task.due_date.isoformat() if task.due_date else None,
                reminder_at=task.reminder_at.isoformat() if task.reminder_at else None,
                created_at=task.created_at.isoformat(),
                completed_at=task.completed_at.isoformat() if task.completed_at else None,
            )
            for task in tasks
        ]

        goal_items.append(GoalItem(
            goal_id=str(goal.id),
            title=goal.title,
            description=goal.description,
            status=goal.status,
            priority=goal.priority,
            deadline=goal.deadline.isoformat() if goal.deadline else None,
            created_at=goal.created_at.isoformat(),
            updated_at=goal.updated_at.isoformat(),
            tasks=task_items,
        ))

    return SuccessResponse(data=GoalListResponse(
        goals=goal_items,
        total=len(goal_items),
    ))


@router.get("/{goal_id}", response_model=SuccessResponse[GoalItem])
async def get_goal(
    goal_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[GoalItem]:
    """Get specific goal with tasks."""
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    # Get tasks for this goal
    tasks_result = await db.execute(
        select(Task)
        .where(Task.goal_id == goal.id)
        .order_by(Task.created_at.asc())
    )
    tasks = tasks_result.scalars().all()

    task_items = [
        TaskItem(
            task_id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status,
            due_date=task.due_date.isoformat() if task.due_date else None,
            reminder_at=task.reminder_at.isoformat() if task.reminder_at else None,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
        for task in tasks
    ]

    goal_item = GoalItem(
        goal_id=str(goal.id),
        title=goal.title,
        description=goal.description,
        status=goal.status,
        priority=goal.priority,
        deadline=goal.deadline.isoformat() if goal.deadline else None,
        created_at=goal.created_at.isoformat(),
        updated_at=goal.updated_at.isoformat(),
        tasks=task_items,
    )

    return SuccessResponse(data=goal_item)


@router.get("/mental-states/", response_model=SuccessResponse[MentalStateListResponse])
async def list_mental_states(
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[MentalStateListResponse]:
    """Get mental state history for current user."""
    # Get total count
    count_result = await db.execute(
        select(MentalState.id).where(MentalState.user_id == current_user.id)
    )
    total = len(count_result.scalars().all())

    # Get records
    result = await db.execute(
        select(MentalState)
        .where(MentalState.user_id == current_user.id)
        .order_by(MentalState.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    mental_states = result.scalars().all()

    mental_state_items = [
        MentalStateItem(
            mental_state_id=str(state.id),
            mood=state.mood,
            energy_level=state.energy_level,
            confidence_level=state.confidence_level,
            detected_emotions=state.detected_emotions,
            context=state.context,
            analysis_source=state.analysis_source,
            created_at=state.created_at.isoformat(),
        )
        for state in mental_states
    ]

    return SuccessResponse(data=MentalStateListResponse(
        mental_states=mental_state_items,
        total=total,
    ))


__all__ = ["router"]