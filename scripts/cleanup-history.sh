#!/bin/bash
set -euo pipefail

# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

# Cleanup Empty Sessions Script
# Calls the history MCP server to archive empty sessions older than 1 hour

HISTORY_MCP_URL="${HISTORY_MCP_URL:-http://localhost:7004}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-1}"

echo "[$(date)] Starting history cleanup..."
echo "  MCP URL: $HISTORY_MCP_URL"
echo "  Max age: $MAX_AGE_HOURS hours"

# Call cleanup tool via MCP HTTP endpoint
response=$(curl -s -X POST "$HISTORY_MCP_URL/mcp/call_tool" \
  -H "Content-Type: application/json" \
  -d "{
    \"tool\": \"cleanup_empty_sessions\",
    \"arguments\": {
      \"max_age_hours\": $MAX_AGE_HOURS
    }
  }")

# Check if curl succeeded
if [ $? -ne 0 ]; then
  echo "[$(date)] ERROR: Failed to connect to history MCP server"
  exit 1
fi

# Parse response
success=$(echo "$response" | jq -r '.content[0].text' | jq -r '.success')
cleaned_count=$(echo "$response" | jq -r '.content[0].text' | jq -r '.cleaned_count')
error_count=$(echo "$response" | jq -r '.content[0].text' | jq -r '.error_count')

if [ "$success" = "true" ]; then
  echo "[$(date)] Cleanup completed successfully"
  echo "  Cleaned: $cleaned_count sessions"
  echo "  Errors: $error_count"
  exit 0
else
  error_msg=$(echo "$response" | jq -r '.content[0].text' | jq -r '.error')
  echo "[$(date)] ERROR: Cleanup failed - $error_msg"
  exit 1
fi
