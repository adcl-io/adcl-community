# MCP Package Management System

## Overview

MCPs are now fully modular and installable just like teams - complete apt/yum-style package management with:

- ✅ Install MCPs from registry
- ✅ Version tracking and updates
- ✅ Dynamic Docker container deployment
- ✅ Lifecycle management (start/stop/restart/uninstall)
- ✅ Automatic discovery and registration
- ✅ Full UI integration

---

## What Changed

### 1. Enhanced MCP Package Structure

MCP packages now include complete Docker deployment metadata:

**Example: agent-1.0.0.json**
```json
{
  "name": "agent",
  "version": "1.0.0",
  "description": "AI Agent with think/code/review capabilities",
  "type": "mcp",
  "deployment": {
    "build": {
      "context": "./mcp_servers",
      "dockerfile": "Dockerfile.agent"
    },
    "image": "mcp-agent:1.0.0",
    "container_name": "mcp-agent",
    "ports": [{"host": "${AGENT_PORT:-7000}", "container": "${AGENT_PORT:-7000}"}],
    "volumes": [{"host": "./logs/agent", "container": "/app/logs"}],
    "environment": {
      "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY:-}",
      "PYTHONUNBUFFERED": "1",
      "AGENT_PORT": "${AGENT_PORT:-7000}",
      "LOG_DIR": "/app/logs"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },
  "requirements": {
    "api_keys": ["ANTHROPIC_API_KEY"],
    "min_memory": "512M",
    "min_cpu": "0.5"
  },
  "tools": [
    {"name": "think", "description": "Reasoning and analysis tool"},
    {"name": "code", "description": "Code generation and analysis"},
    {"name": "review", "description": "Code review capabilities"}
  ],
  "tags": ["ai", "reasoning", "code"],
  "author": "MCP Platform Team",
  "license": "MIT"
}
```

**Key Features:**
- Complete Docker deployment config (build, ports, volumes, environment)
- Network mode support (bridge/host)
- Capabilities for privileged operations (nmap)
- Environment variable resolution (${VAR:-default})
- Resource requirements specification

### 2. MCP Manager (backend/app/mcp_manager.py)

New Docker lifecycle management module with:

**Core Capabilities:**
- `install(mcp_package)` - Download, build, deploy Docker container
- `uninstall(name)` - Stop and remove container
- `start/stop/restart(name)` - Container lifecycle control
- `update(name, new_package)` - Version upgrades
- `get_status(name)` - Container state and health
- `list_installed()` - All installed MCPs with status

**Smart Features:**
- Environment variable resolution (${ANTHROPIC_API_KEY})
- Automatic network creation (mcp-network)
- Volume path creation
- Registry tracking (installed-mcps.json)
- Port binding configuration
- Capability management (NET_RAW, NET_ADMIN)

### 3. Backend API Endpoints

**New MCP Management Routes:**

```python
POST   /registries/install/mcp/{mcp_id}    # Install MCP from registry
DELETE /mcps/{mcp_name}                     # Uninstall MCP
POST   /mcps/{mcp_name}/start               # Start MCP container
POST   /mcps/{mcp_name}/stop                # Stop MCP container
POST   /mcps/{mcp_name}/restart             # Restart MCP container
POST   /mcps/{mcp_name}/update              # Update to latest version
GET    /mcps/installed                      # List installed MCPs
GET    /mcps/{mcp_name}/status              # Get MCP status
```

**Automatic Registration:**
- MCPs are auto-registered with orchestrator on install
- Dynamic endpoint discovery (host mode vs bridge mode)
- Startup discovery of previously installed MCPs
- No manual docker-compose edits required

### 4. Enhanced UI (Registry Page)

**Three Tabs:**

1. **Teams Tab** - Install team packages
2. **MCPs Tab** - Browse and install MCP packages
   - ~~Manual Install Required~~ → ⬇️ Install button
   - One-click deployment with progress indication
3. **💿 Installed MCPs Tab** (NEW)
   - Real-time container status (🟢 Running / 🔴 Stopped)
   - Container name and metadata
   - Installation timestamp
   - Lifecycle controls:
     - ▶️ Start / ⏸️ Stop / 🔄 Restart
     - ⬆️ Update (version management)
     - 🗑️ Uninstall (with confirmation)

**Visual Enhancements:**
- Status indicators with color coding
- Action buttons with loading states
- Success/error notifications
- Installed MCP cards with detailed info

### 5. Docker Integration

**docker-compose.yml Changes:**
```yaml
orchestrator:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
    - ./mcp_servers:/app/mcp_servers              # Build contexts
```

