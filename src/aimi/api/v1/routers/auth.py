"""Authentication endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from aimi.api.v1.deps import get_auth_service, get_uow_dependency
from aimi.db.session import UnitOfWork
from aimi.api.v1.schemas import SuccessResponse
from aimi.api.v1.schemas.auth import (
    AppleSignInRequest,
    AuthResponsePayload,
    RefreshRequest,
    RefreshResponsePayload,
    TokenPayload,
    UserPayload,
)
from aimi.core.config import get_settings
from aimi.services.auth import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/apple-signin/", response_model=SuccessResponse[AuthResponsePayload])
async def apple_sign_in(
    payload: AppleSignInRequest,
    uow: UnitOfWork = Depends(get_uow_dependency),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[AuthResponsePayload]:
    # identity_token verification TBD when Apple credentials added
    logger.info(
        "apple_sign_in_request",
        extra={
            "apple_id": payload.apple_id,
            "email": payload.email,
            "user_name": payload.name,
            "has_identity_token": bool(payload.identity_token),
        },
    )

    result = await service.apple_sign_in(
        uow=uow,
        apple_id=payload.apple_id,
        name=payload.name,
        email=payload.email,
    )

    settings = get_settings()
    response = AuthResponsePayload(
        user=UserPayload(
            id=str(result.user_id),
            email=result.email,
            name=result.display_name,
            is_active=result.is_active,
            role=result.role,
            created_at=result.created_at,
        ),
        token=TokenPayload(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token,
            expires_in=settings.jwt_access_expires_seconds,
        ),
    )
    return SuccessResponse(data=response)


@router.post("/refresh/", response_model=SuccessResponse[RefreshResponsePayload])
async def refresh_tokens(
    payload: RefreshRequest,
    uow: UnitOfWork = Depends(get_uow_dependency),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[RefreshResponsePayload]:
    token = payload.refresh_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required",
        )
    logger.info("refresh_token_requested")

    try:
        result = await service.refresh_tokens(token=token, uow=uow)
    except Exception as exc:  # pragma: no cover - error path
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    settings = get_settings()
    response = RefreshResponsePayload(
        user=UserPayload(
            id=str(result.user_id),
            email=result.email,
            name=result.display_name,
            is_active=result.is_active,
            role=result.role,
            created_at=result.created_at,
        ),
        token=TokenPayload(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token,
            expires_in=settings.jwt_access_expires_seconds,
        ),
    )
    return SuccessResponse(data=response)
