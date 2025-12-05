# ADCL Platform Release Process

## Quick Reference

Complete release process from development to production:

```bash
# 1. Prepare release
./scripts/prepare-release.sh 0.2.0

# 2. Build and push Docker images
./scripts/build-and-push-images.sh 0.2.0

# 3. Publish to S3/CDN
./scripts/publish-release.sh 0.2.0

# 4. Create GitHub release
gh release create v0.2.0 --generate-notes

# 5. Announce release
# (Update website, send notifications, etc.)
```

## Detailed Steps

### Prerequisites

1. **AWS Credentials** (in `.env`)
   ```bash
   AWS_S3_KEY=your-access-key
   AWS_S3_SEC_KEY=your-secret-key
   CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC  # Optional but recommended
   ```

2. **GitHub Access** (for Docker images)
   ```bash
   # Create GitHub Personal Access Token with packages:write scope
   # Login to GHCR:
   echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
   ```

3. **Tools Installed**
   - Docker
   - AWS CLI
   - GitHub CLI (gh)
   - jq
   - git

### Step 1: Prepare Release

Update version numbers and documentation:

```bash
# 1. Update VERSION file
vim VERSION
# Change: "version": "0.2.0"

# 2. Update CHANGELOG.md
vim CHANGELOG.md
# Add release notes:
## [0.2.0] - 2025-12-10

### Added
- New feature X
- Enhancement Y

### Fixed
- Bug Z

# 3. Test locally
docker compose build
docker compose up -d
# Run tests, verify everything works
docker compose down

# 4. Commit changes
git add VERSION CHANGELOG.md
git commit -m "Prepare release v0.2.0"
git push origin main
```

### Step 2: Build and Push Docker Images

Build multi-platform images and push to GitHub Container Registry:

```bash
./scripts/build-and-push-images.sh 0.2.0
```

This will:
- Build `adcl-orchestrator`, `adcl-frontend`, `adcl-registry`
- Tag with version and `latest`
- Push to `ghcr.io/adcl-io/`

**Verify:**
```bash
# Check images are public:
docker pull ghcr.io/adcl-io/adcl-orchestrator:0.2.0
docker pull ghcr.io/adcl-io/adcl-frontend:0.2.0
docker pull ghcr.io/adcl-io/adcl-registry:0.2.0
```

### Step 3: Publish to S3/CDN

Upload all release artifacts to S3:

```bash
./scripts/publish-release.sh 0.2.0
```

This will:
1. Update VERSION file with build date
2. Upload VERSION and CHANGELOG.md
3. Create and upload:
   - `adcl-platform-0.2.0.tar.gz` (full source)
   - `adcl-platform-0.2.0.tar.gz.sha256` (checksum)
   - `configs.tar.gz` (minimal configs)
   - `docker-compose.release.yml` (pre-built images)
   - `.env.example` (environment template)
4. Extract release notes from CHANGELOG
5. Update `latest.json` with new version info
6. Update `versions.json` catalog
7. Invalidate CloudFront cache (if CLOUDFRONT_DISTRIBUTION_ID set)

**Verify:**
```bash
# Check release metadata
curl https://ai-releases.com/adcl-releases/releases/latest.json | jq

# Download and verify archive
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz.sha256 | sha256sum -c

# Test install script
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
```

### Step 4: Create GitHub Release (Optional)

Create official GitHub release:

```bash
# Option 1: Auto-generate release notes
gh release create v0.2.0 --generate-notes

# Option 2: Use CHANGELOG
gh release create v0.2.0 --notes-file CHANGELOG.md

# Option 3: Attach source archive
gh release create v0.2.0 \
    --title "v0.2.0 - ADCL Platform" \
    --notes-file CHANGELOG.md \
    adcl-platform-0.2.0.tar.gz
```

### Step 5: Announce Release

1. **Update website** (if applicable)
2. **Send notifications**:
   - Discord/Slack
   - Mailing list
   - Twitter/social media
3. **Update documentation** at docs.adcl.io

## Release Artifacts Generated

After a release, the following files are published:

### On S3/CDN (https://ai-releases.com/adcl-releases/)

```
releases/
├── latest.json                           # Latest version metadata
├── versions.json                         # All versions catalog
│
└── v0.2.0/
    ├── VERSION                          # Version metadata
    ├── CHANGELOG.md                     # Release notes (markdown)
    ├── release.json                     # Release metadata (JSON)
    ├── adcl-platform-0.2.0.tar.gz      # Full source archive
    ├── adcl-platform-0.2.0.tar.gz.sha256  # Checksum
    ├── configs.tar.gz                   # Minimal configs only
    ├── docker-compose.release.yml       # Pre-built images compose file
    └── .env.example                     # Environment template
```

### On GitHub Container Registry (ghcr.io/adcl-io/)

```
adcl-orchestrator:0.2.0
adcl-orchestrator:latest
adcl-frontend:0.2.0
adcl-frontend:latest
adcl-registry:0.2.0
adcl-registry:latest
```

