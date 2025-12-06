# ADCL Platform Architecture Analysis: MCP Usage & Communication Patterns

## Executive Summary

MCP (Model Context Protocol) in this codebase serves a **specific and well-defined purpose**: exposing tool capabilities to autonomous AI agents. However, the platform has conflated MCP with general backend service-to-service communication, which is a design mismatch.

**Key Finding**: MCP is optimized for **AI agent ↔ tool** communication, NOT for **backend service ↔ backend service** communication.

---

## 1. WHERE IS MCP ACTUALLY BEING USED?

### Current MCP Usage Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent (LLM-powered)                    │
│                  (Claude, GPT-4, etc.)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ReAct Loop:
                     │ 1. Agent decides which tool to use
                     │ 2. Calls MCP tool via HTTP
                     │ 3. Receives structured result
                     │ 4. Continues reasoning
                     │
        ┌────────────▼────────────────┐
        │   Agent Runtime             │
        │ (agent_runtime.py)          │
        │                             │
        │ - Orchestrates ReAct loop   │
        │ - Manages MCP tool calls    │
        │ - Handles multi-turn chat   │
        └────────────┬────────────────┘
                     │
        ┌────────────▼────────────────────────────────────────┐
        │         HTTP POST to MCP Servers                    │
        │                                                      │
        │  POST /mcp/call_tool                               │
        │  {                                                  │
        │    "tool": "port_scan",                            │
        │    "arguments": {"target": "192.168.1.1"}          │
        │  }                                                  │
        └────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────────────────┐
        │        MCP Tool Servers (Docker containers)       │
        │                                                    │
        │  • nmap_recon (network scanning)                  │
        │  • file_tools (file operations)                   │
        │  • agent (code generation, thinking)              │
        │  • history (session management)                   │
        │  • kali (security tools)                          │
        └────────────────────────────────────────────────────┘
```

### MCP Servers Discovered in Codebase

1. **nmap_recon** (`mcp_servers/nmap/nmap_server.py`)
   - Tools: `port_scan`, `service_detection`, `os_detection`, `vulnerability_scan`, `network_discovery`
   - Used by: `security-analyst` agent
   - Pattern: Agent autonomously calls for network reconnaissance

2. **file_tools** (`mcp_servers/file_tools/file_server.py`)
   - Tools: `read_file`, `write_file`, `list_files`
   - Used by: All agents that need filesystem access
   - Pattern: Agent autonomously reads/writes files for work

3. **agent** (`mcp_servers/agent/agent_server.py`)
   - Tools: `think`, `code`, `review`
   - Used by: Agents as self-referential tools (agent calling agent)
   - Pattern: Nested agent capability

4. **history** (`mcp_servers/history/history_server.py`)
   - Tools: Session management, conversation history
   - Used by: Agents that need context recall
   - Pattern: Shared state for multi-turn interactions

### The MCP Protocol in This Codebase

```python
# MCP is purely HTTP-based REST API here, not stdio-based
# See: mcp_servers/base_server.py

class BaseMCPServer:
    @app.post("/mcp/list_tools")
    async def list_tools():
        """List all available tools"""
        return ListToolsResponse(tools=self.tool_definitions)
    
    @app.post("/mcp/call_tool")
    async def call_tool(request: ToolCallRequest):
        """Execute a tool by name"""
        # tool_name, arguments → result
        return ToolCallResponse(content=[...], isError=False)
```

**Important**: This is a **simplified MCP implementation**, not the full MCP protocol.
- Missing: stdio transport, SSE updates, sampling, roots
- Present: Basic tool list and call semantics

---

## 2. WHAT IS MCP DESIGNED FOR?

### Official MCP Purpose (From Anthropic)

MCP is a protocol for **AI models to securely access tools and data sources**:

```
AI Model/Agent ←→ MCP Client ←→ MCP Servers
                   (stdio/SSE)
