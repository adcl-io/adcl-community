#!/bin/bash
#
# ADCL Community Edition Release - Complete Workflow
#
# This script:
#   1. Bumps version
#   2. Cleans code for community edition
#   3. Updates README with install instructions
#   4. Builds and pushes Docker images to GHCR
#   5. Pushes to public GitHub repo (adcl-io/adcl-community)
#   6. Creates GitHub release
#
# Prerequisites:
#   - gh CLI authenticated: gh auth login
#   - Docker logged into GHCR: echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
#   - Public repo cloned at: ../adcl-community

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PUBLIC_REPO_DIR="${REPO_ROOT}/../adcl-community"

cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check prerequisites
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq required${NC}"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) required${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker required${NC}"
    exit 1
fi

if [ ! -d "$PUBLIC_REPO_DIR" ]; then
    echo -e "${RED}Error: Public repo not found at $PUBLIC_REPO_DIR${NC}"
    echo "Clone it first: git clone git@github.com:adcl-io/adcl-community.git ../adcl-community"
    exit 1
fi

GITHUB_REPO="adcl-io/adcl-community"
GHCR_PREFIX="ghcr.io/adcl-io/adcl-community"
VERSION_ARG="${1:-patch}"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}ADCL Community Edition Release${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Step 1: Bump version
echo -e "${BLUE}Step 1: Bumping version...${NC}"
./scripts/bump-version.sh "$VERSION_ARG"
VERSION=$(jq -r '.version' VERSION)
echo -e "${GREEN}✅ Version: ${VERSION}${NC}"

# Step 2: Generate CHANGELOG
echo ""
echo -e "${BLUE}Step 2: Generating CHANGELOG...${NC}"

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    COMMITS=$(git log ${LAST_TAG}..HEAD --oneline --pretty=format:"- %s" 2>/dev/null || echo "- Release v${VERSION}")
else
    COMMITS=$(git log --oneline --pretty=format:"- %s" -10 2>/dev/null || echo "- Release v${VERSION}")
fi

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

echo -e "${GREEN}✅ CHANGELOG updated${NC}"

# Step 3: Clean and prepare public repo
echo ""
echo -e "${BLUE}Step 3: Cleaning code for community edition...${NC}"

# Run clean script to copy and sanitize code
"$SCRIPT_DIR/clean-for-community.sh" "$PUBLIC_REPO_DIR"

cd "$PUBLIC_REPO_DIR"
git pull origin main || true

# Copy install script
cp "$REPO_ROOT/install.sh" "$PUBLIC_REPO_DIR/install.sh"
cp "$REPO_ROOT/VERSION" "$PUBLIC_REPO_DIR/VERSION"
cp "$REPO_ROOT/CHANGELOG.md" "$PUBLIC_REPO_DIR/CHANGELOG.md"

# Create .env.example
cat > "$PUBLIC_REPO_DIR/.env.example" <<'EOF'
# ADCL Community Edition Configuration

# API Keys (add your own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Ports
ORCHESTRATOR_PORT=8000
FRONTEND_PORT=3000
REGISTRY_PORT=9000

# Edition
ADCL_EDITION=community
EOF

# Update README with install instructions
cat > "$PUBLIC_REPO_DIR/README.md" <<EOF
# ADCL Platform - Community Edition

AI-Driven Cyber Lab (ADCL) Platform - Open source AI agent orchestration system.

## Quick Start

Install ADCL in one command:

\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash
\`\`\`

This will:
1. Download configuration files
2. Pull Docker images from GHCR
3. Start the platform

Access the UI at: http://localhost:3000

## Manual Installation

\`\`\`bash
# Clone the repository
git clone https://github.com/adcl-io/adcl-community.git
cd adcl-community

# Create .env file
cp .env.example .env
# Edit .env and add your API keys

# Start the platform
docker compose up -d
\`\`\`

## Configuration

Edit \`.env\` to configure:
- API keys (Anthropic, OpenAI)
- Port numbers
- Other settings

## Images

Docker images are hosted on GitHub Container Registry (GHCR):
- \`ghcr.io/adcl-io/adcl-community/orchestrator:latest\`
- \`ghcr.io/adcl-io/adcl-community/frontend:latest\`
- \`ghcr.io/adcl-io/adcl-community/registry:latest\`

## Version

Current version: **${VERSION}**

## License

See LICENSE file for details.

## Documentation

For full documentation, visit: https://docs.adcl.io

## Support

- Issues: https://github.com/adcl-io/adcl-community/issues
- Discussions: https://github.com/adcl-io/adcl-community/discussions

## Enterprise Edition

For enterprise features, support, and SLA, contact: enterprise@adcl.io
EOF

echo -e "${GREEN}✅ Community edition files prepared${NC}"

# Step 4: Build Docker images
echo ""
echo -e "${BLUE}Step 4: Building Docker images...${NC}"

cd "$REPO_ROOT"

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

# Step 5: Push to GHCR
echo ""
echo -e "${BLUE}Step 5: Pushing images to GHCR...${NC}"

docker push "${GHCR_PREFIX}/orchestrator:${VERSION}"
docker push "${GHCR_PREFIX}/orchestrator:latest"
docker push "${GHCR_PREFIX}/frontend:${VERSION}"
docker push "${GHCR_PREFIX}/frontend:latest"
docker push "${GHCR_PREFIX}/registry:${VERSION}"
docker push "${GHCR_PREFIX}/registry:latest"

echo -e "${GREEN}✅ Images pushed to GHCR${NC}"

# Step 6: Commit to private repo
echo ""
echo -e "${BLUE}Step 6: Committing to private repo...${NC}"

cd "$REPO_ROOT"

if ! git diff --quiet VERSION CHANGELOG.md 2>/dev/null; then
    git add VERSION CHANGELOG.md
    git commit -m "Release v${VERSION}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
    echo -e "${GREEN}✅ Changes committed${NC}"
fi

if ! git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
    echo -e "${GREEN}✅ Tagged v${VERSION}${NC}"
fi

git push origin main
git push origin "v${VERSION}"
echo -e "${GREEN}✅ Pushed to private repo${NC}"

# Step 7: Commit to public repo
echo ""
echo -e "${BLUE}Step 7: Pushing to public repo...${NC}"

cd "$PUBLIC_REPO_DIR"

git add .
git commit -m "Release v${VERSION}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>" || echo "No changes to commit"

if ! git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
fi

git push origin main
git push origin "v${VERSION}"

echo -e "${GREEN}✅ Pushed to public repo${NC}"

# Step 8: Create GitHub release
echo ""
echo -e "${BLUE}Step 8: Creating GitHub release...${NC}"

RELEASE_NOTES=$(awk -v ver="$VERSION" '
    /^## \['"$VERSION"'\]/ { flag=1; next }
    /^## \[/ { flag=0 }
    flag { print }
' "$REPO_ROOT/CHANGELOG.md" | head -50)

if [ -z "$RELEASE_NOTES" ]; then
    RELEASE_NOTES="Release version ${VERSION}"
fi

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
echo "Test it:"
echo "  cd /tmp && rm -rf test-adcl && mkdir test-adcl && cd test-adcl"
echo "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/install.sh | bash"
echo ""
