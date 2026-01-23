"""Create strategies and strategy_executions tables

Revision ID: 023
Revises: 022
Create Date: 2025-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Strategies table - minimal indexed columns, flexible JSONB for the rest
    op.create_table(
        'strategies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        
        # Core identity (indexed for queries)
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved', sa.Boolean(), nullable=False, server_default='false'),
        
        # Everything else in JSONB for flexibility:
        # - description, source_chat_id
        # - file_ids, entrypoint
        # - schedule, schedule_description
        # - risk_limits
        # - stats (total_runs, successful_runs, last_run_at, last_run_status, last_run_summary)
        # - approved_at
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategies_user_id', 'strategies', ['user_id'])
    op.create_index('ix_strategies_enabled', 'strategies', ['enabled'])
    
    # Strategy executions table - audit log
    op.create_table(
        'strategy_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        
        # Indexed for queries
        sa.Column('status', sa.String(), nullable=False),  # 'running', 'success', 'failed'
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        
        # Everything else in JSONB:
        # - trigger ('scheduled', 'manual', 'dry_run')
        # - completed_at
        # - result, error, logs, summary
        # - actions taken
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE')
    )
    op.create_index('ix_strategy_executions_strategy_id', 'strategy_executions', ['strategy_id'])
    op.create_index('ix_strategy_executions_user_id', 'strategy_executions', ['user_id'])
    op.create_index('ix_strategy_executions_started_at', 'strategy_executions', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_strategy_executions_started_at', table_name='strategy_executions')
    op.drop_index('ix_strategy_executions_user_id', table_name='strategy_executions')
    op.drop_index('ix_strategy_executions_strategy_id', table_name='strategy_executions')
    op.drop_table('strategy_executions')
    
    op.drop_index('ix_strategies_enabled', table_name='strategies')
    op.drop_index('ix_strategies_user_id', table_name='strategies')
    op.drop_table('strategies')
