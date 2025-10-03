"""Conversation orchestrator for LLM interactions with tools.

IMPORTANT: Do not use emojis in any user-facing content.
Keep all messages clean and professional without emoji characters.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from aimi.db.models import Message, MessageRole
from aimi.db.session import UnitOfWork
from aimi.llm.client import ChatMessage, LLMClient
from aimi.llm.tools import LLMToolRegistry
from aimi.llm.system_prompt import SystemPromptGenerator

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """Orchestrates LLM conversations with tool calling support."""

    def __init__(
        self,
        uow: UnitOfWork,
        llm_client: LLMClient,
        user_id: UUID,
        chat_id: UUID,
    ):
        self.uow = uow
        self.llm_client = llm_client
        self.user_id = user_id
        self.chat_id = chat_id

        # Initialize tool registry
        self.tool_registry = LLMToolRegistry(uow, user_id, chat_id)

    async def generate_response(
        self,
        history: List[ChatMessage],
    ) -> List[Message]:
        """Generate LLM response with tool calling support, returning Message objects."""
        logger.info(f"[ORCHESTRATOR] Starting generate_response with {len(history)} history messages")
        try:
            # Build complete context with system prompt
            context = await self._build_complete_context(history)
            logger.info(f"[ORCHESTRATOR] Built complete context with {len(context)} messages")

            # Generate response with tools
            logger.info(f"[ORCHESTRATOR] Calling _generate_with_tools...")
            response = await self._generate_with_tools(context)
            logger.info(f"[ORCHESTRATOR] _generate_with_tools returned response with {len(response.get('tool_calls', []))} tool calls")

            messages = []

            # If there were tool calls, add tool message with tool results
            if response.get("tool_calls") and response.get("tool_results"):
                logger.info(f"[ORCHESTRATOR] Tool calls detected - creating tool message")
                tool_message = self._create_tool_message_with_results(
                    response["tool_calls"],
                    response["tool_results"]
                )
                messages.append(tool_message)
                logger.info(f"[ORCHESTRATOR] Tool message created with tool data")

                # Generate second LLM call with tool results context
                logger.info(f"[ORCHESTRATOR] Making second LLM call with tool results...")
                enhanced_context = context + [ChatMessage(role="assistant", content=tool_message.content)]
                final_response = await self.llm_client.generate_with_tools(
                    messages=enhanced_context,
                    tools=[]  # No tools on second call
                )
                logger.info(f"[ORCHESTRATOR] Second LLM call completed")

                assistant_message = self._create_assistant_message(
                    final_response.get("content", "")
                )
                messages.append(assistant_message)
                logger.info(f"[ORCHESTRATOR] Assistant message created from second LLM call")
            else:
                # No tool calls, just return assistant response
                logger.info(f"[ORCHESTRATOR] No tool calls - creating assistant message directly")
                assistant_message = self._create_assistant_message(
                    response.get("content", "")
                )
                messages.append(assistant_message)

            logger.info(f"[ORCHESTRATOR] Returning {len(messages)} messages")
            for i, msg in enumerate(messages):
                logger.info(f"[ORCHESTRATOR] Message {i+1}: role={msg.role}, content_length={len(msg.content)}")
            return messages

        except Exception as e:
            logger.error(f"Error in conversation orchestration: {e}", exc_info=True)
            # Return error as assistant message
            error_message = self._create_assistant_message(
                "I encountered an error while processing your request. Please try again."
            )
            return [error_message]

    async def _build_complete_context(
        self,
        history: List[ChatMessage],
    ) -> List[ChatMessage]:
        """Build complete LLM context with system prompt and history."""
        # Generate system prompt
        prompt_generator = SystemPromptGenerator(self.uow, self.user_id, self.chat_id)
        system_content = await prompt_generator.generate_system_prompt()

        # Build complete context
        context = [
            ChatMessage(role="system", content=system_content)
        ]

        # Add conversation history (includes latest user message)
        context.extend(history)

        return context

    async def _generate_with_tools(self, context: List[ChatMessage]) -> Dict[str, Any]:
        """Generate response with function calling support."""
        # Get available tools
        tool_schemas = self.tool_registry.get_tool_schemas()

        # Log what we're sending to LLM
        logger.info(f"[ORCHESTRATOR] === SENDING TO LLM ===")
        for i, msg in enumerate(context):
            logger.info(f"[ORCHESTRATOR] Message {i+1} (role={msg.role}):")
            logger.info(f"[ORCHESTRATOR] {msg.content}")
            logger.info(f"[ORCHESTRATOR] ---")
        logger.info(f"[ORCHESTRATOR] Tools: {[tool.get('function', {}).get('name', 'unknown') for tool in tool_schemas]}")
        logger.info(f"[ORCHESTRATOR] === END LLM REQUEST ===")

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

            # Extract system messages from tool results and use as assistant response
            system_messages = self._extract_system_messages(tool_results)
            if system_messages:
                # Use tool results as assistant content
                result["content"] = "\n".join(system_messages)

        return result

    def _create_tool_message_with_results(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]]
    ) -> Message:
        """Create tool message with tool calls and results in JSON format."""
        tool_data = {
            "tool_calls": tool_calls,
            "tool_results": tool_results
        }

        message = Message(
            chat_id=self.chat_id,
            role=MessageRole.ASSISTANT.value,
            content=json.dumps(tool_data, indent=2)
        )
        return message

    def _create_assistant_message(self, content: str) -> Message:
        """Create assistant message."""
        message = Message(
            chat_id=self.chat_id,
            role=MessageRole.ASSISTANT.value,
            content=content
        )
        return message

    def _extract_system_messages(self, tool_results: List[Dict[str, Any]]) -> List[str]:
        """Extract system messages from tool results for user feedback."""
        system_messages = []

        for result in tool_results:
            # Check if tool result has success_message
            tool_result_data = result.get("result", {})

            if isinstance(tool_result_data, dict):
                success_msg = tool_result_data.get("success_message")
                if success_msg:
                    system_messages.append(success_msg)
                elif tool_result_data.get("error"):
                    # Show errors as system messages too
                    error_msg = tool_result_data.get("error")
                    system_messages.append(f"Error: {error_msg}")

        return system_messages



__all__ = ["ConversationOrchestrator"]