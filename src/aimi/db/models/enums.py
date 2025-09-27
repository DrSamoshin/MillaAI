"""Database enums for all models."""

from __future__ import annotations

import enum


class UserRole(enum.Enum):
    """Available user roles."""
    USER = "user"
    ADMIN = "admin"


class MessageRole(enum.Enum):
    """Available message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class GoalStatus(enum.Enum):
    """Goal status enumeration."""
    TODO = "todo"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELED = "canceled"


class GoalCategory(enum.Enum):
    """Goal category enumeration."""
    CAREER = "career"
    HEALTH = "health"
    LEARNING = "learning"
    FINANCE = "finance"
    PERSONAL = "personal"
    SOCIAL = "social"
    CREATIVE = "creative"



class EventType(enum.Enum):
    """Event type enumeration."""
    WORK = "work"
    MEETING = "meeting"
    BREAK = "break"
    FOCUS_TIME = "focus_time"
    DEADLINE = "deadline"
    PERSONAL = "personal"


class EventStatus(enum.Enum):
    """Event status enumeration."""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"


class DependencyType(enum.Enum):
    """Dependency type enumeration."""
    REQUIRES = "requires"        # A requires B to be completed first
    ENABLES = "enables"          # A enables B to start
    BLOCKS = "blocks"            # A blocks B from starting
    RELATED = "related"          # A is related to B (weak connection)
    PARALLEL = "parallel"        # A and B can run in parallel


class NotificationType(enum.Enum):
    """Notification type enumeration."""
    MOTIVATION = "motivation"           # "Давай поработаем над целью X"
    REST_SUGGESTION = "rest_suggestion" # "Ты много работал, время отдохнуть"
    PROGRESS_CHECK = "progress_check"   # "Как дела с изучением Python?"
    GOAL_REMINDER = "goal_reminder"     # "Напоминаю о дедлайне"
    CELEBRATION = "celebration"         # "Поздравляю с завершением задачи!"
    PLANNING = "planning"               # "Время спланировать неделю"


class NotificationStatus(enum.Enum):
    """Notification status enumeration."""
    PENDING = "pending"     # Ожидает отправки
    SENT = "sent"          # Отправлено в чат
    DISMISSED = "dismissed" # Пользователь проигнорировал


class MentalStateMood(enum.Enum):
    """Mental state mood enumeration."""
    GREAT = "great"         # Отлично
    GOOD = "good"           # Хорошо
    NEUTRAL = "neutral"     # Нейтрально
    TIRED = "tired"         # Устал
    STRESSED = "stressed"   # Напряжен


__all__ = [
    "UserRole",
    "MessageRole",
    "GoalStatus",
    "GoalCategory",
    "EventType",
    "EventStatus",
    "DependencyType",
    "NotificationType",
    "NotificationStatus",
    "MentalStateMood",
]