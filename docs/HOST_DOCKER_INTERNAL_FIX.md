# Host Network Connection Fix - RESOLVED! ✅

## The Problem

After configuring nmap to use host network mode, workflows were failing with:
```
❌ Node port-scan failed: All connection attempts failed
⚠️ Workflow failed
```

## Root Cause

**Issue:** The orchestrator container runs in Docker bridge network and was trying to connect to `localhost:7003` to reach nmap.

**Problem:** `localhost` inside a Docker container refers to the container itself, not the host machine. Since nmap uses host network mode and runs on the host's localhost, the orchestrator couldn't reach it.

```
┌──────────────────────────────────────┐
│  Docker Bridge Network (172.21.0.0)  │
│                                      │
│  ┌─────────────────────┐            │
│  │ orchestrator        │            │
│  │ tries: localhost    │ ❌         │
│  │ (container local)   │            │
│  └─────────────────────┘            │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│  Host Network (192.168.50.0/24)      │
│                                      │
│  nmap listening on: localhost:7003   │
│  (host's localhost)                  │
└──────────────────────────────────────┘

Container localhost ≠ Host localhost
```

## The Solution

Use Docker's `host.docker.internal` hostname to reach the host machine from containers.

### Changes Made

#### 1. Docker Compose - Add extra_hosts

**File:** `docker-compose.yml` lines 20-22

```yaml
orchestrator:
  # ... other config ...
  # Allow orchestrator to reach host machine where nmap runs
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

This maps `host.docker.internal` to the host gateway IP, allowing containers to reach the host.

#### 2. Update Nmap Endpoint

**File:** `backend/app/main.py` lines 364-370

**Before:**
```python
registry.register(MCPServerInfo(
    name="nmap_recon",
    endpoint=f"http://localhost:{nmap_port}",  # ❌ Wrong
    description="Network reconnaissance using Nmap"
))
```

**After:**
```python
# Nmap uses host network mode, so connect via host.docker.internal
# (added to extra_hosts in docker-compose.yml)
registry.register(MCPServerInfo(
    name="nmap_recon",
    endpoint=f"http://host.docker.internal:{nmap_port}",  # ✅ Correct
    description="Network reconnaissance using Nmap"
))
```

## Verification

### Test 1: DNS Resolution
```bash
$ docker exec orchestrator python -c "import socket; print(socket.gethostbyname('host.docker.internal'))"
172.21.0.1  # ✅ Resolves to host gateway
```

### Test 2: HTTP Connection
```bash
$ docker exec orchestrator python -c "import httpx; print(httpx.get('http://host.docker.internal:7003/health').text)"
{"status":"healthy","server":"nmap_recon"}  # ✅ Can reach nmap
```

### Test 3: MCP Server Registration
```bash
$ curl http://localhost:8000/mcp/servers | jq '.[] | select(.name=="nmap_recon")'
{
  "name": "nmap_recon",
  "endpoint": "http://host.docker.internal:7003",
  "description": "Network reconnaissance using Nmap"
}  # ✅ Correctly registered
```

### Test 4: Actual Workflow Execution
```bash
$ curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow": {"name": "Test", "nodes": [{"id": "scan", "type": "mcp_call", "mcp_server": "nmap_recon", "tool": "port_scan", "params": {"target": "192.168.50.1", "scan_type": "quick"}}], "edges": []}}'

{
  "status": "completed",  # ✅ Success!
  "results": {
    "scan": {
      "target": "192.168.50.1",
      "summary": {
        "total_scanned": 4,
        "open_ports": 4,
        "open_port_list": ["53/tcp", "80/tcp", "8443/tcp", "49152/tcp"]
      }
    }
  },
  "errors": []
}
```

**Successfully scanned router and found 4 open ports!** ✅

## Why This Works

### host.docker.internal Explained

Docker provides special DNS names for containers to reach the host:

| Hostname | Resolution | Use Case |
|----------|-----------|----------|
| `localhost` | Container's own localhost | Access container's own services |
| `host.docker.internal` | Host machine's IP | Access host machine from container |
| `gateway.docker.internal` | Default gateway | Access gateway services |

### Network Diagram - After Fix

```
┌──────────────────────────────────────────────┐
│  Docker Bridge Network (172.21.0.0/16)       │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │ orchestrator                        │    │
│  │ connects to:                        │    │
│  │ host.docker.internal:7003 ────────┐ │    │
│  └───────────────────────────────────┘ │    │
│                                        │    │
└────────────────────────────────────────┼────┘
                                         │
                                         ↓
