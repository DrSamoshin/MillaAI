"""LLM Tools Registry for managing available functions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List
from uuid import UUID

from aimi.db.session import UnitOfWork
from aimi.db.models.enums import GoalStatus, GoalCategory, DependencyType
from .goals import GoalTools
from .events import EventTools
from .notifications import NotificationTools
from .mental_states import MentalStateTools
from .helpers import GoalAnalysisHelpers

logger = logging.getLogger(__name__)


class LLMToolRegistry:
    """Registry for LLM-callable tools with function calling support."""

    def __init__(self, uow: UnitOfWork, user_id: UUID, chat_id: UUID):
        self.uow = uow
        self.user_id = user_id
        self.chat_id = chat_id

        # Initialize tool instances
        self.goal_tools = GoalTools(uow, user_id, chat_id)
        self.event_tools = EventTools(uow, user_id, chat_id)
        self.notification_tools = NotificationTools(uow, user_id, chat_id)
        self.mental_state_tools = MentalStateTools(uow, user_id, chat_id)
        self.goal_analysis_helpers = GoalAnalysisHelpers()

        # Register all available tools
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._functions: Dict[str, Callable] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all available tools with their schemas."""

        # Goal management tools
        self._register_tool(
            name="create_goal",
            function=self.goal_tools.create_goal,
            schema={
                "type": "function",
                "function": {
                    "name": "create_goal",
                    "description": "Create a new goal for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Clear, specific goal title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of what the user wants to achieve"
                            },
                            "priority": {
                                "type": "integer",
                                "description": "Priority level from 1 (low) to 5 (high)",
                                "minimum": 1,
                                "maximum": 5
                            },
                            "category": {
                                "type": "string",
                                "description": "Goal category: career (work/professional), health (fitness/wellness), learning (education/skills), finance (money/savings), personal (self-improvement), social (relationships), creative (art/hobbies)",
                                "enum": [e.value for e in GoalCategory]
                            },
                            "deadline": {
                                "type": "string",
                                "description": "Target completion date in YYYY-MM-DD format",
                                "format": "date"
                            },
                            "estimated_duration_days": {
                                "type": "integer",
                                "description": "Estimated number of days to complete",
                                "minimum": 1
                            },
                            "difficulty_level": {
                                "type": "integer",
                                "description": "Difficulty level from 0 (very easy) to 10 (very hard)",
                                "minimum": 0,
                                "maximum": 10
                            },
                            "motivation": {
                                "type": "string",
                                "description": "Why this goal is important to the user"
                            },
                            "success_criteria": {
                                "type": "string",
                                "description": "How to measure success for this goal"
                            }
                        },
                        "required": ["title", "category"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_status",
            function=self.goal_tools.update_goal_status,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_status",
                    "description": "Update a goal's status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "New goal status: todo (not started), blocked (waiting for dependencies), done (completed), canceled (abandoned)",
                                "enum": [e.value for e in GoalStatus]
                            }
                        },
                        "required": ["goal_id", "status"]
                    }
                }
            }
        )

        self._register_tool(
            name="create_goal_dependency",
            function=self.goal_tools.create_goal_dependency,
            schema={
                "type": "function",
                "function": {
                    "name": "create_goal_dependency",
                    "description": "Create dependency relationship between two goals",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "parent_goal_id": {
                                "type": "string",
                                "description": "UUID of the parent goal (must be obtained from get_user_goals or get_available_goals response)"
                            },
                            "dependent_goal_id": {
                                "type": "string",
                                "description": "UUID of the dependent goal (must be obtained from get_user_goals or get_available_goals response)"
                            },
                            "dependency_type": {
                                "type": "string",
                                "description": "Type of dependency relationship:\n- requires: Dependent goal cannot start until parent is completed\n- enables: Parent goal completion unlocks the dependent goal\n- blocks: Goals are mutually exclusive\n- related: Goals are related but no strict dependency\n- parallel: Goals can be worked on simultaneously",
                                "enum": [e.value for e in DependencyType]
                            },
                            "strength": {
                                "type": "integer",
                                "description": "Dependency strength from 1 (weak) to 5 (strong)",
                                "minimum": 1,
                                "maximum": 5
                            }
                        },
                        "required": ["parent_goal_id", "dependent_goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="get_user_goals",
            function=self.goal_tools.get_user_goals,
            schema={
                "type": "function",
                "function": {
                    "name": "get_user_goals",
                    "description": "Get goals for the user, optionally filtered by status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status",
                                "enum": ["todo", "done", "canceled"]
                            },
                            "include_dependencies": {
                                "type": "boolean",
                                "description": "Include dependency information",
                                "default": True
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="get_available_goals",
            function=self.goal_tools.get_available_goals,
            schema={
                "type": "function",
                "function": {
                    "name": "get_available_goals",
                    "description": "Get goals that are available for work (no blocked dependencies)",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        )

        self._register_tool(
            name="get_goal_by_id",
            function=self.goal_tools.get_goal_by_id,
            schema={
                "type": "function",
                "function": {
                    "name": "get_goal_by_id",
                    "description": "Get a specific goal by its UUID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "UUID of the goal to retrieve"
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        # Goal editing tools
        self._register_tool(
            name="update_goal_title",
            function=self.goal_tools.update_goal_title,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_title",
                    "description": "Update goal title",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "title": {
                                "type": "string",
                                "description": "New goal title"
                            }
                        },
                        "required": ["goal_id", "title"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_description",
            function=self.goal_tools.update_goal_description,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_description",
                    "description": "Update goal description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "description": {
                                "type": "string",
                                "description": "New goal description"
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_priority",
            function=self.goal_tools.update_goal_priority,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_priority",
                    "description": "Update goal priority level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "priority": {
                                "type": "integer",
                                "description": "Priority level from 1 (low) to 5 (high)",
                                "minimum": 1,
                                "maximum": 5
                            }
                        },
                        "required": ["goal_id", "priority"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_deadline",
            function=self.goal_tools.update_goal_deadline,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_deadline",
                    "description": "Update goal deadline",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "deadline": {
                                "type": "string",
                                "description": "Target completion date in YYYY-MM-DD format, or null to remove",
                                "format": "date"
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_category",
            function=self.goal_tools.update_goal_category,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_category",
                    "description": "Update goal category",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "category": {
                                "type": "string",
                                "description": "Goal category: career (work/professional), health (fitness/wellness), learning (education/skills), finance (money/savings), personal (self-improvement), social (relationships), creative (art/hobbies)",
                                "enum": [e.value for e in GoalCategory]
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_motivation",
            function=self.goal_tools.update_goal_motivation,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_motivation",
                    "description": "Update goal motivation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "motivation": {
                                "type": "string",
                                "description": "Why this goal is important"
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_success_criteria",
            function=self.goal_tools.update_goal_success_criteria,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_success_criteria",
                    "description": "Update goal success criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "success_criteria": {
                                "type": "string",
                                "description": "How to measure success for this goal"
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_difficulty",
            function=self.goal_tools.update_goal_difficulty,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_difficulty",
                    "description": "Update goal difficulty level",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "difficulty_level": {
                                "type": "integer",
                                "description": "Difficulty level from 0 (very easy) to 10 (very hard)",
                                "minimum": 0,
                                "maximum": 10
                            }
                        },
                        "required": ["goal_id", "difficulty_level"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_goal_duration",
            function=self.goal_tools.update_goal_duration,
            schema={
                "type": "function",
                "function": {
                    "name": "update_goal_duration",
                    "description": "Update goal estimated duration",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal to update"
                            },
                            "estimated_duration_days": {
                                "type": "integer",
                                "description": "Estimated number of days to complete, or null to remove",
                                "minimum": 1
                            }
                        },
                        "required": ["goal_id"]
                    }
                }
            }
        )

        # Event management tools
        self._register_tool(
            name="create_event",
            function=self.event_tools.create_event,
            schema={
                "type": "function",
                "function": {
                    "name": "create_event",
                    "description": "Create a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Event title"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Event start time in ISO format",
                                "format": "date-time"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Event end time in ISO format",
                                "format": "date-time"
                            },
                            "description": {
                                "type": "string",
                                "description": "Event description"
                            },
                            "location": {
                                "type": "string",
                                "description": "Event location"
                            },
                            "event_type": {
                                "type": "string",
                                "description": "Type of event",
                                "enum": ["work", "meeting", "break", "focus_time", "deadline", "personal"]
                            },
                            "goal_id": {
                                "type": "string",
                                "description": "Optional goal ID to link this event to"
                            }
                        },
                        "required": ["title", "start_time", "end_time"]
                    }
                }
            }
        )

        self._register_tool(
            name="link_event_to_goal",
            function=self.event_tools.link_event_to_goal,
            schema={
                "type": "function",
                "function": {
                    "name": "link_event_to_goal",
                    "description": "Connect an event to a goal",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "type": "string",
                                "description": "ID of the event"
                            },
                            "goal_id": {
                                "type": "string",
                                "description": "ID of the goal"
                            }
                        },
                        "required": ["event_id", "goal_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_event_status",
            function=self.event_tools.update_event_status,
            schema={
                "type": "function",
                "function": {
                    "name": "update_event_status",
                    "description": "Update event status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {
                                "type": "string",
                                "description": "ID of the event"
                            },
                            "status": {
                                "type": "string",
                                "description": "New event status",
                                "enum": ["scheduled", "cancelled", "completed", "in_progress"]
                            }
                        },
                        "required": ["event_id", "status"]
                    }
                }
            }
        )

        self._register_tool(
            name="get_upcoming_events",
            function=self.event_tools.get_upcoming_events,
            schema={
                "type": "function",
                "function": {
                    "name": "get_upcoming_events",
                    "description": "Get upcoming events for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of events to return",
                                "default": 10
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="get_user_events",
            function=self.event_tools.get_user_events,
            schema={
                "type": "function",
                "function": {
                    "name": "get_user_events",
                    "description": "Get events for the user with optional filtering",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status",
                                "enum": ["scheduled", "cancelled", "completed", "in_progress"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of events to return"
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="record_mood",
            function=self.mental_state_tools.record_mood,
            schema={
                "type": "function",
                "function": {
                    "name": "record_mood",
                    "description": "Record user's mood and mental state directly (automatic polling)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mood": {
                                "type": "string",
                                "description": "User's mood",
                                "enum": ["great", "good", "neutral", "tired", "stressed"]
                            },
                            "readiness_level": {
                                "type": "integer",
                                "description": "User's readiness level (1-10)",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes about mental state"
                            },
                            "date_str": {
                                "type": "string",
                                "description": "Date for the mood record (ISO format), defaults to today"
                            }
                        },
                        "required": ["mood"]
                    }
                }
            }
        )

        # Notification management tools
        self._register_tool(
            name="create_notification",
            function=self.notification_tools.create_notification,
            schema={
                "type": "function",
                "function": {
                    "name": "create_notification",
                    "description": "Create a scheduled notification",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Notification message content"
                            },
                            "scheduled_for": {
                                "type": "string",
                                "description": "When to send the notification in ISO format",
                                "format": "date-time"
                            },
                            "notification_type": {
                                "type": "string",
                                "description": "Type of notification",
                                "enum": ["reminder", "check_in", "milestone", "deadline", "encouragement"]
                            },
                            "goal_id": {
                                "type": "string",
                                "description": "Optional goal ID for context"
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context data for the notification"
                            }
                        },
                        "required": ["message", "scheduled_for"]
                    }
                }
            }
        )

        self._register_tool(
            name="update_notification_status",
            function=self.notification_tools.update_notification_status,
            schema={
                "type": "function",
                "function": {
                    "name": "update_notification_status",
                    "description": "Update notification status",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "notification_id": {
                                "type": "string",
                                "description": "ID of the notification"
                            },
                            "status": {
                                "type": "string",
                                "description": "New notification status",
                                "enum": ["pending", "sent", "failed", "cancelled"]
                            }
                        },
                        "required": ["notification_id", "status"]
                    }
                }
            }
        )

        self._register_tool(
            name="get_user_notifications",
            function=self.notification_tools.get_user_notifications,
            schema={
                "type": "function",
                "function": {
                    "name": "get_user_notifications",
                    "description": "Get notifications for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status",
                                "enum": ["pending", "sent", "failed", "cancelled"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of notifications to return",
                                "default": 50
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="get_pending_notifications",
            function=self.notification_tools.get_pending_notifications,
            schema={
                "type": "function",
                "function": {
                    "name": "get_pending_notifications",
                    "description": "Get pending notifications ready to be sent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of notifications to return",
                                "default": 10
                            }
                        }
                    }
                }
            }
        )

        # Mental state management tools
        self._register_tool(
            name="create_daily_poll",
            function=self.mental_state_tools.create_daily_poll,
            schema={
                "type": "function",
                "function": {
                    "name": "create_daily_poll",
                    "description": "Create a daily mental state poll",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_str": {
                                "type": "string",
                                "description": "Date for the poll in ISO format (optional, defaults to today)",
                                "format": "date"
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="respond_to_poll",
            function=self.mental_state_tools.respond_to_poll,
            schema={
                "type": "function",
                "function": {
                    "name": "respond_to_poll",
                    "description": "Respond to a mental state poll",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mental_state_id": {
                                "type": "string",
                                "description": "ID of the mental state poll"
                            },
                            "mood": {
                                "type": "string",
                                "description": "User's mood",
                                "enum": ["very_positive", "positive", "neutral", "negative", "very_negative"]
                            },
                            "readiness_level": {
                                "type": "integer",
                                "description": "Readiness level from 1 to 10",
                                "minimum": 1,
                                "maximum": 10
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes about mental state"
                            }
                        },
                        "required": ["mental_state_id"]
                    }
                }
            }
        )

        self._register_tool(
            name="get_user_mental_states",
            function=self.mental_state_tools.get_user_mental_states,
            schema={
                "type": "function",
                "function": {
                    "name": "get_user_mental_states",
                    "description": "Get mental state history for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of records to return",
                                "default": 30
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date for filtering",
                                "format": "date"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date for filtering",
                                "format": "date"
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="get_unanswered_polls",
            function=self.mental_state_tools.get_unanswered_polls,
            schema={
                "type": "function",
                "function": {
                    "name": "get_unanswered_polls",
                    "description": "Get unanswered mental state polls",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of polls to return",
                                "default": 10
                            }
                        }
                    }
                }
            }
        )

        self._register_tool(
            name="get_mood_trends",
            function=self.mental_state_tools.get_mood_trends,
            schema={
                "type": "function",
                "function": {
                    "name": "get_mood_trends",
                    "description": "Get mood trends and analytics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "Number of days to analyze",
                                "default": 30
                            }
                        }
                    }
                }
            }
        )

        # DateTime and utility tools
        self._register_tool(
            name="suggest_goal_breakdown",
            function=self.goal_analysis_helpers.suggest_goal_breakdown,
            schema={
                "type": "function",
                "function": {
                    "name": "suggest_goal_breakdown",
                    "description": "Get structured guidance for breaking down a goal into actionable sub-goals",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal_title": {
                                "type": "string",
                                "description": "The goal title to analyze"
                            },
                            "goal_description": {
                                "type": "string",
                                "description": "Optional detailed description of the goal"
                            }
                        },
                        "required": ["goal_title"]
                    }
                }
            }
        )



    def _register_tool(self, name: str, function: Callable, schema: Dict[str, Any]) -> None:
        """Register a tool with its schema and function."""
        self._tools[name] = schema
        self._functions[name] = function
        logger.debug(f"Registered tool: {name}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM function calling."""
        return list(self._tools.values())

    def get_function_names(self) -> List[str]:
        """Get list of available function names."""
        return list(self._functions.keys())

    async def call_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered function with provided arguments."""
        logger.info(f"Calling function: {function_name} with args: {arguments}")

        if function_name not in self._functions:
            logger.error(f"Unknown function: {function_name}")
            return {"error": f"Unknown function: {function_name}"}

        try:
            function = self._functions[function_name]

            if asyncio.iscoroutinefunction(function):
                result = await function(**arguments)
            else:
                result = function(**arguments)

            logger.info(f"Successfully called {function_name}")
            return result
        except Exception as e:
            error_msg = f"Error calling {function_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    async def process_function_calls(self, function_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple function calls from LLM response."""
        results = []

        for call in function_calls:
            function_name = call.get("name")
            arguments = call.get("arguments", {})

            # Parse arguments if they're a JSON string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    results.append({
                        "function": function_name,
                        "error": "Invalid JSON arguments"
                    })
                    continue

            result = await self.call_function(function_name, arguments)
            results.append({
                "function": function_name,
                "result": result
            })

        return results


__all__ = ["LLMToolRegistry"]