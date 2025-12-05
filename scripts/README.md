# ADCL Platform Release Scripts

Scripts for building, testing, and publishing ADCL Platform releases.

## Architecture: S3-Only Distribution

ADCL uses **S3 + CloudFront only** for all distribution:
- ✅ Single source of truth (no GHCR, no external registries)
- ✅ Single authentication system (AWS only)
- ✅ Simple release process (one script)
- ✅ Complete control over distribution

Docker images are distributed as compressed tarballs on S3, loaded with `docker load`. This follows Unix philosophy: everything is a file, tools compose.

## Scripts Overview

- **release.sh** - Complete release workflow (recommended)
- **bump-version.sh** - Increment version in VERSION file
- **build-images.sh** - Build Docker images and save as tarballs
- **publish-release.sh** - Publish complete release to S3/CDN
- **load-images.sh** - Load Docker images from tarballs
- **test-upload.sh** - Test S3 upload credentials
- **initial-upload.sh** - First-time S3 infrastructure setup
- **upgrade.sh** - Upgrade running ADCL installation

## Prerequisites

- AWS CLI installed and configured
- `jq` installed (for JSON parsing)
- Docker installed
- Access to S3 bucket (adcl-public)

## First Time Setup

### 1. Configure AWS Credentials

Add to `.env` in repository root:

```bash
AWS_S3_KEY=your-access-key
AWS_S3_SEC_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC  # Optional but recommended
```

### 2. Test Credentials

```bash
./scripts/test-upload.sh
```

This verifies:
- AWS credentials work
- Can upload to S3
- Files are publicly accessible via CDN

### 3. Initialize S3 Infrastructure

Run once to create initial structure:

```bash
./scripts/initial-upload.sh
```

This creates:
- `/adcl-releases/releases/versions.json` - Catalog of all releases
- `/adcl-releases/releases/latest.json` - Current latest release metadata
- `/adcl-releases/install.sh` - One-line installer script

## Publishing a Release

### Quick Release (Fully Automated - Recommended)

Use the all-in-one `release.sh` script - **completely automated, no prompts**:

```bash
# Auto-increment patch version (0.1.0 → 0.1.1) - most common
./scripts/release.sh

# Or specify bump type:
./scripts/release.sh patch   # 0.1.0 → 0.1.1 (bug fixes)
./scripts/release.sh minor   # 0.1.0 → 0.2.0 (new features)
./scripts/release.sh major   # 0.1.0 → 1.0.0 (breaking changes)

# Or explicit version:
./scripts/release.sh 1.5.0

# Optional flags:
./scripts/release.sh patch --no-commit  # Skip git commit
./scripts/release.sh patch --no-tag     # Skip git tag
```

The script automatically:
1. Increments version in VERSION file
2. Auto-generates CHANGELOG.md from git commits
3. Builds Docker images as tarballs
4. Publishes to S3/CDN
5. Commits changes to git
6. Creates git tag

**Then just push:**
```bash
git push origin main v0.1.1
```

### Manual Workflow

For more control, use individual scripts:

```bash
# 1. Bump version
./scripts/bump-version.sh patch   # Or minor/major/X.Y.Z
vim CHANGELOG.md                  # Add release notes

# 2. Build Docker images
./scripts/build-images.sh         # Uses version from VERSION file

# 3. Publish to S3
./scripts/publish-release.sh      # Uses version from VERSION file

# 4. Git operations
git add VERSION CHANGELOG.md
git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

### What Gets Published

```
s3://adcl-public/adcl-releases/releases/v0.2.0/
├── VERSION                           # Version metadata (JSON)
├── CHANGELOG.md                      # Release notes (Markdown)
├── release.json                      # Release metadata for upgrades
├── adcl-platform-0.2.0.tar.gz       # Full source archive
├── adcl-platform-0.2.0.tar.gz.sha256 # Source checksum
├── adcl-orchestrator-0.2.0.tar.gz   # Docker image tarball
├── adcl-orchestrator-0.2.0.tar.gz.sha256
├── adcl-frontend-0.2.0.tar.gz       # Docker image tarball
├── adcl-frontend-0.2.0.tar.gz.sha256
├── adcl-registry-0.2.0.tar.gz       # Docker image tarball
├── adcl-registry-0.2.0.tar.gz.sha256
├── images-0.2.0.sha256              # Combined image checksums
├── configs.tar.gz                   # Minimal configs (agent-definitions, etc.)
├── docker-compose.release.yml       # Docker Compose for pre-built images
└── .env.example                     # Environment template
```

Plus updates to:
- `releases/latest.json` - Points to new version
- `releases/versions.json` - Adds new version to catalog

## Smart Versioning

All scripts support smart versioning that automatically reads from and updates the VERSION file.

### Version Modes

**1. Auto-increment (default for release.sh)**
```bash
./scripts/release.sh          # patch increment (most common)
./scripts/release.sh patch    # 0.1.0 → 0.1.1 (bug fixes)
./scripts/release.sh minor    # 0.1.0 → 0.2.0 (new features)
./scripts/release.sh major    # 0.1.0 → 1.0.0 (breaking changes)
```

**2. Explicit version**
```bash
./scripts/release.sh 1.5.0    # Override to specific version
```

**3. Use current VERSION file**
```bash
./scripts/build-images.sh     # No argument = use current version
./scripts/publish-release.sh  # No argument = use current version
```

### Semantic Versioning

ADCL follows [semver](https://semver.org/):

- **MAJOR** (1.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.2.0): New features, backward compatible
- **PATCH** (0.1.1): Bug fixes, backward compatible

## Detailed Script Usage

### release.sh (Recommended - Fully Automated)

All-in-one release workflow - completely automated with no prompts.

```bash
./scripts/release.sh [patch|minor|major|X.Y.Z] [--no-commit] [--no-tag]

