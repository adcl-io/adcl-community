# MCP Servers Directory

This directory contains self-contained MCP (Model Context Protocol) server implementations.

## Directory Structure

Each MCP server is **fully self-contained** and portable - you can move any folder independently:

```
mcp_servers/
├── base_server.py           # Shared base (also copied to each MCP)
├── requirements.txt         # Shared requirements (also copied to each MCP)
├── agent/                   # ✅ SELF-CONTAINED & PORTABLE
│   ├── mcp.json             # 📋 Metadata (name, version, tools, deployment)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── base_server.py
│   └── agent_server.py
├── file_tools/              # ✅ SELF-CONTAINED & PORTABLE
│   ├── mcp.json             # 📋 Metadata
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── base_server.py
│   └── file_server.py
└── nmap/                    # ✅ SELF-CONTAINED & PORTABLE
    ├── mcp.json             # 📋 Metadata
    ├── Dockerfile
    ├── requirements.txt
    ├── base_server.py
    └── nmap_server.py
```

## Design Philosophy

**Each MCP folder is portable and self-contained:**
- Can be moved/copied anywhere
- Can be built standalone without parent directory
- Contains all its own dependencies
- No hardcoded paths to parent directories

This makes it easy to:
- Distribute individual MCPs
- Develop MCPs independently
- Test MCPs in isolation
- Package MCPs for sharing

## MCP Metadata (mcp.json)

Each MCP folder contains an `mcp.json` file with complete metadata:

```json
{
  "name": "agent",
  "version": "1.0.0",
  "description": "AI Agent with think/code/review capabilities",
  "type": "mcp",
  "deployment": {
    "build": {
      "context": ".",
      "dockerfile": "Dockerfile"
    },
    "image": "mcp-agent:1.0.0",
    "container_name": "mcp-agent",
    "ports": [...],
    "volumes": [...],
    "environment": {...},
    "networks": ["mcp-network"]
  },
  "requirements": {
    "api_keys": ["ANTHROPIC_API_KEY"],
    "min_memory": "512M",
    "min_cpu": "0.5"
  },
  "tools": [
    {
      "name": "think",
      "description": "Reasoning and analysis tool"
    }
  ],
  "tags": ["ai", "reasoning"],
  "author": "MCP Platform Team",
  "license": "MIT"
}
```

**Metadata includes:**
- **Identity**: name, version, description, type
- **Deployment**: Docker build config, ports, volumes, environment variables
- **Requirements**: API keys, resource limits, system capabilities
- **Tools**: List of tools this MCP provides
- **Tags**: Categories for discovery
- **Author & License**: Attribution

**Note:** The registry files in `registry-server/registries/mcps/*.json` should be copies of these metadata files (with adjusted paths for registry context).

## Building MCPs

### Build from MCP directory

Each MCP can be built from its own directory:

```bash
# Agent MCP
cd mcp_servers/agent/
docker build -t mcp-agent:1.0.0 .

# File Tools MCP
cd mcp_servers/file_tools/
docker build -t mcp-file-tools:1.0.0 .

# Nmap Recon MCP
cd mcp_servers/nmap/
docker build -t mcp-nmap-recon:1.0.0 .
```

### Registry-based installation

The registry automatically builds MCPs using their self-contained Dockerfiles:

```json
{
  "deployment": {
    "build": {
      "context": "./mcp_servers/agent",
      "dockerfile": "Dockerfile"
    }
  }
}
```

## Adding a New MCP Server

To add a new self-contained MCP:

### 1. Create MCP folder

```bash
cd mcp_servers/
mkdir my_new_mcp
cd my_new_mcp
```

### 2. Copy base files

```bash
cp ../base_server.py .
cp ../requirements.txt .
```

### 3. Create your server

Create `my_server.py`:

```python
from base_server import BaseMCPServer

class MyMCPServer(BaseMCPServer):
    def __init__(self, port: int = 7004):
        super().__init__(
            name="my_mcp",
            port=port,
            description="My custom MCP server"
        )
        self._register_tools()

    def _register_tools(self):
        self.register_tool(
            name="my_tool",
            handler=self.my_tool_handler,
            description="Does something useful",
            input_schema={
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                },
                "required": ["input"]
            }
        )

    def my_tool_handler(self, input: str) -> str:
        return f"Processed: {input}"

if __name__ == "__main__":
    server = MyMCPServer()
    server.run()
```

