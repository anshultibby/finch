"""drop old strategy tables

Revision ID: 017
Revises: 016
Create Date: 2025-12-03 12:00:00.000000

Drop the old V1 strategy tables (trading_strategies, strategy_backtests, 
strategy_signals, strategy_performance) as we've fully migrated to V2 strategies.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old strategy tables
    
    # Drop strategy_performance (has FK to trading_strategies)
    op.drop_index('ix_strategy_performance_id', table_name='strategy_performance', if_exists=True)
    op.drop_index('idx_performance_user_id', table_name='strategy_performance', if_exists=True)
    op.drop_index('idx_performance_strategy_id', table_name='strategy_performance', if_exists=True)
    op.drop_table('strategy_performance', if_exists=True)
    
    # Drop strategy_signals (has FK to trading_strategies)
    op.drop_index('ix_strategy_signals_signal_id', table_name='strategy_signals', if_exists=True)
    op.drop_index('idx_signals_generated_at', table_name='strategy_signals', if_exists=True)
    op.drop_index('idx_signals_ticker', table_name='strategy_signals', if_exists=True)
    op.drop_index('idx_signals_strategy_id', table_name='strategy_signals', if_exists=True)
    op.drop_table('strategy_signals', if_exists=True)
    
    # Drop strategy_backtests (has FK to trading_strategies)
    op.drop_index('ix_strategy_backtests_backtest_id', table_name='strategy_backtests', if_exists=True)
    op.drop_index('idx_backtests_strategy_id', table_name='strategy_backtests', if_exists=True)
    op.drop_table('strategy_backtests', if_exists=True)
    
    # Drop trading_strategies (main table)
    op.drop_index('ix_trading_strategies_id', table_name='trading_strategies', if_exists=True)
    op.drop_index('idx_strategies_user_id', table_name='trading_strategies', if_exists=True)
    op.drop_table('trading_strategies', if_exists=True)


def downgrade():
    # Recreate tables if needed (for rollback)
    
    # Trading strategies table
    op.create_table(
        'trading_strategies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('natural_language_input', sa.Text(), nullable=False),
        sa.Column('strategy_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_strategies_user_id', 'trading_strategies', ['user_id'])
    op.create_index('ix_trading_strategies_id', 'trading_strategies', ['id'])
    
    # Strategy backtests table
    op.create_table(
        'strategy_backtests',
        sa.Column('backtest_id', sa.String(36), nullable=False),
        sa.Column('strategy_id', sa.String(36), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('backtest_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('backtest_id')
    )
    op.create_index('idx_backtests_strategy_id', 'strategy_backtests', ['strategy_id'])
    op.create_index('ix_strategy_backtests_backtest_id', 'strategy_backtests', ['backtest_id'])
    
    # Strategy signals table
    op.create_table(
        'strategy_signals',
        sa.Column('signal_id', sa.String(36), nullable=False),
        sa.Column('strategy_id', sa.String(36), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('signal_type', sa.String(10), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('price_at_signal', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('data_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_acted', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('outcome', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('signal_id')
    )
    op.create_index('idx_signals_strategy_id', 'strategy_signals', ['strategy_id'])
    op.create_index('idx_signals_ticker', 'strategy_signals', ['ticker'])
    op.create_index('idx_signals_generated_at', 'strategy_signals', ['generated_at'])
    op.create_index('ix_strategy_signals_signal_id', 'strategy_signals', ['signal_id'])
    
    # Strategy performance table
    op.create_table(
        'strategy_performance',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('strategy_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('signals_generated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('signals_acted_on', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actual_trades', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actual_wins', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actual_losses', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actual_return_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('hypothetical_trades', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('hypothetical_return_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_signal_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id')
    )
    op.create_index('idx_performance_strategy_id', 'strategy_performance', ['strategy_id'])
    op.create_index('idx_performance_user_id', 'strategy_performance', ['user_id'])
    op.create_index('ix_strategy_performance_id', 'strategy_performance', ['id'])

