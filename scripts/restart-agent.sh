#!/bin/bash
# Restart Agent MCP server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/docker-compose-compat.sh"

echo "🔄 Restarting Agent MCP Server..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
$DOCKER_COMPOSE restart agent

echo ""
echo "✅ Agent MCP Server restarted"
echo ""
$DOCKER_COMPOSE ps agent

echo ""
echo "View logs: $DOCKER_COMPOSE logs -f agent"
