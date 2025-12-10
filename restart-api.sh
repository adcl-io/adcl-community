#!/bin/bash
# Restart API server (orchestrator)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

echo "🔄 Restarting API Server (orchestrator)..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
$DOCKER_COMPOSE restart orchestrator

echo ""
echo "✅ API Server restarted"
echo ""
$DOCKER_COMPOSE ps orchestrator

echo ""
echo "View logs: $DOCKER_COMPOSE logs -f orchestrator"
