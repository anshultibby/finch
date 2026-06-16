"""add casparser_connections table for Indian demat holdings via CDSL OTP

Revision ID: 083
Revises: 082
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '083'
down_revision = '082'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'casparser_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('pan_encrypted', sa.String(), nullable=False),
        sa.Column('bo_id', sa.String(), nullable=False),
        sa.Column('dob_encrypted', sa.String(), nullable=False),
        sa.Column('investor_name', sa.String(), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('holdings_cache', JSONB, nullable=True),
        sa.Column('holdings_fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_casparser_connections_user_id', 'casparser_connections', ['user_id'], unique=True)


def downgrade():
    op.drop_index('ix_casparser_connections_user_id', table_name='casparser_connections')
    op.drop_table('casparser_connections')
