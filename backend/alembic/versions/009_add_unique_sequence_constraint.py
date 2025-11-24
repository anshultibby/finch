"""add unique constraint on chat_id and sequence

Revision ID: 009
Revises: 008
Create Date: 2025-11-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint on (chat_id, sequence) to prevent duplicate sequence numbers"""
    
    # First, fix any existing duplicates by reassigning sequence numbers
    # This SQL will reassign sequence numbers for each chat in order of timestamp
    connection = op.get_bind()
    
    # Find chats with duplicate sequences
    connection.execute(sa.text("""
        -- Create a temporary table with the correct sequence numbers
        CREATE TEMPORARY TABLE temp_sequences AS
        SELECT 
            id,
            ROW_NUMBER() OVER (PARTITION BY chat_id ORDER BY timestamp, id) - 1 AS new_sequence
        FROM chat_messages;
        
        -- Update the chat_messages table with the corrected sequences
        UPDATE chat_messages
        SET sequence = temp_sequences.new_sequence
        FROM temp_sequences
        WHERE chat_messages.id = temp_sequences.id;
        
        -- Drop the temporary table
        DROP TABLE temp_sequences;
    """))
    
    # Now create unique constraint
    op.create_unique_constraint(
        'uq_chat_messages_chat_id_sequence',
        'chat_messages',
        ['chat_id', 'sequence']
    )


def downgrade() -> None:
    """Remove unique constraint on (chat_id, sequence)"""
    op.drop_constraint(
        'uq_chat_messages_chat_id_sequence',
        'chat_messages',
        type_='unique'
    )

