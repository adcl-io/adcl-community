#!/bin/bash
#
# Load Docker images from tarball for airgap deployment
#
# Usage: ./scripts/load-images.sh <tarball-path>
#        ./adcl load-images ./images/adcl-1.0.0.tar
#
# This script loads pre-built Docker images from a tarball for
# offline/airgap installations where internet access is not available.

set -euo pipefail

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# In production, scripts are in dist/scripts/, so PROJECT_ROOT is dist/
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
TARBALL_PATH="${1:-}"

if [ -z "$TARBALL_PATH" ]; then
    echo -e "${RED}❌ Error: Tarball path required${NC}"
    echo ""
    echo "Usage: $0 <tarball-path>"
    echo ""
    echo "Examples:"
    echo "  $0 ./images/adcl-1.0.0.tar"
    echo "  $0 /path/to/adcl-images.tar"
    echo ""
    exit 1
fi

# Check if tarball exists
if [ ! -f "$TARBALL_PATH" ]; then
    echo -e "${RED}❌ Error: Tarball not found: $TARBALL_PATH${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════╗"
echo "║     ADCL Platform - Load Images (Airgap)            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}📦 Tarball:${NC} $TARBALL_PATH"
echo -e "${BLUE}📊 Size:${NC}    $(du -h "$TARBALL_PATH" | cut -f1)"
echo ""

# Load images from tarball
echo -e "${BLUE}📥 Loading Docker images...${NC}"
echo ""

if docker load -i "$TARBALL_PATH"; then
    echo ""
    echo -e "${GREEN}✅ Images loaded successfully!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Failed to load images${NC}"
    exit 1
fi

# Verify loaded images
echo -e "${BLUE}📋 Loaded images:${NC}"
docker images | grep -E "(adcl|ghcr.io/adcl)" || echo "  (No ADCL images found - check tarball contents)"
echo ""

# Check if images are tagged correctly for docker-compose.yml
echo -e "${BLUE}🔍 Verifying image tags...${NC}"

REGISTRY=${REGISTRY:-ghcr.io/adcl}
VERSION=${VERSION:-latest}

REQUIRED_IMAGES=(
    "${REGISTRY}/backend:${VERSION}"
    "${REGISTRY}/frontend:${VERSION}"
    "${REGISTRY}/registry:${VERSION}"
)

MISSING_IMAGES=0
for image in "${REQUIRED_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"; then
        echo -e "  ${GREEN}✓${NC} $image"
    else
        echo -e "  ${RED}✗${NC} $image (missing)"
        MISSING_IMAGES=$((MISSING_IMAGES + 1))
    fi
done

echo ""

if [ $MISSING_IMAGES -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Some required images are missing or incorrectly tagged${NC}"
    echo ""
    echo "Expected image format: ${REGISTRY}/<service>:${VERSION}"
    echo ""
    echo "If images are tagged differently, you may need to:"
    echo "  1. Re-tag images: docker tag <source> <target>"
    echo "  2. Update .env file with correct REGISTRY and VERSION"
    echo ""
fi

echo "Next steps:"
echo "  1. Verify images:  docker images"
echo "  2. Start platform: ./adcl start"
echo ""

