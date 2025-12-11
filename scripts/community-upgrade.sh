#!/bin/bash
#
# ADCL Community Edition Upgrade
#
# Upgrades the community edition by:
# 1. Downloading latest release files from GitHub
# 2. Updating local files (configs, agents, teams, workflows, scripts)
# 3. Pulling latest Docker images from GHCR
# 4. Running clean-restart
# 5. Health check
#

set -euo pipefail

# Get script directory and source docker-compose compatibility helper
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/docker-compose-compat.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Files/directories to backup and rollback (must match update list)
BACKUP_ITEMS=(
    "configs"
    "agent-definitions"
    "agent-teams"
    "workflows"
    "mcp_servers"
    "registry"
    "scripts"
    "VERSION"
    "docker-compose.yml"
    "registries.conf"
    "start.sh"
    "stop.sh"
    "clean-restart.sh"
    "install.sh"
    ".env"
)

# Check prerequisites
if ! command -v jq &> /dev/null; then
    echo -e "${RED}ERROR: jq is required for JSON parsing${NC}"
    echo "Install: apt-get install jq  OR  brew install jq"
    exit 1
fi

# Lockfile to prevent concurrent upgrades
LOCKFILE="$ROOT_DIR/.upgrade.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo -e "${RED}ERROR: Upgrade already running${NC}"
    echo "If this is a stale lock, remove: $LOCKFILE"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}ADCL Community Edition Upgrade${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# GitHub repo info
GITHUB_REPO="adcl-io/adcl-community"
GITHUB_API="https://api.github.com/repos/${GITHUB_REPO}"

# Get current version using jq
CURRENT_VERSION="unknown"
if [ -f "$ROOT_DIR/VERSION" ]; then
    CURRENT_VERSION=$(jq -r '.version // "unknown"' "$ROOT_DIR/VERSION" 2>/dev/null || echo "unknown")
fi

echo -e "${BLUE}Current version: ${CURRENT_VERSION}${NC}"
echo ""

# Check for latest release (with optional GitHub token for rate limiting)
echo -e "${BLUE}Checking for latest release...${NC}"
AUTH_HEADER=""
if [ -n "${GITHUB_TOKEN:-}" ]; then
    AUTH_HEADER="Authorization: token $GITHUB_TOKEN"
fi

LATEST_RELEASE=$(curl -sH "${AUTH_HEADER}" "${GITHUB_API}/releases/latest")
LATEST_VERSION=$(echo "$LATEST_RELEASE" | jq -r '.tag_name // empty' | sed 's/^v//')
DOWNLOAD_URL=$(echo "$LATEST_RELEASE" | jq -r '.tarball_url // empty')

if [ -z "$LATEST_VERSION" ]; then
    echo -e "${RED}ERROR: Could not fetch latest release from GitHub${NC}"
    echo "Please check your internet connection and try again."
    echo ""
    echo "If you're hitting rate limits, set GITHUB_TOKEN environment variable:"
    echo "  export GITHUB_TOKEN=ghp_your_token_here"
    exit 1
fi

echo -e "${BLUE}Latest version: ${LATEST_VERSION}${NC}"
echo ""

# Check if already up to date
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo -e "${GREEN}Already running latest version (${CURRENT_VERSION})${NC}"
    echo ""
    read -p "Continue with upgrade anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Upgrade cancelled."
        exit 0
    fi
fi

# Warn about destructive updates
echo -e "${YELLOW}WARNING: This upgrade will replace:${NC}"
echo "  - All agent definitions (custom agents will be backed up but replaced)"
echo "  - All agent teams"
echo "  - All workflows"
echo "  - MCP servers"
echo "  - Registry files"
echo "  - Scripts"
echo ""
echo -e "${BLUE}Your backups and logs will be preserved.${NC}"
echo -e "${BLUE}A backup will be created before upgrade.${NC}"
echo ""
read -p "Continue with upgrade? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled."
    exit 0
fi
echo ""

# Create backup (in .backups/ to avoid root-owned workspace/ permission issues)
echo -e "${BLUE}Creating backup...${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${ROOT_DIR}/.backups/backup_${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

# Backup all items in the list
for item in "${BACKUP_ITEMS[@]}"; do
    if [ -e "$ROOT_DIR/$item" ]; then
        if ! cp -rp "$ROOT_DIR/$item" "$BACKUP_DIR/"; then
            echo -e "${RED}ERROR: Failed to backup $item${NC}"
            exit 1
        fi
        echo "  ✓ Backed up: $item"
    fi
done

# Create backup manifest
cat > "$BACKUP_DIR/manifest.json" <<EOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "version_before": "${CURRENT_VERSION}",
  "version_after": "${LATEST_VERSION}"
}
EOF

