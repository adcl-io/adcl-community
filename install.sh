#!/bin/bash
# ADCL Community Edition Installer
#
# Usage:
#   mkdir adcl && cd adcl
#   curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash

set -e

echo "🚀 Installing ADCL Community Edition..."
echo ""

# Clone the repository to current directory
echo "📥 Downloading ADCL..."
git clone https://github.com/adcl-io/adcl-community.git .

# Create .env from example
echo "⚙️  Creating .env file..."
cp .env.example .env
echo "✅ Created .env - edit this file to add your API keys"
echo ""

# Remove any ADCL containers (stopped or running)
echo "🔍 Checking for conflicting containers..."
REMOVED=""
for NAME in adcl-orchestrator adcl-frontend adcl-registry; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${NAME}$"; then
        echo "  Removing ${NAME}..."
        docker rm -f "$NAME" || true
        REMOVED="yes"
    fi
done
[ -n "$REMOVED" ] && echo "✅ Cleaned up old containers"

# Pull and start
echo ""
echo "🐳 Pulling images..."
docker compose pull

echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "✅ ADCL Community Edition installed!"
echo ""
echo "🌐 http://localhost:3000  (Frontend)"
echo "🔧 http://localhost:8000  (API)"
echo "📦 http://localhost:9000  (Registry)"
echo ""
echo "docker compose ps          # Check status"
echo "docker compose logs -f     # View logs"
echo "./stop.sh                  # Stop all"
echo "./start.sh                 # Start all"
echo "./clean-restart.sh         # Clean restart"
echo ""
