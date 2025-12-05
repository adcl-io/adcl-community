# MCP Agent Platform - Architecture v0.1.0

## Core Concept

**Everything speaks MCP (Model Context Protocol).** The platform orchestrates AI agents, tools, and teams through a unified MCP interface. Think of it as a package manager (like yum) for AI capabilities, where each MCP server provides specialized tools that can be composed into workflows or teams.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend (Port 3000)                  │
│  ┌────────────┬──────────┬───────────┬────────┬──────────────┐  │
│  │ Playground │  Models  │    MCPs   │ Teams  │   Registry   │  │
│  │   (Chat)   │  Config  │  Browser  │ Builder│  (Packages)  │  │
│  └────────────┴──────────┴───────────┴────────┴──────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI Orchestrator (Port 8000)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • MCP Registry (in-memory)                              │   │
│  │  • Workflow Engine (visual workflow execution)           │   │
│  │  • Team Manager (file-based: agent-teams/*.json)         │   │
│  │  • Chat API (multi-agent collaboration)                  │   │
│  │  • Registry API (yum-like package management)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────┬────────────────────────────┬─────────────┬─────────────┘
         │                            │             │
         │ MCP Protocol (HTTP)        │             │ HTTP
         ▼                            ▼             ▼
┌─────────────────┐  ┌───────────────────┐  ┌─────────────────┐
│  Agent MCP      │  │  File Tools MCP   │  │  Nmap Recon MCP │
│  (Port 7000)    │  │  (Port 7002)      │  │  (Port 7003)    │
│                 │  │                   │  │                 │
│  ┌───────────┐  │  │  • read_file     │  │  • network_disc │
│  │ Anthropic │  │  │  • write_file    │  │  • port_scan    │
│  │   Claude  │  │  │  • list_dir      │  │  • service_det  │
│  │  3.5/4.0  │  │  │                  │  │  • vuln_scan    │
│  └───────────┘  │  └───────────────────┘  └─────────────────┘
│  Tools:         │        Port 7002              Port 7003
│  • think()      │       (Docker)              (Host Network)
│  • code()       │
│  • review()     │
└─────────────────┘
   Port 7000
   (Docker)
         ▲
         │ Anthropic API
         │
    ┌────┴─────┐
    │ Claude   │
    │   API    │
    └──────────┘
```

### Registry Server (Port 9000)

```
┌─────────────────────────────────────────┐
│     Registry Server (Port 9000)         │
│  ┌───────────────────────────────────┐  │
│  │  Catalog API                      │  │
│  │  • /catalog (list all packages)   │  │
│  │  • /mcps (MCP packages)           │  │
│  │  • /teams (team packages)         │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Package Storage                  │  │
│  │  registries/                      │  │
│  │  ├── mcps/                        │  │
│  │  │   ├── agent-1.0.0.json        │  │
│  │  │   ├── file-tools-1.0.0.json   │  │
│  │  │   └── nmap-recon-1.0.0.json   │  │
│  │  └── teams/                       │  │
│  │      ├── security-team-1.0.0.json│  │
│  │      └── code-review-1.0.1.json  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## How MCPs Work

### MCP Server Structure

Each MCP server is a standalone FastAPI service that implements the Model Context Protocol:

```python
# Base MCP Server Pattern
from fastapi import FastAPI
from mcp_base import MCPServer

app = FastAPI()
mcp = MCPServer()

# Register tools
@mcp.tool()
def my_tool(param: str) -> dict:
    """Tool implementation"""
    return {"result": "..."}

# MCP Protocol Endpoints
@app.post("/mcp/list_tools")
async def list_tools():
    """List available tools"""
    return {"tools": mcp.get_tools()}

@app.post("/mcp/call_tool")
async def call_tool(request: ToolCallRequest):
    """Execute a tool"""
    return mcp.execute_tool(
        request.tool,
        request.arguments
    )
```

### Types of MCP Servers

#### 1. Agent MCP (LLM-powered)

**Location**: `mcp_servers/agent/`

```python
class AgentMCPServer:
    """
    MCP server that wraps Anthropic Claude LLM
    Provides AI reasoning capabilities as MCP tools
    """

    def __init__(self):
        self.anthropic = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

    @mcp.tool()
    def think(self, prompt: str) -> dict:
        """
        Reasoning tool - sends prompt to Claude

        Args:
            prompt: Question or task for the LLM

        Returns:
            {
                "reasoning": "LLM's response",
                "model": "claude-3-5-sonnet-20241022"
            }
        """
        message = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        return {
            "reasoning": message.content[0].text,
            "model": message.model
        }
```

**How it attaches to LLM:**
1. **API Key**: Read from `ANTHROPIC_API_KEY` environment variable
2. **SDK**: Uses Anthropic Python SDK (`anthropic` package)
3. **Messages API**: Calls `messages.create()` with user prompt
4. **Response**: Returns LLM's text response wrapped in MCP format

#### 2. File Tools MCP (Utility)

**Location**: `mcp_servers/file_tools/`

```python
class FileToolsMCPServer:
    """
    MCP server for file system operations
    No LLM - pure utility functions
    """

    @mcp.tool()
    def read_file(self, path: str) -> dict:
        """Read file contents"""
        return {
            "content": Path(path).read_text(),
            "path": path
        }

    @mcp.tool()
    def write_file(self, path: str, content: str) -> dict:
        """Write content to file"""
        Path(path).write_text(content)
        return {"status": "success", "path": path}
```

#### 3. Nmap Recon MCP (Security)

**Location**: `mcp_servers/nmap/`

```python
class NmapMCPServer:
    """
    MCP server for network reconnaissance
    Wraps nmap command-line tool
    """

    @mcp.tool()
    def network_discovery(self, network: str) -> dict:
        """Discover active hosts on network"""
        result = subprocess.run(
            ["nmap", "-sn", network],
            capture_output=True
        )
        return {
            "hosts_discovered": parse_nmap_output(result.stdout),
            "network": network
        }
```

---

## Data Flow

### 1. Chat with Team (Playground)

```
User Message in UI
       │
       ▼
[Frontend: PlaygroundPage]
  - User types: "Scan 192.168.50.0/24"
  - Sends to: POST /chat
       │
       ▼
[Orchestrator: chat endpoint]
  - Detects "scan" keyword + IP pattern
  - Loads team from agent-teams/security-team.json
  - Sees team has 3 agents:
    1. Scanner (nmap_recon)
    2. Security Analyst (agent)
    3. Reporter (file_tools)
       │
       ▼
[Workflow Execution]
  - Creates workflow dynamically:
    ┌─────────────────────────────────────┐
    │ Node 1: discover-hosts              │
    │ MCP: nmap_recon                     │
    │ Tool: network_discovery             │
    │ Params: {network: "192.168.50.0/24"}│
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │ Node 2: analyze-results             │
    │ MCP: agent                          │
    │ Tool: think                         │
    │ Params: {prompt: "Analyze: ${1}"}   │
    └─────────────────────────────────────┘
       │
       ▼
[MCP Execution]
  1. POST http://nmap_recon:7003/mcp/call_tool
     {
       "tool": "network_discovery",
       "arguments": {"network": "192.168.50.0/24"}
     }
     Response: {"hosts_discovered": [...]}

  2. POST http://agent:7000/mcp/call_tool
     {
       "tool": "think",
       "arguments": {
         "prompt": "Analyze these hosts: [...]"
       }
     }
     │
     ▼
  [Agent MCP → Anthropic API]
     POST https://api.anthropic.com/v1/messages
     {
       "model": "claude-3-5-sonnet-20241022",
       "messages": [{
         "role": "user",
         "content": "Analyze these hosts: [...]"
       }]
     }
     Response: Claude's analysis text
       │
       ▼
[Response Flow]
  Orchestrator ← Agent MCP ← Claude API
       │
       ▼
  Orchestrator formats response
       │
       ▼
  Frontend displays:
    - Scan summary
    - Claude's analysis
    - Discovered hosts list
```

### 2. Workflow Execution (Visual Builder)

```
User Builds Workflow in UI
       │
       ▼
[Frontend: WorkflowsPage]
  - Drag nodes: MCP servers
  - Connect edges: data flow
  - Configure params
  - Click "Execute"
       │
       ▼
[WebSocket Connection]
  ws://localhost:8000/ws/execute/{session_id}
  - Real-time execution updates
       │
       ▼
[Orchestrator: WorkflowEngine]
  1. Parse workflow graph
  2. Topological sort (execution order)
  3. Initialize all nodes as "pending"
       │
       ▼
  For each node in order:
    - Mark node "running"
    - Resolve params (${node-1.result})
    - Call MCP server
    - Store result
    - Mark node "completed"
       │
       ▼
  [Send WebSocket updates]
    - Log messages
    - Node state changes
    - Results
       │
       ▼
  Frontend visualizes execution flow
```

### 3. Registry Install (Package Management)

```
User Clicks "Install" on Team Package
       │
       ▼
[Frontend: RegistryPage]
  POST /registries/install/team/security-team-1.0.0
       │
       ▼
[Orchestrator: Registry API]
  1. Parse registries.conf
  2. Find enabled registries by priority
  3. For each registry:
       │
       ▼
     [Fetch from Registry Server]
       GET http://registry:9000/teams/security-team-1.0.0
       Response: {
         "name": "Security Analysis Team",
         "version": "1.0.0",
         "agents": [...]
       }
       │
       ▼
  4. Save to local disk:
     agent-teams/security-team.json
       │
       ▼
  5. Return success:
     {
       "status": "installed",
       "team": "Security Analysis Team",
       "version": "1.0.0"
     }
       │
       ▼
  Frontend shows success message
  Team now available in Teams page
```

---

## How MCP Attaches to LLM

### Direct Integration (Agent MCP)

The **Agent MCP** is the bridge between MCP protocol and LLMs:

```python
# mcp_servers/agent/server.py

from anthropic import Anthropic
import os

class AgentMCP:
    def __init__(self):
        # LLM Connection
        self.anthropic = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-sonnet-20241022"

    def think(self, prompt: str) -> dict:
        """
        MCP Tool → LLM Bridge

        1. Receives prompt via MCP protocol
        2. Forwards to Anthropic API
        3. Returns LLM response in MCP format
        """

        # Call Anthropic API
        message = self.anthropic.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract text response
        reasoning = message.content[0].text

        # Return in MCP format
        return {
            "reasoning": reasoning,
            "model": message.model,
            "usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens
            }
        }
```

### Configuration Flow

```
1. Environment Setup
   ┌─────────────────────────────────────┐
   │ .env file or docker-compose.yml     │
   │ ANTHROPIC_API_KEY=sk-ant-...       │
   └──────────────┬──────────────────────┘
                  │
                  ▼
2. Container Startup
   ┌─────────────────────────────────────┐
   │ docker-compose up                   │
   │ - Reads ANTHROPIC_API_KEY           │
   │ - Passes to agent container         │
   └──────────────┬──────────────────────┘
                  │
                  ▼
3. Agent MCP Initialization
   ┌─────────────────────────────────────┐
   │ agent:7000 container                │
   │ - Reads API key from env            │
   │ - Initializes Anthropic SDK         │
   │ - Registers tools                   │
   └──────────────┬──────────────────────┘
                  │
                  ▼
4. MCP Tool Call
   ┌─────────────────────────────────────┐
   │ Orchestrator calls:                 │
   │ POST http://agent:7000/mcp/call_tool│
   │ {"tool": "think", "arguments": {}} │
   └──────────────┬──────────────────────┘
                  │
                  ▼
5. LLM API Call
   ┌─────────────────────────────────────┐
   │ Agent MCP → Anthropic API           │
   │ POST https://api.anthropic.com/...  │
   │ Authorization: Bearer sk-ant-...    │
   └──────────────┬──────────────────────┘
                  │
                  ▼
6. Response Flow
   Claude API → Agent MCP → Orchestrator → Frontend
```

### Multi-Agent Routing

When a team has multiple agents, the orchestrator routes to different MCPs:

```python
# backend/app/main.py - chat endpoint

team = load_team("security-team")
# {
#   "agents": [
#     {"name": "Scanner", "mcp_server": "nmap_recon"},
#     {"name": "Analyst", "mcp_server": "agent"},
#     {"name": "Reporter", "mcp_server": "file_tools"}
#   ]
# }

for agent in team["agents"]:
    mcp_server = registry.get(agent["mcp_server"])

    if agent["mcp_server"] == "agent":
        # This agent uses LLM
        response = await call_mcp(
            mcp_server.endpoint,
            tool="think",
            params={"prompt": f"You are {agent['name']}..."}
        )
    else:
        # This agent is utility (no LLM)
        # Use the main agent to describe what it would do
        agent_server = registry.get("agent")
        response = await call_mcp(
            agent_server.endpoint,
            tool="think",
            params={
                "prompt": f"As {agent['name']}, explain what "
                          f"you'd do with {agent['mcp_server']}..."
            }
        )
```

---

## File Structure

```
test3-dev-team/
├── backend/                    # FastAPI Orchestrator
│   ├── app/
│   │   └── main.py            # API endpoints, workflow engine
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # React UI
│   ├── src/
│   │   ├── components/
│   │   │   └── Navigation.jsx # Sidebar navigation
│   │   ├── pages/
│   │   │   ├── PlaygroundPage.jsx    # Chat with teams
│   │   │   ├── ModelsPage.jsx        # LLM config
│   │   │   ├── MCPServersPage.jsx    # MCP browser
│   │   │   ├── TeamsPage.jsx         # Team builder
│   │   │   ├── RegistryPage.jsx      # Package manager
│   │   │   └── WorkflowsPage.jsx     # Visual workflows
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
│
├── mcp_servers/               # MCP Server Implementations
│   ├── agent/                 # LLM-powered agent
│   │   ├── server.py          # Anthropic integration
│   │   ├── requirements.txt
│   │   └── Dockerfile.agent
│   │
│   ├── file_tools/            # File operations
│   │   ├── server.py
│   │   └── Dockerfile.file_tools
│   │
│   └── nmap/                  # Network scanning
│       ├── server.py
│       └── Dockerfile.nmap
│
├── registry-server/           # Package Registry (yum-like)
│   ├── server.py              # Registry API
│   ├── registries/
│   │   ├── mcps/              # MCP packages
│   │   └── teams/             # Team packages
│   ├── requirements.txt
│   └── Dockerfile
│
├── agent-teams/               # Local team definitions
│   ├── security-team.json
│   └── code-review-team.json
│
├── workflows/                 # Saved workflows
│   └── *.json
│
├── registries.conf            # Registry sources (like yum.repos.d)
├── docker-compose.yml         # Service orchestration
└── arch.md                    # This file
```

---

## Component Details

### Orchestrator (FastAPI)

**Port**: 8000
**Language**: Python
**Framework**: FastAPI

**Key Responsibilities**:
1. **MCP Registry**: Tracks available MCP servers
2. **Workflow Engine**: Executes visual workflows
3. **Team Manager**: Loads teams from `agent-teams/`
4. **Chat API**: Routes messages to team agents
5. **Registry API**: Package management (install/update)

**Key Endpoints**:
```
GET  /health                          # Health check
GET  /mcp/servers                     # List MCP servers
GET  /mcp/servers/{name}/tools        # Get tools for MCP
POST /workflows/execute               # Execute workflow
WS   /ws/execute/{session_id}         # Real-time execution
GET  /teams                           # List teams
POST /teams                           # Create team
POST /chat                            # Chat with team
GET  /registries                      # List registries
GET  /registries/catalog              # Combined catalog
POST /registries/install/team/{id}   # Install team package
```

### Agent MCP (Anthropic Claude)

**Port**: 7000
**Language**: Python
**Framework**: FastAPI + Anthropic SDK

**LLM Connection**:
- **Provider**: Anthropic
- **Model**: claude-3-5-sonnet-20241022
- **API Key**: From `ANTHROPIC_API_KEY` env var
- **SDK**: `anthropic` Python package

**Tools**:
1. `think(prompt)` - General reasoning
2. `code(spec)` - Code generation
3. `review(code)` - Code review

### File Tools MCP

**Port**: 7002
**Language**: Python
**Type**: Utility (no LLM)

**Tools**:
1. `read_file(path)` - Read file
2. `write_file(path, content)` - Write file
3. `list_directory(path)` - List directory

### Nmap Recon MCP

**Port**: 7003
**Language**: Python
**Type**: Security tool wrapper

**Network Mode**: Host (requires host network access)

**Tools**:
1. `network_discovery(network)` - Find active hosts
2. `port_scan(host)` - Scan ports
3. `service_detection(host)` - Detect services
4. `vulnerability_scan(host)` - CVE scanning

### Registry Server

**Port**: 9000
**Language**: Python
**Framework**: FastAPI

**Purpose**: Package repository for MCPs and teams

**Storage**: File-based in `registries/mcps/` and `registries/teams/`

**Endpoints**:
```
GET /                    # Registry info
GET /catalog             # Full catalog
GET /mcps                # List MCP packages
GET /mcps/{id}           # Get MCP details
GET /teams               # List team packages
GET /teams/{id}          # Get team details
```

---

## Configuration

### Docker Compose

All services defined in `docker-compose.yml`:

```yaml
services:
  orchestrator:      # Port 8000 - FastAPI API
  agent:             # Port 7000 - LLM agent MCP
  file_tools:        # Port 7002 - File tools MCP
  nmap_recon:        # Port 7003 - Nmap MCP (host network)
  registry:          # Port 9000 - Package registry
  frontend:          # Port 3000 - React UI
```

### Environment Variables

```bash
# Orchestrator
AGENT_PORT=7000
FILE_TOOLS_PORT=7002
NMAP_PORT=7003
DEFAULT_SCAN_NETWORK=192.168.50.0/24

# Agent MCP
ANTHROPIC_API_KEY=sk-ant-...  # Required for LLM

# Nmap MCP
ALLOWED_SCAN_NETWORKS=192.168.50.0/24,10.0.0.0/8

# Frontend
VITE_API_URL=http://localhost:8000
```

### Registries Configuration

File: `registries.conf` (INI format, like yum)

```ini
[default]
name=Default MCP Registry
url=http://registry:9000
enabled=true
priority=10

[custom]
name=Custom Registry
url=https://registry.example.com
enabled=false
priority=20
```

---

## Versioning

All components use **Semantic Versioning** (semver2):

```
Format: major.minor.patch

Example: 1.2.3
- major: Breaking changes
- minor: New features (backward compatible)
- patch: Bug fixes

Current Versions:
- Platform: 0.1.0
- Agent MCP: 1.0.0
- File Tools MCP: 1.0.0
- Nmap Recon MCP: 1.0.0
- Security Team: 1.0.0
- Code Review Team: 1.0.1
```

Versions displayed in:
- Navigation sidebar (platform version)
- MCP Servers page (MCP versions)
- Teams page (team versions)
- Registry catalog (package versions)

---

## Key Features

### 1. Multi-Agent Teams

Teams are collections of agents with different roles:

```json
{
  "name": "Security Analysis Team",
  "version": "1.0.0",
  "agents": [
    {
      "name": "Scanner",
      "role": "Network Scanner",
      "mcp_server": "nmap_recon"
    },
    {
      "name": "Security Analyst",
      "role": "Security Expert",
      "mcp_server": "agent"
    }
  ]
}
```

Each agent responds based on their role and MCP capabilities.

### 2. Visual Workflows

ReactFlow-based workflow builder:
- Drag MCP servers as nodes
- Connect with edges (data flow)
- Parameter resolution: `${node-id.result}`
- Environment variables: `${env:VARIABLE_NAME}`
- Real-time execution via WebSocket

### 3. Package Registry (Yum-style)

- **Browse**: View available MCPs and teams
- **Install**: One-click installation
- **Update**: Version management
- **Multi-registry**: Configure multiple sources
- **Priority**: Registry precedence

### 4. Conversation Memory

Playground chat maintains context:
- Last 10 messages sent to LLM
- Multi-agent responses
- Team collaboration

---

## Security Considerations

1. **API Keys**: Store in `.env`, never commit
2. **Network Scanning**: Defensive use only, requires network permissions
3. **File Access**: File tools restricted to workspace directory
4. **LLM Calls**: All routed through agent MCP (auditability)
5. **Registry**: Read-only by default, no automatic installs

---

## Future Enhancements

1. **MCP Installation**: Auto-deploy MCPs from registry
2. **Model Swapping**: Configure which LLM each agent uses
3. **Cost Tracking**: Monitor token usage per team/workflow
4. **Execution History**: Replay past workflows
5. **Multi-tenancy**: Isolated environments per user
6. **MCP Discovery**: Auto-discover MCPs on network
7. **Team Templates**: Predefined team compositions
8. **Workflow Library**: Share workflows between users

---

## Quick Start

```bash
# 1. Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Start all services
docker-compose up -d

# 3. Access UI
open http://localhost:3000

# 4. Browse Registry
# Navigate to Registry page
# Install a team package

# 5. Chat with Team
# Go to Playground
# Select installed team
# Start chatting
```

---

## Architecture Principles

1. **MCP-First**: Every capability is an MCP tool
2. **Composability**: Tools compose into workflows and teams
3. **File-Based**: Teams and workflows stored as JSON
4. **Version-Controlled**: All packages use semver
5. **Distributed**: MCPs run as separate services
6. **Observable**: All MCP calls are traceable
7. **Extensible**: Add new MCPs without code changes
8. **Package Management**: yum-like distribution model

---

## Development

### Adding a New MCP

1. Create new directory: `mcp_servers/my_mcp/`
2. Implement FastAPI server with MCP protocol
3. Add Dockerfile
4. Register in `docker-compose.yml`
5. Add to startup in `backend/app/main.py`
6. Create package JSON in registry

### Adding a New Team

1. Create JSON: `agent-teams/my-team.json`
2. Or use Teams UI page
3. Or install from registry

### Creating a Workflow

1. Use Workflows UI page
2. Drag MCP nodes onto canvas
3. Connect edges
4. Configure parameters
5. Save and execute

---

**Last Updated**: 2025-10-15
**Version**: 0.1.0
**Authors**: MCP Platform Team
