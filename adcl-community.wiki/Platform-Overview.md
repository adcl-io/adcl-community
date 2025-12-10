# Platform Overview

This guide explains ADCL's core concepts, architecture, and how different components work together.

---

## Table of Contents

1. [What is ADCL?](#what-is-adcl)
2. [Core Concepts](#core-concepts)
3. [Architecture](#architecture)
4. [Component Relationships](#component-relationships)
5. [Data Flow](#data-flow)
6. [Design Philosophy](#design-philosophy)

---

## What is ADCL?

**ADCL (Autonomous Distributed Command Loop)** is an open-source platform for building and orchestrating autonomous AI agent systems. It enables agents to independently solve complex tasks by:

- **Reasoning** about problems and deciding which tools to use
- **Acting** by calling MCP tool servers
- **Observing** results and adapting their approach
- **Collaborating** with other agents in teams
- **Automating** workflows through triggers and schedules

### Key Differentiators

**Autonomous vs. Scripted**:
- Traditional automation: Fixed sequences (if X, then Y)
- ADCL agents: Dynamic decision-making (use best tool for current situation)

**Example**:
```
Traditional Workflow: scan_network → analyze_results → write_report
ADCL Agent: "Create a security report"
  → Agent decides to scan network
  → Sees results, decides to run vulnerability check
  → Notices high-priority issue, decides to gather more details
  → Synthesizes findings into report
```

---

## Core Concepts

### 1. Agents

**What**: AI entities with specific personas that autonomously chain tool calls to complete tasks.

**How They Work**: ReAct Pattern (Reason → Act → Observe)

```
User Task: "Review code in app.py"

1. REASON: "I need to read the file first"
2. ACT: Call file_tools.read_file("app.py")
3. OBSERVE: File contents received
4. REASON: "I should check for security issues"
5. ACT: Call agent.code(analyze_security=True)
6. OBSERVE: Security analysis complete
7. REASON: "I should write a report"
8. ACT: Call file_tools.write_file("report.md")
9. OBSERVE: Report written
10. DONE: Return results to user
```

**Agent Definition** (JSON):
```json
{
  "name": "code_reviewer",
  "version": "0.1.0",
  "description": "Analyzes code quality and security",
  "persona": "You are an expert code reviewer...",
  "mcp_servers": ["file_tools", "agent"],
  "config": {
    "model": "claude-sonnet-4-5",
    "temperature": 0.7,
    "max_iterations": 10
  }
}
```

**Key Properties**:
- **Autonomous**: Makes own decisions about tool usage
- **Observable**: All reasoning and actions are logged
- **Configurable**: Behavior tuned via persona and config
- **Composable**: Can be combined into teams

### 2. Agent Teams

**What**: Collections of agents with different roles collaborating on a task.

**How They Work**: Each agent has a specialized role and responds in sequence.

**Example Team Structure**:
```json
{
  "name": "security_analysis_team",
  "version": "0.1.0",
  "description": "Complete security assessment",
  "agents": [
    {
      "role": "scanner",
      "agent_id": "network_scanner",
      "mcp_access": ["nmap_recon"],
      "persona": "You scan networks and identify hosts"
    },
    {
      "role": "analyst",
      "agent_id": "security_analyst",
      "mcp_access": ["agent", "file_tools"],
      "persona": "You analyze scan results for vulnerabilities"
    },
    {
      "role": "reporter",
      "agent_id": "report_writer",
      "mcp_access": ["file_tools"],
      "persona": "You create executive security reports"
    }
  ]
}
```

**Team Execution Flow**:
```
User: "Scan my network and create a security report"

1. Scanner Agent:
   - Runs network scan
   - Identifies active hosts
   - Returns scan results

2. Analyst Agent:
   - Reviews scan results
   - Identifies vulnerabilities
   - Prioritizes findings
   - Returns analysis

3. Reporter Agent:
   - Takes analysis
   - Creates formatted report
   - Writes to file
   - Returns summary
```

### 3. MCP Servers (Tool Servers)

**What**: Independent services that expose tools for agents to use via Model Context Protocol.

**Purpose**: Extend agent capabilities without modifying agent code.

**Architecture**:
```
Agent (AI reasoning)
   ↓
MCP Protocol (HTTP or stdio)
   ↓
MCP Server (tool implementation)
   ↓
External Systems (files, network, APIs)
```

**Example MCP Server**:
```python
# file_tools MCP
class FileToolsMCP:
    @tool("read_file")
    async def read_file(self, path: str) -> dict:
        """Read contents of a file."""
        with open(path, 'r') as f:
            return {"content": f.read()}

    @tool("write_file")
    async def write_file(self, path: str, content: str) -> dict:
        """Write content to a file."""
        with open(path, 'w') as f:
            f.write(content)
        return {"success": True}
```

**Key Properties**:
- **Isolated**: Each MCP runs in separate Docker container
- **Stateless**: No shared state between calls
- **Composable**: Agents can use multiple MCPs
- **Extensible**: Add new MCPs without modifying platform

### 4. Workflows

**What**: Visual node-based compositions of MCP tools for deterministic processes.

**When to Use**:
- **Workflows**: Fixed sequence, deterministic (network scan → parse → report)
- **Agents**: Dynamic decisions, adaptive (figure out how to solve X)

**Workflow Structure**:
```
Node 1: nmap_recon.network_discovery
   ↓
Node 2: agent.think (analyze results)
   ↓
Node 3: file_tools.write_file (save report)
```

**Parameter Resolution**:
```json
{
  "tool": "write_file",
  "params": {
    "path": "/workspace/report.txt",
    "content": "${agent.output}"  // References Node 2 output
  }
}
```

### 5. Triggers

**What**: Automated workflow or team execution based on events.

**Types**:

**Webhook Trigger**:
```
POST http://localhost:8000/trigger/webhook/my-trigger
→ Executes associated workflow or team
```

**Schedule Trigger**:
```
Cron: 0 2 * * *  // Every day at 2am
→ Executes associated workflow or team
```

**Use Cases**:
- CI/CD integration (webhook on deploy)
- Scheduled security scans (daily at 2am)
- Automated reporting (weekly summaries)

### 6. Package Registry

**What**: Centralized repository for distributing teams, triggers, and MCPs.

**Similar to**: Yum/APT package management for Linux

**Registry Structure**:
```
registries.conf
├── [official]
│   └── baseurl=http://registry.adcl.io
└── [community]
    └── baseurl=http://community.adcl.io

Package: security_analysis_team-1.0.0
├── metadata.json      # Package info
├── team.json         # Team definition
├── agents/           # Agent definitions
└── README.md        # Documentation
```

**Installation Flow**:
```
1. User clicks "Install" in Registry UI
2. Platform downloads package from registry
3. Validates package signature and dependencies
4. Installs files to appropriate directories
5. Registers team/trigger in platform
6. Available for immediate use
```

---

## Architecture

ADCL uses a three-tier architecture to separate concerns:

### Tier 1: Frontend ↔ Backend API

**Purpose**: User interaction and real-time updates

**Protocol**: REST (HTTP) + WebSocket

**Components**:
- **Frontend** (React, port 3000)
  - Web UI for all platform features
  - Real-time execution updates via WebSocket
  - Dark/light theme, responsive design

- **Backend API** (FastAPI, port 8000)
  - RESTful API for CRUD operations
  - WebSocket endpoint for streaming execution
  - Health checks and status endpoints

**Communication**:
```javascript
// HTTP request to create agent
const response = await fetch('/api/agents', {
  method: 'POST',
  body: JSON.stringify(agentConfig)
});

// WebSocket for real-time execution
const ws = new WebSocket('/ws/execute/123');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(update.type, update.data);
};
```

### Tier 2: Backend Services

**Purpose**: Orchestration, state management, business logic

**Protocol**: Python modules (monolith) or message queue (distributed)

**Components**:
- **Workflow Engine**: Executes workflows, manages state
- **Agent Orchestrator**: Runs autonomous agents
- **Docker Manager**: Container lifecycle management
- **Execution Store**: Tracks execution history
- **Registry Client**: Package installation

**Communication** (monolith approach):
```python
# Direct Python imports
from backend.services.workflows import WorkflowEngine
from backend.services.docker import DockerManager

workflow_engine = WorkflowEngine(docker_manager)
result = await workflow_engine.execute(workflow_id)
```

**Key Point**: This tier does NOT use MCP - it uses appropriate backend patterns (imports, events, queues).

### Tier 3: AI Agents ↔ MCP Tool Servers

**Purpose**: Agent-to-tool communication

**Protocol**: MCP (Model Context Protocol) - HTTP or stdio

**Components**:
- **Agents**: AI reasoning via Claude API
- **MCP Servers**: Tool implementations
  - agent (port 7000): AI reasoning
  - file_tools (port 7002): File operations
  - nmap_recon (port 7003): Network scanning
  - kali (port 7005): Penetration testing
  - history (port 7004): Conversation storage
  - linear (port 7006): Issue tracking

**Communication**:
```python
# Agent calls MCP tool
result = await mcp_client.call_tool(
    server="nmap_recon",
    tool="scan_network",
    params={"target": "192.168.1.0/24"}
)
```

**Key Point**: MCP is ONLY for agent-to-tool communication, not backend orchestration.

---

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: Frontend ↔ Backend API                             │
│  ┌──────────┐          ┌──────────┐                         │
│  │ React UI │ ◄─────► │ FastAPI  │                         │
│  │ (3000)   │  REST   │ (8000)   │                         │
│  └──────────┘  +WS    └──────────┘                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 2: Backend Services (Orchestration)                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │ Workflow   │  │ Agent      │  │ Docker     │           │
│  │ Engine     │  │ Orchestr   │  │ Manager    │           │
│  └────────────┘  └────────────┘  └────────────┘           │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                         │                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TIER 3: AI Agents ↔ MCP Tool Servers                       │
│  ┌───────────┐                                              │
│  │  Agent    │  ──MCP──► ┌──────────────┐                  │
│  │ (Claude)  │           │ file_tools   │                  │
│  │           │  ◄────────┤ (7002)       │                  │
│  │           │   Result  └──────────────┘                  │
│  │           │                                              │
│  │           │  ──MCP──► ┌──────────────┐                  │
│  │           │           │ nmap_recon   │                  │
│  │           │  ◄────────┤ (7003)       │                  │
│  └───────────┘   Result  └──────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

**User Creates Workflow**:
```
User (UI) → POST /api/workflows → Backend API
                                      ↓
                              Workflow Engine
                                      ↓
                              Save to workflows/workflow.json
```

**User Executes Workflow**:
```
User (UI) → POST /api/workflows/execute → Backend API
                                             ↓
                                      Workflow Engine
                                             ↓
                                      Docker Manager
                                             ↓
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                        Start MCP Container         Agent calls MCP tool
                              │                             │
                              └─────────► Tool executes ◄───┘
                                             ↓
                                      Return result
                                             ↓
                                      WebSocket update
                                             ↓
                                      UI shows progress
```

**Agent Autonomous Execution**:
```
User (UI) → POST /api/agents/run → Backend API
                                       ↓
                              Agent Orchestrator
                                       ↓
                              ┌────────┴────────┐
                              ▼                 ▼
                        Claude API       MCP Tool Server
                         (Reason)          (Act/Observe)
                              │                 │
                              └────► Loop ◄─────┘
                                  (until done)
                                       ↓
                              WebSocket updates
                                       ↓
                              UI shows reasoning
```

---

## Data Flow

### File-Based Storage

ADCL follows Unix philosophy: **everything is a file**.

```
adcl/
├── agent-definitions/     # Agent configs (JSON)
│   ├── code_reviewer.json
│   ├── security_analyst.json
│   └── research_assistant.json
│
├── agent-teams/          # Team configs (JSON)
│   ├── security_team.json
│   └── code_review_team.json
│
├── workflows/            # Workflow definitions (JSON)
│   ├── network_scan.json
│   └── code_review.json
│
├── triggers/             # Trigger implementations
│   ├── webhook/
│   └── schedule/
│
├── configs/              # Service configurations
│   ├── mcp_servers.json
│   ├── registries.conf
│   └── ports.conf
│
├── logs/                 # All logs (*.log)
│   ├── orchestrator-2025-12-08.log
│   ├── agent-mcp-2025-12-08.log
│   └── workflow-execution-123.log
│
├── volumes/              # Persistent data
│   ├── data/            # User data
│   ├── vectors/         # Vector indices (if used)
│   └── history/         # Conversation history (JSONL)
│
└── workspace/            # Shared file workspace
    └── (agent outputs, reports, etc.)
```

### Configuration as Code

All configuration is human-readable text:

```bash
# View agent definition
cat agent-definitions/code_reviewer.json | jq

# Search for agents with specific capability
grep -r "network_analysis" agent-definitions/

# List all MCP servers
cat configs/mcp_servers.json | jq '.servers[].name'

# View conversation history
tail -n 50 volumes/history/session_123.jsonl | jq
```

---

## Design Philosophy

ADCL follows **Unix Philosophy**:

### 1. Do One Thing Well

Each component has a single responsibility:
- **Agents**: Reason and decide
- **MCPs**: Execute tools
- **Workflows**: Orchestrate sequences
- **Triggers**: Automate execution

**Example**: Don't create a "swiss army knife" MCP that does files + network + AI. Create three MCPs.

### 2. Text Streams

All data in plain text (JSON/YAML):
- **Configuration**: JSON files, not databases
- **Logs**: Structured JSON lines, not binary
- **Communication**: JSON over HTTP/stdio

**Benefit**: Use standard Unix tools (`grep`, `jq`, `cat`, `tail`)

### 3. Composability

Simple tools combine into complex systems:
- **Agent** + **file_tools** + **nmap_recon** = Security analyst
- **Workflow** = Chain of MCP calls
- **Team** = Multiple agents with different tools

### 4. No Hidden State

Everything is observable:
- **Configs**: In version-controlled files
- **Logs**: In `logs/` directory
- **Data**: In `volumes/` directory
- **Execution**: Real-time WebSocket updates

**Test**: Can you understand the system state by reading files? If no, it's hidden state.

### 5. Configuration as Code

All settings in text files:
- **Agent behavior**: `agent-definitions/*.json`
- **Team structure**: `agent-teams/*.json`
- **MCP servers**: `configs/mcp_servers.json`
- **Registries**: `registries.conf`

**Benefit**: Version control, code review, GitOps workflows

---

## Key Takeaways

1. **Agents are autonomous** - They reason, act, and observe in a loop
2. **Teams are collaborative** - Multiple agents with specialized roles
3. **MCPs are tools** - Extend agent capabilities without code changes
4. **Workflows are deterministic** - Fixed sequences for repeatable processes
5. **Triggers automate** - Event-based execution (webhooks, schedules)
6. **Everything is a file** - Configuration, data, logs all in plain text
7. **Three-tier architecture** - UI/API (Tier 1), Orchestration (Tier 2), Agent/Tools (Tier 3)
8. **MCP is for agents** - Not for backend service communication

---

## Next Steps

Now that you understand the platform, dive into specific features:

- **[Agents Guide](Agents-Guide)** - Create and use autonomous agents
- **[Teams Guide](Teams-Guide)** - Build multi-agent systems
- **[Workflows Guide](Workflows-Guide)** - Visual workflow builder
- **[MCP Servers Guide](MCP-Servers-Guide)** - Understanding and creating tool servers
- **[Triggers Guide](Triggers-Guide)** - Automate with webhooks and schedules

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
