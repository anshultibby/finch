"""
Database migration: Add credits system

Adds:
1. credits and total_credits_used columns to snaptrade_users table
2. credit_transactions table
3. Sets default 500 credits for existing users
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database import engine, Base
from models.db import SnapTradeUser, CreditTransaction
from utils.logger import get_logger

logger = get_logger(__name__)


def run_migration():
    """Run the migration to add credits system"""
    
    logger.info("Starting credits system migration...")
    
    with engine.begin() as conn:
        # Check if credits column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'snaptrade_users' 
            AND column_name = 'credits'
        """))
        
        if result.fetchone():
            logger.info("✅ Credits column already exists, skipping migration")
            return
        
        # Step 1: Add credits columns to snaptrade_users
        logger.info("Adding credits and total_credits_used columns to snaptrade_users...")
        conn.execute(text("""
            ALTER TABLE snaptrade_users
            ADD COLUMN IF NOT EXISTS credits INTEGER NOT NULL DEFAULT 500,
            ADD COLUMN IF NOT EXISTS total_credits_used INTEGER NOT NULL DEFAULT 0
        """))
        logger.info("✅ Added credits columns")
        
        # Step 2: Set default 500 credits for existing users
        result = conn.execute(text("""
            UPDATE snaptrade_users
            SET credits = 500, total_credits_used = 0
            WHERE credits IS NULL OR credits = 0
        """))
        logger.info(f"✅ Set default 500 credits for {result.rowcount} existing users")
        
        # Step 3: Create credit_transactions table
        logger.info("Creating credit_transactions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id UUID PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                transaction_type VARCHAR NOT NULL,
                description VARCHAR NOT NULL,
                chat_id VARCHAR,
                tool_name VARCHAR,
                transaction_metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        logger.info("✅ Created credit_transactions table")
        
        # Step 4: Create indexes
        logger.info("Creating indexes...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id 
            ON credit_transactions(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_chat_id 
            ON credit_transactions(chat_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at 
            ON credit_transactions(created_at DESC)
        """))
        logger.info("✅ Created indexes")
        
        # Step 5: Add initial credit transaction for existing users
        logger.info("Adding initial credit transactions for existing users...")
        conn.execute(text("""
            INSERT INTO credit_transactions (id, user_id, amount, balance_after, transaction_type, description, created_at)
            SELECT 
                gen_random_uuid(),
                user_id,
                500,
                500,
                'initial_credit',
                'Initial credits (500)',
                created_at
            FROM snaptrade_users
            WHERE NOT EXISTS (
                SELECT 1 FROM credit_transactions 
                WHERE credit_transactions.user_id = snaptrade_users.user_id
            )
        """))
        logger.info("✅ Added initial credit transactions")
    
    logger.info("=" * 60)
    logger.info("🎉 Credits system migration completed successfully!")
    logger.info("=" * 60)
    logger.info("Summary:")
    logger.info("  - Added credits and total_credits_used columns")
    logger.info("  - Created credit_transactions table")
    logger.info("  - Set default 500 credits for all users")
    logger.info("  - Added transaction history for initial credits")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
