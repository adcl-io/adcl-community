#!/bin/bash
# Restart Frontend

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/docker-compose-compat.sh"

echo "🔄 Restarting Frontend..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
$DOCKER_COMPOSE restart frontend

echo ""
echo "✅ Frontend restarted"
echo ""
$DOCKER_COMPOSE ps frontend

echo ""
echo "Frontend available at: http://localhost:3000"
echo "View logs: $DOCKER_COMPOSE logs -f frontend"
