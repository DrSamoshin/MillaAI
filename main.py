from __future__ import annotations

import uvicorn
from argparse import ArgumentParser
import sys
from pathlib import Path

from dotenv import load_dotenv
from src.aimi.core.config import get_settings
from src.aimi.core.logging import build_logging_config

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> str:
    parser = ArgumentParser(description="Run Aimi backend")
    parser.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default="dev",
        help="Run mode: dev enables reload, prod runs without reload",
    )
    args = parser.parse_args()
    return args.mode


def main() -> None:
    mode = parse_args()
    if mode == "dev":
        load_dotenv()

    settings = get_settings()
    log_config = build_logging_config(settings)
    uvicorn.run(
        "aimi.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=(mode == "dev"),
        log_config=log_config,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
