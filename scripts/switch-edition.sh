#!/bin/bash
# Copyright (c) 2025 adcl.io
# ADCL Edition Switcher - Switch between product editions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EDITIONS_DIR="$PROJECT_ROOT/configs/editions"
TARGET_CONFIG="$PROJECT_ROOT/configs/auto-install.json"
BACKUP_DIR="$PROJECT_ROOT/configs/backups"

# Usage
usage() {
  echo "Usage: $0 <edition>"
  echo ""
  echo "Available editions:"
  echo "  community    - Core platform only (open source)"
  echo "  red-team     - Full platform with security features"
  echo "  custom       - Your custom edition"
  echo ""
  echo "Examples:"
  echo "  $0 community"
  echo "  $0 red-team"
  echo "  $0 my-custom"
  echo ""
  echo "Note: Backend restart required for changes to take effect"
  exit 1
}

# Check arguments
if [ -z "$1" ]; then
  echo -e "${RED}❌ Error: No edition specified${NC}"
  usage
fi

EDITION=$1
EDITION_FILE="$EDITIONS_DIR/$EDITION.json"

# Verify edition file exists
if [ ! -f "$EDITION_FILE" ]; then
  echo -e "${RED}❌ Error: Edition '$EDITION' not found${NC}"
  echo ""
  echo "Available editions in $EDITIONS_DIR/:"
  ls -1 "$EDITIONS_DIR"/*.json 2>/dev/null | xargs -n1 basename | sed 's/.json$//' | sed 's/^/  - /'
  echo ""
  exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup current config
if [ -f "$TARGET_CONFIG" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  CURRENT_EDITION=$(cat "$TARGET_CONFIG" | grep -o '"edition": "[^"]*"' | cut -d'"' -f4 || echo "unknown")
  BACKUP_FILE="$BACKUP_DIR/auto-install-${CURRENT_EDITION}-${TIMESTAMP}.json"

  echo -e "${BLUE}📦 Backing up current config...${NC}"
  cp "$TARGET_CONFIG" "$BACKUP_FILE"
  echo -e "${GREEN}   ✓ Backup saved to: $BACKUP_FILE${NC}"
fi

# Copy edition config to active config
echo -e "${BLUE}🔄 Switching to $EDITION edition...${NC}"
cp "$EDITION_FILE" "$TARGET_CONFIG"

# Extract edition info
EDITION_NAME=$(cat "$TARGET_CONFIG" | grep -o '"edition": "[^"]*"' | cut -d'"' -f4)
EDITION_DESC=$(cat "$TARGET_CONFIG" | grep -o '"description": "[^"]*"' | cut -d'"' -f4 | head -1)

# Display success message
echo ""
echo -e "${GREEN}✅ Successfully switched to $EDITION edition${NC}"
echo ""
echo -e "${BLUE}Edition Details:${NC}"
echo "  Name: $EDITION_NAME"
echo "  Description: $EDITION_DESC"
echo ""

# Show enabled features
echo -e "${BLUE}Enabled Features:${NC}"
if command -v jq &> /dev/null; then
  cat "$TARGET_CONFIG" | jq -r '.features | to_entries[] | select(.value.enabled == true) | "  ✓ \(.key): \(.value.description)"'
else
  # Fallback if jq not available
  cat "$TARGET_CONFIG" | grep '"enabled": true' -B 2 | grep 'description' | cut -d'"' -f4 | sed 's/^/  ✓ /'
fi

echo ""
echo -e "${YELLOW}⚠️  Important: Backend restart required${NC}"
echo ""
echo "To apply changes:"
echo "  docker-compose restart backend"
echo ""
echo "Or full restart:"
echo "  docker-compose down && docker-compose up -d"
echo ""

# Ask if user wants to restart now
read -p "Restart backend now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${BLUE}🔄 Restarting backend...${NC}"

  # Check if running in docker-compose
  if docker-compose ps backend &>/dev/null; then
    docker-compose restart backend
    echo -e "${GREEN}✅ Backend restarted${NC}"
  else
    echo -e "${YELLOW}⚠️  Docker Compose not detected - please restart manually${NC}"
  fi
fi

echo ""
echo -e "${GREEN}🎉 Edition switch complete!${NC}"
