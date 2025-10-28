"""Add tool call columns to chat_messages

Revision ID: 007
Revises: 006
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add columns for storing tool calls and function results in chat messages.
    Following OpenAI Chat API message format:
    
    Message roles (per OpenAI API):
    - 'user': User messages (content only)
    - 'assistant': AI responses (content, optionally tool_calls JSONB array)
    - 'tool': Tool/function results (content, tool_call_id, name, resource_id FK)
    
    New columns:
    - tool_calls: JSONB column for 'assistant' role messages with tool invocations
    - tool_call_id: String column for 'tool' role messages linking back to the tool call
    - name: String column for the tool name in 'tool' role messages
    - latency_ms: Integer column for 'assistant' role messages (response time in milliseconds)
    
    The existing resource_id column is used as FK to link tool results to resources.
    """
    # Add tool_calls column for assistant messages with tool calls
    op.add_column('chat_messages', sa.Column('tool_calls', JSONB, nullable=True))
    
    # Add tool_call_id column for tool/function result messages
    op.add_column('chat_messages', sa.Column('tool_call_id', sa.String, nullable=True))
    
    # Add name column for tool name in function result messages
    op.add_column('chat_messages', sa.Column('name', sa.String, nullable=True))
    
    # Add latency column for assistant messages (in milliseconds)
    op.add_column('chat_messages', sa.Column('latency_ms', sa.Integer, nullable=True))
    
    # Add index on tool_call_id for faster lookups
    op.create_index('ix_chat_messages_tool_call_id', 'chat_messages', ['tool_call_id'])


def downgrade():
    """Remove tool call columns"""
    op.drop_index('ix_chat_messages_tool_call_id', 'chat_messages')
    op.drop_column('chat_messages', 'latency_ms')
    op.drop_column('chat_messages', 'name')
    op.drop_column('chat_messages', 'tool_call_id')
    op.drop_column('chat_messages', 'tool_calls')

