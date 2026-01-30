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
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/docker-compose-compat.sh"

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
echo "📁 Project: $PROJECT_ROOT"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "dist/docker-compose.yml" ]; then
    echo "❌ Error: dist/docker-compose.yml not found"
    exit 1
fi

echo "🛑 Stopping all containers..."
echo ""

# First, stop and remove dynamically installed MCP containers
echo "  ├─ Removing dynamic MCP containers..."
# Dynamically find all mcp-* containers
MCP_CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep '^mcp-' || true)
if [ -n "$MCP_CONTAINERS" ]; then
    for container in $MCP_CONTAINERS; do
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
        echo "     ├─ Removing $container..."
        docker rm $container 2>/dev/null || true
    done
else
    echo "     └─ No MCP containers found"
fi

# Remove Vulhub containers (they're also on mcp-network)
echo "  ├─ Removing Vulhub containers..."
VULHUB_CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep '^vulhub-' || true)
if [ -n "$VULHUB_CONTAINERS" ]; then
    for container in $VULHUB_CONTAINERS; do
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
        echo "     ├─ Removing $container..."
        docker rm $container 2>/dev/null || true
    done
else
    echo "     └─ No Vulhub containers found"
fi

# Remove legacy demo-sandbox containers (from before directory restructure)
echo "  ├─ Removing legacy demo-sandbox containers..."
LEGACY_CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep -E '^demo-sandbox[_-]' || true)
if [ -n "$LEGACY_CONTAINERS" ]; then
    for container in $LEGACY_CONTAINERS; do
        echo "     ├─ Stopping $container..."
        docker stop $container 2>/dev/null || true
        echo "     ├─ Removing $container..."
        docker rm $container 2>/dev/null || true
    done
else
    echo "     └─ No legacy containers found"
fi

# Then stop and remove docker-compose containers
echo "  └─ Stopping docker-compose services..."
$DOCKER_COMPOSE down

echo ""
echo "✅ All containers stopped and removed"

# Sync Vulhub backend state (if backend is running)
echo ""
echo "🔄 Syncing Vulhub state with backend..."
if curl -s -X POST http://localhost:8000/api/vulhub/instances/sync > /dev/null 2>&1; then
    echo "  ✓ Vulhub state synced"
else
    echo "  ⚠  Backend not running or Vulhub sync failed (this is okay if backend is stopped)"
fi

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

# Clean up runtime state files (they reference dead containers after nuke)
echo ""
echo "🗑️  Cleaning up runtime state..."
STATE_DIR="var/volumes/state"
if [ -d "$STATE_DIR" ]; then
    echo "  ├─ Removing $STATE_DIR/installed-mcps.json..."
    rm -f "$STATE_DIR/installed-mcps.json"
    echo "  ├─ Removing $STATE_DIR/installed-triggers.json..."
    rm -f "$STATE_DIR/installed-triggers.json"
    echo "  └─ State cleaned"
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
