#!/bin/bash
# Quick script to test SnapTrade transaction fetching

echo "🔍 SnapTrade Transaction Fetch Test"
echo "===================================="
echo ""

# Check if user_id provided
if [ -z "$1" ]; then
    echo "Usage: ./test_transactions.sh <user_id>"
    echo ""
    echo "To find your user_id, check one of these:"
    echo "  1. Frontend browser console (logged on auth)"
    echo "  2. Query database:"
    echo "     psql \$DATABASE_URL -c \"SELECT user_id, is_connected FROM snaptrade_users LIMIT 5;\""
    echo ""
    exit 1
fi

USER_ID=$1

echo "Testing with user_id: $USER_ID"
echo ""

cd "$(dirname "$0")/.."
source venv/bin/activate

python tests/test_snaptrade_quick.py "$USER_ID"

