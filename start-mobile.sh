#!/bin/bash

echo "📱 Starting Finch Mobile (Expo)..."
echo ""

# Navigate to mobile directory
cd frontend-mobile

# Check if node_modules exists or if package.json has changed
if [ ! -d "node_modules" ]; then
    echo "📦 node_modules not found. Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
elif [ package.json -nt node_modules/.package-lock.json ] 2>/dev/null || [ ! -f node_modules/.package-lock.json ]; then
    echo "📦 package.json has changed. Updating dependencies..."
    npm install
    echo "✅ Dependencies updated"
else
    echo "✅ Dependencies are up to date"
fi

# .env carries Supabase keys + the API URL. We can't fabricate the Supabase
# keys, so warn (don't overwrite) if it's missing.
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Copy .env.example to .env and fill in your"
    echo "    Supabase URL + anon key before the app can authenticate."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "    (created .env from .env.example — Supabase keys still need filling in)"
    fi
fi

# For the iOS/Android simulator and web, the backend is reachable at localhost.
# For a physical device, set EXPO_PUBLIC_API_URL to your machine's LAN IP
# (e.g. http://192.168.1.66:8000) either in .env or when invoking this script.
export EXPO_PUBLIC_API_URL="${EXPO_PUBLIC_API_URL:-http://localhost:8000}"

echo ""
echo "✅ Mobile setup complete!"
echo "🚀 Starting Expo dev server..."
echo ""
echo "   API URL: $EXPO_PUBLIC_API_URL"
echo "   In the Expo menu: press i (iOS), a (Android), or w (web)."
echo "   Physical device? Set EXPO_PUBLIC_API_URL to your LAN IP first."
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "----------------------------------------"
echo ""

# Start Expo
npm start
