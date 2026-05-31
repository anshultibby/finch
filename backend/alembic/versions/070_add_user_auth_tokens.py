"""Add user_auth_tokens (stored refresh token for scheduled jobs).

Revision ID: 070
Revises: 069
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


revision = '070'
down_revision = '069'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_auth_tokens',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_index('ix_user_auth_tokens_user_id', 'user_auth_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_auth_tokens_user_id', table_name='user_auth_tokens')
    op.drop_table('user_auth_tokens')