┌────────────────────────────────────────┼────┐
│  Host Network (192.168.50.0/24)        │    │
│                                        │    │
│  ┌─────────────────────────────────────┘    │
│  │ nmap_recon (host network mode)          │
│  │ listening on: localhost:7003             │
│  │ accessible via: host.docker.internal     │
│  └──────────────────────────────────────────┘
│                                              │
└──────────────────────────────────────────────┘

        ✅ Connection successful!
```

## Alternative Solutions Considered

### Option 1: Use Host Gateway IP Directly
```python
endpoint = "http://172.21.0.1:7003"
```
**Verdict:** Works but hardcodes IP. `host.docker.internal` is more portable.

### Option 2: Put Orchestrator in Host Network Mode
```yaml
orchestrator:
  network_mode: host
```
**Verdict:** Would work but breaks communication with other services in bridge network (agent, file_tools, frontend).

### Option 3: Use Docker Network Alias
```yaml
nmap_recon:
  networks:
    mcp-network:
      aliases:
        - nmap
```
**Verdict:** Doesn't work with host network mode - can't be in both host and bridge network.

**Chosen Solution:** Use `host.docker.internal` with `extra_hosts` - most flexible and portable.

## Benefits

✅ **Orchestrator reaches nmap** - Can execute nmap workflows
✅ **Nmap scans host network** - Can scan actual LAN (192.168.50.0/24)
✅ **Portable configuration** - Works across different Docker hosts
✅ **Minimal changes** - Only two files modified
✅ **No breaking changes** - Other services unaffected

## Testing from Web UI

Now you can run nmap workflows from the web UI:

1. Open http://localhost:3000
2. Load "🔍 Nmap Recon" workflow
3. Change target to your network:
   ```json
   {
     "target": "192.168.50.1",
     "scan_type": "quick"
   }
   ```
4. Execute workflow
5. ✅ Should complete successfully with real scan results!

## Troubleshooting

### Still getting connection errors?

**Check 1:** Verify extra_hosts is configured
```bash
docker inspect test3-dev-team_orchestrator_1 | grep -A 5 ExtraHosts
```

**Check 2:** Verify orchestrator was rebuilt
```bash
docker-compose up -d --build orchestrator
```

**Check 3:** Test host.docker.internal resolution
```bash
docker exec test3-dev-team_orchestrator_1 ping -c 1 host.docker.internal
```

### Can't resolve host.docker.internal?

Older Docker versions may not support it. Use gateway IP instead:

```bash
# Find gateway IP
docker network inspect test3-dev-team_mcp-network | jq '.[0].IPAM.Config[0].Gateway'

# Update docker-compose.yml
extra_hosts:
  - "host.docker.internal:172.21.0.1"  # Use your actual gateway IP
```

## Files Modified

1. **docker-compose.yml**
   - Lines 20-22: Added `extra_hosts` to orchestrator
   - Line 18: Fixed NMAP_PORT to 7003

2. **backend/app/main.py**
   - Lines 364-370: Changed endpoint from `localhost` to `host.docker.internal`

## Summary

**Problem:** Container's localhost ≠ Host's localhost
**Solution:** Use `host.docker.internal` with `extra_hosts`
**Result:** Orchestrator can now reach nmap on host network ✅

---

**Date:** 2025-10-14
**Version:** 2.6
**Issue:** Orchestrator couldn't connect to nmap in host network mode
**Cause:** localhost resolution ambiguity between container and host
**Fix:** Use host.docker.internal with extra_hosts configuration
**Status:** ✅ VERIFIED WORKING

**Nmap workflows now execute successfully!** 🎉
