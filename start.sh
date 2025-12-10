#!/bin/bash
# Quick start script for MCP Agent Platform

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

echo "╔══════════════════════════════════════════════════════╗"
echo "║     MCP Agent Platform - Phase 1 Demo               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Project: $SCRIPT_DIR"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found"
    echo "   Make sure you're running from the test3-dev-team directory"
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "ℹ️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "   Note: Agent will use mock responses unless ANTHROPIC_API_KEY is set"
    echo ""
fi

# Check if services are already running
RUNNING_CONTAINERS=$($DOCKER_COMPOSE ps -q 2>/dev/null | wc -l)
if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
    echo "⚠️  Some services are already running"
    echo ""
    $DOCKER_COMPOSE ps
    echo ""
    echo "To avoid ContainerConfig errors, use one of these options:"
    echo "  1. Clean restart:  ./clean-restart.sh    (recommended)"
    echo "  2. Stop first:     ./stop.sh && ./start.sh"
    echo "  3. Force anyway:   Press Enter to continue"
    echo ""
    read -p "Press Enter to force start anyway (may cause errors) or Ctrl+C to cancel: "
    echo ""
    echo "⚠️  Forcing start with running containers..."
    echo "   If you get ContainerConfig errors, use ./clean-restart.sh instead"
    echo ""
fi

echo "🚀 Starting MCP Agent Platform..."
echo ""
echo "Services will be available at:"
echo "  - Frontend:      http://localhost:3000"
echo "  - API:           http://localhost:8000"
echo "  - Registry:      http://localhost:9000"
echo "  - MCPs:          Auto-installed from registry on startup"
echo ""

# Start services in detached mode
$DOCKER_COMPOSE up -d --build

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 Checking status..."
$DOCKER_COMPOSE ps
echo ""
echo "To view logs: $DOCKER_COMPOSE logs -f [service_name]"
echo "To stop: ./stop.sh"
echo "To check status: ./status.sh"
