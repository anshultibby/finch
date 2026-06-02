"""Add robinhood_connections (per-user OAuth connection to Robinhood agentic MCP).

Revision ID: 073
Revises: 072
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa


revision = '073'
down_revision = '072'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'robinhood_connections',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=True),
        sa.Column('encrypted_access_token', sa.Text(), nullable=True),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_connected', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_index('ix_robinhood_connections_user_id', 'robinhood_connections', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_robinhood_connections_user_id', table_name='robinhood_connections')
    op.drop_table('robinhood_connections')
