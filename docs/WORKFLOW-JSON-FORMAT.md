# Workflow JSON Format - Current Implementation

**Created:** 2025-11-06  
**Branch:** prd-75  
**Purpose:** Document current workflow JSON structure for PRD-61 Phase 1 implementation

---

## Overview

Workflows in the MCP Agent Platform are defined as JSON documents with a simple graph structure: **nodes** (operations) and **edges** (dependencies).

---

## JSON Schema

### Top-Level Structure

```json
{
  "name": "string",           // Workflow name (required)
  "description": "string",    // Optional description
  "nodes": [...],             // Array of workflow nodes (required)
  "edges": [...]              // Array of edges defining execution order (required)
}
```

---

## Node Structure

Each node represents a single MCP tool call:

```json
{
  "id": "string",             // Unique node identifier (required)
  "type": "mcp_call",         // Node type (currently only "mcp_call" supported)
  "mcp_server": "string",     // MCP server name (required)
  "tool": "string",           // Tool name on the MCP server (required)
  "params": {                 // Tool parameters (required, can be empty {})
    "key": "value",           // Static values
    "key2": "${node-id.field}" // Dynamic references to previous results
  }
}
```

### Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier for the node (e.g., "agent-think", "file-write") |
| `type` | string | ✅ | Node type - currently only "mcp_call" is supported |
| `mcp_server` | string | ✅ | Name of the MCP server to call (e.g., "agent", "file_tools") |
| `tool` | string | ✅ | Name of the tool on the MCP server (e.g., "think", "code", "write_file") |
| `params` | object | ✅ | Parameters to pass to the tool (can be empty object) |

---

## Edge Structure

Edges define execution order and dependencies:

```json
{
  "source": "string",         // Source node ID (required)
  "target": "string"          // Target node ID (required)
}
```

### Edge Semantics

- **Execution Order:** Target node executes AFTER source node completes
- **Data Flow:** Target node can reference source node results via `${source-id.field}`
- **Topological Sort:** Backend automatically determines execution order from edges

---

## Parameter References

Nodes can reference results from previous nodes using the syntax: `${node-id.field}`

### Example

```json
{
  "nodes": [
    {
      "id": "generate-code",
      "type": "mcp_call",
      "mcp_server": "agent",
      "tool": "code",
      "params": {
        "spec": "Create a Python function",
        "language": "python"
      }
    },
    {
      "id": "save-code",
      "type": "mcp_call",
      "mcp_server": "file_tools",
      "tool": "write_file",
      "params": {
        "path": "output.py",
        "content": "${generate-code.code}"  // References result from previous node
      }
    }
  ],
  "edges": [
    {
      "source": "generate-code",
      "target": "save-code"
    }
  ]
}
```

---

## Complete Examples

### Example 1: Hello World Workflow

```json
{
  "name": "Hello World Workflow",
  "description": "Simple workflow demonstrating agent and file tool interaction",
  "nodes": [
    {
      "id": "agent-think",
      "type": "mcp_call",
      "mcp_server": "agent",
      "tool": "think",
      "params": {
        "prompt": "What is a good greeting message for a new MCP agent platform?"
      }
    },
    {
      "id": "agent-code",
      "type": "mcp_call",
      "mcp_server": "agent",
      "tool": "code",
      "params": {
        "spec": "Write a Python function that prints a welcome message for the MCP Agent Platform",
        "language": "python"
      }
    },
    {
      "id": "file-write",
      "type": "mcp_call",
      "mcp_server": "file_tools",
      "tool": "write_file",
      "params": {
        "path": "hello.py",
        "content": "${agent-code.code}"
      }
    }
  ],
  "edges": [
    {
      "source": "agent-think",
      "target": "agent-code"
    },
    {
      "source": "agent-code",
      "target": "file-write"
    }
  ]
}
```

**Execution Flow:**
1. `agent-think` → Generates greeting idea
2. `agent-code` → Creates Python code
3. `file-write` → Saves code to `hello.py`

---

### Example 2: Code Review Workflow

