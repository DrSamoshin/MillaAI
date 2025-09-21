"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Base settings for the Aimi backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AIMI_",
    )

    api_host: Annotated[str, Field(default="0.0.0.0", description="FastAPI host")]
    api_port: Annotated[int, Field(default=8000, description="FastAPI port")]
    log_level: Annotated[
        str, Field(default="INFO", description="Application log level")
    ]
    uvicorn_access_log: Annotated[
        bool, Field(default=True, description="Enable uvicorn access log")
    ]

    database_url: Annotated[
        str, Field(default="postgresql+asyncpg://aimi:aimi@localhost:5432/aimi")
    ]
    redis_url: Annotated[str, Field(default="redis://localhost:6379/0")]
    session_cache_ttl: Annotated[
        int,
        Field(
            default=600,
            description="Redis session cache TTL in seconds",
            gt=0,
        ),
    ]
    session_cache_max_messages: Annotated[
        int,
        Field(
            default=30,
            description="Maximum number of messages to keep per session",
            gt=0,
        ),
    ]

    openai_api_key: Annotated[Optional[str], Field(default=None)]
    openai_base_url: Annotated[Optional[str], Field(default=None)]
    openai_model: Annotated[
        str, Field(default="gpt-4o-mini", description="Default OpenAI chat model")
    ]

    jwt_secret: Annotated[
        str,
        Field(
            default="change-me",
            description="Secret key used to sign JWT tokens",
        ),
    ]
    jwt_algorithm: Annotated[
        str,
        Field(default="HS256", description="Algorithm for JWT signing"),
    ]
    jwt_access_expires_seconds: Annotated[
        int,
        Field(
            default=900,
            description="Access token lifetime in seconds",
            gt=0,
        ),
    ]
    jwt_refresh_expires_seconds: Annotated[
        int,
        Field(
            default=2592000,
            description="Refresh token lifetime in seconds",
            gt=0,
        ),
    ]


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()


__all__ = ["AppSettings", "get_settings"]
