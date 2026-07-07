"""Wipe client-owned refresh tokens from user_auth_tokens

Job auth now mints backend-owned Supabase sessions (their own refresh-token
family). Every token currently in this table came from a user's browser
session — spending one rotates it inside the browser's family, and Supabase's
reuse detection then revokes the whole family on the browser's next silent
refresh, logging the user out. They must never be used again, so drop them;
job_auth mints fresh sessions on demand.

Revision ID: 086
Revises: 085
Create Date: 2026-07-06
"""
from alembic import op

revision = '086'
down_revision = '085'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM user_auth_tokens")


def downgrade():
    pass  # data-only cleanup; nothing to restore
