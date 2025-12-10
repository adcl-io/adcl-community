#!/bin/bash
# View logs for MCP Agent Platform

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Source docker-compose compatibility helper
source "$SCRIPT_DIR/scripts/docker-compose-compat.sh"

SERVICE="${1:-all}"

echo "╔══════════════════════════════════════════════════════╗"
echo "║     MCP Agent Platform - Logs                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📁 Project: $SCRIPT_DIR"
echo ""

if [ "$SERVICE" = "all" ]; then
    echo "📋 Viewing logs for ALL docker-compose services (Ctrl+C to exit)"
    echo ""
    $DOCKER_COMPOSE logs -f
elif [ "$SERVICE" = "api" ] || [ "$SERVICE" = "orchestrator" ]; then
    echo "📋 Viewing logs for API Server (Ctrl+C to exit)"
    echo ""
    $DOCKER_COMPOSE logs -f orchestrator
elif [ "$SERVICE" = "registry" ]; then
    echo "📋 Viewing logs for Registry (Ctrl+C to exit)"
    echo ""
    $DOCKER_COMPOSE logs -f registry
elif [ "$SERVICE" = "frontend" ]; then
    echo "📋 Viewing logs for Frontend (Ctrl+C to exit)"
    echo ""
    $DOCKER_COMPOSE logs -f frontend
elif [ "$SERVICE" = "agent" ] || [ "$SERVICE" = "mcp-agent" ]; then
    echo "📋 Viewing logs for Agent MCP (Ctrl+C to exit)"
    echo ""
    docker logs -f mcp-agent 2>&1 || echo "❌ mcp-agent container not found"
elif [ "$SERVICE" = "file" ] || [ "$SERVICE" = "file_tools" ] || [ "$SERVICE" = "mcp-file-tools" ]; then
    echo "📋 Viewing logs for File Tools MCP (Ctrl+C to exit)"
    echo ""
    docker logs -f mcp-file-tools 2>&1 || echo "❌ mcp-file-tools container not found"
elif [ "$SERVICE" = "nmap" ] || [ "$SERVICE" = "nmap_recon" ] || [ "$SERVICE" = "mcp-nmap-recon" ]; then
    echo "📋 Viewing logs for Nmap Recon MCP (Ctrl+C to exit)"
    echo ""
    docker logs -f mcp-nmap-recon 2>&1 || echo "❌ mcp-nmap-recon container not found"
else
    echo "❌ Unknown service: $SERVICE"
    echo ""
    echo "Usage: ./logs.sh [service]"
    echo ""
    echo "Available services:"
    echo "  Docker Compose:"
    echo "    - all (default) - All docker-compose services"
    echo "    - api/orchestrator"
    echo "    - registry"
    echo "    - frontend"
    echo "  Dynamic MCPs:"
    echo "    - agent/mcp-agent"
    echo "    - file_tools/mcp-file-tools"
    echo "    - nmap_recon/mcp-nmap-recon"
    exit 1
fi
