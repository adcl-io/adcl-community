#!/bin/bash
#
# Build Docker images and save as tarballs for S3 distribution
#
# Usage: ./scripts/build-images.sh <version>
#
# Creates compressed image tarballs ready for S3 upload

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root is parent of scripts directory
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Check for required dependencies
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is required but not installed"
    echo "Install: sudo apt-get install jq  (or brew install jq on macOS)"
    exit 1
fi

# Determine version
VERSION_ARG="${1:-}"

if [ -z "$VERSION_ARG" ]; then
    # No argument - read from VERSION file
    if [ ! -f "VERSION" ]; then
        echo "❌ Error: VERSION file not found"
        exit 1
    fi
    VERSION=$(jq -r '.version' VERSION)
    echo "Using current version from VERSION file: $VERSION"
elif [[ "$VERSION_ARG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Explicit version provided
    VERSION="$VERSION_ARG"
    echo "Using explicit version: $VERSION"
else
    echo "❌ Error: Invalid version: $VERSION_ARG"
    echo ""
    echo "Usage: $0 [version]"
    echo ""
    echo "Examples:"
    echo "  $0                # Use current version from VERSION file"
    echo "  $0 1.5.0          # Build specific version"
    echo ""
    echo "Note: To increment version, run ./scripts/bump-version.sh first"
    exit 1
fi

echo ""

# Configuration
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
OUTPUT_DIR="${REPO_ROOT}/release-artifacts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 Building ADCL Platform Docker Images${NC}"
echo "Version: $VERSION"
echo "Commit: $GIT_COMMIT"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to build and save image
build_and_save_image() {
    local name=$1
    local context=$2
    local dockerfile=${3:-Dockerfile}

    echo -e "${BLUE}📦 Building adcl-${name}...${NC}"

    docker build \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg GIT_COMMIT="$GIT_COMMIT" \
        -t "adcl-${name}:${VERSION}" \
        -t "adcl-${name}:latest" \
        -f "${context}/${dockerfile}" \
        "${context}"

    echo -e "${BLUE}💾 Saving adcl-${name} to tarball...${NC}"

    # Save image as compressed tarball
    docker save "adcl-${name}:${VERSION}" "adcl-${name}:latest" | \
        gzip > "${OUTPUT_DIR}/adcl-${name}-${VERSION}.tar.gz"

    # Generate checksum
    (cd "$OUTPUT_DIR" && sha256sum "adcl-${name}-${VERSION}.tar.gz" > "adcl-${name}-${VERSION}.tar.gz.sha256")

    local size=$(du -h "${OUTPUT_DIR}/adcl-${name}-${VERSION}.tar.gz" | cut -f1)
    echo -e "${GREEN}✅ Saved adcl-${name} (${size})${NC}"
}

# Build and save all images
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Building and Saving Images${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

build_and_save_image "orchestrator" "./backend"
build_and_save_image "frontend" "./frontend"
build_and_save_image "registry" "./registry-server"

# Create combined checksum file
echo ""
echo -e "${BLUE}📝 Creating combined checksums file...${NC}"
cat "${OUTPUT_DIR}"/adcl-*.tar.gz.sha256 > "${OUTPUT_DIR}/images-${VERSION}.sha256"

# Summary
echo ""
echo -e "${GREEN}✅ All images built and saved successfully!${NC}"
echo ""
echo "Image tarballs in ${OUTPUT_DIR}:"
ls -lh "${OUTPUT_DIR}"/adcl-*.tar.gz | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Total size: $(du -sh "$OUTPUT_DIR" | cut -f1)"
echo ""
echo "Next steps:"
echo "  1. Upload to S3:"
echo "     ./scripts/publish-release.sh ${VERSION}"
echo ""
echo "  2. Test loading locally:"
echo "     docker load < ${OUTPUT_DIR}/adcl-orchestrator-${VERSION}.tar.gz"
echo ""
