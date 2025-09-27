"""Schemas for user profile endpoints."""

from __future__ import annotations

from datetime import time
from typing import Optional

from pydantic import BaseModel


class GoalStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]


class EventStats(BaseModel):
    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]


class UserStatsResponse(BaseModel):
    goals: GoalStats
    events: EventStats


class UserAvailabilitySettings(BaseModel):
    available_from: Optional[time] = None
    available_to: Optional[time] = None
    notification_enabled: bool = True


class UpdateUserAvailabilityRequest(BaseModel):
    available_from: Optional[time] = None
    available_to: Optional[time] = None
    notification_enabled: Optional[bool] = None


__all__ = [
    "GoalStats",
    "EventStats",
    "UserStatsResponse",
    "UserAvailabilitySettings",
    "UpdateUserAvailabilityRequest",
]