# Examples:
./scripts/release.sh          # Auto-increment patch, fully automated
./scripts/release.sh minor    # New feature release
./scripts/release.sh 2.0.0    # Major version release
./scripts/release.sh patch --no-commit  # Skip git commit
./scripts/release.sh patch --no-tag     # Skip git tag
```

**What it does (automatically):**
1. Increments version in VERSION file
2. Auto-generates CHANGELOG.md from git commits since last tag
3. Builds Docker images as tarballs
4. Publishes everything to S3/CloudFront
5. Commits VERSION and CHANGELOG.md to git
6. Creates annotated git tag

**After running:**
```bash
# Just push to remote
git push origin main v0.2.0
```

### bump-version.sh

Standalone version bumping utility.

```bash
./scripts/bump-version.sh [patch|minor|major|X.Y.Z]

# Examples:
./scripts/bump-version.sh          # Increment patch
./scripts/bump-version.sh minor    # Increment minor
./scripts/bump-version.sh 1.5.0    # Set explicit version
```

Updates the VERSION file and displays next steps.

### build-images.sh

Builds Docker images and saves them as compressed tarballs.

```bash
./scripts/build-images.sh [patch|minor|major|X.Y.Z]

# Examples:
./scripts/build-images.sh          # Use current VERSION file
./scripts/build-images.sh patch    # Auto-increment patch and build
./scripts/build-images.sh 0.2.0    # Build explicit version
```

**Output:**
- `release-artifacts/adcl-orchestrator-0.2.0.tar.gz` (~500 MB)
- `release-artifacts/adcl-frontend-0.2.0.tar.gz` (~250 MB)
- `release-artifacts/adcl-registry-0.2.0.tar.gz` (~50 MB)
- Individual and combined SHA256 checksums

**Images are tagged as:**
- `adcl-orchestrator:0.2.0` and `adcl-orchestrator:latest`
- `adcl-frontend:0.2.0` and `adcl-frontend:latest`
- `adcl-registry:0.2.0` and `adcl-registry:latest`

### publish-release.sh

Publishes complete release to S3/CDN.

```bash
./scripts/publish-release.sh [version]

# Examples:
./scripts/publish-release.sh          # Use current VERSION file
./scripts/publish-release.sh 0.2.0    # Publish explicit version
```

**What it does:**
1. Updates VERSION file with build date
2. Uploads VERSION and CHANGELOG.md
3. Creates and uploads source archive
4. Uploads Docker image tarballs (from release-artifacts/)
5. Creates release metadata (release.json, latest.json)
6. Updates versions catalog
7. Invalidates CloudFront cache (if CLOUDFRONT_DISTRIBUTION_ID set)

**Prerequisites:**
- Run `build-images.sh` first (for Docker image tarballs)
- AWS credentials configured
- VERSION and CHANGELOG.md updated

### load-images.sh

Loads Docker images from tarballs (for local testing).

```bash
./scripts/load-images.sh [version]

# Examples:
./scripts/load-images.sh 0.2.0  # Load specific version
./scripts/load-images.sh        # Load version from .env
```

### test-upload.sh

Tests AWS credentials and S3 access.

```bash
./scripts/test-upload.sh
```

Creates and uploads a test file, then verifies it's publicly accessible via CDN.

### initial-upload.sh

First-time S3 infrastructure setup.

```bash
./scripts/initial-upload.sh [bucket] [distribution-id]

