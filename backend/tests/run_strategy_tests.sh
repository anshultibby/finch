#!/bin/bash

# Run Strategy Management Tests
# This script runs all tests for the strategy management system

set -e

echo "🧪 Running Strategy Management Tests"
echo "===================================="
echo ""

# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    echo "📦 Activating virtual environment..."
    source ../venv/bin/activate
fi

# Run tests with pytest
echo "🏃 Running tests..."
echo ""

# Run unit tests
echo "1️⃣  Testing Strategy Executor & Data Fetcher..."
pytest test_strategy_management.py -v --tb=short

echo ""
echo "2️⃣  Testing API Routes..."
pytest test_strategy_routes.py -v --tb=short

echo ""
echo "✅ All tests completed!"
echo ""

# Optional: Run with coverage
read -p "📊 Generate coverage report? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "📊 Generating coverage report..."
    pytest test_strategy_management.py test_strategy_routes.py --cov=../services --cov=../routes --cov-report=html --cov-report=term
    echo "📄 HTML coverage report generated in htmlcov/"
fi

