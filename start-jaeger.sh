#!/bin/bash
#
# Start Jaeger for distributed tracing visualization
#
# This script starts Jaeger all-in-one (includes UI, collector, and storage)
# in Docker for local development.
#
# Prerequisites:
# - Docker installed and running
# - Ports 16686 (UI) and 6831 (UDP collector) available
#

set -e

echo "🔍 Starting Jaeger for distributed tracing..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if Jaeger is already running
if docker ps | grep -q jaeger; then
    echo "⚠️  Jaeger is already running"
    echo ""
    echo "To restart Jaeger:"
    echo "  docker stop jaeger && docker rm jaeger"
    echo "  ./start-jaeger.sh"
    echo ""
    echo "To view Jaeger UI:"
    echo "  http://localhost:16686"
    exit 0
fi

# Remove old container if exists
if docker ps -a | grep -q jaeger; then
    echo "🧹 Removing old Jaeger container..."
    docker rm jaeger > /dev/null 2>&1 || true
fi

# Start Jaeger
echo "🚀 Starting Jaeger container..."
docker run -d \
  --name jaeger \
  -p 16686:16686 \
  -p 6831:6831/udp \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

echo ""
echo "✅ Jaeger started successfully!"
echo ""
echo "📊 Jaeger UI: http://localhost:16686"
echo ""
echo "🔍 How to use Jaeger:"
echo "  1. Make sure your backend is running with ENABLE_TIMING_LOGS=true in .env"
echo "  2. Send a chat message in the UI"
echo "  3. Open Jaeger UI at http://localhost:16686"
echo "  4. Select 'finch-api' from the Service dropdown"
echo "  5. Click 'Find Traces' to see your requests"
echo ""
echo "📈 What you'll see in traces:"
echo "  • agent.ChatAgent.interaction - Overall request flow"
echo "  • agent.turn.N - Each agent iteration/turn"
echo "  • llm.call - LLM API calls with timing (TTFB, total duration)"
echo "  • tool.TOOLNAME - Individual tool executions"
echo "  • Logs correlated with spans (click on spans to see logs)"
echo ""
echo "💡 Tips:"
echo "  • Click on spans to see detailed timing breakdown"
echo "  • Look for 'duration' to see where time is spent"
echo "  • Expand nested spans to see tool call hierarchy"
echo "  • Use 'Trace Timeline' view for visual breakdown"
echo ""
echo "To stop Jaeger:"
echo "  ./stop-jaeger.sh  or  docker stop jaeger"
echo ""

