"""Conversation orchestrator for LLM interactions with tools."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aimi.llm.client import ChatMessage, LLMClient
from aimi.llm.prompts import SYSTEM_PROMPT, CONVERSATION_STARTERS
from aimi.llm.tools import LLMToolRegistry

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """Orchestrates LLM conversations with tool calling support."""

    def __init__(
        self,
        db_session: AsyncSession,
        llm_client: LLMClient,
        user_id: UUID,
        chat_id: UUID,
    ):
        self.db = db_session
        self.llm_client = llm_client
        self.user_id = user_id
        self.chat_id = chat_id

        # Initialize tool registry
        self.tool_registry = LLMToolRegistry(db_session, user_id, chat_id)

    async def generate_response(
        self,
        messages: List[ChatMessage],
        user_message: str,
    ) -> Dict[str, Any]:
        """Generate LLM response with tool calling support."""
        try:
            # Build enhanced context with user state and active goals
            context = await self._build_enhanced_context(messages, user_message)

            # Check if LLM client supports function calling
            if hasattr(self.llm_client, 'generate_with_tools'):
                # Use function calling if supported
                response = await self._generate_with_tools(context)
            else:
                # Fallback to regular generation
                response = await self._generate_with_analysis(context)

            return {
                "content": response["content"],
                "tool_calls": response.get("tool_calls", []),
                "tool_results": response.get("tool_results", []),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error in conversation orchestration: {e}")
            return {
                "content": "I encountered an error while processing your request. Please try again.",
                "tool_calls": [],
                "tool_results": [],
                "status": "error",
                "error": str(e)
            }

    async def _build_enhanced_context(
        self,
        messages: List[ChatMessage],
        user_message: str,
    ) -> List[ChatMessage]:
        """Build enhanced conversation context with user state."""
        # Build system prompt (without goals context to avoid async issues)
        system_content = SYSTEM_PROMPT
        system_content += "\n\nYou can help users create and organize their goals, manage events, and track their mental state."

        # Create enhanced context
        enhanced_context = [
            ChatMessage(role="system", content=system_content)
        ]

        # Add conversation history (limit to recent messages to avoid token limits)
        recent_messages = messages[-20:] if len(messages) > 20 else messages
        enhanced_context.extend(recent_messages)

        # Add current user message
        enhanced_context.append(ChatMessage(role="user", content=user_message))

        return enhanced_context

    def _format_goals_summary(self, goals: List[Dict[str, Any]]) -> str:
        """Format goals summary for system context."""
        if not goals:
            return "No active goals."

        summary_parts = []
        for goal in goals[:5]:  # Limit to top 5 goals to avoid long context
            goal_info = f"• {goal['title']} (Priority: {goal['priority']}"

            if goal.get('deadline'):
                goal_info += f", Deadline: {goal['deadline']}"

            task_count = len(goal.get('tasks', []))
            completed_tasks = len([t for t in goal.get('tasks', []) if t['status'] == 'completed'])

            if task_count > 0:
                goal_info += f", Tasks: {completed_tasks}/{task_count} completed"

            goal_info += ")"

            if goal.get('description'):
                goal_info += f"\n  Description: {goal['description'][:100]}..."

            summary_parts.append(goal_info)

        return "\n".join(summary_parts)

    async def _generate_with_tools(self, context: List[ChatMessage]) -> Dict[str, Any]:
        """Generate response with function calling support."""
        # Get available tools
        tool_schemas = self.tool_registry.get_tool_schemas()

        # Generate response with tools
        response = await self.llm_client.generate_with_tools(
            messages=context,
            tools=tool_schemas,
        )

        result = {
            "content": response.get("content", ""),
            "tool_calls": response.get("tool_calls", []),
            "tool_results": []
        }

        # Process tool calls if any
        if response.get("tool_calls"):
            tool_results = await self.tool_registry.process_function_calls(
                response["tool_calls"]
            )
            result["tool_results"] = tool_results

            # Generate follow-up response incorporating tool results
            if tool_results:
                followup_context = context + [
                    ChatMessage(
                        role="assistant",
                        content=response.get("content", "") + f"\n\nTool results: {json.dumps(tool_results, indent=2)}"
                    ),
                    ChatMessage(
                        role="user",
                        content="Please provide a natural response based on the tool results above."
                    )
                ]

                followup_response = await self.llm_client.generate(followup_context)
                result["content"] = followup_response

        return result

    async def _generate_with_analysis(self, context: List[ChatMessage]) -> Dict[str, Any]:
        """Generate response with goal/task analysis for non-function-calling models."""
        # First, generate regular response
        regular_response = await self.llm_client.generate(context)

        # Analyze the conversation for potential goals/tasks
        analysis_results = await self._analyze_for_entities(
            context[-1].content,  # User message
            regular_response
        )

        return {
            "content": regular_response,
            "tool_calls": [],
            "tool_results": analysis_results
        }

    async def _analyze_for_entities(
        self,
        user_message: str,
        assistant_response: str,
    ) -> List[Dict[str, Any]]:
        """Analyze conversation for potential goals, tasks, or events."""
        try:
            # Use a simple analysis approach
            analysis_prompt = [
                ChatMessage(
                    role="system",
                    content="""You are an intent analyzer. Look at this conversation and determine if the user is expressing:
1. A new goal they want to achieve
2. A task they need to complete
3. An event they want to schedule

