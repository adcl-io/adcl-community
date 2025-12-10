#!/bin/bash
# Status script for MCP Agent Platform

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

echo "╔══════════════════════════════════════════════════════╗"
echo "║     MCP Agent Platform - Status Check               ║"
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
    echo "❌ Error: docker-compose.yml not found in this directory"
    echo "   Make sure you're in the test3-dev-team directory"
    exit 1
fi

echo "📊 Container Status:"
echo ""
echo "Docker Compose Services:"
$DOCKER_COMPOSE ps

echo ""
echo "Dynamic MCP Containers:"
if docker ps -a --filter "name=mcp-" --format "table {{.Names}}\t{{.Status}}" | tail -n +2 | grep -q .; then
    docker ps -a --filter "name=mcp-" --format "table {{.Names}}\t{{.Status}}"
else
    echo "  (No dynamic MCPs installed yet - will auto-install on orchestrator startup)"
fi

echo ""
echo "🌐 Service Endpoints:"
echo "  ├─ Frontend:      http://localhost:3000"
echo "  ├─ API:           http://localhost:8000"
echo "  └─ Registry:      http://localhost:9000"
echo ""

# Check if services are responding
echo "🔍 Health Checks:"

# Check API
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ API Server (port 8000) - UP"
else
    echo "  ❌ API Server (port 8000) - DOWN"
fi

# Check Registry
if curl -s http://localhost:9000/health > /dev/null 2>&1; then
    echo "  ✅ Registry (port 9000) - UP"
else
    echo "  ❌ Registry (port 9000) - DOWN"
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✅ Frontend (port 3000) - UP"
else
    echo "  ❌ Frontend (port 3000) - DOWN"
fi

# Check dynamic MCPs via API
echo ""
echo "  Dynamic MCPs (via API):"
if curl -s http://localhost:8000/mcps/installed > /dev/null 2>&1; then
    MCPS_JSON=$(curl -s http://localhost:8000/mcps/installed)
    if [ -n "$MCPS_JSON" ] && [ "$MCPS_JSON" != "[]" ]; then
        echo "$MCPS_JSON" | python3 -c "import sys, json; mcps = json.load(sys.stdin); [print(f'    {'✅' if m['running'] else '❌'} {m['name']} v{m['version']} - {m['state']}') for m in mcps]" 2>/dev/null || echo "    ⚠️  Unable to parse MCP status"
    else
        echo "    ℹ️  No MCPs installed yet (will auto-install on startup)"
    fi
else
    echo "    ⚠️  API not responding"
fi

echo ""
echo "💡 Useful commands:"
echo "  - View logs:    $DOCKER_COMPOSE logs -f [service_name]"
echo "  - Restart:      $DOCKER_COMPOSE restart [service_name]"
echo "  - Stop all:     ./stop.sh"
echo "  - Start all:    ./start.sh"