```

**Design Goals**:
- Safe tool exposure to AI models
- Structured input validation
- Clear tool semantics for model understanding
- Composable tools into capabilities

### How It's Used Here

1. **Tool Definition Broadcasting** (✓ Correct)
   ```python
   # Agent Runtime fetches tool definitions from MCPs
   tools = await self._build_tools_from_mcps(agent_definition["available_mcps"])
   
   # Converts to Claude tool format
   {
     "name": "nmap_recon__port_scan",
     "description": "[nmap_recon] Scan target for open ports",
     "input_schema": {...}
   }
   ```

2. **Tool Execution Loop** (✓ Correct)
   ```python
   # Agent decides to use a tool
   if response.stop_reason == "tool_use":
       for tool_call in response.content:
           # Execute via MCP
           result = await self._execute_mcp_tool(
               tool_call.name,
               tool_call.input,
               agent_definition["available_mcps"]
           )
   ```

3. **Tool Availability Control** (✓ Correct)
   ```json
   {
     "agent_id": "security-analyst",
     "available_mcps": ["nmap_recon", "file_tools"]
     // ↑ Agent has no access to "agent" MCP, preventing infinite loops
   }
   ```

### What MCP is NOT Designed For

1. **Backend Service-to-Service Communication** ✗
   - MCP assumes one consumer (the AI agent)
   - Backend service coordination needs multi-consumer, async-first patterns
   - No built-in service discovery, load balancing, retry logic
   - No event-driven patterns

2. **Workflow Orchestration** ✗
   - Current: Workflows call MCPs directly via HTTP
   - Problem: Workflows are deterministic, MCPs assume AI decision-making
   - No transaction support, no compensation logic

3. **Persistent State Management** ✗
   - MCP tools are stateless request/response
   - Backend needs shared state, configuration, execution context
   - Current workaround: File-based storage (not ideal for distributed systems)

4. **Authentication & Authorization** ✗
   - MCP has no built-in auth mechanisms
   - Current: No auth between services (assumes trusted network)
   - Production risk: Any container can call any other

5. **Service Health & Resilience** ✗
   - No health check coordination
   - No graceful degradation
   - No circuit breakers or bulkheads
   - Current: Docker restart policies only

---

## 3. CURRENT DATA FLOW ANALYSIS

### Flow 1: Autonomous Agent Execution

```
User Request
    ↓
POST /agent/execute
    ↓
orchestrator (main.py)
    ├─→ AgentRuntime.run_agent()
    │   ├─→ Fetch tool definitions from MCP servers
    │   │   POST http://nmap_recon:7001/mcp/list_tools
    │   │   POST http://file_tools:7002/mcp/list_tools
    │   │
    │   ├─→ Call Claude/OpenAI with tools
    │   │   → Claude decides: "I'll scan this network"
    │   │
    │   ├─→ Execute tool via MCP
    │   │   POST http://nmap_recon:7001/mcp/call_tool
    │   │   {"tool": "port_scan", "arguments": {...}}
    │   │   ← JSON result back to agent
    │   │
    │   ├─→ Loop: Reason → Act → Observe
    │   │   (up to max_iterations: 15)
    │   │
    │   └─→ Final answer
    │
    └─→ WebSocket send to client
```

**Issues Here**:
- Agent Runtime directly HTTP-calls MCPs (tight coupling)
- No retry logic if MCP fails mid-execution
- No way to swap implementations (hard-coded HTTP to specific ports)

### Flow 2: Workflow Execution

```
User Request
    ↓
POST /workflows/execute
    ↓
WorkflowEngine.execute()
    ├─→ For each node in execution order:
    │   ├─→ If type is "mcp_call":
    │   │   POST http://{server.endpoint}/mcp/call_tool
    │   │   ← Direct result used for next node
    │   │
    │   ├─→ If type is "if":
    │   │   Evaluate condition on previous results
    │   │
    │   └─→ Send logs via WebSocket callback
    │
    └─→ Return ExecutionResult
```

**Issues Here**:
- Mixing MCP call semantics with workflow semantics
- Workflows assume synchronous, deterministic execution
- MCP tools return JSON, workflows expect specific structure
- No error recovery beyond single node fail-stop

### Flow 3: Team Runtime (Multi-Agent)

```
User Request
    ↓
POST /teams/{team_id}/execute
    ↓
TeamRuntime.run_team()
    ├─→ Coordination mode:
    │   ├─ Sequential: Agent1 → Agent2 → Agent3
    │   ├─ Parallel: Agent1 || Agent2 || Agent3
    │   └─ Collaborative: Agents discuss results
    │
    ├─→ For each agent:
    │   └─→ AgentRuntime.run_agent()
    │       └─→ (Same MCP calling pattern as Flow 1)
    │
    └─→ Return combined results
