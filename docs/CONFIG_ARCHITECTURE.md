# ADCL Configuration Architecture

## Philosophy

Following Unix principles and 12-Factor App methodology:
- **Configuration is code** - All config in plain text (YAML)
- **Modularity** - Each service has its own config file
- **Environment override** - Environment variables take precedence
- **Inspectability** - All configs viewable via `cat`, `grep`, `jq`

## Directory Structure

```
adcl/
├── .env                          # Environment variable overrides
├── configs/                      # Centralized config view
│   ├── orchestrator.yaml         # Orchestrator's own config
│   ├── agent.yaml -> ../mcp_servers/agent/config.yaml
│   ├── nmap_recon.yaml -> ../mcp_servers/nmap_recon/config.yaml
│   ├── file_tools.yaml -> ../mcp_servers/file_tools/config.yaml
│   ├── history.yaml -> ../mcp_servers/history/config.yaml
│   └── registry.yaml -> ../registry-server/config.yaml
├── mcp_servers/
│   ├── agent/
│   │   ├── config.yaml           # Agent's config (source of truth)
│   │   ├── server.py
│   │   └── README.md
│   ├── nmap_recon/
│   │   ├── config.yaml           # Nmap's config (source of truth)
│   │   └── ...
│   └── ...
└── registry-server/
    ├── config.yaml               # Registry's config (source of truth)
    └── ...
```

## Configuration Precedence

For all services:

```
1. Environment Variable  (highest priority)
2. config.yaml file      (medium priority)
3. Code default          (fallback)
```

### Example:
```yaml
# mcp_servers/agent/config.yaml
service:
  port: 7000
```

```bash
# .env
AGENT_PORT=7100  # This overrides config.yaml
```

Agent reads: `port = os.getenv("AGENT_PORT") or yaml["service.port"] or 7000`

Result: Agent runs on port **7100**

## Per-Service Configuration

### 1. Orchestrator (`configs/orchestrator.yaml`)

**Purpose:** Orchestrator's own settings only

```yaml
orchestrator:
  port: 8000
  host: "0.0.0.0"

paths:
  agent_definitions: "/app/agent-definitions"
  workflows: "/app/workflows"

docker:
  socket_path: "unix:///var/run/docker.sock"
  network_name: "mcp-network"
```

**Environment overrides:**
- `ORCHESTRATOR_PORT` → `orchestrator.port`
- `DOCKER_NETWORK_NAME` → `docker.network_name`
- etc.

### 2. MCP Servers (e.g., `mcp_servers/agent/config.yaml`)

**Purpose:** Each MCP's self-contained configuration

```yaml
service:
  name: "agent"
  port: 7000

llm:
  max_tokens: 4096
```

**Environment overrides:**
- `AGENT_PORT` → `service.port`

**Key principle:** MCPs are **modular** - config lives with the MCP, not centrally

### 3. Registry Server (`registry-server/config.yaml`)

**Purpose:** Registry service configuration

```yaml
service:
  port: 9000

storage:
  registries_path: "/app/registries"
```

**Environment overrides:**
- `REGISTRY_PORT` → `service.port`

## Why Symlinks?

Symlinks in `configs/` provide a **unified view**:

```bash
# Inspect all configurations
ls -l configs/
cat configs/*.yaml

# Find all ports
grep -r "port:" configs/

# Check agent config
cat configs/agent.yaml
```

But the **source of truth** remains in each service's directory, maintaining modularity.

## Inspecting Configuration

### View all configs:
```bash
cat configs/*.yaml | less
```

### Find specific settings:
```bash
grep -r "port:" configs/
grep -r "timeout" configs/
```

### Parse with jq:
```bash
# Convert YAML to JSON first
yq eval -o=json configs/orchestrator.yaml | jq '.orchestrator.port'
```

### Check active environment overrides:
```bash
cat .env | grep -v '^#' | grep -v '^$'
```

## Adding a New MCP

When creating a new MCP:

1. **Create MCP directory:**
   ```bash
   mkdir mcp_servers/my_mcp
   ```

2. **Add config.yaml:**
   ```yaml
   # mcp_servers/my_mcp/config.yaml
   service:
     name: "my_mcp"
     port: 7005
     description: "My custom MCP server"
   ```

3. **Create symlink:**
   ```bash
   ln -s ../mcp_servers/my_mcp/config.yaml configs/my_mcp.yaml
   ```

4. **Add env override (optional):**
   ```bash
   echo "MY_MCP_PORT=7005" >> .env
   ```

5. **MCP reads config:**
   ```python
   import yaml
   import os

   with open("config.yaml") as f:
       config = yaml.safe_load(f)

   port = int(os.getenv("MY_MCP_PORT", config["service"]["port"]))
   ```

## Best Practices

### DO:
✓ Keep each service's config in its own directory
✓ Use environment variables for deployment-specific overrides
✓ Document all config options in the YAML file
✓ Use symlinks for convenient inspection
✓ Follow naming convention: `{SERVICE_NAME}_PORT`, `{SERVICE_NAME}_TIMEOUT`, etc.

### DON'T:
✗ Put MCP-specific config in orchestrator.yaml
✗ Hardcode values in Python code
✗ Share config files between services
✗ Use binary config formats
✗ Hide configuration in databases

## Configuration Loader

### Orchestrator (Python)
```python
from app.config import get_config

config = get_config()  # Loads configs/orchestrator.yaml
port = config.get_orchestrator_port()  # ENV > YAML > default
```

### MCPs (Python)
```python
import yaml
import os

# Load own config
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# Env var override
port = int(os.getenv("AGENT_PORT", config["service"]["port"]))
```

## Debugging Configuration

### Check what orchestrator sees:
```bash
docker exec orchestrator python -c "from app.config import get_config; c = get_config(); print(c.get_orchestrator_port())"
```

### Check what's in config file:
```bash
cat configs/orchestrator.yaml
```

### Check environment overrides:
```bash
docker exec orchestrator env | grep PORT
```

### Reload config (if supported):
```python
from app.config import reload_config
config = reload_config()  # Re-reads YAML file
```

## Migration from Hardcoded Values

Before:
```python
port = 8000  # Hardcoded ❌
```

After:
```python
port = config.get_orchestrator_port()  # ENV > YAML > 8000 ✓
```

All configuration now follows: **ENV > YAML > Code Default**

## Summary

| Component | Config File | Symlinked As | Env Var Prefix |
|-----------|-------------|--------------|----------------|
| Orchestrator | `configs/orchestrator.yaml` | N/A (primary) | Various |
| Agent MCP | `mcp_servers/agent/config.yaml` | `configs/agent.yaml` | `AGENT_*` |
| Nmap MCP | `mcp_servers/nmap_recon/config.yaml` | `configs/nmap_recon.yaml` | `NMAP_*` |
| File Tools MCP | `mcp_servers/file_tools/config.yaml` | `configs/file_tools.yaml` | `FILE_TOOLS_*` |
| History MCP | `mcp_servers/history/config.yaml` | `configs/history.yaml` | `HISTORY_*` |
| Registry | `registry-server/config.yaml` | `configs/registry.yaml` | `REGISTRY_*` |

**Principle:** Each service is self-contained, `configs/` provides unified inspection view.
