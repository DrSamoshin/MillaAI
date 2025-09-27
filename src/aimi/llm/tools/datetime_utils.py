"""DateTime utilities tools for LLM."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DateTimeTools:
    """Tools for LLM to work with dates and time."""

    def __init__(self):
        pass

    async def get_current_time(self) -> Dict[str, Any]:
        """Get current date and time for reference.

        Returns current UTC time with date components for LLM to calculate
        relative dates like "in 3 months", "next week", etc.
        """
        try:
            now = datetime.utcnow()

            return {
                "current_datetime": now.isoformat() + "Z",
                "current_date": now.date().isoformat(),
                "current_time": now.time().isoformat(),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "weekday": now.weekday() + 1,  # 1=Monday, 7=Sunday
                "weekday_name": now.strftime("%A"),
                "month_name": now.strftime("%B"),
                "formatted": now.strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        except Exception as e:
            logger.error(f"Failed to get current time: {e}")
            return {"error": f"Failed to get current time: {str(e)}"}

    async def suggest_goal_breakdown(self, goal_title: str, goal_description: str | None = None) -> Dict[str, Any]:
        """Suggest task breakdown for a goal.

        This is a helper tool to provide LLM with structured approach
        to breaking down goals into actionable tasks.
        """
        try:
            # This is a template/guidance for LLM, not actual AI generation
            suggestions = {
                "breakdown_approach": [
                    "Identify the main phases or stages of this goal",
                    "Break each phase into specific, actionable tasks",
                    "Consider prerequisites and dependencies between tasks",
                    "Estimate time needed for each task",
                    "Identify potential obstacles or challenges"
                ],
                "task_examples": [
                    "Research and gather information",
                    "Plan and prepare resources",
                    "Execute core activities",
                    "Review and iterate",
                    "Complete and evaluate"
                ],
                "questions_to_ask": [
                    "What specific skills or knowledge are needed?",
                    "What resources or tools are required?",
                    "Are there any dependencies on other goals?",
                    "What would be a realistic timeline?",
                    "How will progress be measured?"
                ]
            }

            return {
                "goal_title": goal_title,
                "goal_description": goal_description,
                "suggestions": suggestions,
                "note": "These are general guidelines. The specific tasks should be customized based on the goal's nature and user's situation."
            }

        except Exception as e:
            logger.error(f"Failed to suggest goal breakdown: {e}")
            return {"error": f"Failed to suggest goal breakdown: {str(e)}"}

    async def find_potential_goal_connections(self, new_goal_title: str, existing_goals: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze potential connections between a new goal and existing goals.

        This helps LLM identify relationships and suggest linking goals.
        """
        try:
            if not existing_goals:
                return {"connections": [], "note": "No existing goals to connect with"}

            # Provide analysis framework for LLM
            analysis_framework = {
                "connection_types": {
                    "prerequisite": "One goal must be completed before the other can start",
                    "supportive": "Goals that help each other when worked on together",
                    "competitive": "Goals that compete for the same time/resources",
                    "sequential": "Goals that naturally follow one after another",
                    "parallel": "Goals that can be worked on simultaneously"
                },
                "factors_to_consider": [
                    "Skills overlap between goals",
                    "Time and resource requirements",
                    "Knowledge or experience gained from one goal helping another",
                    "Physical or logistical dependencies",
                    "Motivation and energy synergies"
                ],
                "existing_goals": [
                    {"title": goal["title"], "description": goal.get("description", "")}
                    for goal in existing_goals
                ]
            }

            return {
                "new_goal": new_goal_title,
                "analysis_framework": analysis_framework,
                "instruction": "Use this framework to identify potential connections and suggest appropriate dependency relationships"
            }

        except Exception as e:
            logger.error(f"Failed to analyze goal connections: {e}")
            return {"error": f"Failed to analyze goal connections: {str(e)}"}