#!/usr/bin/env bash
set -euo pipefail

MODE=${1:-dev}
if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
  echo "Usage: $0 [dev|prod]"
  exit 1
fi

uv run python main.py --mode "$MODE"