### On GitHub Releases (optional)

```
https://github.com/adcl-io/adcl-platform/releases/tag/v0.2.0
└── adcl-platform-0.2.0.tar.gz (source archive)
```

## User Installation Methods

After release, users can install ADCL using:

### Method 1: Quick Install (Recommended)

```bash
curl -fsSL https://ai-releases.com/adcl-releases/install.sh | bash
```

Uses pre-built Docker images from GHCR. Fastest method.

### Method 2: Download Source Archive

```bash
# Download
curl -fsSLO https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz

# Verify checksum
curl -fsSL https://ai-releases.com/adcl-releases/releases/v0.2.0/adcl-platform-0.2.0.tar.gz.sha256 | sha256sum -c

# Extract and run
tar xzf adcl-platform-0.2.0.tar.gz
cd adcl-platform
docker compose up -d
```

### Method 3: Git Clone

```bash
git clone https://github.com/adcl-io/adcl-platform.git
cd adcl-platform
git checkout v0.2.0
docker compose up -d
```

## Rollback Procedure

If a release has issues:

### 1. Rollback S3 latest.json

```bash
# Re-publish previous version as latest
./scripts/publish-release.sh 0.1.0
```

### 2. Update Docker image :latest tags

```bash
# Re-tag previous version as latest
docker pull ghcr.io/adcl-io/adcl-orchestrator:0.1.0
docker tag ghcr.io/adcl-io/adcl-orchestrator:0.1.0 ghcr.io/adcl-io/adcl-orchestrator:latest
docker push ghcr.io/adcl-io/adcl-orchestrator:latest

# Repeat for frontend and registry
```

### 3. Notify Users

Send announcement about rollback and workaround.

## Versioning Strategy

ADCL follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

Examples:
0.1.0 - Initial release
0.2.0 - New features, backward compatible
0.2.1 - Bug fixes only
1.0.0 - First stable release
1.1.0 - New features
2.0.0 - Breaking changes
```

**When to increment:**
- **MAJOR**: Breaking API changes, major architectural changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, security patches

## Release Schedule

### Community Edition

- **Minor releases**: Monthly (0.2.0, 0.3.0, etc.)
- **Patch releases**: As needed for critical bugs
- **Major releases**: When stable (1.0.0, 2.0.0)

### Enterprise Edition

- **Stable releases**: Quarterly
- **LTS releases**: Annually with 2-year support
- **Security patches**: Within 48 hours for critical issues

## Testing Checklist

Before releasing:

- [ ] All tests pass
- [ ] Docker builds succeed
- [ ] docker-compose up works
- [ ] Health checks pass
- [ ] Upgrade from previous version works
- [ ] Documentation updated
- [ ] CHANGELOG.md complete
- [ ] VERSION file updated
- [ ] No .env secrets committed
- [ ] All links in docs work

## Hotfix Process

For critical bugs requiring immediate release:

```bash
# 1. Create hotfix branch from release tag
git checkout -b hotfix/v0.2.1 v0.2.0

# 2. Fix the bug
# ... make changes ...

# 3. Update VERSION and CHANGELOG
vim VERSION  # 0.2.0 -> 0.2.1
vim CHANGELOG.md

# 4. Commit and tag
git add -A
git commit -m "Hotfix v0.2.1: Fix critical bug X"
git tag v0.2.1

# 5. Build and publish
./scripts/build-and-push-images.sh 0.2.1
./scripts/publish-release.sh 0.2.1

# 6. Merge back to main
git checkout main
git merge hotfix/v0.2.1
git push origin main --tags
```

## Troubleshooting

### Issue: Docker push fails with "unauthorized"

**Solution:**
```bash
# Re-login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Issue: S3 upload fails with "Access Denied"

**Solution:**
```bash
# Check AWS credentials
./scripts/test-upload.sh

# Verify credentials in .env
grep AWS_ .env
```

### Issue: CloudFront cache not invalidating

**Solution:**
```bash
# Check distribution ID is set
grep CLOUDFRONT_DISTRIBUTION_ID .env

# Manual invalidation
aws cloudfront create-invalidation \
    --distribution-id E1234567890ABC \
    --paths "/adcl-releases/releases/latest.json" "/adcl-releases/releases/versions.json"
```

### Issue: Docker images not public

**Solution:**
```bash
# Make package public in GitHub:
# 1. Go to https://github.com/orgs/adcl-io/packages
# 2. Click on package
# 3. Package settings → Change visibility → Public
```

## Automation (Future)

Consider GitHub Actions workflow:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and push Docker images
        run: ./scripts/build-and-push-images.sh ${GITHUB_REF#refs/tags/v}

      - name: Publish to S3
        run: ./scripts/publish-release.sh ${GITHUB_REF#refs/tags/v}
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Create GitHub Release
        run: gh release create ${{ github.ref_name }} --generate-notes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## References

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [CloudFront Cache Invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
