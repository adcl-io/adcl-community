#!/bin/bash
# Restart Agent MCP server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔄 Restarting Agent MCP Server..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
docker-compose restart agent

echo ""
echo "✅ Agent MCP Server restarted"
echo ""
docker-compose ps agent

echo ""
echo "View logs: docker-compose logs -f agent"
