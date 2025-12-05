#!/bin/bash
# ADCL Community Edition Installer
# curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash

set -e

echo "🚀 Installing ADCL Community Edition..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found."
    exit 1
fi

# Create installation directory
INSTALL_DIR="${HOME}/.adcl"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download docker-compose.yml
echo "📥 Downloading configuration..."
curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/docker-compose.yml -o docker-compose.yml

# Create .env if doesn't exist
if [ ! -f .env ]; then
    cat > .env <<'ENVEOF'
# ADCL Platform Configuration
ADCL_EDITION=community

# API Keys (add your own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Ports
ORCHESTRATOR_PORT=8000
FRONTEND_PORT=3000
REGISTRY_PORT=9000
ENVEOF
    echo "✅ Created .env file"
fi

# Clean up any existing ADCL containers
echo "🧹 Cleaning up old containers..."
docker ps -a --filter "name=adcl-" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true
docker compose down --remove-orphans 2>/dev/null || true

# Pull images from GHCR and start
echo "🐳 Pulling images from GHCR..."
docker compose pull

echo "🚀 Starting ADCL Platform..."
docker compose up -d

echo ""
echo "✅ ADCL Community Edition installed!"
echo ""
echo "Access at: http://localhost:3000"
echo ""
echo "Commands:"
echo "  Stop:   docker compose down"
echo "  Logs:   docker compose logs -f"
echo "  Update: curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash"
echo ""
