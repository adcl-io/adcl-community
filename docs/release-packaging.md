# ADCL Platform Release Packaging Strategy

## Overview

ADCL Platform releases should support multiple deployment scenarios:
1. **Quick Start** - Docker Compose with pre-built images (fastest)
2. **Source Install** - Full source tarball for customization
3. **Git Clone** - Development and contribution
4. **Enterprise** - Same as community + enterprise packages

## Recommended Packaging Approach

### 1. Docker Images (Pre-built, Fastest Deployment)

**Publish to GitHub Container Registry (GHCR)**

```bash
# Images to publish:
ghcr.io/adcl-io/adcl-orchestrator:0.1.0
ghcr.io/adcl-io/adcl-orchestrator:latest
ghcr.io/adcl-io/adcl-frontend:0.1.0
ghcr.io/adcl-io/adcl-frontend:latest
ghcr.io/adcl-io/adcl-registry:0.1.0
ghcr.io/adcl-io/adcl-registry:latest
```

**Advantages:**
- Users don't need to build (saves 5-10 minutes)
- Consistent, tested builds
- Smaller download than full source
- Easy version rollback

**Build & Push Script:**

```bash
#!/bin/bash
# scripts/build-and-push-images.sh

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

REGISTRY="ghcr.io/adcl-io"

# Build images
echo "Building orchestrator..."
docker build -t "${REGISTRY}/adcl-orchestrator:${VERSION}" ./backend
docker tag "${REGISTRY}/adcl-orchestrator:${VERSION}" "${REGISTRY}/adcl-orchestrator:latest"

echo "Building frontend..."
docker build -t "${REGISTRY}/adcl-frontend:${VERSION}" ./frontend
docker tag "${REGISTRY}/adcl-frontend:${VERSION}" "${REGISTRY}/adcl-frontend:latest"

echo "Building registry..."
docker build -t "${REGISTRY}/adcl-registry:${VERSION}" ./registry-server
docker tag "${REGISTRY}/adcl-registry:${VERSION}" "${REGISTRY}/adcl-registry:latest"

# Push images
echo "Pushing images..."
docker push "${REGISTRY}/adcl-orchestrator:${VERSION}"
docker push "${REGISTRY}/adcl-orchestrator:latest"
docker push "${REGISTRY}/adcl-frontend:${VERSION}"
docker push "${REGISTRY}/adcl-frontend:latest"
docker push "${REGISTRY}/adcl-registry:${VERSION}"
docker push "${REGISTRY}/adcl-registry:latest"

echo "✅ Images published!"
```

### 2. Source Archive (Full Customization)

**What to Include:**

```bash
adcl-platform-0.1.0.tar.gz
├── orchestrator/           # Backend source
├── frontend/              # Frontend source
├── registry-server/       # Registry source
├── mcp_servers/           # Community MCP servers
├── agent-definitions/     # Agent configs
├── agent-teams/          # Team configs
├── workflows/            # Example workflows
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── docker-compose.yml    # Deployment config
├── .env.example          # Environment template
├── VERSION               # Version file
├── CHANGELOG.md          # Release notes
├── README.md             # Getting started
└── LICENSE               # License file

# Excluded:
.git/                     # Git history (use git clone for this)
node_modules/             # Rebuild on install
__pycache__/              # Python cache
.env                      # User secrets
*.log                     # Log files
workspace/                # User data
volumes/                  # Runtime data
```

**Current Implementation:** Already in publish-release.sh (lines 109-129)

### 3. Optimized docker-compose.yml for Releases

**Create docker-compose.release.yml** - Uses pre-built images:

```yaml
version: '3.8'

services:
  orchestrator:
    image: ghcr.io/adcl-io/adcl-orchestrator:${ADCL_VERSION:-latest}
    ports:
      - "${ORCHESTRATOR_PORT:-8000}:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./agent-definitions:/app/agent-definitions:ro
      - ./workflows:/app/workflows
      - ./workspace:/app/workspace
      - ./logs:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - adcl-network

  frontend:
    image: ghcr.io/adcl-io/adcl-frontend:${ADCL_VERSION:-latest}
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:${ORCHESTRATOR_PORT:-8000}
    depends_on:
      - orchestrator
    networks:
      - adcl-network

  registry:
    image: ghcr.io/adcl-io/adcl-registry:${ADCL_VERSION:-latest}
    ports:
      - "${REGISTRY_PORT:-9000}:9000"
    volumes:
      - ./registry-server/registries:/app/registries:ro
    networks:
      - adcl-network

networks:
  adcl-network:
    driver: bridge
```

### 4. Improved Install Script

**Enhanced install.sh features:**

