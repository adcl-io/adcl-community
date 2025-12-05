#!/bin/bash
#
# Load Docker images from tarballs
#
# Usage: ./scripts/load-images.sh [version]
#
# If version not specified, uses ADCL_VERSION from .env or "latest"

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Get version
VERSION=${1:-${ADCL_VERSION:-latest}}

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🐳 Loading ADCL Platform Docker Images${NC}"
echo "Version: $VERSION"
echo ""

# Function to load image tarball
load_image() {
    local name=$1
    local tarball="${name}-${VERSION}.tar.gz"

    if [ -f "$tarball" ]; then
        echo -e "${BLUE}📥 Loading ${name}...${NC}"
        docker load < "$tarball"
        echo -e "${GREEN}✅ Loaded ${name}${NC}"
    else
        echo -e "${YELLOW}⚠️  ${tarball} not found, skipping${NC}"
    fi
}

# Load all images
load_image "adcl-orchestrator"
load_image "adcl-frontend"
load_image "adcl-registry"

echo ""
echo -e "${GREEN}✅ Images loaded successfully!${NC}"
echo ""
echo "Verify images:"
echo "  docker images | grep adcl"
echo ""
echo "Start platform:"
echo "  docker compose up -d"
echo ""
