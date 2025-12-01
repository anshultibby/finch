"""update strategies v2 clean model

Revision ID: 014
Revises: 013
Create Date: 2024-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update strategies_v2 table
    op.add_column('strategies_v2', sa.Column('candidate_source', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('strategies_v2', sa.Column('screening_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('strategies_v2', sa.Column('management_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Migrate old 'rules' to 'screening_rules'
    op.execute("UPDATE strategies_v2 SET screening_rules = rules WHERE screening_rules IS NULL")
    op.execute("UPDATE strategies_v2 SET candidate_source = '{\"type\": \"universe\", \"universe\": \"sp500\"}' WHERE candidate_source IS NULL")
    
    # Now make them non-nullable
    op.alter_column('strategies_v2', 'screening_rules', nullable=False)
    op.alter_column('strategies_v2', 'candidate_source', nullable=False)
    
    # Drop old columns
    op.drop_column('strategies_v2', 'rules')
    op.drop_column('strategies_v2', 'stock_universe')
    
    # Create strategy_positions table
    op.create_table(
        'strategy_positions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('shares', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_decision_id', sa.String(), nullable=False),
        sa.Column('current_price', sa.Float(), default=0.0),
        sa.Column('current_value', sa.Float(), default=0.0),
        sa.Column('pnl', sa.Float(), default=0.0),
        sa.Column('pnl_pct', sa.Float(), default=0.0),
        sa.Column('days_held', sa.Integer(), default=0),
        sa.Column('exit_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_decision_id', sa.String(), nullable=True),
        sa.Column('is_open', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategy_positions_strategy_id', 'strategy_positions', ['strategy_id'])
    op.create_index('ix_strategy_positions_user_id', 'strategy_positions', ['user_id'])
    op.create_index('ix_strategy_positions_ticker', 'strategy_positions', ['ticker'])
    op.create_index('ix_strategy_positions_is_open', 'strategy_positions', ['is_open'])
    
    # Create strategy_budgets table
    op.create_table(
        'strategy_budgets',
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('total_budget', sa.Float(), default=1000.0),
        sa.Column('cash_available', sa.Float(), nullable=False),
        sa.Column('position_value', sa.Float(), default=0.0),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('strategy_id')
    )
    op.create_index('ix_strategy_budgets_user_id', 'strategy_budgets', ['user_id'])
    
    # Update strategy_decisions table
    op.add_column('strategy_decisions', sa.Column('position_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Drop old forward_tests table (not needed with new model)
    op.drop_table('forward_tests')


def downgrade() -> None:
    # Reverse all changes
    op.add_column('strategies_v2', sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('strategies_v2', sa.Column('stock_universe', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    op.execute("UPDATE strategies_v2 SET rules = screening_rules")
    
    op.drop_column('strategies_v2', 'candidate_source')
    op.drop_column('strategies_v2', 'screening_rules')
    op.drop_column('strategies_v2', 'management_rules')
    
    op.drop_table('strategy_budgets')
    op.drop_table('strategy_positions')
    
    op.drop_column('strategy_decisions', 'position_data')

