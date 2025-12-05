# ADCL Platform Upgrade Guide

## Overview

The ADCL platform includes a built-in upgrade system that follows Unix philosophy and ADCL principles:
- **Text-based configuration** - All version info in `VERSION` file
- **Shell scripts** - Portable, inspectable upgrade process
- **Fail fast** - Clear error messages, rollback on failure
- **Idempotent operations** - Safe to re-run

## Quick Start

### Check for Updates

**Via UI:**
1. Look for "Update Available" button in the navigation sidebar
2. Click the version number (e.g., "v0.1.0") to open upgrade dialog
3. Review release notes and click "Prepare Upgrade"

**Via API:**
```bash
curl http://localhost:8000/system/updates/check
```

**Via CLI:**
```bash
# List available backups
./scripts/upgrade.sh --list-backups
```

### Perform Upgrade

**Method 1: Semi-Automated (Recommended)**

1. Check for updates via UI or API
2. Backend creates automatic backup
3. Follow the provided upgrade steps:
   ```bash
   docker-compose down
   ./scripts/upgrade.sh <version>
   docker-compose up -d
   ```

**Method 2: Fully Manual**

```bash
# Stop services
docker-compose down

# Run upgrade script
./scripts/upgrade.sh 0.2.0

# Start services
docker-compose up -d
```

## Upgrade Process Details

### Prerequisites

The upgrade system checks for:
- ✅ Docker installed and running
- ✅ Git installed and repository valid
- ✅ At least 1GB free disk space
- ✅ No active agent executions

### Backup System

**Automatic Backup:**
- Created before each upgrade
- Stored in `workspace/backups/backup_YYYYMMDD_HHMMSS/`
- Includes:
  - `configs/` - All configuration files
  - `agent-definitions/` - Agent JSON files
  - `agent-teams/` - Team configurations
  - `workspace/executions/` - Execution history
  - `VERSION` - Version file
  - `.env` - Environment variables

**Backup Manifest:**
Each backup includes `manifest.json`:
```json
{
  "timestamp": "2025-11-24T12:00:00Z",
  "version_before": "0.1.0",
  "git_commit": "a9ac349...",
  "git_branch": "main"
}
```

### Upgrade Steps

The `upgrade.sh` script performs:

1. **Prerequisites Check**
   - Validates Docker, Git, disk space
   - Ensures repository is clean

2. **Backup Creation**
   - Creates timestamped backup
   - Writes manifest with current state

3. **Code Update**
   - Pulls latest code from git
   - Checks out version tag if available

4. **Version Update**
   - Updates `VERSION` file with new version
   - Sets build number and release date

5. **Container Management**
   - Stops all services
   - Pulls latest images
   - Rebuilds with `--no-cache`
   - Starts services

6. **Health Check**
   - Waits for backend to respond
   - Retries up to 30 times (60 seconds)
   - Rolls back on failure

### Rollback

**Automatic Rollback:**
- Triggered on health check failure
- Restores all backed up files
- Restarts services with previous version

**Manual Rollback:**
```bash
# List available backups
./scripts/upgrade.sh --list-backups

# Rollback to specific backup
./scripts/upgrade.sh --rollback backup_20251124_120000
```

## API Endpoints

### GET /system/version
Get current platform version information.

**Response:**
```json
{
  "version": "0.1.0",
  "build": "20251124.001",
  "release_date": "2025-11-24",
  "components": {
    "orchestrator": "0.1.0",
    "frontend": "0.1.0",
    "registry": "1.0.0"
  }
}
```

### GET /system/updates/check
Check for available platform updates.

**Query Parameters:**
- `update_url` (optional): Custom URL for update checks

**Response:**
```json
{
  "current_version": "0.1.0",
  "latest_version": "0.2.0",
  "update_available": true,
  "release_name": "v0.2.0 - Feature Release",
  "release_notes": "## Features\n- New upgrade system\n...",
  "published_at": "2025-11-24T10:00:00Z",
  "download_url": "https://github.com/adcl-io/demo-sandbox/releases/tag/v0.2.0"
}
```

### POST /system/updates/apply
Prepare platform for upgrade.

**Request:**
```json
{
  "target_version": "0.2.0",
  "auto_backup": true
}
```

**Response:**
```json
{
  "status": "ready",
  "message": "Backup created. Ready to execute upgrade script.",
  "backup_path": "/workspace/backups/backup_20251124_120000",
  "next_steps": [
    "Stop the platform: docker-compose down",
    "Run upgrade script: ./scripts/upgrade.sh 0.2.0",
    "Start the platform: docker-compose up -d"
  ]
}
```

### GET /system/backups
List available backup snapshots.

**Response:**
```json
{
  "backups": [
    {
      "path": "/workspace/backups/backup_20251124_120000",
      "timestamp": "20251124_120000",
      "version": "0.1.0",
      "size": 15728640
    }
  ]
}
```

### POST /system/backups/{backup_id}/restore
Restore platform from a backup.

