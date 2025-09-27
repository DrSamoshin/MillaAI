"""Schemas for goals endpoints."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class GoalDependencyItem(BaseModel):
    """Goal dependency information."""
    dependency_id: str
    parent_goal_id: str
    dependent_goal_id: str
    dependency_type: str
    strength: int
    notes: str | None
    created_at: str


class GoalItem(BaseModel):
    """Goal item in unified graph."""
    goal_id: str
    title: str
    description: str | None
    status: str
    category: str | None
    priority: int
    estimated_duration_days: int | None
    difficulty_level: int
    deadline: Optional[date] = None
    created_at: str
    updated_at: str
    dependencies: list[GoalDependencyItem]


class CreateGoalRequest(BaseModel):
    """Request to create a new goal."""
    title: str
    description: str | None = None
    category: str | None = None
    priority: int = 3
    estimated_duration_days: int | None = None
    difficulty_level: int = 0
    deadline: Optional[date] = None


class UpdateGoalRequest(BaseModel):
    """Request to update an existing goal."""
    title: str | None = None
    description: str | None = None
    status: str | None = None
    category: str | None = None
    priority: int | None = None
    estimated_duration_days: int | None = None
    difficulty_level: int | None = None
    deadline: Optional[date] = None


class GoalListResponse(BaseModel):
    """Response with list of goals."""
    goals: list[GoalItem]
    total: int


class MentalStateItem(BaseModel):
    """Daily mental state polling record."""
    mental_state_id: str
    date: str
    mood: str | None
    readiness_level: int | None
    notes: str | None
    question_asked_at: str
    responded_at: str | None


class MentalStateListResponse(BaseModel):
    """Response with mental state history."""
    mental_states: list[MentalStateItem]
    total: int


__all__ = [
    "GoalDependencyItem",
    "GoalItem",
    "CreateGoalRequest",
    "UpdateGoalRequest",
    "GoalListResponse",
    "MentalStateItem",
    "MentalStateListResponse",
]