"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Base settings for the Aimi backend."""

    api_host: Annotated[str, Field(default="0.0.0.0", description="FastAPI host")]
    api_port: Annotated[int, Field(default=8000, description="FastAPI port")]
    log_level: Annotated[
        str, Field(default="INFO", description="Application log level")
    ]
    uvicorn_access_log: Annotated[
        bool, Field(default=True, description="Enable uvicorn access log")
    ]

    database_url: Annotated[
        str, Field(default="postgresql://aimi:aimi@localhost:5432/aimi")
    ]
    redis_url: Annotated[str, Field(default="redis://localhost:6379/0")]

    openai_api_key: Annotated[Optional[str], Field(default=None)]
    openai_base_url: Annotated[Optional[str], Field(default=None)]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "AIMI_"


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()


__all__ = ["AppSettings", "get_settings"]
