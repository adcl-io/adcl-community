# Upgrade System - Architecture Improvements

## Current Implementation Status

The upgrade system is **functional** and follows most ADCL principles, but has architectural debt identified during code review.

## Architecture Review Findings

### Issues Identified

1. **Split-brain Execution**
   - Current: API prepares upgrade, user manually runs script
   - Problem: Unclear separation of responsibilities
   - Fix: API should execute script and stream output, OR script should be standalone

2. **Service Bloat**
   - Current: VersionService does version read, update check, comparison, AND file updates
   - Problem: Violates single responsibility principle
   - Fix: Split into separate commands: `version`, `check-updates`, `upgrade`

3. **Mixed Concerns in upgrade.sh**
   - Current: One script handles git, Docker, backup, rollback, health checks
   - Problem: Monolithic, hard to test individual parts
   - Fix: Separate scripts: `backup.sh`, `upgrade.sh`, `rollback.sh`, `health-check.sh`

4. **Backup Tool Choice**
   - Current: Python shutil for backups
   - Problem: Doesn't preserve permissions, symlinks, extended attributes
   - Fix: Use tar (Unix standard since 1979)

5. **Progress Reporting**
   - Current: Optional callback in async function
   - Problem: Complex, not Unix-like
   - Fix: Write to log file, tail for progress (Unix streams)

6. **UI Update Polling**
   - Current: Frontend polls every hour
   - Problem: Inefficient, not real-time
   - Fix: Webhook or Server-Sent Events (SSE)

## Recommended Architecture (v2)

### Simple, Composable Tools

```bash
# Individual scripts, each does ONE thing:

./scripts/backup.sh
  - Creates timestamped backup
  - Outputs backup path to stdout
  - Returns 0 on success, 1 on failure

./scripts/upgrade.sh <version>
  - Reads backup path from stdin OR creates backup
  - Pulls code, rebuilds containers
  - Runs health check
  - Auto-rollback on failure
  - Returns 0 on success, 1 on failure

./scripts/rollback.sh <backup-path>
  - Restores from specified backup
  - Restarts services
  - Returns 0 on success, 1 on failure

./scripts/health-check.sh
  - Checks all services
  - Returns 0 if healthy, 1 if not

# Composition example:
BACKUP=$(./scripts/backup.sh) && \
./scripts/upgrade.sh 0.2.0 <<< "$BACKUP" || \
./scripts/rollback.sh "$BACKUP"
```

### API Simplification

```python
# API just orchestrates shell commands:

@router.post("/system/upgrade")
async def upgrade(version: str):
    """Execute upgrade script and stream output"""
    process = await asyncio.create_subprocess_exec(
        './scripts/upgrade.sh', version,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Stream output to client via SSE
    async for line in process.stdout:
        yield f"data: {line.decode()}\n\n"
```

### Version Service Split

```python
# Separate services, each with ONE job:

class VersionReader:
    """Read current version from VERSION file"""
    def get_version(self) -> str

class UpdateChecker:
    """Check for available updates"""
    def check_updates(self) -> Dict

class VersionComparator:
    """Compare semantic versions"""
    def compare(self, v1: str, v2: str) -> int
```

## Migration Plan

### Phase 1: Fix Critical Issues (Completed)
- [x] Fix shell injection vulnerabilities
- [x] Add path traversal validation
- [x] Remove hardcoded paths (use env vars)
- [x] Add proper error logging

### Phase 2: Modularize Scripts (Future)
- [ ] Extract `backup.sh` from `upgrade.sh`
- [ ] Extract `rollback.sh` logic
- [ ] Create standalone `health-check.sh`
- [ ] Make scripts composable via stdin/stdout

### Phase 3: Simplify Services (Future)
- [ ] Split VersionService into three focused classes
- [ ] Remove callback-based progress reporting
- [ ] Use log tailing for progress

### Phase 4: Improve Backup (Future)
- [ ] Replace shutil with tar
- [ ] Preserve permissions and extended attributes
- [ ] Add compression options

### Phase 5: Real-time Updates (Future)
- [ ] Replace polling with Server-Sent Events
- [ ] Add webhook support for update notifications
- [ ] Implement push-based version checking

## Current Trade-offs

For the initial implementation (v0.1.0 -> v0.2.0), we accept:

1. **Split-brain execution**: Acceptable for manual upgrades, improves in Phase 2
2. **Service bloat**: Functional but not ideal, refactor in Phase 3
3. **Monolithic script**: Works for now, split in Phase 2
4. **shutil backups**: Sufficient for config files, improve in Phase 4
5. **Polling**: Simple and works, optimize in Phase 5

## Principles to Maintain

As we refactor, maintain these ADCL principles:

1. **Text-based configuration**: Keep VERSION as JSON, no databases
2. **Shell scripts**: Keep upgrade logic in shell, not Python
3. **Fail fast**: Clear errors, no silent failures
4. **Idempotent**: Safe to re-run operations
5. **Inspectable**: All state on disk, no hidden state
6. **Composable**: Small tools that do one thing well

## References

- Unix Philosophy: https://en.wikipedia.org/wiki/Unix_philosophy
- ADCL Principles: `/CLAUDE.md`
- Code Review: See git history for nitpicker and linus-torvalds reviews
