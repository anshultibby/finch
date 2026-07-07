"""user_activity — when the user last opened the app

One row per user, touched by high-traffic authed endpoints (the home recap
fetch). Gates credit-spending automations: the heartbeat pauses for users
inactive >72h and resumes the moment they come back.

Revision ID: 087
Revises: 086
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = '087'
down_revision = '086'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_activity',
        sa.Column('user_id', sa.String(), primary_key=True),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('user_activity')
