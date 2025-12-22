#!/bin/bash
# Nuclear option - Stop and remove ALL containers and images
# Does NOT restart. Use ./start.sh to restart after nuking.
#
# Usage:
#   ./nuke.sh              # Stop and remove containers
#   ./nuke.sh --images     # Also remove images
#   ./nuke.sh --full       # Remove containers, images, and volumes

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

# Parse arguments
REMOVE_IMAGES=false
REMOVE_VOLUMES=false

for arg in "$@"; do
    case $arg in
        --images)
            REMOVE_IMAGES=true
            ;;
        --full)
            REMOVE_IMAGES=true
            REMOVE_VOLUMES=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./nuke.sh [--images] [--full]"
            exit 1
            ;;
    esac
done

echo "╔══════════════════════════════════════════════════════╗"
echo "║     ☢️  NUCLEAR OPTION - REMOVE ALL CONTAINERS ☢️    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Project: $SCRIPT_DIR"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    exit 1
fi

echo "🛑 Stopping all containers..."
echo ""

# First, stop and remove dynamically installed MCP containers
echo "  ├─ Removing dynamic MCP containers..."
for container in mcp-agent mcp-file-tools mcp-nmap-recon mcp-history; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
        echo "     ├─ Removing $container..."
        docker rm $container 2>/dev/null || true
    fi
done

# Then stop and remove docker-compose containers
echo "  └─ Stopping docker-compose services..."
$DOCKER_COMPOSE down

echo ""
echo "✅ All containers stopped and removed"

if [ "$REMOVE_IMAGES" = true ]; then
    echo ""
    echo "🗑️  Removing images..."
    echo "  ├─ Removing orchestrator, registry, and frontend images..."
    docker rmi demo-sandbox_orchestrator demo-sandbox_registry demo-sandbox_frontend 2>/dev/null || echo "     (some images may not exist)"

    echo "  └─ Removing MCP images..."
    docker images | grep "^mcp-" | awk '{print $1":"$2}' | xargs -r docker rmi 2>/dev/null || echo "     (no MCP images found)"

    echo ""
    echo "✅ Images removed"
fi

if [ "$REMOVE_VOLUMES" = true ]; then
    echo ""
    echo "🗑️  Removing volumes..."
    $DOCKER_COMPOSE down -v
    echo "✅ Volumes removed"
fi

echo ""
echo "══════════════════════════════════════════════════════"
echo "☢️  NUKE COMPLETE"
echo "══════════════════════════════════════════════════════"
echo ""
echo "To restart the platform, run:"
echo "  ./start.sh              # Normal start"
echo "  ./clean-restart.sh      # Clean start with rebuild"
echo ""
