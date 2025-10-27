#!/bin/bash
# Database setup script for Finch backend

set -e  # Exit on error

echo "🚀 Finch Database Setup"
echo "======================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Run: source venv/bin/activate"
    exit 1
fi

# Check if .env exists
if [[ ! -f ".env" ]]; then
    echo "⚠️  .env file not found"
    echo "   Creating from template..."
    cp env.template .env
    echo "✅ Created .env file"
    echo ""
    echo "📝 Please edit .env and add:"
    echo "   - DATABASE_URL (from Supabase)"
    echo "   - ENCRYPTION_KEY (generate with: python scripts/generate_encryption_key.py)"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if DATABASE_URL is set
source .env
if [[ -z "$DATABASE_URL" ]] || [[ "$DATABASE_URL" == "postgresql://postgres:your_password@db.xxx.supabase.co:5432/postgres" ]]; then
    echo "⚠️  DATABASE_URL not configured in .env"
    echo "   Get it from: Supabase Dashboard > Settings > Database > Connection String"
    exit 1
fi

if [[ -z "$ENCRYPTION_KEY" ]] || [[ "$ENCRYPTION_KEY" == "your_fernet_encryption_key_here" ]]; then
    echo "⚠️  ENCRYPTION_KEY not configured in .env"
    echo "   Generate one with: python scripts/generate_encryption_key.py"
    exit 1
fi

echo "✅ Environment variables configured"
echo ""

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Run migrations
echo "🗄️  Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete"
echo ""

# Verify migration
echo "🔍 Verifying database..."
CURRENT=$(alembic current 2>&1 | grep -o '001' || echo "none")
if [[ "$CURRENT" == "001" ]]; then
    echo "✅ Database schema up to date (revision: 001)"
else
    echo "⚠️  Warning: Unexpected migration state"
    alembic current
fi

echo ""
echo "🎉 Database setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the backend: uvicorn main:app --reload"
echo "2. Test login through frontend"
echo "3. Check Supabase Table Editor for 'robinhood_sessions' table"
echo ""

