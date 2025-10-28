#!/bin/bash

echo "🎨 Starting Finch Frontend..."
echo ""

# Navigate to frontend directory
cd frontend

# Check if node_modules exists or if package.json has changed
if [ ! -d "node_modules" ]; then
    echo "📦 node_modules not found. Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
elif [ package.json -nt node_modules/.package-lock.json ] 2>/dev/null || [ ! -f node_modules/.package-lock.json ]; then
    echo "📦 Package.json has changed. Updating dependencies..."
    npm install
    echo "✅ Dependencies updated"
else
    echo "✅ Dependencies are up to date"
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "⚠️  .env.local not found. Creating with defaults..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
    echo "✅ Created .env.local"
fi

echo ""
echo "✅ Frontend setup complete!"
echo "🚀 Starting Next.js development server..."
echo ""
echo "🌐 App will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "----------------------------------------"
echo ""

# Start the development server
npm run dev

