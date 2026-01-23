#!/usr/bin/env python3
"""
SnapTrade User Management Script

Allows querying and deleting SnapTrade users via the API.
Shows user emails from Supabase Auth for easy identification.

Usage:
    ./venv/bin/python scripts/manage_snaptrade_users.py          # Interactive mode
    ./venv/bin/python scripts/manage_snaptrade_users.py list     # List all users with emails
    ./venv/bin/python scripts/manage_snaptrade_users.py delete <email>  # Delete by email
"""
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snaptrade_client import SnapTrade
from supabase import create_client
from config import Config
from database import SessionLocal
from crud import snaptrade_user as snaptrade_crud


def get_snaptrade_client() -> SnapTrade:
    """Initialize SnapTrade client"""
    if not Config.SNAPTRADE_CLIENT_ID or not Config.SNAPTRADE_CONSUMER_KEY:
        print("❌ Error: SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY must be set in .env")
        sys.exit(1)
    
    return SnapTrade(
        consumer_key=Config.SNAPTRADE_CONSUMER_KEY,
        client_id=Config.SNAPTRADE_CLIENT_ID
    )


def get_supabase_client():
    """Initialize Supabase admin client"""
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_KEY:
        print("⚠️  Warning: SUPABASE_URL and SUPABASE_SERVICE_KEY not set - email lookup disabled")
        return None
    
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def get_supabase_users(supabase) -> dict[str, dict]:
    """Get all users from Supabase Auth, returns {user_id: {email, ...}}"""
    if not supabase:
        return {}
    
    try:
        # Use admin API to list all users
        response = supabase.auth.admin.list_users()
        users = {}
        for user in response:
            users[user.id] = {
                "email": user.email,
                "created_at": user.created_at,
            }
        return users
    except Exception as e:
        print(f"⚠️  Could not fetch Supabase users: {e}")
        return {}


def list_snaptrade_users(client: SnapTrade) -> list[str]:
    """List all SnapTrade users registered with your client ID"""
    try:
        response = client.authentication.list_snap_trade_users()
        users = response.body if hasattr(response, 'body') else response
        return users if users else []
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return []


def delete_snaptrade_user(client: SnapTrade, user_id: str) -> bool:
    """Delete a SnapTrade user"""
    try:
        client.authentication.delete_snap_trade_user(user_id=user_id)
        print(f"✅ Deleted user from SnapTrade API: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting user from SnapTrade: {e}")
        return False


def delete_user_from_db(user_id: str) -> bool:
    """Delete a user from the local database"""
    db = SessionLocal()
    try:
        success = snaptrade_crud.delete_user(db, user_id)
        if success:
            print(f"✅ Deleted user from local database: {user_id}")
        else:
            print(f"ℹ️  User not found in local database: {user_id}")
        return success
    finally:
        db.close()


def get_local_snaptrade_users() -> list[dict]:
    """Get all users from local snaptrade_users table"""
    from models.db import SnapTradeUser
    db = SessionLocal()
    try:
        users = db.query(SnapTradeUser).all()
        return [
            {
                "user_id": u.user_id,
                "snaptrade_user_id": u.snaptrade_user_id,
                "is_connected": u.is_connected,
                "brokerage_name": u.brokerage_name,
                "last_activity": u.last_activity.isoformat() if u.last_activity else None,
            }
            for u in users
        ]
    finally:
        db.close()


def find_user_id_by_email(supabase_users: dict, email: str) -> str | None:
    """Find user_id by email address"""
    email_lower = email.lower()
    for user_id, info in supabase_users.items():
        if info.get("email", "").lower() == email_lower:
            return user_id
    return None


def display_users_with_emails(snaptrade_users: list[str], supabase_users: dict, local_users: list[dict]):
    """Display all SnapTrade users with their email addresses"""
    local_user_ids = {u["user_id"] for u in local_users}
    local_user_map = {u["user_id"]: u for u in local_users}
    
    print("\n📋 SnapTrade Users:")
    print("-" * 80)
    
    if not snaptrade_users:
        print("   No users found in SnapTrade API")
        return
    
    for i, user_id in enumerate(snaptrade_users, 1):
        # Get email from Supabase
        user_info = supabase_users.get(user_id, {})
        email = user_info.get("email", "N/A")
        
        # Check if in local DB
        in_local_db = user_id in local_user_ids
        local_info = local_user_map.get(user_id, {})
        
        # Status indicators
        db_status = "📁 In DB" if in_local_db else "⚠️  Not in DB"
        connected = ""
        if in_local_db:
            connected = "🟢" if local_info.get("is_connected") else "🔴"
            brokerage = local_info.get("brokerage_name") or ""
            if brokerage:
                connected += f" {brokerage}"
        
        print(f"\n   {i}. {email}")
        print(f"      ID: {user_id}")
        print(f"      Status: {db_status} {connected}")
    
    print("-" * 80)
    print(f"Total: {len(snaptrade_users)} users in SnapTrade API")