**Response:**
```json
{
  "status": "success",
  "restored": [
    "configs",
    "agent-definitions",
    "agent-teams",
    "VERSION"
  ],
  "version_restored": "0.1.0"
}
```

## Configuration

### VERSION File Format

```json
{
  "version": "0.1.0",
  "build": "20251124.001",
  "release_date": "2025-11-24",
  "components": {
    "orchestrator": "0.1.0",
    "frontend": "0.1.0",
    "registry": "1.0.0"
  },
  "upgrade_available": false,
  "latest_version": "0.1.0",
  "release_notes_url": "https://github.com/adcl-io/demo-sandbox/releases"
}
```

### Update Check Configuration

**Frequency:**
- UI checks every 1 hour automatically
- API endpoint can be called anytime

**Custom Update URL:**
Set environment variable to use custom update server:
```bash
ADCL_UPDATE_URL=https://updates.example.com/check
```

Or pass directly to API:
```bash
curl "http://localhost:8000/system/updates/check?update_url=https://custom.example.com"
```

## Troubleshooting

### Upgrade Failed with Health Check Timeout

**Symptoms:**
- Upgrade script reports health check failures
- Services not responding after upgrade

**Resolution:**
1. Check logs: `docker-compose logs`
2. Verify all containers running: `docker-compose ps`
3. Manual health check: `curl http://localhost:8000/health`
4. If still failing, rollback:
   ```bash
   ./scripts/upgrade.sh --list-backups
   ./scripts/upgrade.sh --rollback backup_YYYYMMDD_HHMMSS
   ```

### Backup Creation Failed

**Symptoms:**
- "Backup failed" error during upgrade

**Resolution:**
1. Check disk space: `df -h`
2. Verify write permissions: `ls -la workspace/backups`
3. Check logs: `cat workspace/logs/upgrade.log`

### Git Pull Failed

**Symptoms:**
- "Failed to pull latest code" error

**Resolution:**
1. Check git status: `git status`
2. Resolve conflicts manually
3. Try upgrade again

### Docker Images Not Pulling

**Symptoms:**
- "Failed to pull images" warning

**Resolution:**
1. Check Docker daemon: `docker ps`
2. Check network connectivity
3. Manual pull: `docker-compose pull`
4. Continue upgrade: images will rebuild

## Best Practices

### Before Upgrading

1. **Review Release Notes**
   - Check for breaking changes
   - Note any configuration updates required
   - Review migration steps

2. **Test in Development**
   - Clone production to dev environment
   - Test upgrade process
   - Verify all features work

3. **Schedule Downtime**
   - Plan for 5-10 minutes downtime
   - Notify users if applicable
   - Choose low-traffic period

### During Upgrade

1. **Monitor Logs**
   - Watch `workspace/logs/upgrade.log`
   - Check Docker container logs
   - Verify health checks pass

2. **Keep Backup Reference**
   - Note backup path from output
   - Don't delete until upgrade verified

### After Upgrade

1. **Verify All Services**
   - Test agent execution
   - Verify MCP servers running
   - Check workflow execution

2. **Review Logs**
   - Check for errors or warnings
   - Verify all containers healthy

3. **Test Critical Features**
   - Run sample workflows
   - Test team execution
   - Verify registry access

## Zero-Downtime Deployments

For production environments requiring zero downtime:

### Blue-Green Deployment

1. **Setup Second Environment**
   ```bash
   # Clone current environment
   docker-compose -f docker-compose.blue.yml up -d
   ```

2. **Upgrade Green Environment**
   ```bash
   # Upgrade without affecting blue
   ./scripts/upgrade.sh 0.2.0
   ```

3. **Switch Traffic**
   ```bash
   # Update load balancer or DNS
   # Point to green environment
   ```

4. **Monitor and Rollback if Needed**
   ```bash
   # If issues, switch back to blue
   # Green remains for debugging
   ```

### Rolling Updates (Future)

Planned for future releases:
- Container-level rolling updates
- Health check integration
- Automatic traffic shifting

## Version Naming

ADCL follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

Example: 0.2.1
         │ │ └─ Patch: Bug fixes
         │ └─── Minor: New features (backward compatible)
         └───── Major: Breaking changes
```

### Version Compatibility

- **Patch updates (0.1.0 → 0.1.1)**: Always safe, no config changes
- **Minor updates (0.1.0 → 0.2.0)**: May add features, check release notes
- **Major updates (0.x → 1.0)**: May break compatibility, plan migration

## Migration Scripts

For breaking changes, migration scripts are provided:

```bash
# Located in scripts/migrations/
scripts/migrations/0.1.0-to-0.2.0.sh
```

These run automatically during upgrade if needed.

## Support

For upgrade issues:

1. Check logs: `workspace/logs/upgrade.log`
2. Review troubleshooting section above
3. Rollback if critical: `./scripts/upgrade.sh --rollback <backup_name>`
4. Report issues: https://github.com/adcl-io/demo-sandbox/issues
