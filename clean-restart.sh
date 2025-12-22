#!/bin/bash
# Clean restart - Stops, removes, and starts all services
# Use this to avoid ContainerConfig errors
#
# Usage:
#   ./clean-restart.sh         # Normal clean restart (uses cache)
#   ./clean-restart.sh --force # Force rebuild without cache
#   ./nuke.sh                  # To stop/remove WITHOUT restarting

set -e

# Parse arguments
NUKE_MODE=false
if [ "$1" == "--force" ]; then
    NUKE_MODE=true
elif [ "$1" == "-nuke" ] || [ "$1" == "--nuke" ]; then
    echo "❌ Error: -nuke flag is deprecated"
    echo ""
    echo "Use instead:"
    echo "  ./clean-restart.sh --force    # Clean restart with force rebuild (no cache)"
    echo "  ./nuke.sh                     # Stop and remove all (no restart)"
    echo "  ./nuke.sh --images            # Also remove images"
    echo "  ./nuke.sh --full              # Remove containers, images, and volumes"
    echo ""
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

echo "╔══════════════════════════════════════════════════════╗"
if [ "$NUKE_MODE" = true ]; then
    echo "║     MCP Agent Platform - FORCE REBUILD               ║"
    echo "║     (Rebuild from scratch without cache)            ║"
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

# First, remove dynamically installed MCP containers
echo "  └─ Removing dynamic MCP containers..."
for container in mcp-agent mcp-file-tools mcp-nmap-recon mcp-history; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
        echo "     ├─ Removing $container..."
        docker rm $container 2>/dev/null || true
    fi
done

# Then run docker-compose down
$DOCKER_COMPOSE down

if [ "$NUKE_MODE" = true ]; then
    echo ""
    echo "🔨 FORCE REBUILD: Removing images to force clean rebuild..."
    echo "  └─ Removing orchestrator, registry, and frontend images..."
    docker rmi demo-sandbox_orchestrator demo-sandbox_registry demo-sandbox_frontend 2>/dev/null || true

    echo "  └─ Removing MCP images..."
    docker images | grep "^mcp-" | awk '{print $1":"$2}' | xargs -r docker rmi 2>/dev/null || true
fi

echo ""
if [ "$NUKE_MODE" = true ]; then
    echo "🚀 Starting services with FULL REBUILD (no cache)..."
    $DOCKER_COMPOSE build --no-cache
    $DOCKER_COMPOSE up -d
else
    echo "🚀 Starting services fresh..."
    # Source code is now bind-mounted, so rebuilds are only needed for dependency changes
    $DOCKER_COMPOSE up -d --build
fi

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ Clean restart complete!"
echo ""
echo "📊 Service Status:"
$DOCKER_COMPOSE ps

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
echo "  - Force rebuild:  ./clean-restart.sh --force"
echo "  - Nuclear option: ./nuke.sh (stop/remove without restart)"
echo ""
echo "ℹ️  Options:"
echo "   ./clean-restart.sh --force    # Force rebuild from scratch (no cache)"
echo "   ./nuke.sh                     # Stop and remove all (no restart)"
echo "   ./nuke.sh --images            # Also remove images"
echo "   ./nuke.sh --full              # Remove everything (containers, images, volumes)"
