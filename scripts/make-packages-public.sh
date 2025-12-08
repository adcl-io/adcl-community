#!/bin/bash
# Make GitHub Container Registry packages public
#
# NOTE: GitHub API does not currently support changing package visibility programmatically.
# This script verifies package status but you must manually update via GitHub UI.
#
# Usage: ./scripts/make-packages-public.sh

set -e

ORG="adcl-io"
PACKAGES=("orchestrator" "frontend" "registry")

echo "🔍 Checking GHCR package visibility..."
echo ""

ALL_PUBLIC=true

for PACKAGE in "${PACKAGES[@]}"; do
    PACKAGE_NAME="adcl-community/${PACKAGE}"
    PACKAGE_URL="adcl-community%2F${PACKAGE}"

    VISIBILITY=$(gh api "/orgs/${ORG}/packages/container/${PACKAGE_URL}" --jq '.visibility' 2>/dev/null || echo "error")

    if [ "$VISIBILITY" = "public" ]; then
        echo "✅ ${PACKAGE_NAME}: public"
    elif [ "$VISIBILITY" = "private" ]; then
        echo "🔒 ${PACKAGE_NAME}: private (needs manual update)"
        ALL_PUBLIC=false
    else
        echo "❌ ${PACKAGE_NAME}: not found or error"
        ALL_PUBLIC=false
    fi
done

echo ""

if [ "$ALL_PUBLIC" = true ]; then
    echo "✅ All packages are public!"
else
    echo "⚠️  Some packages need manual update:"
    echo ""
    echo "   1. Go to: https://github.com/orgs/${ORG}/packages"
    echo "   2. For each private package:"
    echo "      - Click the package name"
    echo "      - Click 'Package settings' (bottom left)"
    echo "      - Scroll to 'Danger Zone'"
    echo "      - Click 'Change visibility' → 'Public'"
    echo ""
    echo "   GitHub API does not support programmatic visibility changes."
fi