```

**Issues Here**:
- No inter-agent communication except shared context
- MCP selection at team level (all agents see all MCPs)
- No role-based MCP access control
- Shared context is just passed as dict (no transactions)

### Flow 4: Backend Service Management (Docker)

```
orchestrator startup
    ↓
get_mcp_manager() → DockerManager
    ├─→ List installed MCPs
    │   └─ Reads: /app/installed-mcps.json
    │
    ├─→ Start stopped containers
    │   └─ docker start {container_name}
    │
    ├─→ Register with MCPRegistry
    │   MCPRegistry.register(MCPServerInfo{
    │       name: "nmap_recon",
    │       endpoint: "http://mcp-nmap_recon:7001"
    │   })
    │
    └─→ When agent executes:
        Fetch from registry
        Call via HTTP
```

**Issues Here**:
- Container discovery is manual (installed-mcps.json)
- No automatic health checks before registration
- Port mapping is implicit in config files
- No load balancing across replicas

---

## 4. WHAT THE BACKEND ACTUALLY NEEDS

### Requirements Identified

| Need | Current Solution | Verdict |
|------|-----------------|---------|
| AI Agent → Tool communication | MCP (HTTP REST) | ✓ Correct |
| Tool availability to agents | MCP list_tools | ✓ Correct |
| Tool execution for agents | MCP call_tool | ✓ Correct |
| **Service discovery** | Manual JSON file | ✗ Manual |
| **Async task execution** | Task not needed yet | - |
| **Event streaming** | WebSocket callbacks | ~ Partial |
| **Workflow orchestration** | Custom WorkflowEngine | ~ Partial |
| **Service health checks** | Docker restart policy | ~ Partial |
| **Configuration management** | YAML files | ✓ Good |
| **Execution logging** | File-based JSONL | ✓ Good |
| **State persistence** | File system | ✓ Reasonable |
| **Service-to-service auth** | None (trust network) | ✗ Missing |
| **Multi-tenancy** | Not implemented | ✗ Missing |

### What Backend Services Need to Communicate About

1. **Orchestrator ↔ MCP Servers**
   - Purpose: Tell agents which tools exist
   - Pattern: Read-only queries (list_tools, call_tool)
   - Current: Direct HTTP REST ✓

2. **Orchestrator ↔ Docker/Container Runtime**
   - Purpose: Manage lifecycle (install, start, stop)
   - Pattern: Imperative commands
   - Current: Docker CLI subprocess calls ✓

3. **Orchestrator ↔ Frontend**
   - Purpose: Real-time execution updates
   - Pattern: Server-initiated push (WebSocket)
   - Current: WebSocket with JSON messages ✓

4. **Orchestrator ↔ Registry Server**
   - Purpose: Discover available MCP packages
   - Pattern: HTTP REST (get catalog, fetch package)
   - Current: Lazy-loaded at startup ✓

5. **Orchestrator ↔ Execution State**
   - Purpose: Track execution progress, handle cancellation
   - Pattern: Imperative state updates
   - Current: In-memory ConnectionManager ✗ (not persistent)

---

## 5. CURRENT PATTERNS & ISSUES

### Pattern 1: HTTP Direct Call (Current)

```python
# agent_runtime.py
async def _call_mcp(self, endpoint: str, tool: str, params: Dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{endpoint}/mcp/call_tool",
            json={"tool": tool, "arguments": params},
            timeout=300  # 5 minutes
        ) as response:
            return await response.json()
```

**Issues**:
- Tight coupling to HTTP implementation
- Hardcoded timeout values scattered in code
- No retry logic (timeout = failure)
- No circuit breaker (cascade failures)
- Endpoint must be known ahead of time

### Pattern 2: Service Registration in Memory

```python
# main.py
registry = MCPRegistry()  # In-memory dict

# On startup:
registry.register(MCPServerInfo(
    name="nmap_recon",
    endpoint="http://mcp-nmap_recon:7001",
    description="Network reconnaissance",
    version="1.0.0"
))

