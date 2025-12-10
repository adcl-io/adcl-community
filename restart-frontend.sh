#!/bin/bash
# Restart Frontend

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

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
