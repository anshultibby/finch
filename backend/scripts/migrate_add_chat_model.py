"""
Database migration: Add per-chat LLM model

Adds a nullable `model` column to the `chats` table so each chat can remember
the LLM model the user picked. NULL means "use the default model".
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from core.database import engine
from utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """Add the chats.model column."""
    logger.info("Starting per-chat model migration...")

    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'chats' AND column_name = 'model'
        """))

        if result.fetchone():
            logger.info("✅ chats.model column already exists, skipping migration")
            return

        logger.info("Adding model column to chats...")
        conn.execute(text("""
            ALTER TABLE chats
            ADD COLUMN IF NOT EXISTS model VARCHAR
        """))
        logger.info("✅ Added chats.model column")

    logger.info("🎉 Per-chat model migration completed successfully!")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
