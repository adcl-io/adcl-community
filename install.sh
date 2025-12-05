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

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 ADCL directory exists at $INSTALL_DIR"
    echo "   Updating installation..."
    cd "$INSTALL_DIR"

    # Pull latest changes if it's a git repo
    if [ -d .git ]; then
        git pull origin main 2>/dev/null || true
    else
        # Backup existing .env if it exists
        [ -f .env ] && cp .env .env.backup

        # Remove old files and re-clone
        cd ..
        rm -rf "$INSTALL_DIR"
        git clone --depth 1 https://github.com/adcl-io/adcl-community.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"

        # Restore .env
        [ -f .env.backup ] && mv .env.backup .env
    fi
else
    echo "📥 Downloading ADCL Community Edition..."
    git clone --depth 1 https://github.com/adcl-io/adcl-community.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create runtime directories
mkdir -p workspace logs

# Create .env if doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Configuring ADCL..."
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
    echo ""
    echo "ℹ️  Remember to add your API keys to ~/.adcl/.env:"
    echo "   ANTHROPIC_API_KEY=your-key-here"
    echo "   OPENAI_API_KEY=your-key-here"
fi

# Check for port conflicts and auto-stop conflicting containers
echo "🔍 Checking for port conflicts..."
STOPPED_CONTAINERS=""
for PORT in 3000 8000 9000; do
    CONTAINER=$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E ":${PORT}->" | awk '{print $1}' | head -1 || true)
    if [ -n "$CONTAINER" ]; then
        if [ -z "$STOPPED_CONTAINERS" ]; then
            echo "🛑 Stopping conflicting containers to free up ports..."
        fi
        echo "  Stopping ${CONTAINER} (using port ${PORT})..."
        docker stop "$CONTAINER" 2>/dev/null || true
        STOPPED_CONTAINERS="${STOPPED_CONTAINERS} ${CONTAINER}"
    fi
done

if [ -n "$STOPPED_CONTAINERS" ]; then
    echo "✅ Stopped containers:${STOPPED_CONTAINERS}"
fi

# Clean up any existing ADCL containers
echo "🧹 Cleaning up old ADCL containers..."
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
echo "🌐 Access the UI at: http://localhost:3000"
echo "🔧 Backend API at: http://localhost:8000"
echo ""
echo "📁 Installation directory: $INSTALL_DIR"
echo ""
echo "Commands:"
echo "  Stop:      cd $INSTALL_DIR && docker compose down"
echo "  Logs:      cd $INSTALL_DIR && docker compose logs -f"
echo "  Status:    cd $INSTALL_DIR && docker compose ps"
echo "  Update:    curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash"
echo ""
echo "📚 Documentation: https://github.com/adcl-io/adcl-community"
echo ""