```bash
#!/bin/bash
# Improved installation script

set -e

echo "🚀 Installing ADCL Platform (Community Edition)..."

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    local missing=""

    if ! command -v docker &> /dev/null; then
        missing="$missing docker"
    fi

    if ! docker compose version &> /dev/null 2>&1; then
        missing="$missing docker-compose"
    fi

    if ! command -v curl &> /dev/null; then
        missing="$missing curl"
    fi

    if [ -n "$missing" ]; then
        echo "❌ Missing required tools:$missing"
        echo ""
        echo "Install instructions:"
        echo "  Docker: https://docs.docker.com/get-docker/"
        echo "  curl: Use your package manager (apt/yum/brew)"
        exit 1
    fi
}

check_prerequisites

# Fetch latest release info
echo "📥 Fetching latest release..."
RELEASE_JSON=$(curl -fsSL https://ai-releases.com/adcl-releases/releases/latest.json)
VERSION=$(echo "$RELEASE_JSON" | grep -o '"version":"[^"]*' | cut -d'"' -f4)
DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep -o '"download_url":"[^"]*' | cut -d'"' -f4)

echo "✅ Latest version: $VERSION"

# Installation directory
INSTALL_DIR="${HOME}/.adcl"
mkdir -p "$INSTALL_DIR"

# Choose installation method
echo ""
echo "Choose installation method:"
echo "  1) Pre-built images (recommended, fastest)"
echo "  2) Build from source (for development)"
echo ""
read -p "Select [1/2]: " -n 1 -r METHOD
echo ""

case $METHOD in
    1)
        # Pre-built images (fastest)
        echo "📦 Using pre-built Docker images..."

        cd "$INSTALL_DIR"

        # Download release files
        curl -fsSL "https://ai-releases.com/adcl-releases/releases/v${VERSION}/docker-compose.release.yml" \
            -o docker-compose.yml

        curl -fsSL "https://ai-releases.com/adcl-releases/releases/v${VERSION}/.env.example" \
            -o .env.example

        # Download minimal files needed (configs, not source)
        mkdir -p agent-definitions workflows
        curl -fsSL "https://ai-releases.com/adcl-releases/releases/v${VERSION}/configs.tar.gz" | tar xz

        # Create .env
        if [ ! -f .env ]; then
            cp .env.example .env
            echo "ADCL_VERSION=$VERSION" >> .env
        fi

        echo "✅ Configuration downloaded"
        ;;

    2)
        # Build from source
        echo "📦 Downloading source archive..."

        cd "$INSTALL_DIR"

        if [ "$DOWNLOAD_URL" != "null" ] && [ -n "$DOWNLOAD_URL" ]; then
            curl -fsSL "$DOWNLOAD_URL" | tar xz --strip-components=1
        else
            # Fallback to git clone
            echo "📦 Cloning from GitHub..."
            if [ ! -d ".git" ]; then
                git clone https://github.com/adcl-io/adcl-platform.git .
            else
                git pull origin main
            fi
        fi

        # Create .env from template
        if [ ! -f .env ]; then
            cp .env.example .env
        fi

        echo "✅ Source downloaded"
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Start services
echo "🐳 Starting ADCL Platform..."
cd "$INSTALL_DIR"
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo ""
    echo "✅ ADCL Platform installed successfully!"
    echo ""
    echo "🌐 Access the platform:"
    echo "   Web UI: http://localhost:3000"
    echo "   API: http://localhost:8000/docs"
    echo ""
    echo "📚 Quick commands:"
    echo "   cd ~/.adcl"
    echo "   docker compose logs -f    # View logs"
    echo "   docker compose down       # Stop platform"
    echo "   docker compose up -d      # Start platform"
    echo ""
    echo "📖 Documentation: https://docs.adcl.io"
    echo "⭐ GitHub: https://github.com/adcl-io/adcl-platform"
else
    echo ""
    echo "⚠️  Services may not have started correctly"
    echo "Check logs: cd ~/.adcl && docker compose logs"
fi
```

## Complete Release Process

### Step 1: Prepare Release

```bash
# 1. Update version numbers
vim VERSION  # Update version
vim CHANGELOG.md  # Add release notes

# 2. Test locally
docker compose build
docker compose up -d
# Run tests, verify functionality
docker compose down

# 3. Commit changes
git add VERSION CHANGELOG.md
git commit -m "Prepare release v0.2.0"
git push
```

### Step 2: Build and Push Docker Images

```bash
# Build and push to GHCR
./scripts/build-and-push-images.sh 0.2.0
```

### Step 3: Publish Release to S3

```bash
# Publish VERSION, CHANGELOG, archives to S3
./scripts/publish-release.sh 0.2.0

# When prompted, create archive: Y
# When prompted, create git tag: Y
```

### Step 4: Create GitHub Release

```bash
# Create GitHub release with tag
gh release create v0.2.0 \
    --title "v0.2.0 - Release Name" \
    --notes-file CHANGELOG.md \
    adcl-platform-0.2.0.tar.gz
```

### Step 5: Verify

```bash
# Test install script
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash

# Test direct docker pull
docker pull ghcr.io/adcl-io/adcl-orchestrator:0.2.0

# Test upgrade from previous version
# (in existing installation)
./scripts/upgrade.sh
```

## File Structure on S3

