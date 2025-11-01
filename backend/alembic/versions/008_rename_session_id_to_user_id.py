"""rename session_id to user_id

Revision ID: 008
Revises: 007
Create Date: 2024-11-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename session_id column to user_id in snaptrade_users table for clarity.
    This column stores the Supabase user ID (OAuth user identifier).
    """
    # Rename the column
    op.alter_column('snaptrade_users', 'session_id', new_column_name='user_id')
    
    # Note: Indexes and constraints are automatically updated by PostgreSQL
    # The primary key and index on this column will retain their functionality


def downgrade() -> None:
    """
    Revert user_id back to session_id
    """
    op.alter_column('snaptrade_users', 'user_id', new_column_name='session_id')

