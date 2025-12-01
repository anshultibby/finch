"""create strategies v2 tables

Revision ID: 013
Revises: 012
Create Date: 2024-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create strategies_v2 table
    op.create_table(
        'strategies_v2',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('stock_universe', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategies_v2_user_id', 'strategies_v2', ['user_id'])
    op.create_index('ix_strategies_v2_is_active', 'strategies_v2', ['is_active'])
    op.create_index('ix_strategies_v2_created_at', 'strategies_v2', ['created_at'])
    
    # Create strategy_decisions table
    op.create_table(
        'strategy_decisions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('rule_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('user_acted', sa.Boolean(), nullable=True, default=False),
        sa.Column('outcome', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_decisions_strategy_id', 'strategy_decisions', ['strategy_id'])
    op.create_index('ix_strategy_decisions_ticker', 'strategy_decisions', ['ticker'])
    op.create_index('ix_strategy_decisions_timestamp', 'strategy_decisions', ['timestamp'])
    
    # Create forward_tests table
    op.create_table(
        'forward_tests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('total_signals', sa.Integer(), nullable=True, default=0),
        sa.Column('signals_acted_on', sa.Integer(), nullable=True, default=0),
        sa.Column('hypothetical_pnl', sa.Float(), nullable=True, default=0.0),
        sa.Column('actual_pnl', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forward_tests_strategy_id', 'forward_tests', ['strategy_id'])
    op.create_index('ix_forward_tests_user_id', 'forward_tests', ['user_id'])
    op.create_index('ix_forward_tests_is_active', 'forward_tests', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_forward_tests_is_active', table_name='forward_tests')
    op.drop_index('ix_forward_tests_user_id', table_name='forward_tests')
    op.drop_index('ix_forward_tests_strategy_id', table_name='forward_tests')
    op.drop_table('forward_tests')
    
    op.drop_index('ix_strategy_decisions_timestamp', table_name='strategy_decisions')
    op.drop_index('ix_strategy_decisions_ticker', table_name='strategy_decisions')
    op.drop_index('ix_strategy_decisions_strategy_id', table_name='strategy_decisions')
    op.drop_table('strategy_decisions')
    
    op.drop_index('ix_strategies_v2_created_at', table_name='strategies_v2')
    op.drop_index('ix_strategies_v2_is_active', table_name='strategies_v2')
    op.drop_index('ix_strategies_v2_user_id', table_name='strategies_v2')
    op.drop_table('strategies_v2')

