"""Generate JWT access/refresh tokens for a given user id."""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aimi.core.config import get_settings
from aimi.core.security import create_access_token, create_refresh_token


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate JWT tokens")
    parser.add_argument("user_id", nargs="?", help="User UUID")
    return parser.parse_args(argv)


def _resolve_uuid(raw: str) -> str:
    try:
        return str(uuid.UUID(raw))
    except ValueError as exc:  # pragma: no cover - CLI parsing
        raise SystemExit(f"Invalid UUID: {raw}") from exc


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])

    if args.user_id:
        user_uuid = _resolve_uuid(args.user_id)
    else:
        entered = input("User UUID: ").strip()
        if not entered:
            raise SystemExit("UUID is required")
        user_uuid = _resolve_uuid(entered)

    settings = get_settings()
    access = create_access_token(subject=user_uuid, settings=settings)
    refresh = create_refresh_token(subject=user_uuid, settings=settings)

    print("Access Token\n", access)
    print("\nRefresh Token\n", refresh)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
