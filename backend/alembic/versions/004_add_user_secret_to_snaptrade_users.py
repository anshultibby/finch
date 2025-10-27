"""add user secret to snaptrade_users

Revision ID: 004
Revises: 003
Create Date: 2025-10-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add snaptrade_user_secret column to snaptrade_users table"""
    op.add_column('snaptrade_users', sa.Column('snaptrade_user_secret', sa.Text(), nullable=True))
    
    # After migration, any existing rows without a secret will need to reconnect
    # This is OK since they'd lose their session on server restart anyway


def downgrade() -> None:
    """Remove snaptrade_user_secret column"""
    op.drop_column('snaptrade_users', 'snaptrade_user_secret')

