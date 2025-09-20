"""create users table"""

from __future__ import annotations

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202409201630"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("apple_id", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'UTC'"),
        ),
        sa.Column(
            "locale",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'en_US'"),
        ),
        sa.Column(
            "profile",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_apple_id", "users", ["apple_id"])
    op.create_index("ix_users_created_at", "users", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_constraint("uq_users_apple_id", "users", type_="unique")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")
