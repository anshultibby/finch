#!/bin/bash

echo "🐦 Starting Finch Backend..."
echo ""

# Navigate to backend directory
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.template .env
    echo ""
    echo "❌ IMPORTANT: Please add your OpenAI API key to backend/.env"
    echo "   Edit the file and set: OPENAI_API_KEY=your-key-here"
    echo "   Get your key from: https://platform.openai.com/api-keys"
    echo ""
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env && ! grep -q "OPENAI_API_KEY=your_openai" .env; then
    echo "⚠️  Checking API key..."
fi

if grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo "❌ Please update your OPENAI_API_KEY in backend/.env"
    echo "   Get your key from: https://platform.openai.com/api-keys"
    echo ""
    exit 1
fi

# Install/update dependencies
if [ ! -f "venv/.requirements-installed" ] || [ requirements.txt -nt venv/.requirements-installed ]; then
    echo "📦 Installing/updating Python dependencies..."
    pip install -r requirements.txt
    touch venv/.requirements-installed
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies are up to date"
fi

echo ""
echo "✅ Backend setup complete!"
echo "🚀 Starting FastAPI server..."
echo ""
echo "📝 API will be available at: http://localhost:8000"
echo "📚 API Documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "----------------------------------------"
echo ""

# Start the server
python3 main.py

