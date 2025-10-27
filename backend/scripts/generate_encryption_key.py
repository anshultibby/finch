#!/usr/bin/env python3
"""
Generate a new Fernet encryption key for storing Robinhood tokens

Usage:
    python scripts/generate_encryption_key.py
"""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key().decode()
    print("\n" + "="*60)
    print("🔐 NEW ENCRYPTION KEY GENERATED")
    print("="*60)
    print(f"\n{key}\n")
    print("📋 Add this to your .env file:")
    print(f"   ENCRYPTION_KEY={key}")
    print("\n⚠️  IMPORTANT:")
    print("   - Keep this key secret")
    print("   - Back it up securely")
    print("   - Never commit to version control")
    print("   - Losing this key means losing access to encrypted data")
    print("="*60 + "\n")

