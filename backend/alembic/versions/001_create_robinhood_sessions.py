"""Create robinhood_sessions table

Revision ID: 001
Revises: 
Create Date: 2025-10-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create robinhood_sessions table"""
    op.create_table(
        'robinhood_sessions',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_token', sa.String(), nullable=True),
        sa.Column('logged_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_robinhood_sessions_session_id'), 'robinhood_sessions', ['session_id'], unique=False)


def downgrade() -> None:
    """Drop robinhood_sessions table"""
    op.drop_index(op.f('ix_robinhood_sessions_session_id'), table_name='robinhood_sessions')
    op.drop_table('robinhood_sessions')