echo -e "${GREEN}Backup created: $BACKUP_DIR${NC}"
echo ""

# Rollback function (used on failure)
rollback_from_backup() {
    echo -e "${YELLOW}Rolling back to backup...${NC}"

    for item in "${BACKUP_ITEMS[@]}"; do
        if [ -e "$BACKUP_DIR/$item" ]; then
            rm -rf "$ROOT_DIR/$item"
            cp -rp "$BACKUP_DIR/$item" "$ROOT_DIR/$item"
        fi
    done

    # Restart with old version
    cd "$ROOT_DIR"
    $DOCKER_COMPOSE up -d || true

    echo -e "${RED}Upgrade failed and rolled back${NC}"
    echo "Backup restored from: $BACKUP_DIR"
    echo "Check logs: $DOCKER_COMPOSE logs -f"
}

# Download latest release
echo -e "${BLUE}Downloading latest release (${LATEST_VERSION})...${NC}"
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/adcl-upgrade.XXXXXX")
trap 'rm -rf "$TEMP_DIR"' EXIT

if ! curl -sL "$DOWNLOAD_URL" -o "$TEMP_DIR/release.tar.gz"; then
    echo -e "${RED}ERROR: Failed to download release${NC}"
    exit 1
fi

echo -e "${GREEN}Downloaded release${NC}"
echo ""

# Extract release
echo -e "${BLUE}Extracting release files...${NC}"
mkdir -p "$TEMP_DIR/extracted"
if ! tar -xzf "$TEMP_DIR/release.tar.gz" -C "$TEMP_DIR/extracted" --strip-components=1; then
    echo -e "${RED}ERROR: Failed to extract release${NC}"
    exit 1
fi

EXTRACT_DIR="$TEMP_DIR/extracted"

echo -e "${GREEN}Extracted release${NC}"
echo ""

# Update files
echo -e "${BLUE}Updating files...${NC}"

