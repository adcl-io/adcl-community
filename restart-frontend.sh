#!/bin/bash
# Restart Frontend

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔄 Restarting Frontend..."
echo "📁 Project: $SCRIPT_DIR"
echo ""
docker-compose restart frontend

echo ""
echo "✅ Frontend restarted"
echo ""
docker-compose ps frontend

echo ""
echo "Frontend available at: http://localhost:3000"
echo "View logs: docker-compose logs -f frontend"
