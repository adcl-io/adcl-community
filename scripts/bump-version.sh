#!/bin/bash
#
# Bump version in VERSION file
#
# Usage:
#   ./scripts/bump-version.sh              # Auto-increment patch
#   ./scripts/bump-version.sh patch        # Increment patch (0.1.0 → 0.1.1)
#   ./scripts/bump-version.sh minor        # Increment minor (0.1.0 → 0.2.0)
#   ./scripts/bump-version.sh major        # Increment major (0.1.0 → 1.0.0)
#   ./scripts/bump-version.sh 1.2.3        # Set explicit version

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Check for required dependencies
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed"
    echo "Install: sudo apt-get install jq  (or brew install jq on macOS)"
    exit 1
fi

# Check if VERSION file exists
if [ ! -f "VERSION" ]; then
    echo "Error: VERSION file not found"
    exit 1
fi

# Read current version
CURRENT=$(jq -r '.version' VERSION)

# Parse version components
if [[ ! $CURRENT =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "Error: Invalid version format in VERSION file: $CURRENT"
    exit 1
fi

MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"

# Determine new version
BUMP_TYPE="${1:-patch}"

case "$BUMP_TYPE" in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
        ;;
    [0-9]*.[0-9]*.[0-9]*)
        # Explicit version provided
        NEW_VERSION="$BUMP_TYPE"
        ;;
    *)
        echo "Error: Invalid bump type: $BUMP_TYPE"
        echo "Usage: $0 [major|minor|patch|X.Y.Z]"
        exit 1
        ;;
esac

echo "Current version: $CURRENT"
echo "New version:     $NEW_VERSION"
echo ""

# Update VERSION file
jq --arg version "$NEW_VERSION" '.version = $version' VERSION > VERSION.tmp
mv VERSION.tmp VERSION

echo "✅ Updated VERSION file"
echo ""
echo "Next steps:"
echo "  1. Update CHANGELOG.md with release notes for v${NEW_VERSION}"
echo "  2. Review changes: git diff VERSION CHANGELOG.md"
echo "  3. Build and publish: ./scripts/build-images.sh && ./scripts/publish-release.sh"
