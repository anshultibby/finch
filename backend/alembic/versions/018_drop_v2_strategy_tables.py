"""drop v2 strategy tables

Revision ID: 018
Revises: 017
Create Date: 2025-12-03 13:00:00.000000

Drop V2 strategy tables (strategies_v2, strategy_positions, strategy_budgets, 
strategy_decisions) as strategies are no longer needed.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # Drop V2 strategy tables in reverse dependency order
    
    # Drop strategy_decisions (has FK to strategies_v2)
    op.drop_index('ix_strategy_decisions_timestamp', table_name='strategy_decisions', if_exists=True)
    op.drop_index('ix_strategy_decisions_ticker', table_name='strategy_decisions', if_exists=True)
    op.drop_index('ix_strategy_decisions_chat_id', table_name='strategy_decisions', if_exists=True)
    op.drop_index('ix_strategy_decisions_strategy_id', table_name='strategy_decisions', if_exists=True)
    op.drop_index('ix_strategy_decisions_id', table_name='strategy_decisions', if_exists=True)
    op.drop_table('strategy_decisions', if_exists=True)
    
    # Drop strategy_budgets (has FK to strategies_v2)
    op.drop_index('ix_strategy_budgets_chat_id', table_name='strategy_budgets', if_exists=True)
    op.drop_index('ix_strategy_budgets_user_id', table_name='strategy_budgets', if_exists=True)
    op.drop_table('strategy_budgets', if_exists=True)
    
    # Drop strategy_positions (has FK to strategies_v2)
    op.drop_index('ix_strategy_positions_is_open', table_name='strategy_positions', if_exists=True)
    op.drop_index('ix_strategy_positions_ticker', table_name='strategy_positions', if_exists=True)
    op.drop_index('ix_strategy_positions_chat_id', table_name='strategy_positions', if_exists=True)
    op.drop_index('ix_strategy_positions_user_id', table_name='strategy_positions', if_exists=True)
    op.drop_index('ix_strategy_positions_strategy_id', table_name='strategy_positions', if_exists=True)
    op.drop_index('ix_strategy_positions_id', table_name='strategy_positions', if_exists=True)
    op.drop_table('strategy_positions', if_exists=True)
    
    # Drop strategies_v2 (main table)
    op.drop_index('ix_strategies_v2_is_active', table_name='strategies_v2', if_exists=True)
    op.drop_index('ix_strategies_v2_chat_id', table_name='strategies_v2', if_exists=True)
    op.drop_index('ix_strategies_v2_user_id', table_name='strategies_v2', if_exists=True)
    op.drop_index('ix_strategies_v2_id', table_name='strategies_v2', if_exists=True)
    op.drop_table('strategies_v2', if_exists=True)


def downgrade():
    # Recreate V2 tables if needed (for rollback)
    
    # Create strategies_v2
    op.create_table(
        'strategies_v2',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('candidate_source', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('screening_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('management_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategies_v2_id', 'strategies_v2', ['id'])
    op.create_index('ix_strategies_v2_user_id', 'strategies_v2', ['user_id'])
    op.create_index('ix_strategies_v2_chat_id', 'strategies_v2', ['chat_id'])
    op.create_index('ix_strategies_v2_is_active', 'strategies_v2', ['is_active'])
    
    # Create strategy_positions
    op.create_table(
        'strategy_positions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('shares', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_decision_id', sa.String(), nullable=False),
        sa.Column('current_price', sa.Float(), server_default='0.0'),
        sa.Column('current_value', sa.Float(), server_default='0.0'),
        sa.Column('pnl', sa.Float(), server_default='0.0'),
        sa.Column('pnl_pct', sa.Float(), server_default='0.0'),
        sa.Column('days_held', sa.Integer(), server_default='0'),
        sa.Column('exit_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_decision_id', sa.String(), nullable=True),
        sa.Column('is_open', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_positions_id', 'strategy_positions', ['id'])
    op.create_index('ix_strategy_positions_strategy_id', 'strategy_positions', ['strategy_id'])
    op.create_index('ix_strategy_positions_user_id', 'strategy_positions', ['user_id'])
    op.create_index('ix_strategy_positions_chat_id', 'strategy_positions', ['chat_id'])
    op.create_index('ix_strategy_positions_ticker', 'strategy_positions', ['ticker'])
    op.create_index('ix_strategy_positions_is_open', 'strategy_positions', ['is_open'])
    
    # Create strategy_budgets
    op.create_table(
        'strategy_budgets',
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('total_budget', sa.Float(), server_default='1000.0'),
        sa.Column('cash_available', sa.Float(), nullable=False),
        sa.Column('position_value', sa.Float(), server_default='0.0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('strategy_id')
    )
    op.create_index('ix_strategy_budgets_user_id', 'strategy_budgets', ['user_id'])
    op.create_index('ix_strategy_budgets_chat_id', 'strategy_budgets', ['chat_id'])
    
    # Create strategy_decisions
    op.create_table(
        'strategy_decisions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('rule_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('position_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_decisions_id', 'strategy_decisions', ['id'])
    op.create_index('ix_strategy_decisions_strategy_id', 'strategy_decisions', ['strategy_id'])
    op.create_index('ix_strategy_decisions_chat_id', 'strategy_decisions', ['chat_id'])
    op.create_index('ix_strategy_decisions_ticker', 'strategy_decisions', ['ticker'])
    op.create_index('ix_strategy_decisions_timestamp', 'strategy_decisions', ['timestamp'])

