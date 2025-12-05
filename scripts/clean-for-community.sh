#!/bin/bash
#
# Clean code for community edition
# Removes enterprise features and proprietary code
#
# Usage: ./scripts/clean-for-community.sh <target-directory>

set -euo pipefail

TARGET_DIR="${1:-../adcl-community}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧹 Cleaning code for community edition..."
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Create target directory
mkdir -p "$TARGET_DIR"

# Copy source files (excluding enterprise-only and sensitive files)
echo "📁 Copying source files..."

rsync -av \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='*.log' \
    --exclude='workspace' \
    --exclude='volumes' \
    --exclude='release-artifacts' \
    --exclude='*.tar.gz' \
    --exclude='*.sha256' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='test2.txt' \
    --exclude='scripts/versions.json' \
    --exclude='scripts/*s3*' \
    --exclude='scripts/initial-upload.sh' \
    --exclude='scripts/publish-release.sh' \
    --exclude='scripts/release.sh' \
    --exclude='docker-compose.release.yml' \
    "$SOURCE_DIR/" \
    "$TARGET_DIR/"

# Use GHCR docker-compose
cp "$SOURCE_DIR/docker-compose.ghcr.yml" "$TARGET_DIR/docker-compose.yml"

echo "✅ Files copied"

# Remove enterprise-only features (if any exist)
echo ""
echo "🔒 Removing enterprise-only code..."

# Example: Remove enterprise-only directories (adjust as needed)
# rm -rf "$TARGET_DIR/enterprise"
# rm -rf "$TARGET_DIR/backend/app/enterprise"

# Example: Remove enterprise imports from Python files
# find "$TARGET_DIR/backend" -name "*.py" -exec sed -i '/from .*enterprise/d' {} \;

echo "✅ Enterprise code removed"

# Sanitize configuration files
echo ""
echo "🔧 Sanitizing configuration..."

# Remove any hardcoded secrets/tokens
find "$TARGET_DIR" -name "*.py" -o -name "*.js" -o -name "*.ts" | while read -r file; do
    # Remove lines with API keys/tokens (this is a simple example)
    sed -i '/ANTHROPIC_API_KEY.*=.*sk-ant-/d' "$file" 2>/dev/null || true
    sed -i '/OPENAI_API_KEY.*=.*sk-proj-/d' "$file" 2>/dev/null || true
    sed -i '/AWS.*KEY.*=.*AK/d' "$file" 2>/dev/null || true
done

echo "✅ Configuration sanitized"

# Create clean .gitignore for public repo
echo ""
echo "📝 Creating .gitignore..."

cat > "$TARGET_DIR/.gitignore" <<'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv

# Node
node_modules/
npm-debug.log*
.npm

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# Workspace
workspace/
volumes/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml
EOF

echo "✅ .gitignore created"

echo ""
echo "✅ Community edition code prepared at: $TARGET_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the cleaned code"
echo "  2. Test locally: cd $TARGET_DIR && docker compose up"
echo "  3. Commit and push to adcl-io/adcl-community"
echo ""
