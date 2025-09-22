"""add goals tasks mental_states tables"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '8ac6cb41090a'
down_revision: str | Sequence[str] | None = '1c09ed14a98b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Note: Using simple string columns instead of enums for simplicity

    # Create goals table
    op.create_table(
        'goals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('goal_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('due_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reminder_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create mental_states table
    op.create_table(
        'mental_states',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('chat_id', sa.UUID(), nullable=False),
        sa.Column('mood', sa.VARCHAR(50), nullable=True),
        sa.Column('energy_level', sa.Integer(), nullable=True),
        sa.Column('confidence_level', sa.Integer(), nullable=True),
        sa.Column('detected_emotions', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('analysis_source', sa.VARCHAR(20), nullable=False, server_default='summary'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    op.create_index('ix_goals_chat_id', 'goals', ['chat_id'])
    op.create_index('ix_goals_status', 'goals', ['status'])
    op.create_index('ix_goals_deadline', 'goals', ['deadline'])

    op.create_index('ix_tasks_goal_id', 'tasks', ['goal_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])
    op.create_index('ix_tasks_reminder_at', 'tasks', ['reminder_at'])

    op.create_index('ix_mental_states_user_id', 'mental_states', ['user_id'])
    op.create_index('ix_mental_states_chat_id', 'mental_states', ['chat_id'])
    op.create_index('ix_mental_states_created_at', 'mental_states', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_mental_states_created_at')
    op.drop_index('ix_mental_states_chat_id')
    op.drop_index('ix_mental_states_user_id')
    op.drop_index('ix_tasks_reminder_at')
    op.drop_index('ix_tasks_due_date')
    op.drop_index('ix_tasks_status')
    op.drop_index('ix_tasks_goal_id')
    op.drop_index('ix_goals_deadline')
    op.drop_index('ix_goals_status')
    op.drop_index('ix_goals_chat_id')
    op.drop_index('ix_goals_user_id')

    # Drop tables
    op.drop_table('mental_states')
    op.drop_table('tasks')
    op.drop_table('goals')

    # Note: No enums to drop since we used simple strings
