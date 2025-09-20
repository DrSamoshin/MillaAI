from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path

import pytest

# Ensure `src` is on sys.path when running via uv/pytest
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def now() -> datetime:
    return datetime.now(tz=timezone.utc)
