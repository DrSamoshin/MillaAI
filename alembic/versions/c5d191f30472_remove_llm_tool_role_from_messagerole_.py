"""remove llm_tool role from messagerole enum"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c5d191f30472'
down_revision: str | Sequence[str] | None = '8c01ec45a490'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # First, update any existing llm_tool messages to assistant
    op.execute("UPDATE messages SET role = 'assistant' WHERE role = 'llm_tool'")

    # Remove llm_tool from the enum
    op.execute("ALTER TYPE messagerole RENAME TO messagerole_old")
    op.execute("CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system')")
    op.execute("ALTER TABLE messages ALTER COLUMN role TYPE messagerole USING role::text::messagerole")
    op.execute("DROP TYPE messagerole_old")


def downgrade() -> None:
    # Recreate the old enum with llm_tool
    op.execute("ALTER TYPE messagerole RENAME TO messagerole_old")
    op.execute("CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system', 'llm_tool')")
    op.execute("ALTER TABLE messages ALTER COLUMN role TYPE messagerole USING role::text::messagerole")
    op.execute("DROP TYPE messagerole_old")
