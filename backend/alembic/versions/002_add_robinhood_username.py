"""Add robinhood_username column for session lookup

Revision ID: 002
Revises: 001
Create Date: 2025-10-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add robinhood_username column and index"""
    # Add column (nullable for now to handle existing rows)
    op.add_column('robinhood_sessions', 
        sa.Column('robinhood_username', sa.String(), nullable=True)
    )
    
    # Create index for faster lookups
    op.create_index(
        op.f('ix_robinhood_sessions_robinhood_username'), 
        'robinhood_sessions', 
        ['robinhood_username'], 
        unique=False
    )


def downgrade() -> None:
    """Remove robinhood_username column and index"""
    op.drop_index(op.f('ix_robinhood_sessions_robinhood_username'), table_name='robinhood_sessions')
    op.drop_column('robinhood_sessions', 'robinhood_username')