# During execution:
mcp_info = registry.get("nmap_recon")  # Fast but ephemeral
```

**Issues**:
- Lost on orchestrator restart
- No service health validation
- No automatic deregistration of failed services
- Must manually edit code to change services

### Pattern 3: File-Based Configuration

```yaml
# configs/orchestrator.yaml
auto_install:
  mcps:
    - "agent"
    - "file_tools"
    - "nmap_recon"
    - "history"
```

**Issues**:
- Requires code redeploy to add MCP
- No runtime changes
- No A/B testing of versions
- No gradual rollouts

### Pattern 4: Workflow Engine (Current)

```python
# workflow_engine.py
async def _execute_node(self, node, previous_results):
    # All nodes treated the same
    if node.mcp_server:
        # Call MCP directly, blocking
        url = f"{server.endpoint}/mcp/call_tool"
        response = await self.client.post(url, json=payload)
        # Immediate result or error
        results[node_id] = response.json()
```

**Issues**:
- Workflows are deterministic, MCPs assume autonomy
- No way to handle "tool declined" or "try again"
- Linear execution only (parallel support is incomplete)
- No human-in-the-loop checkpoints

### Pattern 5: Team Runtime (Current)

```python
# team_runtime.py
async def _run_sequential(self, team_def, task, ...):
    for agent_config in team_def["agents"]:
        agent_result = await self.agent_runtime.run_agent(
            agent_def,
            task,
            context=shared_context
        )
        agent_results.append(agent_result)
        # No coordination between agents
```

**Issues**:
- "Sequential" just means one-at-a-time
- "Collaborative" mode doesn't actually coordinate
- No debate or consensus mechanisms
- Shared context is mutable dict (race conditions in parallel)

---

## 6. RECOMMENDED ARCHITECTURE

### Three-Tier Communication Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    TIER 1: AI Agent ↔ Tools                     │
│                                                                  │
│  Protocol: MCP (HTTP REST, simplified)                          │
│  Transport: HTTP POST to /mcp/call_tool                         │
│  Semantics: Tool call with structured input/output              │
│  Caller: AI agents (Claude, GPT-4)                              │
│  Responsibilities: Tool discovery, execution, result parsing    │
│                                                                  │
│  Current Issues: None significant                               │
│  Recommendation: KEEP AS-IS (working well)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│            TIER 2: Orchestrator ↔ Backend Services              │
│                                                                  │
│  Protocol: Service Bus (Event-driven)                           │
│  Transport: Message queue (future: Redis, RabbitMQ)             │
│  Semantics: Async tasks, event ordering                         │
│  Callers: Workflows, teams, user actions                        │
│  Responsibilities: Decouple services, enable scale              │
│                                                                  │
│  Current Issues: Tight HTTP coupling, no async patterns         │
│  Recommendation: REFACTOR to event-driven                       │
│                                                                  │
│  What Goes Here:                                                │
│  • Workflow node execution                                      │
│  • Agent task scheduling                                        │
│  • Container lifecycle events                                   │
│  • Execution state updates                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│            TIER 3: Orchestrator ↔ Clients                       │
│                                                                  │
│  Protocol: WebSocket (Real-time)                                │
│  Transport: WebSocket connection                                │
│  Semantics: Server-push updates, bidirectional                  │
│  Callers: Frontend, CLI clients                                 │
│  Responsibilities: User-facing updates, cancellation signals    │
│                                                                  │
│  Current Issues: Basic implementation (works but limited)       │
│  Recommendation: ENHANCE with proper event types                │
│                                                                  │
│  What Goes Here:                                                │
│  • Execution progress updates                                   │
│  • Tool execution logs                                          │
│  • Agent reasoning traces                                       │
│  • Cancellation requests                                        │
│  • User notifications                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Tier 1: AI Agent ↔ Tools (MCP)

**Status**: ✓ Well-designed, keep as-is

```python
# agent_runtime.py (current pattern is good)
async def run_agent(self, agent_def, task, ...):
    """
    Reason → Act → Observe loop
    
    Reason: Call Claude with tools
    Act: Claude picks a tool
    Observe: Execute tool, get result
    """
    while iteration < max_iterations:
        # Call LLM with available tools
        response = client.messages.create(
            model=agent_def["model_config"]["model"],
            messages=messages,
            tools=tools  # From MCPs
        )
        
        if response.stop_reason == "tool_use":
            # Execute each tool call
            for tool_call in response.content:
                result = await self._execute_mcp_tool(
                    tool_call.name,
                    tool_call.input
                )
                # Add result to conversation
                messages.append({"role": "user", "content": tool_result})
        
        elif response.stop_reason == "end_turn":
            # Agent is done
            return result
