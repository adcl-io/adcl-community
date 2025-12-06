#!/bin/bash
#
# ADCL Community Edition Upgrade
#
# Simple upgrade for community users:
# - Pull latest Docker images from GHCR
# - Restart containers
# - Health check
#
# No git, no rebuilding, just pull and restart.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}ADCL Community Edition Upgrade${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Detect paths (different inside vs outside container)
if [ -d "/app/workspace" ]; then
    # Inside container
    WORKSPACE_DIR="/app/workspace"
    CONFIGS_DIR="/configs"
    AGENT_DEFS_DIR="/app/agent-definitions"
    AGENT_TEAMS_DIR="/app/agent-teams"
    WORKFLOWS_DIR="/app/workflows"
    VERSION_FILE="/app/VERSION"
    ENV_FILE="/.env"
else
    # Outside container (host)
    WORKSPACE_DIR="workspace"
    CONFIGS_DIR="configs"
    AGENT_DEFS_DIR="agent-definitions"
    AGENT_TEAMS_DIR="agent-teams"
    WORKFLOWS_DIR="workflows"
    VERSION_FILE="VERSION"
    ENV_FILE=".env"
fi

# Create backup
echo -e "${BLUE}Creating backup...${NC}"
timestamp=$(date +%Y%m%d_%H%M%S)
backup_dir="${WORKSPACE_DIR}/backups/backup_${timestamp}"
mkdir -p "$backup_dir"

# Backup critical files
for item in "$CONFIGS_DIR" "$AGENT_DEFS_DIR" "$AGENT_TEAMS_DIR" "$WORKFLOWS_DIR" "$VERSION_FILE" "$ENV_FILE"; do
    if [ -e "$item" ]; then
        if ! cp -r "$item" "$backup_dir/"; then
            echo -e "${RED}ERROR: Failed to backup $item${NC}"
            exit 1
        fi
        echo "  ✓ Backed up: $(basename "$item")"
    fi
done

# Create backup manifest
cat > "$backup_dir/manifest.json" <<EOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "version_before": "$(grep -o '"version": *"[^"]*"' $VERSION_FILE 2>/dev/null | sed 's/"version": *"\(.*\)"/\1/' || echo 'unknown')"
}
EOF

echo -e "${GREEN}✅ Backup created: $backup_dir${NC}"
echo ""

# Detect compose file location
COMPOSE_FILE="/docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

# Validate compose file path (security: prevent injection)
if [[ ! "$COMPOSE_FILE" =~ ^[a-zA-Z0-9./_-]+$ ]]; then
    echo -e "${RED}ERROR: Invalid compose file path${NC}"
    exit 1
fi

# Pull latest images
echo -e "${BLUE}Pulling latest images...${NC}"
if ! docker compose -f "$COMPOSE_FILE" pull; then
    echo -e "${RED}Failed to pull images${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Images pulled${NC}"
echo ""

# Restart containers
echo -e "${BLUE}Restarting containers...${NC}"
if ! docker compose -f "$COMPOSE_FILE" up -d; then
    echo -e "${RED}Failed to restart containers${NC}"
    echo -e "${YELLOW}Rolling back...${NC}"

    # Restore .env if it exists in backup
    if [ -f "$backup_dir/.env" ]; then
        cp "$backup_dir/.env" "$ENV_FILE"
    fi

    docker compose -f "$COMPOSE_FILE" up -d
    echo -e "${RED}Upgrade failed, rolled back to previous version${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Containers restarted${NC}"
echo ""

# Health check - wait for container to be healthy, not just running
echo -e "${BLUE}Checking health...${NC}"

max_retries=30
retry=0
while [ $retry -lt $max_retries ]; do
    # Check if orchestrator container is healthy
    container_health=$(docker inspect --format='{{.State.Health.Status}}' adcl-orchestrator 2>/dev/null || echo "unknown")

    if [ "$container_health" = "healthy" ]; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo -e "${GREEN}✅ Upgrade Complete!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo ""
        echo "Backup saved at: $backup_dir"
        echo ""
        exit 0
    fi

    retry=$((retry + 1))
    echo "  Retry $retry/$max_retries (status: $container_health)..."
    sleep 2
done

# Health check failed - rollback
echo -e "${RED}Health check failed${NC}"
echo -e "${YELLOW}Rolling back to backup...${NC}"

# Restore .env
if [ -f "$backup_dir/.env" ]; then
    cp "$backup_dir/.env" "$ENV_FILE"
fi

# Restart with old config
docker compose -f "$COMPOSE_FILE" up -d

echo -e "${RED}Upgrade failed and rolled back${NC}"
echo "Check logs: docker compose -f $COMPOSE_FILE logs -f"
exit 1
