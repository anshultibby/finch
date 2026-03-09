"""Trading bots pivot — rename strategy tables to bot tables, add new columns.

Revision ID: 036
Revises: 035
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Rename tables ---
    op.rename_table('strategies', 'trading_bots')
    op.rename_table('strategy_files', 'bot_files')
    op.rename_table('strategy_executions', 'bot_executions')
    op.rename_table('strategy_positions', 'bot_positions')

    # --- Rename FK columns in bot_files ---
    op.alter_column('bot_files', 'strategy_id', new_column_name='bot_id')

    # --- Add file_type to bot_files ---
    op.add_column('bot_files', sa.Column('file_type', sa.String(), nullable=True, server_default='code'))
    op.execute("UPDATE bot_files SET file_type = 'code' WHERE file_type IS NULL")
    op.alter_column('bot_files', 'file_type', nullable=False)

    # --- Add icon and directory to trading_bots ---
    op.add_column('trading_bots', sa.Column('icon', sa.String(10), nullable=True))
    op.add_column('trading_bots', sa.Column('directory', sa.String(), nullable=True))

    # --- Rename FK columns in bot_executions ---
    op.alter_column('bot_executions', 'strategy_id', new_column_name='bot_id')

    # --- Rename FK columns in bot_positions ---
    op.alter_column('bot_positions', 'strategy_id', new_column_name='bot_id')

    # --- Add bot_id to chats table ---
    op.add_column('chats', sa.Column('bot_id', sa.String(), nullable=True))
    op.create_index('ix_chats_bot_id', 'chats', ['bot_id'])

    # --- Rename indexes (recreate them with correct names) ---
    # Drop old indexes that reference strategy_id and recreate with bot_id
    # Note: index names vary by DB, using if_exists where supported
    try:
        op.drop_index('ix_strategies_user_id', table_name='trading_bots')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategies_enabled', table_name='trading_bots')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_files_strategy_id', table_name='bot_files')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_executions_strategy_id', table_name='bot_executions')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_executions_user_id', table_name='bot_executions')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_executions_started_at', table_name='bot_executions')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_positions_strategy_id', table_name='bot_positions')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_positions_user_id', table_name='bot_positions')
    except Exception:
        pass
    try:
        op.drop_index('ix_strategy_positions_status', table_name='bot_positions')
    except Exception:
        pass

    # Create new indexes
    op.create_index('ix_trading_bots_user_id', 'trading_bots', ['user_id'])
    op.create_index('ix_trading_bots_enabled', 'trading_bots', ['enabled'])
    op.create_index('ix_bot_files_bot_id', 'bot_files', ['bot_id'])
    op.create_index('ix_bot_executions_bot_id', 'bot_executions', ['bot_id'])
    op.create_index('ix_bot_executions_user_id', 'bot_executions', ['user_id'])
    op.create_index('ix_bot_executions_started_at', 'bot_executions', ['started_at'])
    op.create_index('ix_bot_positions_bot_id', 'bot_positions', ['bot_id'])
    op.create_index('ix_bot_positions_user_id', 'bot_positions', ['user_id'])
    op.create_index('ix_bot_positions_status', 'bot_positions', ['status'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('ix_bot_positions_status', table_name='bot_positions')
    op.drop_index('ix_bot_positions_user_id', table_name='bot_positions')
    op.drop_index('ix_bot_positions_bot_id', table_name='bot_positions')
    op.drop_index('ix_bot_executions_started_at', table_name='bot_executions')
    op.drop_index('ix_bot_executions_user_id', table_name='bot_executions')
    op.drop_index('ix_bot_executions_bot_id', table_name='bot_executions')
    op.drop_index('ix_bot_files_bot_id', table_name='bot_files')
    op.drop_index('ix_trading_bots_enabled', table_name='trading_bots')
    op.drop_index('ix_trading_bots_user_id', table_name='trading_bots')

    # Remove bot_id from chats
    op.drop_index('ix_chats_bot_id', table_name='chats')
    op.drop_column('chats', 'bot_id')

    # Rename FK columns back
    op.alter_column('bot_positions', 'bot_id', new_column_name='strategy_id')
    op.alter_column('bot_executions', 'bot_id', new_column_name='strategy_id')

    # Remove new columns from trading_bots
    op.drop_column('trading_bots', 'directory')
    op.drop_column('trading_bots', 'icon')

    # Remove file_type from bot_files
    op.drop_column('bot_files', 'file_type')

    # Rename FK column back in bot_files
    op.alter_column('bot_files', 'bot_id', new_column_name='strategy_id')

    # Rename tables back
    op.rename_table('bot_positions', 'strategy_positions')
    op.rename_table('bot_executions', 'strategy_executions')
    op.rename_table('bot_files', 'strategy_files')
    op.rename_table('trading_bots', 'strategies')
