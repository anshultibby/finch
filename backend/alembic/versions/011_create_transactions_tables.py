"""Create transactions, portfolio_snapshots, trade_analytics, and transaction_sync_jobs tables

Revision ID: 011
Revises: 010
Create Date: 2024-11-30

MVP Phase 1: Trade Analyzer - Core transaction and analytics tables
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create transactions table - flexible JSON schema
    op.create_table(
        'transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('account_id', sa.String(), nullable=False, index=True),
        
        # Key fields for indexing/filtering
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('transaction_type', sa.String(20), nullable=False),  # BUY, SELL, DIVIDEND, FEE, etc.
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('external_id', sa.String(), nullable=True),  # SnapTrade ID for deduplication
        
        # All transaction data stored in JSONB for flexibility
        sa.Column('data', JSONB, nullable=False),
        
        # Tracking
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for transactions
    op.create_index('idx_user_transactions', 'transactions', ['user_id', sa.text('transaction_date DESC')])
    op.create_index('idx_symbol_transactions', 'transactions', ['symbol', sa.text('transaction_date DESC')])
    op.create_index('idx_user_symbol', 'transactions', ['user_id', 'symbol'])
    op.create_index('idx_external_id', 'transactions', ['user_id', 'external_id'], unique=True)
    
    # JSONB GIN index for flexible queries
    op.execute("CREATE INDEX idx_transactions_data ON transactions USING GIN (data)")
    
    # Create transaction_sync_jobs table - flexible JSON schema
    op.create_table(
        'transaction_sync_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False),  # pending, running, completed, failed
        
        # Job data stored in JSONB
        sa.Column('data', JSONB, nullable=False),
        
        # Timing
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('idx_user_sync_jobs', 'transaction_sync_jobs', ['user_id', sa.text('created_at DESC')])
    
    # Create portfolio_snapshots table - flexible JSON schema
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False, index=True),
        
        # All snapshot data stored in JSONB
        sa.Column('data', JSONB, nullable=False),
        
        # Tracking
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_user_snapshots', 'portfolio_snapshots', ['user_id', sa.text('snapshot_date DESC')])
    op.create_index('idx_unique_user_date', 'portfolio_snapshots', ['user_id', 'snapshot_date'], unique=True)
    
    # Create trade_analytics table - flexible JSON schema
    op.create_table(
        'trade_analytics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('exit_date', sa.DateTime(timezone=True), nullable=False, index=True),
        
        # All analytics data stored in JSONB
        sa.Column('data', JSONB, nullable=False),
        
        # Tracking
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('idx_user_analytics', 'trade_analytics', ['user_id', sa.text('exit_date DESC')])
    op.create_index('idx_symbol_analytics', 'trade_analytics', ['symbol', sa.text('exit_date DESC')])
    
    # JSONB GIN index for flexible queries (e.g., filtering by trade_grade)
    op.execute("CREATE INDEX idx_trade_analytics_data ON trade_analytics USING GIN (data)")


def downgrade() -> None:
    op.drop_table('trade_analytics')
    op.drop_table('portfolio_snapshots')
    op.drop_table('transaction_sync_jobs')
    op.drop_table('transactions')

