"""Add strategy_files table; strategies own their code directly

Strategies no longer reference ChatFile IDs. Each strategy has its own
file rows in this table, owned by strategy_id (not chat_id).

Revision ID: 031
Revises: 030
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strategy_files',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_strategy_files_strategy_id', 'strategy_files', ['strategy_id'])


def downgrade() -> None:
    op.drop_index('ix_strategy_files_strategy_id', table_name='strategy_files')
    op.drop_table('strategy_files')
