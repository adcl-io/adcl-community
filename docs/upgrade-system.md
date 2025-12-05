# ADCL Platform Upgrade System

## Overview

The ADCL Platform includes an automated upgrade system that allows users to check for new versions and upgrade their installation with a single click. The system follows best practices for software distribution and supports both community and enterprise editions.

## Architecture

### Components

1. **VERSION File** (`/VERSION`)
   - JSON file tracking current platform version
   - Contains version, build number, release date, and component versions
   - Updated by the publish script during releases

2. **Backend Services**
   - `VersionService` - Checks for updates from CDN
   - `UpgradeService` - Orchestrates upgrades with backup/rollback
   - System API endpoints at `/system/version` and `/system/updates`

3. **Frontend UI**
   - Upgrade button in navigation bar
   - `UpgradeDialog` component showing release notes
   - Automatic polling for updates (hourly)
   - Real-time progress updates via WebSocket

4. **Release Infrastructure**
   - S3 bucket: `adcl-public`
   - CloudFront CDN: `https://ai-releases.com`
   - Release path: `adcl-releases/releases/`

### Release Structure

```
s3://adcl-public/adcl-releases/
├── install.sh                           # Installation script
├── releases/
│   ├── latest.json                      # Latest release metadata
│   ├── versions.json                    # Catalog of all versions
│   └── v{VERSION}/
│       ├── VERSION                      # Version file
│       ├── CHANGELOG.md                 # Release notes
│       ├── release.json                 # Version-specific metadata
│       └── adcl-platform-{VERSION}.tar.gz  # Optional release archive
```

### Update Flow

1. **Check for Updates**
   - Frontend polls `/system/updates/check` every hour
   - Backend fetches `latest.json` from CDN
   - Semantic version comparison determines if update available

2. **Initiate Upgrade**
   - User clicks "Upgrade Now" button
   - Frontend calls `/system/upgrade/start` endpoint
   - Backend creates backup and starts upgrade process

3. **Execute Upgrade**
   - Backup current workspace to `workspace/backups/`
   - Download new version from CDN
   - Run upgrade script (`scripts/upgrade.sh`)
   - Restart services via Docker Compose

4. **Health Check**
   - System waits for services to become healthy
   - If health checks fail, automatic rollback to previous version
   - Backup restoration if needed

5. **Completion**
   - Update VERSION file with new version
   - Remove old backups (keep last 5)
   - Notify user of success/failure

## Publishing Releases

### First-Time Setup

Run once to initialize the S3 release infrastructure:

```bash
./scripts/initial-upload.sh
```

This creates:
- Initial `versions.json` catalog
- Generic `install.sh` script
- Placeholder `latest.json`

### Publishing New Version

1. **Update VERSION and CHANGELOG**
   ```bash
   # VERSION file will be automatically updated by the script
   # Ensure CHANGELOG.md has entries for the new version
   ```

2. **Run Publish Script**
   ```bash
   ./scripts/publish-release.sh 0.2.0
   ```

   This will:
   - Update VERSION file with new version and build date
   - Upload VERSION and CHANGELOG to S3
   - Extract release notes from CHANGELOG
   - Create `release.json` with metadata
   - Update `latest.json` for version checks
   - Add version to `versions.json` catalog
   - Optionally create release archive
   - Optionally create git tag

3. **Optional: Invalidate CloudFront Cache**
   ```bash
   # If CLOUDFRONT_DISTRIBUTION_ID is set, cache is auto-invalidated
   # Otherwise, wait up to 1 hour for cache to expire
   # Or manually invalidate in AWS Console
   ```

### Test Upload

Verify AWS credentials and S3 access:

```bash
./scripts/test-upload.sh
```

## Configuration

### Environment Variables

#### Backend (.env)

```bash
# Version tracking
ADCL_WORKSPACE=./workspace
VERSION_FILE=./VERSION

# Update URLs
COMMUNITY_UPDATE_URL=https://ai-releases.com/adcl-releases/releases/latest.json
REGISTRY_URL=http://registry:9000  # For enterprise edition
```

#### AWS Credentials (.env)

```bash
# Option 1: Standard AWS names
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1

# Option 2: Custom names (scripts handle both)
AWS_S3_KEY=your-access-key
AWS_S3_SEC_KEY=your-secret-key

# Optional: CloudFront distribution for cache invalidation
CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC
```

### Docker Volume Mounts

Ensure VERSION file is accessible in containers:

```yaml
volumes:
  - ./VERSION:/app/VERSION:ro
  - ./workspace:/workspace
```

## API Endpoints

### Check for Updates

```http
GET /system/updates/check
```