### 4. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies (if needed)
# RUN apt-get update && apt-get install -y <packages>

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY base_server.py .
COPY my_server.py .

# Expose port
EXPOSE 7004

# Run server
CMD ["python", "my_server.py"]
```

### 5. Create metadata file

Create `mcp.json`:

```json
{
  "name": "my_mcp",
  "version": "1.0.0",
  "description": "My custom MCP server",
  "type": "mcp",
  "deployment": {
    "build": {
      "context": ".",
      "dockerfile": "Dockerfile"
    },
    "image": "mcp-my-mcp:1.0.0",
    "container_name": "mcp-my-mcp",
    "ports": [
      {
        "host": "${MY_MCP_PORT:-7004}",
        "container": "${MY_MCP_PORT:-7004}"
      }
    ],
    "environment": {
      "PYTHONUNBUFFERED": "1",
      "MY_MCP_PORT": "${MY_MCP_PORT:-7004}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },
  "requirements": {
    "min_memory": "256M",
    "min_cpu": "0.25"
  },
  "tools": [
    {
      "name": "my_tool",
      "description": "Does something useful"
    }
  ],
  "tags": ["custom"],
  "author": "Your Name",
  "license": "MIT"
}
```

### 6. Update requirements.txt (if needed)

If your MCP needs additional Python packages, add them to `requirements.txt` in your MCP folder.

### 7. Publish to registry (optional)

To make your MCP available via the registry server, copy `mcp.json` to the registry with adjusted paths:

Create `registry-server/registries/mcps/my-mcp-1.0.0.json`:

```json
{
  "name": "my_mcp",
  "version": "1.0.0",
  "description": "My custom MCP server",
  "type": "mcp",
  "deployment": {
    "build": {
      "context": "./mcp_servers/my_new_mcp",  // ← Adjusted from "." to full path
      "dockerfile": "Dockerfile"
    },
    "image": "mcp-my-mcp:1.0.0",
    "container_name": "mcp-my-mcp",
    "ports": [
      {
        "host": "${MY_MCP_PORT:-7004}",
        "container": "${MY_MCP_PORT:-7004}"
      }
    ],
    "environment": {
      "PYTHONUNBUFFERED": "1",
      "MY_MCP_PORT": "${MY_MCP_PORT:-7004}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },
  "tools": [
    {
      "name": "my_tool",
      "description": "Does something useful"
    }
  ],
  "tags": ["custom"],
  "author": "Your Name",
  "license": "MIT"
}
```

## Testing

Test your MCP standalone:

```bash
cd mcp_servers/my_new_mcp/
docker build -t mcp-my-mcp:test .
docker run -p 7004:7004 mcp-my-mcp:test
```

Test with curl:

```bash
# Health check
curl http://localhost:7004/health

# List tools
curl -X POST http://localhost:7004/mcp/list_tools

# Call tool
curl -X POST http://localhost:7004/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "my_tool", "arguments": {"input": "test"}}'
```

## Portability

Each MCP folder can be:
- **Zipped and shared**: `tar -czf agent-mcp.tar.gz agent/`
- **Moved to another project**: `cp -r agent/ /other/project/`
- **Versioned independently**: Each MCP has its own git history
- **Built anywhere**: No dependency on parent directory structure

## Shared Base Server

`base_server.py` provides:
- FastAPI app setup
- Standard MCP protocol endpoints (`/mcp/list_tools`, `/mcp/call_tool`)
- Tool registration system
- Health check endpoint

Each MCP folder has its own copy to ensure portability.

## Related Files

- Registry packages: `registry-server/registries/mcps/*.json`
- Build manager: `backend/app/mcp_manager.py`
- Docker manager: `backend/app/docker_manager.py`

## Migration Notes

This structure was updated from root-level Dockerfiles to self-contained folders for better portability. Each MCP now:
- ✅ Has its own Dockerfile in its folder
- ✅ Has its own copy of dependencies
- ✅ Can be built from its own directory
- ✅ Doesn't rely on parent directory structure
