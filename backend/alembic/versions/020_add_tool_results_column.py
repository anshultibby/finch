"""Add tool_results column to chat_messages for persisting execution results

Revision ID: 020
Revises: 019
Create Date: 2025-12-27

This migration adds a JSONB column to store tool execution results,
including code_output (stdout/stderr) from execute_code tool.
This allows viewing code output from previous sessions.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add tool_results JSONB column to chat_messages.
    
    This column stores execution results for assistant messages with tool_calls.
    Structure: {
        "<tool_call_id>": {
            "status": "completed" | "error",
            "code_output": {"stdout": "...", "stderr": "..."},  # for execute_code
            "result_summary": "...",
            "error": "...",  # if status == "error"
            "resource_id": "..."  # if tool created a resource
        },
        ...
    }
    
    This is stored on the assistant message (same row as tool_calls) for easy lookup.
    """
    op.add_column('chat_messages', sa.Column('tool_results', JSONB, nullable=True))


def downgrade():
    """Remove tool_results column"""
    op.drop_column('chat_messages', 'tool_results')

