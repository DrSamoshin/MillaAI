"""Administrative endpoints."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command  # type: ignore[attr-defined]
from alembic.config import Config
from fastapi import APIRouter

from aimi.api.v1.schemas import SuccessResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _run_migrations() -> None:
    root = Path(__file__).resolve().parents[4]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(cfg, "head")


@router.post("/migrate/", response_model=SuccessResponse[dict[str, str]])
async def run_migrations() -> SuccessResponse[dict[str, str]]:
    """Apply latest Alembic migrations (admin only)."""

    await asyncio.to_thread(_run_migrations)
    return SuccessResponse(data={"message": "Migrations applied"})


__all__: list[str] = ["router"]