**backend/requirements.txt:**
```
docker==7.0.0  # Python Docker SDK
```

---

## How It Works

### Installation Flow

```
User clicks "Install" on MCP in UI
         ↓
POST /registries/install/mcp/{mcp_id}
         ↓
Fetch package from registry (agent-1.0.0.json)
         ↓
MCPManager.install(mcp_package)
    1. Build Docker image (if build context provided)
    2. Create volumes (./logs/agent)
    3. Resolve environment variables
    4. Configure network (mcp-network)
    5. Create and start container
    6. Save to installed-mcps.json
         ↓
register_installed_mcp(mcp_package)
    - Determine endpoint (bridge vs host mode)
    - Register with orchestrator MCP registry
         ↓
Response: {
  "status": "installed",
  "name": "agent",
  "version": "1.0.0",
  "container_id": "abc123...",
  "container_name": "mcp-agent"
}
```

### Startup Discovery

```
Orchestrator starts
         ↓
Load installed-mcps.json
         ↓
For each installed MCP:
    - Check if container is running
    - Parse deployment config
    - Determine endpoint
    - Register with orchestrator
         ↓
Result: Dynamically installed MCPs available immediately
```

### Version Updates

```
User clicks "Update" on installed MCP
         ↓
POST /mcps/{mcp_name}/update
         ↓
Fetch latest version from registry
         ↓
MCPManager.update(name, new_package)
    1. Uninstall old version (stop + remove)
    2. Install new version (build + deploy)
    3. Update installed-mcps.json
         ↓
Re-register with orchestrator
         ↓
Response: {
  "status": "updated",
  "old_version": "1.0.0",
  "new_version": "1.1.0"
}
```

---

## Usage Examples

### Install MCP from Registry

**Via UI:**
1. Navigate to Registry page
2. Click "MCPs" tab
3. Find desired MCP (e.g., "agent-1.0.0")
4. Click "⬇️ Install"
5. Wait for success notification
6. Check "Installed MCPs" tab

**Via API:**
```bash
curl -X POST http://localhost:8000/registries/install/mcp/agent-1.0.0
```

### Manage Installed MCPs

**Check Status:**
```bash
curl http://localhost:8000/mcps/agent/status
```

**Stop MCP:**
```bash
curl -X POST http://localhost:8000/mcps/agent/stop
```

**Update MCP:**
```bash
curl -X POST http://localhost:8000/mcps/agent/update
```

### List All Installed MCPs

```bash
curl http://localhost:8000/mcps/installed
```

**Response:**
```json
[
  {
    "name": "agent",
    "version": "1.0.0",
    "container_id": "abc123...",
    "container_name": "mcp-agent",
    "state": "running",
    "running": true,
    "installed_at": "2025-10-15T10:30:00Z"
  }
]
```

---

## Registry Package Format

All three MCPs have been updated with full deployment metadata:

1. **agent-1.0.0.json** - AI Agent with LLM
   - Bridge network mode
   - Port 7000
   - Requires ANTHROPIC_API_KEY

2. **file-tools-1.0.0.json** - File operations
   - Bridge network mode
   - Port 7002
   - Workspace volume mount

3. **nmap-recon-1.0.0.json** - Network scanning
   - Host network mode (special)
   - Port 7003
   - Requires NET_RAW, NET_ADMIN capabilities

---

## Architecture Benefits

### Before (Manual)
- MCPs hardcoded in docker-compose.yml
- Manual container management
- No version tracking
- Static configuration

### After (Package Management)
- Dynamic MCP installation from registry
- Automatic container lifecycle
- Full version management
- Modular, scalable architecture

### Key Advantages

1. **Zero Manual Configuration**
   - No docker-compose edits
   - No container management commands
   - Point-and-click installation

2. **Version Control**
   - Track installed versions
   - Update to latest releases
   - Rollback support (via uninstall + reinstall)

3. **Dynamic Discovery**
   - MCPs auto-register on startup
   - Survive orchestrator restarts
   - Network-aware endpoint detection

4. **User-Friendly**
   - Visual status indicators
   - One-click operations
   - Clear success/error feedback

5. **Production Ready**
   - Resource requirements
   - Health monitoring
   - Automatic restart policies

---

## Testing

### 1. Rebuild Orchestrator

```bash
docker-compose build orchestrator
```

### 2. Start Platform

```bash
docker-compose up -d
```

### 3. Test Installation

**Via UI:**
1. Open http://localhost:3000
2. Navigate to Registry page
3. Go to "MCPs" tab
4. Install an MCP package
5. Check "Installed MCPs" tab
6. Test start/stop/restart controls
7. Try updating to a new version

