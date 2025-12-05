# ContainerConfig Error - FIXED! ✅

## The Problem

When restarting services, you would frequently hit this error:

```
Recreating test3-dev-team_orchestrator_1 ...

ERROR: for test3-dev-team_orchestrator_1  'ContainerConfig'
ERROR: for orchestrator  'ContainerConfig'

KeyError: 'ContainerConfig'
  at compose/service.py line 1579:
  container.image_config['ContainerConfig'].get('Volumes') or {}
```

**What causes this:**
- Running `./start.sh` or `docker-compose up -d` when containers are already running
- Docker-compose tries to recreate containers while preserving volume bindings
- The old container's image metadata is incompatible or missing
- Docker-compose fails when trying to merge the old and new configurations

## The Solution

Created three approaches to handle this:

### 1. Clean Restart Script (Recommended) ✅

**New script:** `clean-restart.sh`

```bash
./clean-restart.sh
```

**What it does:**
1. Stops all containers: `docker-compose down`
2. Removes all containers and networks
3. Starts everything fresh: `docker-compose up -d --build`
4. No ContainerConfig errors possible!

**When to use:**
- Anytime you want to restart services
- After code changes
- When you hit ContainerConfig errors
- For a clean slate

### 2. Updated start.sh Script ✅

**Enhanced:** `start.sh` now detects running containers

```bash
./start.sh
```

**What it does now:**
1. Checks if services are already running
2. If running, warns you and offers options:
   - Use `./clean-restart.sh` (recommended)
   - Use `./stop.sh && ./start.sh`
   - Force start anyway (may cause errors)
3. Prevents accidental ContainerConfig errors

### 3. Manual Approach

If you need to restart a specific service:

```bash
# Stop and remove specific service
docker-compose stop orchestrator
docker-compose rm -f orchestrator

# Start it fresh
docker-compose up -d orchestrator
```

## Usage Examples

### Scenario 1: Normal Restart
```bash
# Best approach - clean restart everything
./clean-restart.sh
```

### Scenario 2: Already Got ContainerConfig Error
```bash
# Stop everything cleanly
docker-compose down

# Start fresh
docker-compose up -d
```

### Scenario 3: Restart Single Service
```bash
# Use the existing restart scripts (safe)
./restart-api.sh      # Just restarts without recreating
./restart-agent.sh
./restart-frontend.sh
```

### Scenario 4: First Time Starting
```bash
# Use start.sh (will start fresh if nothing running)
./start.sh
```

## Why This Happens

The error occurs because:

1. **Docker-compose's smart recreation:** When you run `docker-compose up -d`, it tries to be smart about recreating containers only if needed

2. **Volume binding preservation:** It attempts to preserve volume bindings from the old container

3. **Image metadata mismatch:** If the old container's image was updated or its metadata changed, the merge fails

4. **Missing ContainerConfig:** The old container's image config may not have the expected `ContainerConfig` key

## What Changed

### Created: `clean-restart.sh`
- New script for clean, error-free restarts
- Always does `down` before `up`
- Executable: `chmod +x clean-restart.sh`

### Updated: `start.sh`
- Added running container detection (lines 40-57)
- Warns before attempting restart with running containers
- Recommends using `clean-restart.sh` to avoid errors
- Added interactive confirmation

### Unchanged: `restart-*.sh` scripts
- These use `docker-compose restart` (not recreate)
- Safe to use - just restarts the process
- Won't trigger ContainerConfig errors

## Quick Reference

| Command | When to Use | Safe? |
|---------|-------------|-------|
| `./clean-restart.sh` | Anytime, especially after errors | ✅ Always safe |
| `./start.sh` | First start, or when nothing running | ✅ With warning |
| `./stop.sh && ./start.sh` | Manual clean restart | ✅ Always safe |
| `./restart-api.sh` | Quick API restart without recreate | ✅ Always safe |
| `docker-compose down && docker-compose up -d` | Manual clean restart | ✅ Always safe |
| `docker-compose up -d` (when running) | Never! | ❌ Causes error |

## Testing

Verified the fix works:

```bash
# Started services
./start.sh
# ✅ All services up

# Ran clean restart
./clean-restart.sh
# ✅ No errors, clean restart

# Checked status
./status.sh
# ✅ All services running:
#   - orchestrator (port 8000)
#   - agent (port 7000)
#   - nmap_recon (port 7003)
#   - file_tools (port 7002)
#   - frontend (port 3000)
```

## Files Modified

1. **`clean-restart.sh`** (NEW)
   - Clean restart script
   - Lines 1-48: Full down/up cycle

2. **`start.sh`** (UPDATED)
   - Lines 40-57: Running container detection
   - Interactive warning and confirmation

## Prevention Tips

Going forward, to avoid ContainerConfig errors:

1. **Use clean-restart.sh by default** - It's fast and always works
2. **Stop before starting** - If in doubt, `./stop.sh` first
3. **Don't force up with --force-recreate** - That's what triggers the error
4. **Use restart scripts for quick restarts** - They don't recreate containers

## Error Recovery

If you still hit the error somehow:

```bash
# Nuclear option - stops and removes everything
docker-compose down

# Then start fresh
docker-compose up -d
```

Or just use:
```bash
./clean-restart.sh
```

## Benefits

✅ **No more ContainerConfig errors** - Clean shutdown prevents the issue
✅ **Fast restarts** - `docker-compose down` is quick
✅ **User-friendly warnings** - Start script alerts you before causing errors
✅ **Multiple approaches** - Choose what works for your situation
✅ **Documented** - Clear guidance on what to use when

## Verification

✅ ContainerConfig error fixed
✅ Clean restart script created
✅ Start script enhanced with detection
✅ All services running correctly
✅ Documentation complete

**Status: PRODUCTION READY** 🎉

---

**Date:** 2025-10-13
**Version:** 2.3
**Bug:** KeyError: 'ContainerConfig' when restarting services
**Cause:** docker-compose trying to recreate containers with incompatible image metadata
**Fix:** Created clean-restart.sh and updated start.sh with running container detection
**Recovery:** Always use `docker-compose down` before `docker-compose up -d`