# Example:
./scripts/initial-upload.sh adcl-public E1234567890ABC
```

Uses defaults from .env if arguments not provided.

## Public URLs

After publishing, releases are available at:

- **Latest release:** https://ai-releases.com/adcl-releases/releases/latest.json
- **Install script:** https://ai-releases.com/adcl-releases/install.sh
- **Versions catalog:** https://ai-releases.com/adcl-releases/releases/versions.json
- **Specific version:** https://ai-releases.com/adcl-releases/releases/v0.2.0/VERSION
- **Docker images:** https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-orchestrator-0.2.0.tar.gz

## User Installation Methods

### Method 1: Quick Install (Recommended)

```bash
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
```

Script automatically:
1. Downloads version metadata
2. Downloads Docker image tarballs
3. Loads images with `docker load`
4. Downloads configs
5. Creates docker-compose.yml
6. Starts platform with `docker compose up -d`

### Method 2: Manual Download

```bash
# Download source archive
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz

# Verify checksum
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz.sha256 | sha256sum -c

# Extract and run
tar xzf adcl-platform-0.2.0.tar.gz
cd adcl-platform
docker compose build && docker compose up -d
```

### Method 3: Pre-built Images

```bash
# Download image tarballs
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-orchestrator-0.2.0.tar.gz
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-frontend-0.2.0.tar.gz
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-registry-0.2.0.tar.gz

# Verify checksums
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/images-0.2.0.sha256 | sha256sum -c

# Load images
docker load < adcl-orchestrator-0.2.0.tar.gz
docker load < adcl-frontend-0.2.0.tar.gz
docker load < adcl-registry-0.2.0.tar.gz

# Start platform
docker compose up -d
```

## Verification

### Verify Release Published

```bash
# Check latest.json
curl -s https://ai-releases.com/adcl-releases/releases/latest.json | jq

# Check versions catalog
curl -s https://ai-releases.com/adcl-releases/releases/versions.json | jq

# Check specific version
curl -s https://ai-releases.com/adcl-releases/releases/v0.2.0/VERSION | jq
```

### Verify Checksums

```bash
# Download and verify source archive
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz.sha256 | sha256sum -c

# Verify Docker images
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/images-0.2.0.sha256
```

### Test Installation

```bash
# Test in clean environment
docker run -it --rm ubuntu:22.04 bash
# Inside container:
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
```

## Troubleshooting

### AWS Credentials Not Working

```bash
# Test credentials
./scripts/test-upload.sh

# Check credentials are loaded
echo $AWS_ACCESS_KEY_ID

# Verify IAM permissions
aws s3 ls s3://adcl-public/
```

### CloudFront Cache Not Updating

```bash
# Manual invalidation
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/adcl-releases/releases/latest.json" "/adcl-releases/releases/versions.json"

# Or wait up to 1 hour for cache to expire
```

### Docker Image Tarball Too Large

Image tarballs are typically:
- orchestrator: ~500 MB
- frontend: ~250 MB
- registry: ~50 MB
- **Total: ~800 MB**

This is normal. CloudFront handles large files efficiently.

To optimize:
- Use multi-stage Docker builds (already implemented)
- Consider Alpine base images (trade-off: compatibility)
- Split images if needed (e.g., orchestrator-base + orchestrator)

### build-images.sh Fails

```bash
# Check Docker is running
docker ps

# Check disk space
df -h

# Clean up old images
docker system prune -a
```

### publish-release.sh Can't Find Images

```bash
# Ensure you ran build-images.sh first
ls -lh release-artifacts/

# If missing, rebuild
./scripts/build-images.sh 0.2.0
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Publish Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Build Docker images
        run: ./scripts/build-images.sh ${{ steps.version.outputs.VERSION }}

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Publish to S3
        run: ./scripts/publish-release.sh ${{ steps.version.outputs.VERSION }}
        env:
          CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}
```

## Best Practices

1. **Always run build-images.sh before publish-release.sh**
   ```bash
   ./scripts/build-images.sh 0.2.0
   ./scripts/publish-release.sh 0.2.0
   ```

2. **Test locally before publishing**
   ```bash
   ./scripts/load-images.sh 0.2.0
   docker compose up -d
   # Test the platform
   docker compose down
   ```

3. **Update VERSION and CHANGELOG first**
   - Commit these changes before building/publishing
   - Helps with traceability

4. **Use CloudFront cache invalidation**
   - Set CLOUDFRONT_DISTRIBUTION_ID in .env
   - Ensures users get new version immediately

5. **Keep release-artifacts/ directory**
   - Useful for debugging
   - Can re-publish without rebuilding
   - Add to .gitignore

6. **Verify checksums after upload**
   ```bash
   curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/images-0.2.0.sha256
   ```

## Support

For issues with release scripts:

1. Check AWS CLI is configured: `aws sts get-caller-identity`
2. Check S3 bucket access: `aws s3 ls s3://adcl-public/`
3. Check Docker is running: `docker ps`
4. Run test script: `./scripts/test-upload.sh`
5. Check script logs for errors

For more detailed documentation, see:
- `/docs/release-process.md` - Complete release workflow
- `/docs/release-packaging.md` - Packaging architecture
- `/docs/distribution-strategy.md` - Distribution model

