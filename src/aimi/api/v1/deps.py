"""FastAPI dependency providers."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from aimi.core.config import get_settings
from aimi.core.errors import ServiceError
from aimi.core.redis import get_redis_client
from aimi.llm.client import LLMClient
from aimi.llm.openai import OpenAIChatClient
from aimi.memory.cache.session import SessionCache
from aimi.repositories.messages import InMemoryMessageRepository
from aimi.db.models import User
from aimi.repositories.users import UserRepository
from aimi.services.conversation import ConversationService
from aimi.services.auth import AuthService
from aimi.db.session import get_db_session


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


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(get_settings())


@lru_cache
def get_session_cache() -> SessionCache:
    """Instantiate the Redis-backed session cache."""

    settings = get_settings()
    return SessionCache(
        get_redis_client(),
        ttl_seconds=settings.session_cache_ttl,
        max_messages=settings.session_cache_max_messages,
    )


@lru_cache
def get_conversation_service() -> ConversationService:
    """Provide a conversation service wired with repositories and LLM."""

    return ConversationService(
        message_repository=get_message_repository(),
        llm_client=get_llm_client(),
        session_cache=get_session_cache(),
    )


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    token = credentials.credentials.strip()

    try:
        user_id = service.parse_access_token(token)
    except Exception as exc:  # pragma: no cover - invalid token path
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


__all__: list[str] = [
    "get_conversation_service",
    "get_llm_client",
    "get_message_repository",
    "get_session_cache",
    "get_db_session",
    "get_auth_service",
    "get_current_user",
]