```json
{
  "name": "Code Review Workflow",
  "description": "Generate code and have it reviewed by the agent",
  "nodes": [
    {
      "id": "generate-code",
      "type": "mcp_call",
      "mcp_server": "agent",
      "tool": "code",
      "params": {
        "spec": "Create a Python function to calculate fibonacci numbers recursively",
        "language": "python"
      }
    },
    {
      "id": "review-code",
      "type": "mcp_call",
      "mcp_server": "agent",
      "tool": "review",
      "params": {
        "code": "${generate-code.code}"
      }
    },
    {
      "id": "save-code",
      "type": "mcp_call",
      "mcp_server": "file_tools",
      "tool": "write_file",
      "params": {
        "path": "fibonacci.py",
        "content": "${generate-code.code}"
      }
    },
    {
      "id": "save-review",
      "type": "mcp_call",
      "mcp_server": "file_tools",
      "tool": "write_file",
      "params": {
        "path": "fibonacci_review.txt",
        "content": "${review-code.feedback}"
      }
    }
  ],
  "edges": [
    {
      "source": "generate-code",
      "target": "review-code"
    },
    {
      "source": "generate-code",
      "target": "save-code"
    },
    {
      "source": "review-code",
      "target": "save-review"
    }
  ]
}
```

**Execution Flow:**
1. `generate-code` → Creates fibonacci function
2. `review-code` → Reviews the code (parallel with save-code)
3. `save-code` → Saves code to file (parallel with review-code)
4. `save-review` → Saves review feedback

---

## Backend Implementation

### Pydantic Models

```python
class WorkflowNode(BaseModel):
    id: str
    type: str  # "mcp_call"
    mcp_server: str
    tool: str
    params: Dict[str, Any]

class WorkflowEdge(BaseModel):
    source: str
    target: str

class WorkflowDefinition(BaseModel):
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
```

### Execution Endpoint

```
POST /workflows/execute
Content-Type: application/json

{
  "workflow": {
    "name": "...",
    "nodes": [...],
    "edges": [...]
  }
}
```

### WebSocket Endpoint (Real-time)

```
WS /ws/execute/{session_id}

Send: { "workflow": {...} }
Receive: { "type": "log", "log": {...}, "node_states": {...} }
Receive: { "type": "node_state", "node_id": "...", "status": "...", "node_states": {...} }
Receive: { "type": "result", "result": {...} }
```

---

## Frontend Implementation

### React Flow Conversion

The frontend converts workflow JSON to React Flow format:

```javascript
// Workflow JSON → React Flow Nodes
const flowNodes = workflow.nodes.map((node, index) => ({
  id: node.id,
  type: 'mcpNode',
  position: { x: 100 + index * 250, y: 100 },
  data: {
    label: `${node.mcp_server}.${node.tool}`,
    mcp_server: node.mcp_server,
    tool: node.tool,
    params: node.params,
  },
}));

// Workflow JSON → React Flow Edges
const flowEdges = workflow.edges.map((edge, index) => ({
  id: `edge-${index}`,
  source: edge.source,
  target: edge.target,
  sourceHandle: 'output',
  targetHandle: 'input',
  animated: true,
}));
```

### React Flow → Workflow JSON

```javascript
// Convert React Flow nodes/edges back to workflow JSON
const workflow = {
  name: workflowName,
  nodes: nodes.map(node => ({
    id: node.id,
    type: 'mcp_call',
    mcp_server: node.data.mcp_server,
    tool: node.data.tool,
    params: node.data.params || {}
  })),
  edges: edges.map(edge => ({
    source: edge.source,
    target: edge.target
  }))
};
```

---

## Execution States

During execution, nodes have the following states:

| State | Description | Visual Indicator |
|-------|-------------|------------------|
| `idle` | Not yet executed | Gray border |
| `pending` | Waiting for dependencies | Clock icon |
| `running` | Currently executing | Spinning loader, blue border |
| `completed` | Successfully completed | Green checkmark, green border |
| `error` | Failed with error | Red X, red border |

---

## Validation Rules

### Required Validations

1. **Unique Node IDs:** All node IDs must be unique
2. **Valid Edges:** Source and target must reference existing node IDs
3. **No Cycles:** Workflow graph must be acyclic (DAG)
4. **Valid MCP Servers:** MCP server must exist in registry
5. **Valid Tools:** Tool must exist on the specified MCP server
6. **Required Parameters:** All required tool parameters must be provided

