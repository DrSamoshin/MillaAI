"""Custom exception hierarchy for the Aimi backend."""

from __future__ import annotations

from typing import Any, Optional


class BaseAppError(Exception):
    """Base exception carrying API-friendly metadata."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int = 500,
        details: Optional[Any] = None,
    ) -> None:
        if not code:
            raise ValueError("Error code must be a non-empty string.")
        if not message:
            raise ValueError("Error message must be a non-empty string.")

        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details

        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - human-readable helper
        base = f"{self.code}: {self.message} (status={self.http_status})"
        if self.details is not None:
            return f"{base} details={self.details!r}"
        return base


class DomainError(BaseAppError):
    """Raised when domain validation or business rules fail."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int = 400,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=http_status,
            details=details,
        )


class ServiceError(BaseAppError):
    """Raised when an external service interaction fails."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int = 502,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=http_status,
            details=details,
        )


class RepositoryError(BaseAppError):
    """Raised when data persistence or retrieval fails."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int = 503,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            http_status=http_status,
            details=details,
        )


__all__ = ["BaseAppError", "DomainError", "ServiceError", "RepositoryError"]