Response:
```json
{
  "current_version": "0.1.0",
  "latest_version": "0.2.0",
  "update_available": true,
  "release_name": "v0.2.0 - ADCL Platform",
  "release_notes": "### Added\n- New features...",
  "published_at": "2025-12-03T16:20:42Z",
  "download_url": "https://ai-releases.com/...",
  "assets": []
}
```

### Get Current Version

```http
GET /system/version
```

Response:
```json
{
  "version": "0.1.0",
  "edition": "community",
  "build": "20251203.001",
  "release_date": "2025-12-03",
  "components": {
    "orchestrator": "0.1.0",
    "frontend": "0.1.0",
    "registry": "1.0.0"
  }
}
```

### Start Upgrade

```http
POST /system/upgrade/start
```

Response:
```json
{
  "status": "started",
  "message": "Upgrade to version 0.2.0 started",
  "backup_id": "backup_20251203_162042"
}
```

### Get Upgrade Status

```http
GET /system/upgrade/status
```

Response:
```json
{
  "status": "in_progress",
  "current_step": "downloading",
  "progress": 45,
  "message": "Downloading version 0.2.0..."
}
```

### List Backups

```http
GET /system/backups
```

Response:
```json
{
  "backups": [
    {
      "id": "backup_20251203_162042",
      "version": "0.1.0",
      "created_at": "2025-12-03T16:20:42Z",
      "size": "256MB"
    }
  ]
}
```

### Restore Backup

```http
POST /system/backups/{backup_id}/restore
```

## Security Considerations

1. **Path Validation**
   - Backup IDs are validated with regex: `^backup_\d{8}_\d{6}$`
   - Prevents path traversal attacks

2. **No Shell Commands**
   - Replaced `subprocess` with `shutil` for file operations
   - Eliminates shell injection vulnerabilities

3. **Environment Variables**
   - All paths configurable via environment variables
   - No hardcoded paths in code

4. **Backup Safety**
   - Automatic backups before upgrades
   - Configurable retention (default: 5 most recent)
   - Backup restoration on failed upgrades

5. **Health Checks**
   - Services must respond to health checks post-upgrade
   - Automatic rollback if health checks fail
   - Configurable timeout and retry logic

## Troubleshooting

### Issue: "Unable to locate credentials"

**Solution**: Ensure `.env` file exists in repository root with AWS credentials:

```bash
# Check credentials
cat .env | grep AWS_

# Test credentials
./scripts/test-upload.sh
```

### Issue: "Update available: false" but new version exists

**Solution**: CloudFront cache may be stale (up to 1 hour). Either:

1. Wait for cache to expire
2. Invalidate CloudFront distribution
3. Check S3 directly: `aws s3 cp s3://adcl-public/adcl-releases/releases/latest.json -`

### Issue: Upgrade fails and doesn't rollback

**Solution**: Manually restore from backup:

```bash
# List backups
curl http://localhost:8000/system/backups

# Restore specific backup
curl -X POST http://localhost:8000/system/backups/backup_20251203_162042/restore
```

### Issue: Version file not found in container

**Solution**: Ensure VERSION file is mounted in docker-compose.yml:

```yaml
volumes:
  - ./VERSION:/app/VERSION:ro
```

## Future Enhancements

### Identified During Architecture Review

1. **Split Upgrade Execution**
   - Move upgrade logic from backend to standalone script
   - Backend only coordinates, doesn't execute
   - Prevents "split-brain" scenario where upgrader gets upgraded

2. **Simplify VersionService**
   - Remove comparison logic to utility module
   - Keep only version fetching in service

3. **Modular Upgrade Script**
   - Break upgrade.sh into composable functions
   - Support plugin-based upgrade steps
   - Enable custom pre/post upgrade hooks

4. **Enhanced Monitoring**
   - Upgrade telemetry and metrics
   - Failed upgrade analytics
   - Rollback frequency tracking

## References

- [Keep a Changelog](https://keepachangelog.com/) - CHANGELOG format
- [Semantic Versioning](https://semver.org/) - Version numbering
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)

## Files Modified

- `VERSION` - Version tracking file
- `CHANGELOG.md` - Release notes
- `backend/app/services/version_service.py` - Version checking
- `backend/app/services/upgrade_service.py` - Upgrade orchestration
- `backend/app/api/system.py` - System API endpoints
- `frontend/src/components/UpgradeDialog.jsx` - Upgrade UI
- `frontend/src/components/Navigation.jsx` - Navigation with upgrade button
- `scripts/publish-release.sh` - Publish new releases
- `scripts/initial-upload.sh` - First-time S3 setup
- `scripts/test-upload.sh` - Test AWS credentials
- `scripts/upgrade.sh` - Upgrade execution script
