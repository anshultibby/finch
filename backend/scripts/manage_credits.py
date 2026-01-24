"""
Credit management CLI tool

Usage:
    python scripts/manage_credits.py balance <user_id>
    python scripts/manage_credits.py add <user_id> <credits> [description]
    python scripts/manage_credits.py history <user_id> [limit]
"""
import sys
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import get_db_session
from services.credits import CreditsService
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_balance(user_id: str):
    """Get credit balance for a user"""
    async with get_db_session() as db:
        credits = await CreditsService.get_user_credits(db, user_id)
        
        if credits is None:
            print(f"❌ User {user_id} not found")
            return
        
        print("=" * 60)
        print(f"User: {user_id}")
        print(f"Credits: {credits}")
        print("=" * 60)


async def add_credits(user_id: str, amount: int, description: str = "Credits added via CLI"):
    """Add credits to a user"""
    async with get_db_session() as db:
        success = await CreditsService.add_credits(
            db=db,
            user_id=user_id,
            credits=amount,
            transaction_type="admin_adjustment",
            description=description
        )
        
        if not success:
            print(f"❌ User {user_id} not found")
            return
        
        new_balance = await CreditsService.get_user_credits(db, user_id)
        
        print("=" * 60)
        print(f"✅ Added {amount} credits to user {user_id}")
        print(f"New balance: {new_balance}")
        print(f"Description: {description}")
        print("=" * 60)


async def show_history(user_id: str, limit: int = 20):
    """Show credit transaction history for a user"""
    async with get_db_session() as db:
        transactions = await CreditsService.get_transaction_history(
            db=db,
            user_id=user_id,
            limit=limit
        )
        
        if not transactions:
            print(f"No transactions found for user {user_id}")
            return
        
        print("=" * 80)
        print(f"Credit History for {user_id} (last {len(transactions)} transactions)")
        print("=" * 80)
        print(f"{'Date':<20} {'Type':<15} {'Amount':>8} {'Balance':>8} {'Description'}")
        print("-" * 80)
        
        for t in transactions:
            date_str = t['created_at'][:19] if t['created_at'] else "N/A"
            amount_str = f"+{t['amount']}" if t['amount'] > 0 else str(t['amount'])
            
            print(f"{date_str:<20} {t['transaction_type']:<15} {amount_str:>8} {t['balance_after']:>8} {t['description'][:30]}")
        
        print("=" * 80)


def print_usage():
    """Print usage information"""
    print("Credit Management CLI")
    print("=" * 60)
    print("Usage:")
    print("  python scripts/manage_credits.py balance <user_id>")
    print("  python scripts/manage_credits.py add <user_id> <credits> [description]")
    print("  python scripts/manage_credits.py history <user_id> [limit]")
    print()
    print("Examples:")
    print("  python scripts/manage_credits.py balance abc-123")
    print("  python scripts/manage_credits.py add abc-123 1000 'Bonus credits'")
    print("  python scripts/manage_credits.py history abc-123 50")
    print("=" * 60)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "balance":
            if len(sys.argv) < 3:
                print("❌ Error: user_id required")
                print_usage()
                sys.exit(1)
            
            user_id = sys.argv[2]
            await get_balance(user_id)
        
        elif command == "add":
            if len(sys.argv) < 4:
                print("❌ Error: user_id and credits amount required")
                print_usage()
                sys.exit(1)
            
            user_id = sys.argv[2]
            credits = int(sys.argv[3])
            description = sys.argv[4] if len(sys.argv) > 4 else "Credits added via CLI"
            
            if credits <= 0:
                print("❌ Error: credits must be positive")
                sys.exit(1)
            
            await add_credits(user_id, credits, description)
        
        elif command == "history":
            if len(sys.argv) < 3:
                print("❌ Error: user_id required")
                print_usage()
                sys.exit(1)
            
            user_id = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            
            await show_history(user_id, limit)
        
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            sys.exit(1)
    
    except ValueError as e:
        print(f"❌ Error: Invalid argument - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
