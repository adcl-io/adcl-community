#!/bin/bash
# ADCL Community Edition Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash

set -e

echo "🚀 Installing ADCL Community Edition..."
echo ""

# Create installation directory
INSTALL_DIR="adcl"
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory '$INSTALL_DIR' already exists"
    COUNTER=1
    while [ -d "${INSTALL_DIR}-${COUNTER}" ]; do
        COUNTER=$((COUNTER + 1))
    done
    INSTALL_DIR="${INSTALL_DIR}-${COUNTER}"
    echo "📁 Using '$INSTALL_DIR' instead"
fi

echo "📁 Creating directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

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
echo "✅ ADCL Community Edition installed in $(pwd)!"
echo ""
echo "🌐 http://localhost:3000  (Frontend)"
echo "🔧 http://localhost:8000  (API)"
echo "📦 http://localhost:9000  (Registry)"
echo ""
echo "Next steps:"
echo "  cd $INSTALL_DIR"
echo ""
echo "Then run:"
echo "  docker compose ps          # Check status"
echo "  docker compose logs -f     # View logs"
echo "  ./stop.sh                  # Stop all"
echo "  ./start.sh                 # Start all"
echo "  ./clean-restart.sh         # Clean restart"
echo ""
