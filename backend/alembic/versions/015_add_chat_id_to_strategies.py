"""Add chat_id to strategy tables

Revision ID: 015
Revises: 014
Create Date: 2025-12-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Add chat_id to strategies_v2
    op.add_column('strategies_v2', sa.Column('chat_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_strategies_v2_chat_id'), 'strategies_v2', ['chat_id'], unique=False)
    
    # Add chat_id to strategy_positions
    op.add_column('strategy_positions', sa.Column('chat_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_strategy_positions_chat_id'), 'strategy_positions', ['chat_id'], unique=False)
    
    # Add chat_id to strategy_budgets
    op.add_column('strategy_budgets', sa.Column('chat_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_strategy_budgets_chat_id'), 'strategy_budgets', ['chat_id'], unique=False)
    
    # Add chat_id to strategy_decisions
    op.add_column('strategy_decisions', sa.Column('chat_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_strategy_decisions_chat_id'), 'strategy_decisions', ['chat_id'], unique=False)


def downgrade():
    # Remove indexes and columns
    op.drop_index(op.f('ix_strategy_decisions_chat_id'), table_name='strategy_decisions')
    op.drop_column('strategy_decisions', 'chat_id')
    
    op.drop_index(op.f('ix_strategy_budgets_chat_id'), table_name='strategy_budgets')
    op.drop_column('strategy_budgets', 'chat_id')
    
    op.drop_index(op.f('ix_strategy_positions_chat_id'), table_name='strategy_positions')
    op.drop_column('strategy_positions', 'chat_id')
    
    op.drop_index(op.f('ix_strategies_v2_chat_id'), table_name='strategies_v2')
    op.drop_column('strategies_v2', 'chat_id')