def interactive_mode(snaptrade: SnapTrade, supabase):
    """Run interactive user management"""
    supabase_users = get_supabase_users(supabase)
    
    while True:
        print("\n" + "=" * 60)
        print("SnapTrade User Management")
        print("=" * 60)
        print("1. List all users (with emails)")
        print("2. Delete user by email")
        print("3. Delete user by ID")
        print("4. Clean up orphaned API users")
        print("5. Refresh user list")
        print("6. Exit")
        print("=" * 60)
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            snaptrade_users = list_snaptrade_users(snaptrade)
            local_users = get_local_snaptrade_users()
            display_users_with_emails(snaptrade_users, supabase_users, local_users)
        
        elif choice == "2":
            email = input("\nEnter email address to delete: ").strip()
            if not email:
                print("❌ No email provided")
                continue
            
            user_id = find_user_id_by_email(supabase_users, email)
            if not user_id:
                print(f"❌ No user found with email: {email}")
                continue
            
            print(f"\n   Found user: {email}")
            print(f"   User ID: {user_id}")
            
            confirm = input(f"\n⚠️  Delete this user from SnapTrade API and local DB? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_snaptrade_user(snaptrade, user_id)
                delete_user_from_db(user_id)
            else:
                print("Cancelled")
        
        elif choice == "3":
            user_id = input("\nEnter user ID to delete: ").strip()
            if not user_id:
                print("❌ No user ID provided")
                continue
            
            # Show email if available
            user_info = supabase_users.get(user_id, {})
            email = user_info.get("email", "Unknown")
            print(f"\n   Email: {email}")
            print(f"   User ID: {user_id}")
            
            confirm = input(f"\n⚠️  Delete this user from SnapTrade API and local DB? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_snaptrade_user(snaptrade, user_id)
                delete_user_from_db(user_id)
            else:
                print("Cancelled")
        
        elif choice == "4":
            print("\n🔄 Checking for orphaned API users...")
            api_users = set(list_snaptrade_users(snaptrade))
            local_users = {u["user_id"] for u in get_local_snaptrade_users()}
            
            orphaned = api_users - local_users
            if not orphaned:
                print("✅ No orphaned users found")
            else:
                print(f"\nFound {len(orphaned)} orphaned users (in API but not in local DB):")
                for user_id in orphaned:
                    email = supabase_users.get(user_id, {}).get("email", "Unknown")
                    print(f"   - {email} ({user_id})")
                
                confirm = input("\n⚠️  Delete all orphaned users from SnapTrade API? (yes/no): ").strip().lower()
                if confirm == "yes":
                    for user_id in orphaned:
                        delete_snaptrade_user(snaptrade, user_id)
                    print(f"✅ Deleted {len(orphaned)} orphaned users")
                else:
                    print("Cancelled")
        
        elif choice == "5":
            print("🔄 Refreshing user list from Supabase...")
            supabase_users = get_supabase_users(supabase)
            print(f"✅ Loaded {len(supabase_users)} users from Supabase Auth")
        
        elif choice == "6":
            print("\nGoodbye! 👋")
            break
        
        else:
            print("❌ Invalid choice, please enter 1-6")


def main():
    snaptrade = get_snaptrade_client()
    supabase = get_supabase_client()
    supabase_users = get_supabase_users(supabase)
    
    if len(sys.argv) == 1:
        # Interactive mode
        interactive_mode(snaptrade, supabase)
    
    elif sys.argv[1] == "list":
        snaptrade_users = list_snaptrade_users(snaptrade)
        local_users = get_local_snaptrade_users()
        display_users_with_emails(snaptrade_users, supabase_users, local_users)
    
    elif sys.argv[1] == "delete" and len(sys.argv) >= 3:
        identifier = sys.argv[2]
        
        # Check if it's an email or user_id
        if "@" in identifier:
            user_id = find_user_id_by_email(supabase_users, identifier)
            if not user_id:
                print(f"❌ No user found with email: {identifier}")
                sys.exit(1)
            print(f"🗑️  Deleting user: {identifier} ({user_id})")
        else:
            user_id = identifier
            email = supabase_users.get(user_id, {}).get("email", "Unknown")
            print(f"🗑️  Deleting user: {email} ({user_id})")
        
        delete_snaptrade_user(snaptrade, user_id)
        delete_user_from_db(user_id)
    
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
