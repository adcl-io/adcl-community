# ContainerConfig Error - Fixed

## Error Message

```
KeyError: 'ContainerConfig'
ERROR: for test3-dev-team_nmap_recon_1  'ContainerConfig'

File "/usr/lib/python3/dist-packages/compose/service.py", line 1579
    container.image_config['ContainerConfig'].get('Volumes') or {}
    ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
KeyError: 'ContainerConfig'
```

## What Causes This

This error occurs when docker-compose tries to **recreate** a container but encounters a mismatch between:
- The old container's metadata
- The new image structure

Common triggers:
- Running `docker-compose up` after rebuilding an image
- Volume bindings changed in docker-compose.yml
- Image metadata corruption
- Docker version incompatibilities

## The Fix

**Simple Solution:** Stop and remove the container, then recreate it fresh.

```bash
# Stop and remove the problematic container
docker-compose stop nmap_recon
docker-compose rm -f nmap_recon

# Recreate it fresh
docker-compose up -d nmap_recon
```

**For multiple services:**
```bash
# Stop all
docker-compose stop

# Remove all containers
docker-compose rm -f

# Start fresh
docker-compose up -d
```

**Nuclear option (if above doesn't work):**
```bash
# Stop and remove everything including volumes
docker-compose down -v

# Rebuild and start fresh
docker-compose up -d --build
```

## Why This Works

When you `rm -f` the container:
- Docker removes the old container completely
- All old metadata is discarded
- `docker-compose up -d` creates a brand new container
- New container has fresh metadata matching the current image

## Preventing This Error

1. **Use proper workflow for rebuilds:**
   ```bash
   # Instead of just 'up'
   docker-compose build service_name
   docker-compose stop service_name
   docker-compose rm -f service_name
   docker-compose up -d service_name
   ```

2. **Clean restart script:**
   ```bash
   #!/bin/bash
   # clean-restart.sh
   docker-compose stop
   docker-compose rm -f
   docker-compose up -d --build
   ```

3. **Use down/up instead of restart:**
   ```bash
   # Instead of restart after changes
   docker-compose down
   docker-compose up -d
   ```

## In This Case

**What happened:**
- Nmap container was running
- start.sh tried to recreate it with `--build` flag
- docker-compose hit the ContainerConfig mismatch

**How we fixed it:**
```bash
# 1. Remove the problematic container
docker-compose stop nmap_recon
docker-compose rm -f nmap_recon

# 2. Create fresh
docker-compose up -d nmap_recon

# 3. Restart other services that exited
docker-compose start orchestrator frontend

# 4. Verify all running
./status.sh
```

**Result:** ✅ All 5 services UP

## Quick Reference

| Error | Command to Fix |
|-------|----------------|
| Single service | `docker-compose stop SERVICE && docker-compose rm -f SERVICE && docker-compose up -d SERVICE` |
| All services | `docker-compose down && docker-compose up -d` |
| Clean slate | `docker-compose down -v && docker-compose up -d --build` |

## Updated start.sh

Consider updating start.sh to use `down/up` instead of `up --build`:

```bash
# Option 1: Clean start
docker-compose down
docker-compose up -d --build

# Option 2: Smart restart
docker-compose up -d --build --force-recreate
```

The `--force-recreate` flag tells docker-compose to always recreate containers, avoiding the ContainerConfig issue.

## Prevention in Scripts

You could update start.sh to prevent this:

```bash
#!/bin/bash
echo "🚀 Starting MCP Agent Platform..."

# Clean stop first
docker-compose stop 2>/dev/null

# Remove containers without removing volumes
docker-compose rm -f 2>/dev/null

# Build and start fresh
docker-compose up -d --build

echo "✅ Services started successfully!"
./status.sh
```

This ensures a clean start every time.

---

**Status:** ✅ Fixed
**Resolution:** Stop, remove, recreate
**Prevention:** Use down/up or --force-recreate
**Date:** 2025-10-13
