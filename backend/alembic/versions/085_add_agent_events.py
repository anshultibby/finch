"""agent_events ledger + agent_activity_seen

The agent-activity ledger: an append-only record of everything the agent does
on the user's behalf (automation runs, market alerts, trade proposals and
decisions, morning briefs). Powers the in-app activity feed and the
"while you were gone" recap. agent_activity_seen tracks when the user last
viewed the recap so it can aggregate only what's new.

Revision ID: 085
Revises: 084
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '085'
down_revision = '084'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        # job_run | alert | trade_proposed | trade_decided | brief
        sa.Column('event_type', sa.String(), nullable=False),
        # automation | monitor | trade | brief
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        # symbol, chat_id, job_id, pending_trade_id, pct, status, ...
        sa.Column('data', JSONB(), nullable=True),
        # dollar stake of the event in cents, when computable (e.g. order size)
        sa.Column('value_cents', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_agent_events_user_created', 'agent_events',
                    ['user_id', 'created_at'])

    op.create_table(
        'agent_activity_seen',
        sa.Column('user_id', sa.String(), primary_key=True),
        sa.Column('seen_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('agent_activity_seen')
    op.drop_index('ix_agent_events_user_created', table_name='agent_events')
    op.drop_table('agent_events')