```
s3://adcl-public/adcl-releases/
├── install.sh                              # Main install script
│
├── releases/
│   ├── latest.json                         # Points to latest version
│   ├── versions.json                       # Catalog of all versions
│   │
│   └── v0.1.0/                            # Version-specific files
│       ├── VERSION                         # Version metadata
│       ├── CHANGELOG.md                    # Release notes
│       ├── release.json                    # Release metadata
│       ├── adcl-platform-0.1.0.tar.gz     # Full source archive
│       ├── docker-compose.release.yml      # Pre-built images compose
│       ├── configs.tar.gz                  # Minimal configs (for pre-built)
│       └── .env.example                    # Environment template
│
└── docker/                                 # Optional: Docker manifests
    └── v0.1.0/
        └── images.json                     # Image checksums, signatures
```

## Deployment Scenarios

### Scenario 1: Production Deployment (Pre-built Images)

```bash
# Fastest, most reliable
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
# Choose option 1 (pre-built images)

# Pulls:
# - docker-compose.release.yml
# - configs.tar.gz (agent-definitions, workflows)
# - .env.example
# Images from: ghcr.io/adcl-io/*
```

**Time: ~2 minutes** (just pull images)

### Scenario 2: Development/Customization (Source)

```bash
# Full source code
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
# Choose option 2 (build from source)

# Downloads:
# - adcl-platform-0.1.0.tar.gz (all source)
# Builds images locally
```

**Time: ~10 minutes** (includes build time)

### Scenario 3: Git Clone (Contributors)

```bash
# For development and contributions
git clone https://github.com/adcl-io/adcl-platform.git
cd adcl-platform
cp .env.example .env
docker compose up -d --build
```

**Time: ~10 minutes** (includes build + git history)

### Scenario 4: Enterprise Deployment

```bash
# Same as Scenario 1, plus enterprise packages
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash

# Add enterprise credentials
cat >> ~/.adcl/.env <<EOF
ADCL_EDITION=enterprise
ADCL_LICENSE_KEY=ent_xyz123
REGISTRY_AUTH_TOKEN=abc789
EOF

# Install enterprise MCPs
cd ~/.adcl
./scripts/install-enterprise-mcps.sh
```

## Size Optimization

### Current Sizes (Estimated)

```
Full source archive:          ~50 MB (uncompressed)
Compressed source:            ~10 MB (.tar.gz)
Docker images (all):          ~800 MB
  - orchestrator:             ~500 MB
  - frontend:                 ~250 MB
  - registry:                 ~50 MB
Configs only:                 ~500 KB
```

### Optimization Tips

1. **Multi-stage Docker builds** - Already implemented
2. **Layer caching** - Tag and reuse base layers
3. **Alpine base images** - Consider for registry
4. **Minimal configs package** - For pre-built image deployments

## Recommended S3 Bucket Lifecycle

```json
{
  "Rules": [
    {
      "Id": "Archive old releases",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Filter": {
        "Prefix": "adcl-releases/releases/"
      }
    },
    {
      "Id": "Keep latest and recent",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      },
      "Filter": {
        "Prefix": "adcl-releases/releases/latest.json"
      }
    }
  ]
}
```

## Security Considerations

### Checksums

Generate and publish SHA256 checksums:

```bash
# In publish-release.sh, add:
sha256sum "adcl-platform-${VERSION}.tar.gz" > "adcl-platform-${VERSION}.tar.gz.sha256"
aws s3 cp "adcl-platform-${VERSION}.tar.gz.sha256" "s3://${BUCKET}/${RELEASE_DIR}/"

# Users verify:
curl -fsSL "https://ai-releases.com/.../adcl-platform-0.1.0.tar.gz" -o adcl-platform-0.1.0.tar.gz
curl -fsSL "https://ai-releases.com/.../adcl-platform-0.1.0.tar.gz.sha256" | sha256sum -c
```

### Image Signing (Future)

```bash
# Sign Docker images with cosign
cosign sign ghcr.io/adcl-io/adcl-orchestrator:0.1.0

# Users verify:
cosign verify ghcr.io/adcl-io/adcl-orchestrator:0.1.0
```

## Metrics to Track

1. **Download counts** (CloudFront logs)
2. **Installation method breakdown** (pre-built vs source)
3. **Version adoption rate**
4. **Failed installations** (telemetry opt-in)
5. **Build times** (CI/CD metrics)

## Conclusion

**Recommended packaging strategy:**

1. **Primary**: Pre-built Docker images on GHCR (fastest, most reliable)
2. **Secondary**: Source tarball on S3 (for customization)
3. **Tertiary**: Git clone (for contributors)

This approach:
- ✅ Supports multiple use cases
- ✅ Minimizes download size for most users
- ✅ Provides transparency (full source available)
- ✅ Easy to upgrade and rollback
- ✅ Scales with user base

Next steps:
1. Create `build-and-push-images.sh` script
2. Set up GHCR authentication
3. Create `docker-compose.release.yml`
4. Update `install.sh` with method selection
5. Add checksums to publish process
