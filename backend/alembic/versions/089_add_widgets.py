"""widgets — declarative financial dashboard cards (agent-generated)

One row per widget: JSONB spec (tiles + refresh) plus row-level metadata and
publish/clone state. See docs/widgets/spec.md and models/widget.py.

Revision ID: 089
Revises: 088
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '089'
down_revision = '088'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'widgets',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('emoji', sa.String(), nullable=True),
        sa.Column('tags', JSONB(), nullable=True),
        sa.Column('spec', JSONB(), nullable=False),
        sa.Column('visibility', sa.String(), nullable=False, server_default='private'),  # private | public
        sa.Column('slug', sa.String(), nullable=True),
        sa.Column('cloned_from', sa.String(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clone_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_widgets_user_id', 'widgets', ['user_id'])
    op.create_index('ix_widgets_slug', 'widgets', ['slug'], unique=True)
    # Gallery query: public widgets ordered by recency / popularity.
    op.create_index('ix_widgets_visibility_created', 'widgets', ['visibility', 'created_at'])


def downgrade():
    op.drop_index('ix_widgets_visibility_created', table_name='widgets')
    op.drop_index('ix_widgets_slug', table_name='widgets')
    op.drop_index('ix_widgets_user_id', table_name='widgets')
    op.drop_table('widgets')
