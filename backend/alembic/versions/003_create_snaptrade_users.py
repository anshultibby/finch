"""create snaptrade_users table

Revision ID: 003
Revises: 002
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create snaptrade_users table to replace robinhood_sessions"""
    op.create_table(
        'snaptrade_users',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('snaptrade_user_id', sa.String(), nullable=False),
        sa.Column('connected_account_ids', sa.Text(), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('brokerage_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
    )
    op.create_index(op.f('ix_snaptrade_users_session_id'), 'snaptrade_users', ['session_id'], unique=False)
    op.create_index(op.f('ix_snaptrade_users_snaptrade_user_id'), 'snaptrade_users', ['snaptrade_user_id'], unique=True)


def downgrade() -> None:
    """Drop snaptrade_users table"""
    op.drop_index(op.f('ix_snaptrade_users_snaptrade_user_id'), table_name='snaptrade_users')
    op.drop_index(op.f('ix_snaptrade_users_session_id'), table_name='snaptrade_users')
    op.drop_table('snaptrade_users')

