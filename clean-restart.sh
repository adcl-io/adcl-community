#!/bin/bash
# Clean restart - Stops, removes, and starts all services
# Use this to avoid ContainerConfig errors
#
# Usage:
#   ./clean-restart.sh         # Normal clean restart (uses cache)
#   ./clean-restart.sh -nuke   # Nuclear option: rebuild from scratch (no cache)

set -e

# Parse arguments
NUKE_MODE=false
if [ "$1" == "-nuke" ] || [ "$1" == "--nuke" ]; then
    NUKE_MODE=true
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════╗"
if [ "$NUKE_MODE" = true ]; then
    echo "║     MCP Agent Platform - NUCLEAR RESTART ☢️          ║"
    echo "║     (Force rebuild without cache)                   ║"
else
    echo "║     MCP Agent Platform - Clean Restart               ║"
fi
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Project: $SCRIPT_DIR"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    exit 1
fi

echo "🛑 Stopping and removing all containers..."

# Remove ALL adcl-* containers (including stopped ones)
echo "  └─ Removing all ADCL containers..."
docker ps -a --filter "name=adcl-" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true

# Remove dynamically installed MCP containers
echo "  └─ Removing dynamic MCP containers..."
for container in mcp-agent mcp-file-tools mcp-nmap-recon mcp-history; do
    docker rm -f $container 2>/dev/null || true
done

# Clean up with docker-compose
docker-compose down --remove-orphans 2>/dev/null || true

if [ "$NUKE_MODE" = true ]; then
    echo ""
    echo "☢️  NUCLEAR MODE: Removing images to force clean rebuild..."
    echo "  └─ Removing orchestrator, registry, and frontend images..."
    docker rmi demo-sandbox_orchestrator demo-sandbox_registry demo-sandbox_frontend 2>/dev/null || true

    echo "  └─ Removing MCP images..."
    docker images | grep "^mcp-" | awk '{print $1":"$2}' | xargs -r docker rmi 2>/dev/null || true
fi

echo ""
# Check if using GHCR images (community edition) or local build
if grep -q "ghcr.io" docker-compose.yml 2>/dev/null; then
    echo "🐳 Using GHCR images (pulling latest)..."
    docker-compose pull
    docker-compose up -d
else
    if [ "$NUKE_MODE" = true ]; then
        echo "🚀 Starting services with FULL REBUILD (no cache)..."
        docker-compose build --no-cache
        docker-compose up -d
    else
        echo "🚀 Starting services fresh..."
        # Source code is now bind-mounted, so rebuilds are only needed for dependency changes
        docker-compose up -d --build
    fi
fi

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ Clean restart complete!"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🌐 Service Endpoints:"
echo "  ├─ Frontend:      http://localhost:3000"
echo "  ├─ API:           http://localhost:8000"
echo "  ├─ Registry:      http://localhost:9000"
echo "  └─ MCPs:          Auto-installed from registry on startup"
echo ""
echo "💡 Useful commands:"
echo "  - View logs:      ./logs.sh [service_name]"
echo "  - Status:         ./status.sh"
echo "  - Stop:           ./stop.sh"
echo "  - Nuclear reset:  ./clean-restart.sh -nuke"
echo ""
echo "ℹ️  Use -nuke option to force rebuild from scratch (no cache)"
echo "   Example: ./clean-restart.sh -nuke"
