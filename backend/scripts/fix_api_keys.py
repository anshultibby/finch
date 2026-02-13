#!/usr/bin/env python3
"""
Fix corrupted API keys for a user by clearing them

This is needed when:
- Encryption key has changed since the keys were stored
- Data corruption occurred

Usage:
    python scripts/fix_api_keys.py <user_id>
    python scripts/fix_api_keys.py dba02deb-cace-42be-b795-61ac34558144
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from database import get_async_db
from models.db import UserSettings


async def fix_user_api_keys(user_id: str):
    """Clear corrupted API keys for a user"""
    async for db in get_async_db():
        # Find the user settings
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalars().first()
        
        if not settings:
            print(f"No user settings found for user {user_id}")
            return
        
        print(f"Found user settings for {user_id}")
        print(f"  - Has encrypted_api_keys: {bool(settings.encrypted_api_keys)}")
        print(f"  - Settings keys: {list(settings.settings.keys()) if settings.settings else []}")
        
        if settings.encrypted_api_keys:
            # Try to decrypt to see if it works
            try:
                from services.encryption import encryption_service
                import json
                decrypted = encryption_service.decrypt(settings.encrypted_api_keys)
                api_keys = json.loads(decrypted)
                print(f"  - Decryption successful! Services: {list(api_keys.keys())}")
                print("  - No fix needed, keys are valid")
                return
            except Exception as e:
                print(f"  - Decryption failed: {e}")
                print("  - Will clear corrupted keys")
        
        # Clear the corrupted data
        old_metadata = settings.settings.get("api_keys_metadata", {})
        if old_metadata:
            print(f"  - Clearing metadata for services: {list(old_metadata.keys())}")
        
        # Remove encrypted keys and metadata
        settings.encrypted_api_keys = None
        new_settings = {k: v for k, v in settings.settings.items() if k != "api_keys_metadata"}
        settings.settings = new_settings
        
        await db.commit()
        print(f"\n✅ Cleared corrupted API keys for user {user_id}")
        print("   User will need to re-enter their Kalshi credentials in the app")


async def list_users_with_api_keys():
    """List all users who have API keys stored"""
    async for db in get_async_db():
        result = await db.execute(
            select(UserSettings).where(UserSettings.encrypted_api_keys.isnot(None))
        )
        users = result.scalars().all()
        
        print(f"\nFound {len(users)} users with API keys:")
        for settings in users:
            metadata = settings.settings.get("api_keys_metadata", {})
            services = list(metadata.keys()) if metadata else ["unknown"]
            print(f"  - {settings.user_id}: {', '.join(services)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_api_keys.py <user_id>")
        print("       python scripts/fix_api_keys.py --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        asyncio.run(list_users_with_api_keys())
    else:
        user_id = sys.argv[1]
        asyncio.run(fix_user_api_keys(user_id))
