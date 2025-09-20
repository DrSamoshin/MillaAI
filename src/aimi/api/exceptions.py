"""Exception handlers for FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from aimi.core.errors import BaseAppError

from .schemas import ErrorInfo, ErrorResponse

logger = logging.getLogger(__name__)


def _to_json_response(status_code: int, *, error: ErrorInfo) -> JSONResponse:
    response = ErrorResponse(error=error)
    return JSONResponse(status_code=status_code, content=response.model_dump())


async def handle_app_error(request: Request, exc: BaseAppError) -> JSONResponse:
    level = logging.ERROR if exc.http_status >= 500 else logging.WARNING
    logger.log(level, "app_error", extra={"code": exc.code, "details": exc.details})

    error = ErrorInfo(code=exc.code, message=exc.message, details=exc.details)
    return _to_json_response(exc.http_status, error=error)


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    status_code = exc.status_code
    level = logging.ERROR if status_code >= 500 else logging.WARNING
    logger.log(
        level, "http_exception", extra={"status": status_code, "detail": exc.detail}
    )

    error = ErrorInfo(
        code=f"http.{status_code}",
        message=str(exc.detail) if exc.detail else "HTTP error",
        details=None,
    )
    return _to_json_response(status_code, error=error)


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("validation_error", extra={"errors": exc.errors()})
    error = ErrorInfo(
        code="validation.request",
        message="Invalid request payload",
        details=exc.errors(),
    )
    return _to_json_response(422, error=error)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception")
    error = ErrorInfo(
        code="internal.server_error",
        message="Internal server error",
        details=None,
    )
    return _to_json_response(500, error=error)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach custom exception handlers to the FastAPI application."""

    app.add_exception_handler(BaseAppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)


__all__ = ["register_exception_handlers"]
