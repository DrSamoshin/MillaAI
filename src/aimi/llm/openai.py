"""Async OpenAI chat client implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import AsyncOpenAI, OpenAIError

from aimi.core.errors import ServiceError

from .client import ChatMessage, LLMClient


class OpenAIChatClient(LLMClient):
    """LLM client backed by OpenAI's chat completion API."""

    def __init__(
        self, *, api_key: str | None, base_url: str | None, model: str
    ) -> None:
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: list[ChatMessage]) -> str:
        if not messages:
            raise ServiceError(
                code="llm.missing_messages",
                message="No messages provided for generation.",
            )

        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,
            )
        except OpenAIError as exc:  # pragma: no cover - depends on external service
            raise ServiceError(
                code="llm.request_failed",
                message="Failed to obtain response from OpenAI.",
                details={"error": str(exc)},
            ) from exc

        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if content is None:
            raise ServiceError(
                code="llm.empty_response",
                message="OpenAI returned an empty response.",
            )

        if isinstance(content, list):
            text = "".join(_extract_text(segment) for segment in content)
        else:
            text = content

        if not text:
            raise ServiceError(
                code="llm.empty_response",
                message="OpenAI returned an empty response.",
            )

        return text

    async def generate_with_tools(
        self,
        messages: List[ChatMessage],
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate response with function calling support."""
        if not messages:
            raise ServiceError(
                code="llm.missing_messages",
                message="No messages provided for generation.",
            )

        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                tools=tools,
                tool_choice="auto" if tools else None,
            )
        except OpenAIError as exc:  # pragma: no cover - depends on external service
            raise ServiceError(
                code="llm.request_failed",
                message="Failed to obtain response from OpenAI.",
                details={"error": str(exc)},
            ) from exc

        choice = response.choices[0]
        message = choice.message

        result = {
            "content": message.content or "",
            "tool_calls": []
        }

        # Process tool calls if any
        if message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                if tool_call.type == "function":
                    function = tool_call.function
                    try:
                        arguments = json.loads(function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    tool_calls.append({
                        "id": tool_call.id,
                        "name": function.name,
                        "arguments": arguments
                    })

            result["tool_calls"] = tool_calls

        return result


def _extract_text(segment: Any) -> str:
    """Extract concatenated text from a message segment."""

    if isinstance(segment, str):
        return segment
    if isinstance(segment, dict):
        return str(segment.get("text") or "")
    return ""


__all__: list[str] = ["OpenAIChatClient"]
