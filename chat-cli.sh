#!/usr/bin/env bash
set -euo pipefail

uv run python -m cli.chat "$@"
