# Workflows Guide

Learn how to create visual, node-based workflows for deterministic task execution.

---

## Table of Contents

1. [What are Workflows?](#what-are-workflows)
2. [When to Use Workflows](#when-to-use-workflows)
3. [Workflow Builder Interface](#workflow-builder-interface)
4. [Creating Your First Workflow](#creating-your-first-workflow)
5. [Node Configuration](#node-configuration)
6. [Parameter Resolution](#parameter-resolution)
7. [Execution and Monitoring](#execution-and-monitoring)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## What are Workflows?

**Workflows** are visual, node-based compositions of MCP tool calls that execute in a fixed sequence. They provide a deterministic, repeatable way to chain tools together.

### Workflow vs. Agent vs. Team

| Feature | Workflow | Agent | Team |
|---------|----------|-------|------|
| **Decision Making** | Fixed sequence | Dynamic, adaptive | Multi-perspective |
| **Determinism** | 100% predictable | Adaptive | Partially adaptive |
| **Complexity** | Simple to moderate | Moderate to complex | Complex |
| **Use Case** | Repeatable processes | Problem-solving | Multi-phase tasks |

**Visual Representation**:
```
Workflow:
[Node 1] → [Node 2] → [Node 3] → [Node 4]
  |          |          |          |
  ↓          ↓          ↓          ↓
 Tool A    Tool B    Tool C    Tool D
(Always executes in this exact order)

Agent:
Start → Reason → Choose Tool → Execute → Observe → Reason → ...
(Dynamic path based on results)

Team:
Agent 1 (Scanner) → Agent 2 (Analyst) → Agent 3 (Reporter)
(Each agent makes decisions within their phase)
```

---

## When to Use Workflows

### Use Workflows For:

✅ **Repeatable Processes** - Same steps every time
```
Example: "Deploy and test"
  1. Build code
  2. Run tests
  3. Deploy to staging
  4. Run smoke tests
  5. Notify team
```

✅ **Data Pipelines** - Transform data through stages
```
Example: "Process security scan"
  1. Scan network
  2. Parse scan results
  3. Enrich with CVE data
  4. Format as report
  5. Upload to Linear
```

✅ **Automation** - Triggered workflows (webhooks, schedules)
```
Example: "Nightly security scan"
  Trigger: Schedule (2am daily)
  1. Scan network
  2. Compare with baseline
  3. Alert on changes
```

✅ **Integration Chains** - Connect multiple systems
```
Example: "CI/CD integration"
  Webhook: GitHub push
  1. Fetch code
  2. Run tests
  3. Scan for vulnerabilities
  4. Update Linear issue
  5. Post to Slack
```

### Use Agents Instead For:

❌ **Problem Solving** - When approach varies
```
Example: "Debug why the service is failing"
(Agent needs to investigate dynamically)
```

❌ **Research Tasks** - When path is unclear
```
Example: "Research best practices for X"
(Agent determines what to research based on findings)
```

❌ **Complex Analysis** - Requires reasoning
```
Example: "Analyze this codebase and suggest improvements"
(Agent needs to think and adapt)
```

---

## Workflow Builder Interface

### Accessing the Builder

1. Open ADCL: http://localhost:3000
2. Click "Workflows" in sidebar
3. Click "New Workflow" button

### Interface Components

```
┌─────────────────────────────────────────────────────────┐
│ [Workflow Name]                    [Execute] [Save]     │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  MCP     │         Canvas (Drag & Drop Area)           │
│ Servers  │                                              │
│          │    ┌──────┐       ┌──────┐                  │
│ • agent  │    │Node 1│──────▶│Node 2│                  │
│ • files  │    └──────┘       └──────┘                  │
│ • nmap   │         │              │                     │
│ • kali   │         └──────┬───────┘                     │
│ • linear │                ▼                             │
│ • history│           ┌──────┐                           │
│          │           │Node 3│                           │
│          │           └──────┘                           │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Left Panel**: Available MCP servers (drag onto canvas)

**Canvas**: Visual workflow composition area
- **Nodes**: MCP tool calls
- **Edges**: Data flow connections
- **Selection**: Click node to configure

**Top Bar**: Workflow actions
- **Name**: Editable workflow name
- **Execute**: Run the workflow
- **Save**: Persist to `workflows/`

---

## Creating Your First Workflow

### Example: "Hello World" Workflow

Let's create a simple workflow that generates a message and writes it to a file.

**Step 1: Create New Workflow**

1. Go to Workflows page
2. Click "New Workflow"
3. Name it: "Hello World"

**Step 2: Add Agent Node**

1. Drag "agent" from left panel onto canvas
2. Click the node to configure
3. Set parameters:
   ```json
   {
     "tool": "think",
     "params": {
       "task": "Generate a creative hello world message"
     }
   }
   ```

**Step 3: Add File Tools Node**

1. Drag "file_tools" onto canvas
2. Click the node to configure
3. Set parameters:
   ```json
   {
     "tool": "write_file",
     "params": {
       "path": "/workspace/hello.txt",
       "content": "${agent.output}"
     }
   }
   ```

**Step 4: Connect Nodes**

1. Hover over agent node
2. Drag from output port to file_tools input port
3. Connection (edge) appears

**Step 5: Execute**

1. Click "Execute" button
2. Watch nodes light up as they execute:
   - agent node: Green (executing) → Blue (complete)
   - file_tools node: Green (executing) → Blue (complete)
3. View results in execution panel

**Step 6: Verify Output**

```bash
# Check the file was created
cat /workspace/hello.txt
```

---

## Node Configuration

### Node Structure

Each node represents an MCP tool call:

```json
{
  "id": "node_123",
  "type": "mcp_server",
  "server": "nmap_recon",
  "tool": "network_discovery",
  "params": {
    "target": "192.168.1.0/24",
    "scan_type": "ping"
  }
}
```

### Available MCP Servers

#### 1. agent (AI Reasoning)

**Tools**:
- `think`: General reasoning
- `code`: Generate code
- `review`: Code review

**Example**:
```json
{
  "server": "agent",
  "tool": "think",
  "params": {
    "task": "Analyze the scan results and identify risks"
  }
}
```

#### 2. file_tools (File Operations)

**Tools**:
- `read_file`: Read file contents
- `write_file`: Write to file
- `list_directory`: List directory contents

**Example**:
```json
{
  "server": "file_tools",
  "tool": "write_file",
  "params": {
    "path": "/workspace/report.md",
    "content": "# Security Report\n\n${analysis.output}"
  }
}
```

#### 3. nmap_recon (Network Scanning)

**Tools**:
- `network_discovery`: Find active hosts
- `port_scan`: Scan ports
- `service_detection`: Identify services
- `vulnerability_scan`: Check for vulns

**Example**:
```json
{
  "server": "nmap_recon",
  "tool": "network_discovery",
  "params": {
    "target": "192.168.1.0/24",
    "scan_type": "ping"
  }
}
```

#### 4. linear (Issue Tracking)

**Tools**:
- `get_issue`: Fetch issue details
- `create_issue`: Create new issue
- `update_issue`: Update existing issue
- `list_issues`: Query issues

**Example**:
```json
{
  "server": "linear",
  "tool": "create_issue",
  "params": {
    "title": "Security Finding: ${vuln.title}",
    "description": "${vuln.details}",
    "team": "SECURITY"
  }
}
```

---

## Parameter Resolution

Workflows support dynamic parameter resolution to pass data between nodes.

### Reference Previous Node Output

Use `${node-id.field}` syntax:

```json
// Node 1 (ID: scan-node)
{
  "server": "nmap_recon",
  "tool": "network_discovery",
  "params": {"target": "192.168.1.0/24"}
}
// Output: {"hosts": ["192.168.1.1", "192.168.1.2"]}

// Node 2 references Node 1
{
  "server": "agent",
  "tool": "think",
  "params": {
    "task": "Analyze these hosts: ${scan-node.hosts}"
  }
}
// Receives: "Analyze these hosts: ['192.168.1.1', '192.168.1.2']"
```

### Environment Variables

Use `${env:VARIABLE_NAME}` syntax:

```json
{
  "server": "nmap_recon",
  "tool": "network_discovery",
  "params": {
    "target": "${env:DEFAULT_SCAN_NETWORK}"
  }
}
// Resolves to value from .env file
```

### Complex References

Reference nested fields:

```json
// Node 1 output
{
  "scan_results": {
    "hosts": [
      {"ip": "192.168.1.1", "ports": [22, 80]},
      {"ip": "192.168.1.2", "ports": [443]}
    ]
  }
}

// Node 2 references nested field
{
  "params": {
    "data": "${scan-node.scan_results.hosts}"
  }
}
```

### Multiple References

Combine multiple node outputs:

```json
{
  "params": {
    "summary": "Scanner found ${scan.host_count} hosts. Analyst identified ${analyze.vuln_count} vulnerabilities."
  }
}
```

---

## Execution and Monitoring

### Starting Execution

**Via UI**:
1. Open workflow in builder
2. Click "Execute" button
3. Watch real-time execution

**Via API**:
```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "hello_world"}'
```

### Real-Time Updates

Execution updates stream via WebSocket:

```json
// Node started
{
  "type": "node_started",
  "node_id": "scan-node",
  "timestamp": "2025-12-08T10:30:00Z"
}

// Node executing
{
  "type": "node_executing",
  "node_id": "scan-node",
  "status": "running"
}

// Node completed
{
  "type": "node_completed",
  "node_id": "scan-node",
  "result": {"hosts": ["192.168.1.1"]},
  "status": "success"
}

// Workflow completed
{
  "type": "workflow_completed",
  "status": "success",
  "duration_ms": 5432
}
```

### Node Status Indicators

Nodes change color based on status:

- **Gray**: Not started
- **Yellow**: Queued
- **Green**: Executing
- **Blue**: Completed successfully
- **Red**: Failed

### Viewing Results

**In UI**:
- Execution panel shows each node's output
- Click node to see detailed result

**In Files**:
```bash
# View execution log
cat logs/workflow-execution-123.log

# Check output files
ls -la /workspace/
```

---

## Best Practices

### 1. Clear Node Naming

**Do**:
```json
{
  "id": "scan-network",
  "id": "analyze-results",
  "id": "write-report"
}
```

**Don't**:
```json
{
  "id": "node1",
  "id": "node2",
  "id": "node3"
}
```

### 2. Error Handling Nodes

Add nodes to handle failures:

```
[Scan Network] → [Check Success?] → [Analyze]
                       ↓ (if failed)
                 [Alert Team]
```

### 3. Modular Workflows

Keep workflows focused on single purpose:

**Good**: "Network Scan Workflow"
- Scan network
- Parse results
- Write summary

**Bad**: "Do Everything Workflow"
- Scan network
- Analyze code
- Update database
- Send emails
- (Too many responsibilities)

### 4. Reusable Components

Create workflows that can be triggered:

```
Workflow: "Security Scan"
  - Can be called from other workflows
  - Can be triggered by webhook
  - Can run on schedule
```

### 5. Parameter Validation

Use agent nodes to validate inputs:

```
[Validate Input] → [Process Data] → [Output]
     ↓ (if invalid)
[Return Error]
```

---

## Advanced Patterns

### Conditional Branching (via Files)

Use file existence as conditions:

```
[Scan] → [Write Critical Issues to /workspace/critical.json]
    ↓
[Check File Exists?]
    ├─ Exists → [Deep Analysis]
    └─ Not Exists → [Standard Report]
```

### Parallel Execution (Planned)

Future feature: Execute nodes in parallel:

```
        ┌─[Scan Network A]─┐
[Start]─┼─[Scan Network B]─┼─[Merge Results]
        └─[Scan Network C]─┘
```

### Loop Simulation

Use agents to process lists:

```
[Get Host List] → [Agent: Process Each Host] → [Aggregate Results]
```

The agent node uses iteration to process each host.

---

## Troubleshooting

### Node Not Executing

**Symptom**: Node stays gray or yellow

**Possible Causes**:
1. Previous node failed
2. MCP server not running
3. Invalid parameters

**Solution**:
```bash
# Check MCP servers
docker-compose ps | grep mcp

# View execution logs
cat logs/workflow-execution-*.log

# Check node configuration
cat workflows/my_workflow.json | jq '.nodes[] | select(.id=="node-id")'
```

### Parameter Resolution Failed

**Symptom**: Error: "Cannot resolve ${node.field}"

**Possible Causes**:
1. Referenced node doesn't exist
2. Field doesn't exist in output
3. Typo in reference

**Solution**:
Check referenced node output:
```bash
# View execution log
cat logs/workflow-execution-*.log | grep "node-id"

# Verify field exists in output
```

### Workflow Executes Too Slowly

**Symptom**: Long execution time

**Possible Causes**:
1. Agent nodes with high iterations
2. Network scans on large ranges
3. Too many sequential nodes

**Solution**:
- Reduce agent max_iterations
- Narrow scan ranges
- Consider parallel execution (when available)
- Use faster models (Sonnet vs Opus)

---

## Example Workflows

### Security Scan Workflow

```
[1. Network Discovery]
  ↓
[2. Port Scan]
  ↓
[3. Service Detection]
  ↓
[4. Analyze Results]
  ↓
[5. Write Report]
  ↓
[6. Create Linear Issue]
```

### Code Review Workflow

```
[1. List Python Files]
  ↓
[2. Read Each File]
  ↓
[3. Analyze Security]
  ↓
[4. Check Quality]
  ↓
[5. Generate Report]
  ↓
[6. Write to File]
```

### CI/CD Integration Workflow

```
[1. Fetch Code from Webhook]
  ↓
[2. Run Tests]
  ↓
[3. Scan for Vulnerabilities]
  ↓
[4. Update Linear Issue]
  ↓
[5. Post to Slack]
```

---

## Next Steps

- **[Triggers Guide](Triggers-Guide)** - Automate workflow execution
- **[MCP Servers Guide](MCP-Servers-Guide)** - Create custom workflow nodes
- **[Agents Guide](Agents-Guide)** - Alternative to workflows for complex tasks
- **[Teams Guide](Teams-Guide)** - Multi-agent alternative to workflows

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
