#!/bin/bash
#
# GitHub + GHCR Release Script - Simple and clean
#
# Usage:
#   ./scripts/release-github.sh              # Auto-increment patch
#   ./scripts/release-github.sh patch        # Bug fixes (0.1.0 → 0.1.1)
#   ./scripts/release-github.sh minor        # New features (0.1.0 → 0.2.0)
#   ./scripts/release-github.sh major        # Breaking changes (0.1.0 → 1.0.0)
#   ./scripts/release-github.sh 1.5.0        # Explicit version
#
# Prerequisites:
#   - gh CLI installed and authenticated: gh auth login
#   - Docker logged into GHCR: echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
#
# This script:
#   1. Bumps version
#   2. Generates CHANGELOG
#   3. Builds Docker images
#   4. Pushes images to GHCR
#   5. Creates GitHub release with tarball
#   6. Commits and tags

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check for required dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Install: sudo apt-get install jq  (or brew install jq on macOS)"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is required but not installed${NC}"
    echo "Install: https://cli.github.com/"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is required but not installed${NC}"
    exit 1
fi

# GitHub config
GITHUB_REPO="adcl-io/adcl-community"
GHCR_PREFIX="ghcr.io/adcl-io/adcl-community"

VERSION_ARG="${1:-patch}"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}ADCL Community Edition Release${NC}"
echo -e "${BLUE}Repository: ${GITHUB_REPO}${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Step 1: Bump version
echo -e "${BLUE}Step 1: Bumping version...${NC}"
./scripts/bump-version.sh "$VERSION_ARG"

# Get the new version
VERSION=$(jq -r '.version' VERSION)
echo -e "${GREEN}✅ Version set to: ${VERSION}${NC}"

# Step 2: Auto-generate CHANGELOG entry
echo ""
echo -e "${BLUE}Step 2: Auto-generating CHANGELOG entry...${NC}"

# Get git commits since last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    COMMITS=$(git log ${LAST_TAG}..HEAD --oneline --pretty=format:"- %s" 2>/dev/null || echo "- Release v${VERSION}")
else
    COMMITS=$(git log --oneline --pretty=format:"- %s" -10 2>/dev/null || echo "- Release v${VERSION}")
fi

# Prepend new entry to CHANGELOG.md
if [ -f "CHANGELOG.md" ]; then
    cat > CHANGELOG.tmp <<EOF
## [${VERSION}] - $(date '+%Y-%m-%d')

### Changes
${COMMITS}

EOF
    cat CHANGELOG.md >> CHANGELOG.tmp
    mv CHANGELOG.tmp CHANGELOG.md
else
    cat > CHANGELOG.md <<EOF
# ADCL Platform Changelog

## [${VERSION}] - $(date '+%Y-%m-%d')

### Changes
${COMMITS}
EOF
fi

echo -e "${GREEN}✅ CHANGELOG.md updated${NC}"

# Step 3: Build Docker images
echo ""
echo -e "${BLUE}Step 3: Building Docker images...${NC}"

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD)

# Build orchestrator
echo -e "${BLUE}  Building orchestrator...${NC}"
docker build \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_COMMIT="$GIT_COMMIT" \
    -t "${GHCR_PREFIX}/orchestrator:${VERSION}" \
    -t "${GHCR_PREFIX}/orchestrator:latest" \
    -f ./backend/Dockerfile \
    ./backend

# Build frontend
echo -e "${BLUE}  Building frontend...${NC}"
docker build \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_COMMIT="$GIT_COMMIT" \
    -t "${GHCR_PREFIX}/frontend:${VERSION}" \
    -t "${GHCR_PREFIX}/frontend:latest" \
    -f ./frontend/Dockerfile \
    ./frontend

# Build registry
echo -e "${BLUE}  Building registry...${NC}"
docker build \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_COMMIT="$GIT_COMMIT" \
    -t "${GHCR_PREFIX}/registry:${VERSION}" \
    -t "${GHCR_PREFIX}/registry:latest" \
    -f ./registry-server/Dockerfile \
    ./registry-server

echo -e "${GREEN}✅ Images built${NC}"

# Step 4: Push to GHCR
echo ""
echo -e "${BLUE}Step 4: Pushing images to GHCR...${NC}"

docker push "${GHCR_PREFIX}/orchestrator:${VERSION}"
docker push "${GHCR_PREFIX}/orchestrator:latest"
docker push "${GHCR_PREFIX}/frontend:${VERSION}"
docker push "${GHCR_PREFIX}/frontend:latest"
docker push "${GHCR_PREFIX}/registry:${VERSION}"
docker push "${GHCR_PREFIX}/registry:latest"

echo -e "${GREEN}✅ Images pushed to GHCR${NC}"

# Step 5: Commit and tag
echo ""
echo -e "${BLUE}Step 5: Git operations...${NC}"

if ! git diff --quiet VERSION CHANGELOG.md 2>/dev/null; then
    echo "Committing VERSION and CHANGELOG.md..."
    git add VERSION CHANGELOG.md
    git commit -m "Release v${VERSION}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
    echo -e "${GREEN}✅ Changes committed${NC}"
fi

if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Tag v${VERSION} already exists${NC}"
else
    echo "Creating git tag v${VERSION}..."
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
    echo -e "${GREEN}✅ Git tag created: v${VERSION}${NC}"
fi

# Step 6: Push to GitHub
echo ""
echo -e "${BLUE}Step 6: Pushing to GitHub...${NC}"
git push origin main
git push origin "v${VERSION}"
echo -e "${GREEN}✅ Pushed to GitHub${NC}"

# Step 7: Create GitHub release
echo ""
echo -e "${BLUE}Step 7: Creating GitHub release...${NC}"

# Extract release notes from CHANGELOG
RELEASE_NOTES=$(awk -v ver="$VERSION" '
    /^## \['"$VERSION"'\]/ { flag=1; next }
    /^## \[/ { flag=0 }
    flag { print }
' CHANGELOG.md | head -50)

if [ -z "$RELEASE_NOTES" ]; then
    RELEASE_NOTES="Release version ${VERSION}"
fi

# Create release (no tarball needed - images are on GHCR)
gh release create "v${VERSION}" \
    --repo "$GITHUB_REPO" \
    --title "v${VERSION} - ADCL Community Edition" \
    --notes "$RELEASE_NOTES"

echo -e "${GREEN}✅ GitHub release created${NC}"

# Summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Release v${VERSION} Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Release URL: https://github.com/${GITHUB_REPO}/releases/tag/v${VERSION}"
echo ""
echo "Docker images:"
echo "  ${GHCR_PREFIX}/orchestrator:${VERSION}"
echo "  ${GHCR_PREFIX}/frontend:${VERSION}"
echo "  ${GHCR_PREFIX}/registry:${VERSION}"
echo ""
echo "Install command:"
echo "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/install.sh | bash"
echo ""
