# MCP Servers Guide

Learn about Model Context Protocol (MCP) servers - the tool servers that extend agent capabilities.

---

## Table of Contents

1. [What are MCP Servers?](#what-are-mcp-servers)
2. [How MCP Works](#how-mcp-works)
3. [Available MCP Servers](#available-mcp-servers)
4. [Using MCP Servers](#using-mcp-servers)
5. [Creating Custom MCP Servers](#creating-custom-mcp-servers)
6. [MCP Server Configuration](#mcp-server-configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What are MCP Servers?

**MCP (Model Context Protocol) Servers** are independent tool servers that expose specific capabilities to AI agents. They enable agents to interact with external systems without modifying the agent code.

### Key Concepts

**Separation of Concerns**:
```
Agent (AI Brain)         MCP Server (Tool Implementation)
     │                            │
     │ "I need to scan network"  │
     ├───────MCP Protocol ───────▶│
     │                            │ Executes nmap scan
     │                            │
     │◀────── Results ────────────┤
     │                            │
     │ "I need to write file"    │
     ├───────MCP Protocol ───────▶│
     │                            │ Writes file
```

**Benefits**:
- **Modularity**: Each MCP is independent
- **Reusability**: One MCP, many agents
- **Isolation**: MCPs run in separate containers
- **Extensibility**: Add new MCPs without changing platform
- **Security**: Limited scope per MCP

---

## How MCP Works

### Architecture

```
┌──────────────────────────────────────────────┐
│  Agent (Claude AI)                           │
│  - Reasons about task                        │
│  - Decides which tool to call                │
│  - Passes parameters                         │
└────────────────┬─────────────────────────────┘
                 │ MCP Protocol (HTTP/stdio)
                 ▼
┌──────────────────────────────────────────────┐
│  MCP Server (e.g., nmap_recon)               │
│  - Exposes tools via MCP                     │
│  - Validates parameters                      │
│  - Executes tool                             │
│  - Returns JSON result                       │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│  External System (e.g., Nmap, filesystem)    │
│  - Actual implementation                     │
│  - System calls, API requests, etc.          │
└──────────────────────────────────────────────┘
```

### Tool Call Flow

**1. Agent Decides**:
```
Agent reasoning: "I need to scan the network to find hosts"
Decision: Call nmap_recon.network_discovery
```

**2. MCP Request**:
```json
POST http://localhost:7003/call_tool
{
  "tool": "network_discovery",
  "params": {
    "target": "192.168.1.0/24",
    "scan_type": "ping"
  }
}
```

**3. MCP Execution**:
```python
# Inside MCP server
@tool("network_discovery")
async def network_discovery(target: str, scan_type: str):
    # Execute nmap scan
    result = subprocess.run(["nmap", "-sn", target])

    # Parse results
    hosts = parse_nmap_output(result.stdout)

    # Return JSON
    return {"hosts": hosts, "count": len(hosts)}
```

**4. MCP Response**:
```json
{
  "result": {
    "hosts": ["192.168.1.1", "192.168.1.2", "192.168.1.100"],
    "count": 3
  },
  "status": "success"
}
```

**5. Agent Observes**:
```
Agent receives: Found 3 active hosts
Agent reasoning: "Good, now I should scan ports on these hosts"
Next decision: Call nmap_recon.port_scan
```

---

## Available MCP Servers

### Core MCPs (Pre-installed)

#### 1. agent (Port 7000)

**Purpose**: AI reasoning capabilities

**Tools**:
- **think**: General reasoning and analysis
- **code**: Generate code solutions
- **review**: Code review and analysis

**Example Usage**:
```json
{
  "tool": "think",
  "params": {
    "task": "Analyze the security implications of these open ports: 22, 80, 443, 3389"
  }
}
```

**Response**:
```json
{
  "result": "Port 3389 (RDP) is concerning as it's often targeted. Recommendations: ..."
}
```

**Configuration**:
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Required
AGENT_PORT=7000
```

#### 2. file_tools (Port 7002)

**Purpose**: File system operations

**Tools**:
- **read_file**: Read file contents
- **write_file**: Write content to file
- **list_directory**: List directory contents

**Example Usage**:
```json
{
  "tool": "read_file",
  "params": {
    "path": "/workspace/config.json"
  }
}
```

**Response**:
```json
{
  "result": {
    "content": "{\"setting\": \"value\"}",
    "size": 24
  }
}
```

**Working Directory**: `/workspace` (shared volume)

#### 3. nmap_recon (Port 7003)

**Purpose**: Network security scanning

**Tools**:
- **network_discovery**: Find active hosts
- **port_scan**: Scan for open ports
- **service_detection**: Identify running services
- **vulnerability_scan**: Check for known vulnerabilities

**Example Usage**:
```json
{
  "tool": "network_discovery",
  "params": {
    "target": "192.168.1.0/24",
    "scan_type": "ping"
  }
}
```

**Response**:
```json
{
  "result": {
    "hosts": [
      {"ip": "192.168.1.1", "hostname": "router.local"},
      {"ip": "192.168.1.100", "hostname": "server.local"}
    ],
    "scan_time": "2.3s"
  }
}
```

**Requirements**:
- Docker: Host network mode
- Network: Access to scan targets

### Optional MCPs (Install from Registry)

#### 4. kali (Port 7005)

**Purpose**: Penetration testing tools

**Tools**:
- **nikto_scan**: Web server scanner
- **dirb_scan**: Directory brute force
- **sqlmap_scan**: SQL injection testing
- **metasploit_search**: Exploit search
- **hydra_bruteforce**: Password cracking
- **wpscan**: WordPress scanner
- **dns_enum**: DNS enumeration
- **subdomain_enum**: Subdomain discovery

**Warning**: For authorized security testing only

**Example Usage**:
```json
{
  "tool": "nikto_scan",
  "params": {
    "target": "http://192.168.1.100",
    "options": ["-Tuning", "1"]
  }
}
```

#### 5. history (Port 7004)

**Purpose**: Conversation history management

**Tools**:
- **create_session**: Start new session
- **append_message**: Add message to session
- **get_messages**: Retrieve conversation
- **search_titles**: Search by title
- **search_messages**: Full-text search

**Storage**: JSONL files in `volumes/history/`

**Example Usage**:
```json
{
  "tool": "get_messages",
  "params": {
    "session_id": "01JEXAMPLE123",
    "limit": 10
  }
}
```

#### 6. linear (Port 7006)

**Purpose**: Linear issue tracking integration

**Tools**:
- **get_issue**: Fetch issue details
- **create_issue**: Create new issue
- **update_issue**: Update existing issue
- **list_issues**: Query issues
- **create_comment**: Add comment

**Configuration**:
```bash
LINEAR_API_KEY=lin_api_...  # Required
```

**Example Usage**:
```json
{
  "tool": "create_issue",
  "params": {
    "title": "Security vulnerability found",
    "description": "Port 3389 exposed to internet",
    "team": "SECURITY",
    "priority": 1
  }
}
```

---

## Using MCP Servers

### Viewing Available MCPs

**Via UI**:
1. Go to http://localhost:3000
2. Click "MCP Servers" in sidebar
3. View list of installed servers

**Via API**:
```bash
curl http://localhost:8000/mcp/servers
```

**Response**:
```json
{
  "servers": [
    {
      "name": "agent",
      "port": 7000,
      "status": "running",
      "tools": ["think", "code", "review"]
    },
    {
      "name": "file_tools",
      "port": 7002,
      "status": "running",
      "tools": ["read_file", "write_file", "list_directory"]
    }
  ]
}
```

### Testing MCP Tools

**Direct API Call**:
```bash
# Test file_tools MCP
curl -X POST http://localhost:7002/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_directory",
    "params": {"path": "/workspace"}
  }'
```

**Via Agent**:
```
Go to Playground
Select any agent with file_tools access
Ask: "List the files in /workspace"
```

### MCP Server Status

**Check Health**:
```bash
# Check all MCPs
docker-compose ps | grep mcp

# Check specific MCP health endpoint
curl http://localhost:7000/health  # agent
curl http://localhost:7002/health  # file_tools
curl http://localhost:7003/health  # nmap_recon
```

**View Logs**:
```bash
# View all MCP logs
docker-compose logs | grep mcp

# View specific MCP
docker-compose logs agent-mcp
docker-compose logs file-tools-mcp
docker-compose logs nmap-mcp
```

---

## Creating Custom MCP Servers

### MCP Server Structure

```
mcp_servers/my_mcp/
├── mcp.json           # MCP metadata
├── server.py          # MCP implementation
├── requirements.txt   # Python dependencies
├── Dockerfile         # Container definition
└── README.md         # Documentation
```

### Step-by-Step: Create a Weather MCP

**1. Create Directory**:
```bash
mkdir -p mcp_servers/weather_mcp
cd mcp_servers/weather_mcp
```

**2. Create mcp.json**:
```json
{
  "name": "weather_mcp",
  "version": "0.1.0",
  "description": "Fetch weather data",
  "port": 7010,
  "protocol": "http",
  "tools": [
    {
      "name": "get_weather",
      "description": "Get current weather for a location",
      "parameters": {
        "location": {
          "type": "string",
          "description": "City name or coordinates"
        }
      }
    }
  ]
}
```

**3. Create server.py**:
```python
#!/usr/bin/env python3
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

class ToolRequest(BaseModel):
    tool: str
    params: dict

class ToolResponse(BaseModel):
    result: dict
    status: str

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/call_tool", response_model=ToolResponse)
async def call_tool(request: ToolRequest):
    """Execute MCP tool."""
    if request.tool == "get_weather":
        return await get_weather(request.params)
    else:
        raise HTTPException(status_code=404, detail=f"Tool {request.tool} not found")

async def get_weather(params: dict) -> ToolResponse:
    """Fetch weather data."""
    location = params.get("location")
    if not location:
        return ToolResponse(
            result={"error": "location required"},
            status="error"
        )

    # Call weather API (example using wttr.in)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://wttr.in/{location}?format=j1"
        )
        data = response.json()

    # Extract relevant data
    current = data["current_condition"][0]
    result = {
        "location": location,
        "temperature": current["temp_C"],
        "condition": current["weatherDesc"][0]["value"],
        "humidity": current["humidity"],
        "wind_speed": current["windspeedKmph"]
    }

    return ToolResponse(result=result, status="success")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7010))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**4. Create requirements.txt**:
```txt
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.1
pydantic==2.5.0
```

**5. Create Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-7010}/health || exit 1

# Run server
CMD ["python", "server.py"]
```

**6. Add to docker-compose.yml**:
```yaml
  weather-mcp:
    build: ./mcp_servers/weather_mcp
    container_name: weather-mcp
    environment:
      - PORT=7010
    ports:
      - "7010:7010"
    networks:
      - adcl_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7010/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**7. Build and Run**:
```bash
# Build the MCP
docker-compose build weather-mcp

# Start the MCP
docker-compose up -d weather-mcp

# Test it
curl -X POST http://localhost:7010/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_weather",
    "params": {"location": "London"}
  }'
```

**8. Create Agent That Uses It**:
```json
{
  "name": "weather_assistant",
  "version": "0.1.0",
  "description": "Provides weather information",
  "persona": "You are a weather assistant. Use the get_weather tool to provide current weather information.",
  "mcp_servers": ["weather_mcp", "agent"],
  "config": {
    "model": "claude-sonnet-4-5"
  }
}
```

---

## MCP Server Configuration

### Port Assignment

Default ports (configure in `.env`):
```bash
AGENT_PORT=7000
FILE_TOOLS_PORT=7002
NMAP_PORT=7003
HISTORY_PORT=7004
KALI_PORT=7005
LINEAR_PORT=7006
# Custom MCPs: 7010+
```

### Environment Variables

Pass configuration via environment:
```yaml
# docker-compose.yml
  my-mcp:
    environment:
      - PORT=7010
      - API_KEY=${MY_API_KEY}
      - DEBUG=false
```

### Resource Limits

Set container limits:
```yaml
  my-mcp:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### Network Mode

**Bridge (default)**: Isolated network
```yaml
  my-mcp:
    networks:
      - adcl_network
```

**Host**: Access host network (for network tools)
```yaml
  nmap-mcp:
    network_mode: "host"
```

---

## Best Practices

### 1. Single Responsibility

**Do**: One MCP, one domain
```
file_tools: File operations only
nmap_recon: Network scanning only
weather_mcp: Weather data only
```

**Don't**: Swiss army knife
```
everything_mcp: Files + Network + Weather + Email + ...
```

### 2. Clear Tool Descriptions

**Do**:
```json
{
  "tool": "network_discovery",
  "description": "Scan network to find active hosts using ping scan",
  "parameters": {
    "target": {
      "type": "string",
      "description": "Target network in CIDR notation (e.g., 192.168.1.0/24)"
    }
  }
}
```

**Don't**:
```json
{
  "tool": "scan",
  "description": "Scan stuff"
}
```

### 3. Validation

Validate inputs:
```python
@app.post("/call_tool")
async def call_tool(request: ToolRequest):
    # Validate tool exists
    if request.tool not in AVAILABLE_TOOLS:
        raise HTTPException(404, f"Tool {request.tool} not found")

    # Validate required parameters
    if "target" not in request.params:
        raise HTTPException(400, "Parameter 'target' required")

    # Execute tool
    return await execute_tool(request.tool, request.params)
```

### 4. Error Handling

Return meaningful errors:
```python
try:
    result = await execute_tool(params)
    return ToolResponse(result=result, status="success")
except FileNotFoundError:
    return ToolResponse(
        result={"error": "File not found"},
        status="error"
    )
except PermissionError:
    return ToolResponse(
        result={"error": "Permission denied"},
        status="error"
    )
```

### 5. Logging

Log all operations:
```python
import logging

logger = logging.getLogger(__name__)

@app.post("/call_tool")
async def call_tool(request: ToolRequest):
    logger.info(f"Tool called: {request.tool}")
    logger.debug(f"Parameters: {request.params}")

    try:
        result = await execute_tool(request.tool, request.params)
        logger.info(f"Tool succeeded: {request.tool}")
        return ToolResponse(result=result, status="success")
    except Exception as e:
        logger.error(f"Tool failed: {request.tool}: {e}")
        raise
```

---

## Troubleshooting

### MCP Server Not Starting

**Symptom**: Container exits immediately

**Solution**:
```bash
# View logs
docker-compose logs my-mcp

# Common issues:
# - Port already in use
# - Missing environment variables
# - Python dependencies not installed
# - Syntax errors in server.py
```

### Tool Not Found

**Symptom**: "Tool X not found"

**Solution**:
1. Check tool is defined in mcp.json
2. Verify tool handler exists in server.py
3. Ensure tool name matches exactly

### MCP Not Responding

**Symptom**: Requests timeout

**Solution**:
```bash
# Check MCP is running
docker-compose ps my-mcp

# Test health endpoint
curl http://localhost:7010/health

# Check network connectivity
docker network inspect adcl_network
```

---

## Next Steps

- **[Agents Guide](Agents-Guide)** - Use MCPs in agents
- **[Workflows Guide](Workflows-Guide)** - Use MCPs in workflows
- **[Configuration Guide](Configuration-Guide)** - Advanced MCP configuration

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