Respond with JSON containing suggestions for entities to create:
{
  "suggestions": [
    {
      "type": "goal",
      "title": "goal title",
      "description": "description",
      "confidence": 0.8,
      "reason": "why you think this is a goal"
    }
  ]
}

Only suggest entities if you're confident (>0.7) they represent clear intentions."""
                ),
                ChatMessage(
                    role="user",
                    content=f"User said: {user_message}\nAssistant replied: {assistant_response}"
                )
            ]

            analysis_result = await self.llm_client.generate(analysis_prompt)

            try:
                suggestions = json.loads(analysis_result)
                return [{"function": "analysis", "result": suggestions}]
            except json.JSONDecodeError:
                return []

        except Exception as e:
            logger.error(f"Error in entity analysis: {e}")
            return []

    async def suggest_goal_connections_after_creation(self, new_goal_id: str) -> List[str]:
        """Proactively suggest connections for a newly created goal."""
        try:
            # Get the new goal details
            active_goals = await self.tool_registry.goal_tools.get_active_goals()

            if active_goals.get("error"):
                return []

            goals = active_goals.get("goals", [])
            new_goal = None
            existing_goals = []

            for goal in goals:
                if goal["goal_id"] == new_goal_id:
                    new_goal = goal
                else:
                    existing_goals.append(goal)

            if not new_goal or not existing_goals:
                return []

            # Analyze potential connections
            connection_analysis = await self.tool_registry.datetime_tools.find_potential_goal_connections(
                new_goal_title=new_goal["title"],
                existing_goals=existing_goals
            )

            if connection_analysis.get("error"):
                return []

            # Generate proactive suggestions based on analysis framework
            suggestions = []

            # Check for skill/knowledge overlap
            for existing_goal in existing_goals:
                if self._has_potential_connection(new_goal, existing_goal):
                    suggestions.append(
                        f"I notice '{new_goal['title']}' might relate to your existing goal '{existing_goal['title']}'. "
                        f"Should I create a connection between them?"
                    )

            return suggestions[:2]  # Limit to 2 suggestions to avoid overwhelming

        except Exception as e:
            logger.error(f"Error suggesting goal connections: {e}")
            return []

    def _has_potential_connection(self, goal1: Dict[str, Any], goal2: Dict[str, Any]) -> bool:
        """Simple heuristic to detect potential goal connections."""
        # Check category match
        if goal1.get("category") == goal2.get("category"):
            return True

        # Check for common keywords in titles/descriptions
        goal1_text = f"{goal1['title']} {goal1.get('description', '')}".lower()
        goal2_text = f"{goal2['title']} {goal2.get('description', '')}".lower()

        # Simple keyword overlap detection
        common_keywords = ["learn", "improve", "develop", "build", "create", "master", "skill", "knowledge"]

        for keyword in common_keywords:
            if keyword in goal1_text and keyword in goal2_text:
                return True

        return False

    async def suggest_task_breakdown_after_goal_creation(self, goal_id: str, goal_title: str) -> List[str]:
        """Proactively suggest task breakdown for a newly created goal."""
        try:
            # Get breakdown suggestions
            breakdown_suggestions = await self.tool_registry.datetime_tools.suggest_goal_breakdown(
                goal_title=goal_title,
                goal_description=None
            )

            if breakdown_suggestions.get("error"):
                return []

            suggestions = breakdown_suggestions.get("suggestions", {})
            task_examples = suggestions.get("task_examples", [])

            if not task_examples:
                return []

            # Create proactive suggestions
            return [
                f"Great! I've created the goal '{goal_title}'. Let me suggest breaking it down into these tasks:",
                f"• {task_examples[0]}",
                f"• {task_examples[1]}" if len(task_examples) > 1 else "",
                f"• {task_examples[2]}" if len(task_examples) > 2 else "",
                "Should I create these tasks for you?"
            ]

        except Exception as e:
            logger.error(f"Error suggesting task breakdown: {e}")
            return []

    async def get_conversation_starter(self) -> str:
        """Get a context-aware conversation starter."""
        try:
            # Get active goals for personalized greeting
            active_goals = await self.tool_registry.goal_tools.get_active_goals()

            if active_goals.get("goals") and not active_goals.get("error"):
                goals = active_goals["goals"][:3]  # Limit to top 3

                goals_list = []
                for goal in goals:
                    task_count = len(goal.get("tasks", []))
                    completed_tasks = len([t for t in goal.get("tasks", []) if t["status"] == "completed"])

                    goal_summary = f"• {goal['title']}"
                    if task_count > 0:
                        goal_summary += f" ({completed_tasks}/{task_count} tasks completed)"
                    else:
                        goal_summary += " (no tasks yet)"

                    goals_list.append(goal_summary)

                return f"""Hi! I see you have these active goals:

{chr(10).join(goals_list)}

What would you like to work on today? I can help you:
- Break down goals into actionable tasks
- Create new goals or modify existing ones
- Schedule time for your priorities
- Track your progress"""

            else:
                return """Hello! I'm here to help you set and achieve your goals.

I can assist you with:
- Creating and organizing your objectives
- Breaking large goals into manageable tasks
- Setting up schedules and reminders
- Tracking your progress

What would you like to work towards?"""

        except Exception as e:
            logger.error(f"Error generating conversation starter: {e}")
            return "Hello! How can I help you achieve your goals today?"