```

**Keep**:
- Direct HTTP calls for simplicity
- Tool definition broadcasting
- ReAct loop implementation
- Per-agent MCP access control

**Enhance** (future):
- Timeout handling with retry
- Rate limiting per agent
- Tool execution tracing
- Cost tracking per tool

---

### Tier 2: Orchestrator ↔ Backend Services (Event Bus)

**Status**: ✗ Currently uses direct HTTP, needs refactoring

**Current Problem**:
```python
# BAD: Direct HTTP call in workflow
async def _execute_node(self, node, previous_results):
    result = await self.client.post(
        f"{server.endpoint}/mcp/call_tool",
        json=payload
    )  # ← Blocks workflow, no retry, timeout = failure
    return result
```

**Recommended Solution**:

```python
# GOOD: Event-driven task execution

class WorkflowEngine:
    def __init__(self, event_bus, mcp_registry):
        self.event_bus = event_bus  # Redis, RabbitMQ, etc.
        self.registry = mcp_registry
    
    async def execute_workflow(self, workflow_def, params):
        """Execute workflow via event bus"""
        context = ExecutionContext(...)
        
        for node in topological_sort(workflow_def.nodes):
            if node.type == "mcp_call":
                # Don't call MCP directly
                # Instead: publish event, wait for result
                
                event = {
                    "type": "execute_tool",
                    "execution_id": context.id,
                    "node_id": node.id,
                    "mcp_name": node.mcp_server,
                    "tool": node.tool,
                    "arguments": node.params,
                    "timeout": 300
                }
                
                # Publish to event bus
                await self.event_bus.publish("workflow.tool_execution", event)
                
                # Wait for result with timeout
                result = await self.event_bus.wait_for(
                    f"workflow.{context.id}.node.{node.id}",
                    timeout=300
                )
                
                context.results[node.id] = result
```

**Event Types to Support**:

```python
# Task execution
{
    "type": "execute_tool",
    "mcp": "nmap_recon",
    "tool": "port_scan",
    "args": {...}
}

# Workflow control
{
    "type": "workflow.cancelled",
    "workflow_id": "...",
    "reason": "user_request"
}

# Service health
{
    "type": "service.health",
    "service": "nmap_recon",
    "status": "unhealthy",
    "error": "..."
}

# State updates
{
    "type": "execution.progress",
    "execution_id": "...",
    "node_id": "...",
    "status": "completed",
    "result": {...}
}
```

**Benefits**:
- Decouple orchestrator from MCP implementation
- Enable async patterns (fire-and-forget, fanout)
- Automatic retry and circuit breaker (in message queue)
- Enable scaling (multiple workers processing tasks)
- Better error handling and recovery

---

### Tier 3: Orchestrator ↔ Frontend (WebSocket)

**Status**: ~ Partial implementation, enhance with proper structure

**Current**:
```python
# main.py - Basic WebSocket
@app.websocket("/ws/execute/{session_id}")
async def websocket_execute(websocket, session_id):
    data = await websocket.receive_json()
    result = await engine.execute(workflow, update_callback=send_update)
```

**Recommended Enhancement**:

```python
# Event-driven WebSocket with proper message types

