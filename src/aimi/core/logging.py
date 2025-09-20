"""Logging configuration utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from logging.config import dictConfig
from typing import Any

from pythonjsonlogger import jsonlogger

from .config import AppSettings


class AimiJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with opinionated default fields."""

    def add_fields(self, log_record: dict[str, Any], record, message_dict) -> None:  # type: ignore[override]
        """Populate standard fields (timestamp, level, logger)."""

        super().add_fields(log_record, record, message_dict)

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        level = record.levelname
        logger_name = record.name
        message = log_record.get("message", record.getMessage())

        extra_items = {
            key: value
            for key, value in log_record.items()
            if key not in {"level", "timestamp", "logger", "message"}
        }

        log_record.clear()
        log_record.update(
            {
                "level": level,
                "timestamp": timestamp,
                "logger": logger_name,
                "message": message,
            }
        )
        log_record.update(extra_items)


def build_logging_config(settings: AppSettings) -> dict[str, Any]:
    """Return dictConfig structure for JSON logging."""

    level = settings.log_level.upper()
    access_handlers: list[str] = ["default"] if settings.uvicorn_access_log else []

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "class": "aimi.core.logging.AimiJsonFormatter",
                "fmt": "%(message)s",
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            }
        },
        "loggers": {
            "": {"handlers": ["default"], "level": level},
            "uvicorn.error": {
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": access_handlers,
                "level": level,
                "propagate": False,
            },
        },
    }


def configure_logging(settings: AppSettings) -> None:
    """Configure logging using the provided settings."""

    dictConfig(build_logging_config(settings))


__all__ = ["AimiJsonFormatter", "build_logging_config", "configure_logging"]
