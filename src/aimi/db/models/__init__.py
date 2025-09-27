"""ORM model package."""

from __future__ import annotations

# Import all models and enums
from .chat import Chat
from .device import Device
from .message import Message
from .enums import (
    DependencyType,
    EventStatus,
    EventType,
    GoalCategory,
    GoalStatus,
    MessageRole,
    NotificationStatus,
    NotificationType,
    MentalStateMood,
    UserRole,
)
from .event import Event
from .goal import Goal, GoalDependency
from .mental_state import MentalState
from .notification import Notification
from .user import User
from .goal_embedding import GoalEmbedding

__all__ = [
    # User domain
    "User",
    "UserRole",
    # Chat domain
    "Chat",
    "Message",
    "MessageRole",
    "Device",
    # Goals domain
    "Goal",
    "GoalDependency",
    "GoalEmbedding",
    # Events domain
    "Event",
    # Analytics domain
    "MentalState",
    # Notifications domain
    "Notification",
    # Enums
    "GoalStatus",
    "GoalCategory",
    "EventType",
    "EventStatus",
    "NotificationType",
    "NotificationStatus",
    "DependencyType",
    "MentalStateMood",
]