# Update configs
if [ -d "$EXTRACT_DIR/configs" ]; then
    echo "  ├─ Updating configs..."
    cp -rp "$EXTRACT_DIR/configs"/* "$ROOT_DIR/configs/"
    echo "  │  ✓ Configs updated"
fi

# Update agent definitions
if [ -d "$EXTRACT_DIR/agent-definitions" ]; then
    echo "  ├─ Updating agent definitions..."
    rm -rf "$ROOT_DIR/agent-definitions"
    cp -rp "$EXTRACT_DIR/agent-definitions" "$ROOT_DIR/agent-definitions"
    echo "  │  ✓ Agent definitions updated"
fi

# Update agent teams
if [ -d "$EXTRACT_DIR/agent-teams" ]; then
    echo "  ├─ Updating agent teams..."
    rm -rf "$ROOT_DIR/agent-teams"
    cp -rp "$EXTRACT_DIR/agent-teams" "$ROOT_DIR/agent-teams"
    echo "  │  ✓ Agent teams updated"
fi

# Update workflows
if [ -d "$EXTRACT_DIR/workflows" ]; then
    echo "  ├─ Updating workflows..."
    rm -rf "$ROOT_DIR/workflows"
    cp -rp "$EXTRACT_DIR/workflows" "$ROOT_DIR/workflows"
    echo "  │  ✓ Workflows updated"
fi

# Update MCP servers
if [ -d "$EXTRACT_DIR/mcp_servers" ]; then
    echo "  ├─ Updating MCP servers..."
    rm -rf "$ROOT_DIR/mcp_servers"
    cp -rp "$EXTRACT_DIR/mcp_servers" "$ROOT_DIR/mcp_servers"
    echo "  │  ✓ MCP servers updated"
fi

# Update registry
if [ -d "$EXTRACT_DIR/registry" ]; then
    echo "  ├─ Updating registry..."
    rm -rf "$ROOT_DIR/registry"
    cp -rp "$EXTRACT_DIR/registry" "$ROOT_DIR/registry"
    echo "  │  ✓ Registry updated"
fi

# Update scripts
if [ -d "$EXTRACT_DIR/scripts" ]; then
    echo "  ├─ Updating scripts..."
    cp -rp "$EXTRACT_DIR/scripts"/* "$ROOT_DIR/scripts/"
    find "$ROOT_DIR/scripts" -name "*.sh" -exec chmod +x {} +
    echo "  │  ✓ Scripts updated"
fi

# Update root scripts
for script in start.sh stop.sh clean-restart.sh install.sh; do
    if [ -f "$EXTRACT_DIR/$script" ]; then
        echo "  ├─ Updating $script..."
        cp -p "$EXTRACT_DIR/$script" "$ROOT_DIR/$script"
        chmod +x "$ROOT_DIR/$script"
        echo "  │  ✓ $script updated"
    fi
done

# Update VERSION file
if [ -f "$EXTRACT_DIR/VERSION" ]; then
    echo "  ├─ Updating VERSION..."
    cp -p "$EXTRACT_DIR/VERSION" "$ROOT_DIR/VERSION"
    echo "  │  ✓ VERSION updated"
fi

# Update docker-compose.yml
if [ -f "$EXTRACT_DIR/docker-compose.yml" ]; then
    echo "  ├─ Updating docker-compose.yml..."
    cp -p "$EXTRACT_DIR/docker-compose.yml" "$ROOT_DIR/docker-compose.yml"
    echo "  │  ✓ docker-compose.yml updated"
fi

# Update registries.conf
if [ -f "$EXTRACT_DIR/registries.conf" ]; then
    echo "  └─ Updating registries.conf..."
    cp -p "$EXTRACT_DIR/registries.conf" "$ROOT_DIR/registries.conf"
    echo "     ✓ registries.conf updated"
fi

echo -e "${GREEN}Files updated${NC}"
echo ""

# Pull latest Docker images
echo -e "${BLUE}Pulling latest Docker images...${NC}"
cd "$ROOT_DIR"

if ! $DOCKER_COMPOSE pull; then
    echo -e "${RED}ERROR: Failed to pull Docker images${NC}"
    rollback_from_backup
    exit 1
fi

echo -e "${GREEN}Docker images pulled${NC}"
echo ""

# Run clean-restart
echo -e "${BLUE}Running clean-restart...${NC}"
cd "$ROOT_DIR"

if ! ./clean-restart.sh; then
    echo -e "${RED}ERROR: Clean-restart failed${NC}"
    rollback_from_backup
    exit 1
fi

echo -e "${GREEN}Services restarted${NC}"
echo ""

# Health check
echo -e "${BLUE}Performing health check...${NC}"

MAX_RETRIES=30
retry=0
while [ $retry -lt $MAX_RETRIES ]; do
    # Check if orchestrator container is healthy
    container_health=$(docker inspect --format='{{.State.Health.Status}}' adcl-orchestrator 2>/dev/null || echo "unknown")

    if [ "$container_health" = "healthy" ]; then
        echo -e "${GREEN}Health check passed${NC}"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo -e "${GREEN}Upgrade Complete!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo ""
        echo "Upgraded from: ${CURRENT_VERSION}"
        echo "Upgraded to:   ${LATEST_VERSION}"
        echo ""
        echo "Backup saved at: $BACKUP_DIR"
        echo ""
        echo "Service Endpoints:"
        echo "  - Frontend:  http://localhost:3000"
        echo "  - API:       http://localhost:8000"
        echo "  - Registry:  http://localhost:9000"
        echo ""
        exit 0
    fi

    retry=$((retry + 1))
    echo "  Retry $retry/$MAX_RETRIES (status: $container_health)..."
    sleep 2
done

# Health check failed - rollback
echo -e "${RED}Health check failed${NC}"
rollback_from_backup
exit 1
