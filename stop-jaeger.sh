#!/bin/bash
#
# Stop Jaeger tracing container
#

set -e

echo "🛑 Stopping Jaeger..."

if docker ps | grep -q jaeger; then
    docker stop jaeger
    docker rm jaeger
    echo "✅ Jaeger stopped and removed"
else
    echo "⚠️  Jaeger is not running"
fi

