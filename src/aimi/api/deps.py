"""FastAPI dependency providers."""

from __future__ import annotations

from functools import lru_cache

from aimi.core.config import get_settings
from aimi.core.errors import ServiceError
from aimi.llm.client import LLMClient
from aimi.llm.openai import OpenAIChatClient
from aimi.repositories.messages import InMemoryMessageRepository
from aimi.services.conversation import ConversationService


@lru_cache
def get_message_repository() -> InMemoryMessageRepository:
    """Return a singleton in-memory repository placeholder."""

    return InMemoryMessageRepository()


@lru_cache
def get_llm_client() -> LLMClient:
    """Instantiate and cache the OpenAI chat client."""

    settings = get_settings()
    base_url = settings.openai_base_url or None
    if settings.openai_api_key is None and base_url is None:
        raise ServiceError(
            code="llm.configuration_missing",
            message="OpenAI credentials are not configured.",
        )

    return OpenAIChatClient(
        api_key=settings.openai_api_key,
        base_url=base_url,
        model=settings.openai_model,
    )


def get_conversation_service() -> ConversationService:
    """Provide a conversation service wired with repositories and LLM."""

    return ConversationService(
        message_repository=get_message_repository(),
        llm_client=get_llm_client(),
    )


__all__: list[str] = [
    "get_conversation_service",
    "get_llm_client",
    "get_message_repository",
]