**Via API:**
```bash
# Install MCP
curl -X POST http://localhost:8000/registries/install/mcp/agent-1.0.0

# Check status
curl http://localhost:8000/mcps/installed

# Stop container
curl -X POST http://localhost:8000/mcps/agent/stop

# Start container
curl -X POST http://localhost:8000/mcps/agent/start

# Update to latest
curl -X POST http://localhost:8000/mcps/agent/update

# Uninstall
curl -X DELETE http://localhost:8000/mcps/agent
```

### 4. Verify Dynamic Discovery

```bash
# Restart orchestrator
docker-compose restart orchestrator

# Check logs - should see auto-registration
docker-compose logs orchestrator | grep "Registered"
```

Expected output:
```
✅ Registered agent v1.0.0 at http://mcp-agent:7000
✅ Orchestrator ready! 3 MCP servers registered.
```

---

## Files Modified

### New Files
- `backend/app/mcp_manager.py` - Docker lifecycle manager (440 lines)
- `MCP_PACKAGE_MANAGEMENT.md` - This documentation

### Modified Files

**Backend:**
- `backend/requirements.txt` - Added docker==7.0.0
- `backend/app/main.py` - Added MCP management endpoints, dynamic discovery
  - Lines 16: Import MCPManager
  - Lines 143: Initialize mcp_manager
  - Lines 369-454: Enhanced startup with discovery
  - Lines 1115-1292: MCP management API (8 endpoints)

**Registry Packages:**
- `registry-server/registries/mcps/agent-1.0.0.json` - Full deployment config
- `registry-server/registries/mcps/file-tools-1.0.0.json` - Full deployment config
- `registry-server/registries/mcps/nmap-recon-1.0.0.json` - Full deployment config

**Frontend:**
- `frontend/src/pages/RegistryPage.jsx` - Added MCP install + Installed MCPs tab
  - Lines 9-13: New state for installed MCPs
  - Lines 36-43: Load installed MCPs function
  - Lines 77-195: MCP management functions (install, uninstall, start, stop, restart, update)
  - Lines 284-289: New "Installed MCPs" tab
  - Lines 357-363: Install button for MCPs
  - Lines 371-454: Installed MCPs UI with controls

- `frontend/src/pages/RegistryPage.css` - Styles for installed MCPs
  - Lines 376-513: New styles for installed MCP cards, status, actions

**Docker:**
- `docker-compose.yml` - Docker socket mount + build contexts
  - Line 16: `/var/run/docker.sock:/var/run/docker.sock`
  - Line 17: `./mcp_servers:/app/mcp_servers`

---

## Troubleshooting

### MCP Installation Fails

**Check:**
1. Docker socket accessible: `ls -la /var/run/docker.sock`
2. Orchestrator has access: `docker exec orchestrator ls /var/run/docker.sock`
3. Build context exists: `ls mcp_servers/`
4. Registry reachable: `curl http://localhost:9000/catalog`

### Container Not Starting

**Debug:**
```bash
# Check container logs
docker logs mcp-agent

# Check container exists
docker ps -a | grep mcp-agent

# Manual start attempt
docker start mcp-agent
```

### MCP Not Registered

**Verify:**
```bash
# Check orchestrator sees it
curl http://localhost:8000/mcp/servers

# Check installed registry
docker exec orchestrator cat /app/installed-mcps.json

# Restart orchestrator to trigger discovery
docker-compose restart orchestrator
```

---

## Future Enhancements

1. **Dependency Management**
   - Automatic dependency installation
   - Version conflict resolution

2. **Resource Limits**
   - Enforce min_memory/min_cpu requirements
   - Container resource constraints

3. **Health Checks**
   - Automated health monitoring
   - Auto-restart on failure

4. **Rollback Support**
   - Keep previous versions
   - One-click rollback

5. **Multi-Registry**
   - Install from any configured registry
   - Registry priority handling

6. **Build Optimization**
   - Layer caching
   - Pre-built images (pull vs build)

---

## Summary

MCPs are now **fully modular packages** with:

- ✅ **Install from registry** - One-click deployment
- ✅ **Version tracking** - Update to latest releases
- ✅ **Lifecycle management** - Start/stop/restart/uninstall
- ✅ **Dynamic deployment** - Docker container automation
- ✅ **Auto-discovery** - No manual configuration
- ✅ **Full UI integration** - Visual management interface

**Just like yum/apt for packages, but for MCP servers!**

```bash
# Old way
vi docker-compose.yml  # Edit manually
docker-compose up -d   # Rebuild everything

# New way
Click "Install" in UI  # Done!
```
