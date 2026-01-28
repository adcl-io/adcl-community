#!/bin/bash
# Stop script for MCP Agent Platform

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/docker-compose-compat.sh"

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Stopping MCP Agent Platform                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Project: $SCRIPT_DIR"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "   Make sure you're running from the dist/ directory"
    exit 1
fi

echo "🛑 Stopping all services..."

# Stop dynamic MCP containers first
echo "  ├─ Stopping dynamic MCP containers..."
# Dynamically find all mcp-* containers
MCP_CONTAINERS=$(docker ps --format '{{.Names}}' | grep '^mcp-' || true)
if [ -n "$MCP_CONTAINERS" ]; then
    for container in $MCP_CONTAINERS; do
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
    done
else
    echo "     └─ No running MCP containers found"
fi

# Stop Vulhub containers
echo "  ├─ Stopping Vulhub containers..."
VULHUB_CONTAINERS=$(docker ps --format '{{.Names}}' | grep '^vulhub-' || true)
if [ -n "$VULHUB_CONTAINERS" ]; then
    for container in $VULHUB_CONTAINERS; do
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
    done
else
    echo "     └─ No running Vulhub containers found"
fi

# Stop docker-compose services
echo "  └─ Stopping docker-compose services..."
$DOCKER_COMPOSE stop

echo ""
echo "✅ All services stopped"

# Sync Vulhub backend state (containers stopped but backend may still be running)
echo ""
echo "🔄 Syncing Vulhub state with backend..."
if curl -s -X POST http://localhost:8000/api/vulhub/instances/sync > /dev/null 2>&1; then
    echo "  ✓ Vulhub state synced"
else
    echo "  ⚠  Backend not running or Vulhub sync failed (this is okay if backend is stopped)"
fi

echo ""
echo "To remove containers: $DOCKER_COMPOSE down"
echo "To start again: ./start.sh"
echo "To check status: ./status.sh"
