"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from aimi.api.v1.schemas import HealthPayload, SuccessResponse

router = APIRouter()


@router.get("/health/", tags=["system"], response_model=SuccessResponse[HealthPayload])
async def health_check(request: Request) -> SuccessResponse[HealthPayload]:
    payload = HealthPayload(version=request.app.version or "0.0.0")
    return SuccessResponse(data=payload)