### Current Validation (frontend/src/utils/workflowValidation.js)

```javascript
export function validateWorkflow(nodes, edges) {
  const errors = [];
  const warnings = [];

  // Check for nodes
  if (nodes.length === 0) {
    errors.push('Workflow must have at least one node');
  }

  // Check for disconnected nodes
  const connectedNodes = new Set();
  edges.forEach(edge => {
    connectedNodes.add(edge.source);
    connectedNodes.add(edge.target);
  });

  nodes.forEach(node => {
    if (!connectedNodes.has(node.id) && nodes.length > 1) {
      warnings.push(`Node ${node.id} is not connected`);
    }
  });

  // Check for cycles (simplified)
  // ... cycle detection logic ...

  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}
```

---

## Storage Locations

### Example Workflows (Read-only)

```
workflows/
├── hello_world.json
├── code_review.json
├── nmap_recon.json
├── full_recon.json
└── network_discovery.json
```

### User Workflows (Phase 1.4 - To Be Implemented)

```
workflows/user/
└── {user_id}/
    ├── {workflow_id}.json
    └── ...
```

### Workflow Templates (Phase 3.1 - To Be Implemented)

```
workflows/templates/
├── basic_code_generation.json
├── code_review_pipeline.json
├── network_scanning.json
└── ...
```

---

## API Endpoints (Current)

### Existing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflows/execute` | Execute workflow (non-streaming) |
| WS | `/ws/execute/{session_id}` | Execute workflow (real-time updates) |
| GET | `/workflows/examples` | List example workflows |
| GET | `/workflows/examples/{filename}` | Get specific example workflow |

### To Be Implemented (Phase 1.4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workflows` | Save new workflow |
| GET | `/workflows` | List user workflows |
| GET | `/workflows/{id}` | Get specific workflow |
| PUT | `/workflows/{id}` | Update workflow |
| DELETE | `/workflows/{id}` | Delete workflow |

---

## Key Insights for PRD-61 Phase 1

### What Works Well

1. ✅ **Simple, clean JSON format** - Easy to understand and edit
2. ✅ **Parameter references** - `${node-id.field}` syntax works well
3. ✅ **Topological sort** - Backend handles execution order automatically
4. ✅ **Real-time updates** - WebSocket provides live execution feedback
5. ✅ **Type safety** - Pydantic models validate structure

### What Needs Improvement (Phase 1 Scope)

1. ❌ **No persistence** - Workflows only exist in memory or as files
2. ❌ **No UI for editing params** - Must edit JSON manually
3. ❌ **No drag-and-drop** - Must write JSON by hand
4. ❌ **No save/load UI** - Must use API directly
5. ❌ **No validation feedback** - Errors only shown on execution

### Phase 1 Will Add

1. ✅ **Drag-and-drop node creation** - Visual workflow building
2. ✅ **Inline parameter editing** - Modal dialog for editing node params
3. ✅ **Save/Load UI** - Save workflows with names, load from dropdown
4. ✅ **Enhanced visualization** - Status badges, progress bars
5. ✅ **Shadcn/Tailwind** - Consistent UI with theme support

---

## Notes for Implementation

### Parameter Editing (Task 1.2)

When implementing the NodeConfigModal, we need to:
- Fetch tool schema from MCP server: `POST /mcp/servers/{server}/tools`
- Generate form fields from schema properties
- Validate required fields
- Support `${node-id.field}` syntax in text inputs
- Show autocomplete for available references

### Save/Load (Task 1.4)

Workflow save format should match current JSON exactly:
```json
{
  "name": "User-provided name",
  "description": "Optional description",
  "nodes": [...],  // From React Flow nodes
  "edges": [...]   // From React Flow edges
}
```

Storage options:
1. **LocalStorage** (Phase 1) - Quick win, no backend changes
2. **Backend API** (Phase 1.4) - Persistent storage, requires new endpoints
3. **Both** (Recommended) - LocalStorage for drafts, API for saved workflows

---

## Document Version

**Version:** 1.0  
**Last Updated:** 2025-11-06  
**Status:** ✅ Complete