@app.websocket("/ws/session/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """
    Bidirectional stream for real-time updates
    
    Client → Server:
    • {"type": "run_workflow", "workflow_id": "...", "params": {...}}
    • {"type": "cancel_execution", "execution_id": "..."}
    • {"type": "subscribe", "topic": "execution.progress"}
    
    Server → Client:
    • {"type": "execution.started", "execution_id": "..."}
    • {"type": "tool.execution", "tool": "...", "status": "running"}
    • {"type": "agent.reasoning", "text": "...", "iteration": 5}
    • {"type": "execution.completed", "result": {...}}
    • {"type": "execution.error", "error": "..."}
    """
    
    await manager.connect(session_id, websocket)
    
    try:
        while True:
            # Receive user command
            message = await websocket.receive_json()
            message_type = message.get("type")
            
            if message_type == "run_workflow":
                # Publish task to event bus
                # WebSocket will receive updates via event subscription
                await event_bus.publish("user.run_workflow", {
                    "session_id": session_id,
                    "workflow_id": message["workflow_id"],
                    "params": message["params"]
                })
            
            elif message_type == "cancel_execution":
                # Signal cancellation
                await event_bus.publish("user.cancel_execution", {
                    "session_id": session_id,
                    "execution_id": message["execution_id"]
                })
    
    finally:
        manager.disconnect(session_id)

# Event handler - separate service or thread
async def handle_execution_events():
    """Subscribe to execution events and push to WebSocket"""
    async for event in event_bus.subscribe("execution.*"):
        session_id = extract_session_id(event)
        await manager.send_update(session_id, {
            "type": event["type"],
            "data": event
        })
```

**Benefits**:
- Separate concerns (execution logic vs. streaming)
- Multiple clients can subscribe to same execution
- Clients can control execution (cancel, pause, etc.)
- Better error handling and reconnection

---

## 7. COMMUNICATION PROTOCOL COMPARISON

### Tier 1: MCP (AI Agent → Tools)

```
Protocol: HTTP REST (simplified MCP)
Endpoint: POST /mcp/call_tool
Request:
  {
    "tool": "port_scan",
    "arguments": {"target": "192.168.1.1", "ports": "1-1000"}
  }
Response:
  {
    "content": [{"type": "text", "text": "{\"open_ports\": [...]}"}],
    "isError": false
  }
Features:
  ✓ Simple HTTP (no special libraries needed)
  ✓ Tool definition broadcasting via /mcp/list_tools
  ✓ Structured input validation (input_schema)
  ✗ No retry logic
  ✗ No streaming (waiting for full result)
  ✗ No async execution
```

### Tier 2: Event Bus (Orchestrator → Services)

```
Protocol: Message Queue (Redis, RabbitMQ, or simple HTTP queue)
Topic Pattern: {domain}.{action}

Examples:
  workflow.tool_execution
  workflow.cancelled
  service.health
  execution.progress

Message Structure:
  {
    "id": "evt_12345",
    "type": "execute_tool",
    "timestamp": "2025-01-01T12:00:00Z",
    "source": "workflow_engine",
    "payload": {
      "execution_id": "exec_20250101_120000_abc123",
      "node_id": "node_5",
      "mcp": "nmap_recon",
      "tool": "port_scan",
      "args": {...}
    },
    "correlation_id": "user_session_123"
  }

Features:
  ✓ Async execution (publish and forget)
  ✓ Automatic retry (queue persistence)
  ✓ Event ordering
  ✓ Multiple subscribers (fanout)
  ✓ Dead letter queue for failures
  ✓ Circuit breaker (queue backpressure)
  ✓ Supports streaming results
```

### Tier 3: WebSocket (Orchestrator → Frontend)

```
Protocol: WebSocket (bidirectional stream)

Client → Server Messages:
  {
    "type": "run_workflow",
    "workflow_id": "sec_analysis",
    "params": {"target": "192.168.1.0/24"}
  }

Server → Client Messages:
  {
    "type": "execution.started",
    "execution_id": "exec_20250101_120000_abc123",
    "timestamp": "2025-01-01T12:00:00Z"
  }
  
  {
    "type": "tool.execution.started",
    "tool": "port_scan",
    "status": "running"
  }
  
  {
    "type": "agent.reasoning",
    "agent": "security_analyst",
    "text": "Found port 22 open, checking SSH...",
    "iteration": 3
  }
  
  {
    "type": "execution.completed",
    "status": "success",
    "result": {...}
  }

Features:
  ✓ Real-time bidirectional communication
  ✓ Low latency
  ✓ Server can push updates without polling
  ✓ Single connection per client
  ✗ Stateful (needs connection management)
  ✗ Not suitable for service-to-service (overhead)
```

---

## 8. MIGRATION STRATEGY (Phased)

### Phase 1: Add Service Registry (No code changes yet)

Create a service discovery file:

```yaml
# services.yaml (replaces installed-mcps.json)
services:
  nmap_recon:
    type: "tool"
    image: "mcp-nmap_recon:1.0.0"
    container_name: "mcp-nmap_recon"
    port: 7001
    health_check:
      endpoint: "/health"
      interval: 30s
    retry:
      max_attempts: 3
      backoff: exponential
  
  file_tools:
    type: "tool"
    image: "mcp-file_tools:1.0.0"
    container_name: "mcp-file_tools"
    port: 7002
    health_check:
      endpoint: "/health"
      interval: 30s
    
  orchestrator:
    type: "service"
    port: 8000
    health_check:
      endpoint: "/health"
      interval: 10s
```

### Phase 2: Add Health Checks (Improve robustness)

```python
# app/service_registry.py
class ServiceRegistry:
    async def register_with_health_check(self, service_info):
        # Test endpoint before registering
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{service_info.endpoint}/health",
                    timeout=5
                )
                if resp.status_code == 200:
                    self.registry[service_info.name] = service_info
                    return True
            except:
                return False
    
    async def health_check_loop(self):
        # Periodically check service health
        while True:
            for name, info in self.registry.items():
                healthy = await self.register_with_health_check(info)
                if not healthy:
                    del self.registry[name]
                    # Alert: service down
            await asyncio.sleep(30)
```

### Phase 3: Add Retry Logic (Improve resilience)

```python
# app/mcp_client.py
class MCPClient:
    async def call_tool_with_retry(self, mcp_name, tool, args):
        max_retries = 3
        backoff = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                result = await self._call_mcp(mcp_name, tool, args)
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    raise
```

### Phase 4: Introduce Event Bus (Major refactor)

```python
# Pseudo-code for event-driven workflow engine
class EventDrivenWorkflowEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    async def execute(self, workflow, params):
        context = ExecutionContext(workflow.id, params)
        
        for node in workflow.nodes:
            # Publish task event
            await self.event_bus.publish("workflow.execute_node", {
                "execution_id": context.id,
                "node": node
            })
            
            # Wait for completion event
            result = await self.wait_for_completion(
                f"workflow.{context.id}.node.{node.id}"
            )
            
            context.results[node.id] = result
        
        return context.results

# Workers subscribe to events
async def tool_execution_worker():
    async for event in event_bus.subscribe("workflow.execute_node"):
        # Execute tool
        result = await call_mcp(
            event["node"]["mcp"],
            event["node"]["tool"],
            event["node"]["args"]
        )
        
        # Publish completion
        await event_bus.publish(
            f"workflow.{event['execution_id']}.node.{event['node']['id']}.completed",
            result
        )
```

### Phase 5: Enhance WebSocket (User experience)

```python
# Better real-time updates with proper types
class WebSocketManager:
    async def send_event(self, session_id, event_type, data):
        message = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        await self.send_update(session_id, message)

# Subscribe to execution events
async def execution_event_forwarder():
    async for event in event_bus.subscribe("execution.*"):
        session_id = event.get("session_id")
        await ws_manager.send_event(
            session_id,
            event["type"],
            event["payload"]
        )
```

---

## 9. WHAT MCP IS GOOD FOR IN THIS CODEBASE

1. ✓ **Exposing capabilities to AI agents**
   - Agents need to know what tools exist
   - Tools need clear semantics for models
   - Input validation before execution

2. ✓ **Autonomous agent loops**
   - Reason → Act → Observe pattern
   - Tool selection by model
   - Result incorporation back into context

3. ✓ **Tool composition**
   - Agents can chain multiple tools
   - Each tool's output becomes next tool's input
   - Model decides the sequence

4. ✓ **Safety boundaries**
   - Agents only see authorized MCPs
   - Input schema validation
   - Structured output parsing

---

## 10. WHAT MCP IS NOT GOOD FOR

1. ✗ **Service-to-service orchestration**
   - Use event bus instead
   - Services should publish events, subscribe to topics
   - Decouple implementation from orchestration

2. ✗ **Workflow execution**
   - Workflows are deterministic, MCPs assume autonomy
   - Use dedicated workflow engine
   - Workflows call backend services via event bus, not directly

3. ✗ **State management**
   - Use file system or database
   - MCP tools should be stateless
   - Shared state via execution context

4. ✗ **Authentication/Authorization**
   - Add auth middleware at Tier 2 boundary
   - Service-to-service communication needs tokens
   - Agent-to-tool can assume trusted network (for now)

5. ✗ **Load balancing**
   - Use reverse proxy (nginx) in front of MCPs
   - Or use Kubernetes for container orchestration
   - Current Docker setup is single-instance

---

## 11. CONCRETE RECOMMENDATIONS

### Immediate (Next Sprint)

1. **Add health check endpoint to all MCP servers**
   ```python
   # base_server.py
   @app.get("/health")
   async def health():
       return {"status": "healthy", "server": self.name, "timestamp": ...}
   ```

2. **Implement retry logic in AgentRuntime**
   ```python
   # agent_runtime.py - _call_mcp method
   # Add exponential backoff for transient failures
   ```

3. **Add service startup verification**
   ```python
   # main.py - startup event
   # Wait for all registered MCPs to be healthy before starting
   ```

4. **Document MCP boundaries**
   ```markdown
   # docs/ARCHITECTURE.md
   - MCP is for AI agent tool calls only
   - Workflows should NOT call MCPs directly
   - Backend services communicate via event bus (future)
   ```

### Short-term (2-3 Sprints)

1. **Refactor WorkflowEngine to decouple from MCP**
   - Workflows publish events, don't call MCPs directly
   - Separate "tool execution worker" listens on event bus
   - Results flow back through event publication

2. **Add execution state persistence**
   - Save execution progress to disk
   - Recover from orchestrator restarts
   - Enable audit trail

3. **Implement proper cancellation**
   - Cancellation signal should stop current tool execution
   - Not just set a flag (agent may not check)

### Medium-term (1-2 Quarters)

1. **Introduce message queue**
   - Redis for development, RabbitMQ for production
   - Replace direct HTTP calls with event publication
   - Enable scaling to multiple workers

2. **Implement service mesh concepts**
   - Service-to-service communication through abstraction
   - Circuit breaker, retry, timeout policies
   - Could use Linkerd or native implementation

3. **Add observability**
   - Distributed tracing (OpenTelemetry)
   - Metrics: tool latency, success rate, error types
   - Centralized logging (ELK stack)

---

## 12. SUMMARY TABLE

| Aspect | MCP (Tier 1) | Event Bus (Tier 2) | WebSocket (Tier 3) |
|--------|---------|------------|------------|
| **Purpose** | AI agent → tools | Backend orchestration | User → backend |
| **Transport** | HTTP REST | Message queue | WebSocket |
| **Semantics** | Tool call | Async task | Stream |
| **Current Status** | ✓ Good | ✗ Missing | ~ Partial |
| **Coupling** | Tight (OK for agents) | Should be loose | Loose |
| **Failure Handling** | Manual retry | Auto-retry in queue | Reconnect on client |
| **Scaling** | Single instance MCP | Multiple workers | Multiple clients |
| **State** | Stateless (good) | Event sourcing | Streaming state |

---

## 13. FINAL RECOMMENDATION

### Keep Tier 1 (MCP) AS-IS

The current implementation of MCP for AI agent tool calling is **well-designed and working correctly**. No changes needed here.

### Refactor Tier 2 (Orchestrator Services)

**Currently**: Tight HTTP coupling through direct REST calls
**Should Be**: Event-driven with async patterns
**Timeline**: Start with Phase 1 (service registry), build to Phase 4 (event bus)

### Enhance Tier 3 (Frontend Communication)

**Currently**: Basic WebSocket with limited message types
**Should Be**: Structured events with proper typing
**Timeline**: Quick wins in Phase 5

### The Key Insight

MCP was designed for one specific pattern: **AI models deciding which tools to use**. This is exactly how it's used for autonomous agents, and it's perfect for that.

However, **don't use MCP for things it wasn't designed for** (workflows, service coordination, state management). Those need different patterns. The platform is conflating three different communication needs, which creates unnecessary coupling.

By separating these concerns into three tiers with appropriate protocols for each, the system becomes:
- More maintainable (clear separation of concerns)
- More resilient (event bus with retries)
- More scalable (multiple workers, loose coupling)
- More testable (can mock each tier independently)

