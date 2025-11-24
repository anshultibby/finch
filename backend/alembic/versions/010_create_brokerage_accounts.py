"""Create brokerage_accounts table

Revision ID: 010
Revises: 009
Create Date: 2024-11-24

Track individual brokerage account connections with full metadata
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create brokerage_accounts table
    op.create_table(
        'brokerage_accounts',
        sa.Column('id', sa.String(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('account_id', sa.String(), nullable=False, index=True),
        sa.Column('broker_id', sa.String(), nullable=False),  # e.g., "ROBINHOOD", "ALPACA"
        sa.Column('broker_name', sa.String(), nullable=False),  # e.g., "Robinhood", "Alpaca"
        sa.Column('account_name', sa.String(), nullable=True),  # User-friendly name
        sa.Column('account_number', sa.String(), nullable=True),  # Masked account number
        sa.Column('account_type', sa.String(), nullable=True),  # e.g., "TFSA", "IRA", "margin"
        sa.Column('balance', sa.Float(), nullable=True),
        sa.Column('account_metadata', JSONB, nullable=True),  # Additional account metadata
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create composite index for user_id + account_id (unique constraint)
    op.create_index(
        'idx_brokerage_accounts_user_account',
        'brokerage_accounts',
        ['user_id', 'account_id'],
        unique=True
    )
    
    # Create index for broker lookups
    op.create_index(
        'idx_brokerage_accounts_broker',
        'brokerage_accounts',
        ['broker_id']
    )


def downgrade() -> None:
    op.drop_table('brokerage_accounts')

