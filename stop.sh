#!/bin/bash
# Stop script for MCP Agent Platform

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

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
    exit 1
fi

echo "🛑 Stopping all services..."

# Stop dynamic MCP containers first
echo "  └─ Stopping dynamic MCP containers..."
for container in mcp-agent mcp-file-tools mcp-nmap-recon; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
    fi
done

# Stop docker-compose services
$DOCKER_COMPOSE stop

echo ""
echo "✅ All services stopped"
echo ""
echo "To remove containers: $DOCKER_COMPOSE down"
echo "To start again: ./start.sh"
echo "To check status: ./status.sh"
