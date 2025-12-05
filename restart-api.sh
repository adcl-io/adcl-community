#!/bin/bash
# Restart API server (orchestrator)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔄 Restarting API Server (orchestrator)..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
docker-compose restart orchestrator

echo ""
echo "✅ API Server restarted"
echo ""
docker-compose ps orchestrator

echo ""
echo "View logs: docker-compose logs -f orchestrator"
