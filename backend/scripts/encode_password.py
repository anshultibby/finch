#!/usr/bin/env python3
"""
URL-encode a password for use in DATABASE_URL

Usage:
    python scripts/encode_password.py "MyP@ssword123"
"""
import sys
from urllib.parse import quote

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n🔐 Password URL Encoder")
        print("="*60)
        password = input("Enter your password: ")
    else:
        password = sys.argv[1]
    
    # URL-encode the password (safe for database URLs)
    encoded = quote(password, safe='')
    
    print("\n" + "="*60)
    print("🔐 PASSWORD ENCODING RESULT")
    print("="*60)
    print(f"\nOriginal:  {password}")
    print(f"Encoded:   {encoded}")
    
    if password != encoded:
        print(f"\n⚠️  Your password contains special characters!")
        print(f"    Use the ENCODED version in your DATABASE_URL")
    else:
        print(f"\n✅ No special characters - safe to use as-is")
    
    print("\n📋 Full DATABASE_URL format:")
    print(f"   postgresql://postgres:{encoded}@db.xxx.supabase.co:5432/postgres")
    print("="*60 + "\n")

