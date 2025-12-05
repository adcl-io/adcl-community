#!/bin/bash
# Stop script for MCP Agent Platform

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

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

echo "🛑 Stopping and removing all services..."

# Remove ALL adcl-* containers
echo "  └─ Removing all ADCL containers..."
docker ps -a --filter "name=adcl-" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true

# Remove dynamic MCP containers
echo "  └─ Removing dynamic MCP containers..."
for container in mcp-agent mcp-file-tools mcp-nmap-recon mcp-history; do
    docker rm -f $container 2>/dev/null || true
done

# Stop docker-compose services and remove containers
docker-compose down --remove-orphans

echo ""
echo "✅ All services stopped and removed"
echo ""
echo "To start again: ./start.sh or ./clean-restart.sh"
echo "To check status: ./status.sh"
