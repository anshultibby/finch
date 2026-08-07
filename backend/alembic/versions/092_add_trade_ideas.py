"""trade_ideas — catalyst ideas scored independently of execution

The day-trading journal only records trades that were taken, so it can't answer
whether the ideas were any good. This table records every proposal with the
reference price at that moment and scores it on its horizon, traded or not.

Revision ID: 092
Revises: 091
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '092'
down_revision = '091'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'trade_ideas',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False, server_default='long'),
        sa.Column('catalyst_type', sa.String(), nullable=False),
        sa.Column('catalyst_summary', sa.Text(), nullable=False),
        sa.Column('thesis', sa.Text(), nullable=False),
        sa.Column('bear_case', sa.Text(), nullable=True),
        sa.Column('sources', postgresql.JSONB(), nullable=True),

        sa.Column('entry_ref', sa.Float(), nullable=False),
        sa.Column('stop', sa.Float(), nullable=False),
        sa.Column('target', sa.Float(), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('conviction', sa.Integer(), nullable=False, server_default='3'),

        sa.Column('status', sa.String(), nullable=False, server_default='proposed'),
        sa.Column('execution_mode', sa.String(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('outcome', sa.String(), nullable=False, server_default='pending'),
        sa.Column('scored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('return_pct', sa.Float(), nullable=True),
        sa.Column('benchmark_return_pct', sa.Float(), nullable=True),
        sa.Column('r_multiple', sa.Float(), nullable=True),
    )
    op.create_index('ix_trade_ideas_user_id', 'trade_ideas', ['user_id'])
    op.create_index('ix_trade_ideas_symbol', 'trade_ideas', ['symbol'])
    op.create_index('ix_trade_ideas_catalyst_type', 'trade_ideas', ['catalyst_type'])
    op.create_index('ix_trade_ideas_status', 'trade_ideas', ['status'])
    op.create_index('ix_trade_ideas_outcome', 'trade_ideas', ['outcome'])
    # The scoring sweep's hot path: open ideas due for a look.
    op.create_index('ix_trade_ideas_open', 'trade_ideas', ['outcome', 'created_at'])


def downgrade():
    op.drop_table('trade_ideas')
