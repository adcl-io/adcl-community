#!/bin/bash
#
# Test S3 upload with credentials
# Usage: ./scripts/test-upload.sh

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root is parent of scripts directory
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📋 Loading credentials from $ENV_FILE..."

    # Use while-read loop for robust parsing (handles spaces and special chars)
    while IFS='=' read -r key value; do
        # Remove leading/trailing whitespace and quotes from value
        value="${value#"${value%%[![:space:]]*}"}"  # trim leading whitespace
        value="${value%"${value##*[![:space:]]}"}"  # trim trailing whitespace
        value="${value%\"}"  # remove trailing quote
        value="${value#\"}"  # remove leading quote

        [[ $key =~ ^AWS_ ]] && export "$key=$value"
    done < <(grep -E '^AWS_' "$ENV_FILE" | grep -v '^#')

    # Handle both naming conventions
    if [ -n "${AWS_S3_KEY:-}" ]; then
        export AWS_ACCESS_KEY_ID="$AWS_S3_KEY"
    fi
    if [ -n "${AWS_S3_SEC_KEY:-}" ]; then
        export AWS_SECRET_ACCESS_KEY="$AWS_S3_SEC_KEY"
    fi

    echo "✅ Credentials loaded"
else
    echo "⚠️  .env file not found at $ENV_FILE"
fi

# Configuration
BUCKET="adcl-public"
S3_BASE_PATH="adcl-releases"
CDN_URL="https://ai-releases.com"

echo ""
echo "🧪 Testing S3 upload to bucket: $BUCKET"
echo "Path: $S3_BASE_PATH"
echo ""

# Check if AWS credentials are set
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "❌ AWS credentials not found!"
    echo ""
    echo "Add to .env file (either format):"
    echo "  AWS_ACCESS_KEY_ID=your-access-key"
    echo "  AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo "Or:"
    echo "  AWS_S3_KEY=your-access-key"
    echo "  AWS_S3_SEC_KEY=your-secret-key"
    echo ""
    exit 1
else
    echo "✅ AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."
    echo "✅ AWS_SECRET_ACCESS_KEY: ********"
fi

echo ""

# Create test file
echo "📝 Creating test file..."
cat > test2.txt <<EOF
ADCL Platform S3 Upload Test
============================

Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Bucket: $BUCKET
Path: $S3_BASE_PATH
CDN URL: $CDN_URL

This is a test file to verify S3 upload credentials work.

If you can see this file at:
  ${CDN_URL}/${S3_BASE_PATH}/test2.txt

Then your AWS credentials are configured correctly! ✅
EOF

echo "✅ Test file created: test2.txt"
cat test2.txt
echo ""

# Upload test file
echo "📤 Uploading test2.txt to S3..."
if aws s3 cp test2.txt "s3://${BUCKET}/${S3_BASE_PATH}/test2.txt" \
    --content-type "text/plain" \
    --cache-control "max-age=300"; then
    echo "✅ Upload successful!"
else
    echo "❌ Upload failed!"
    echo ""
    echo "Common issues:"
    echo "  1. AWS credentials not set correctly"
    echo "  2. Bucket name is wrong"
    echo "  3. No permissions to upload to this bucket"
    echo "  4. AWS CLI not configured"
    exit 1
fi

# Verify upload
echo ""
echo "🔍 Verifying upload..."
if aws s3 ls "s3://${BUCKET}/${S3_BASE_PATH}/test2.txt" > /dev/null 2>&1; then
    echo "✅ File exists in S3"
else
    echo "❌ File not found in S3"
    exit 1
fi

# Get file info
echo ""
echo "📊 File information:"
aws s3 ls "s3://${BUCKET}/${S3_BASE_PATH}/test2.txt" --human-readable

# Test public access
echo ""
echo "🌐 Testing public access..."
TEST_URL="${CDN_URL}/${S3_BASE_PATH}/test2.txt"
echo "URL: $TEST_URL"
echo ""

if curl -f -s "$TEST_URL" > /dev/null; then
    echo "✅ File is publicly accessible!"
    echo ""
    echo "Content:"
    curl -s "$TEST_URL"
else
    echo "⚠️  File uploaded but not publicly accessible yet"
    echo "This may take a few minutes for CloudFront to propagate"
    echo "Or you may need to configure CloudFront/bucket permissions"
fi

echo ""
echo "✅ Test complete!"
echo ""
echo "Next steps:"
echo "  1. If test was successful, run initial setup:"
echo "     ./scripts/initial-upload.sh"
echo ""
echo "  2. Then publish your first release:"
echo "     ./scripts/publish-release.sh 0.1.0"
echo ""
echo "Clean up test file:"
echo "  aws s3 rm s3://${BUCKET}/${S3_BASE_PATH}/test2.txt"
echo "  rm test2.txt"
