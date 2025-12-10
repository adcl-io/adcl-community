# Agents Guide

Learn how to create, configure, and use autonomous AI agents in ADCL.

---

## Table of Contents

1. [What are Agents?](#what-are-agents)
2. [How Agents Work](#how-agents-work)
3. [Using Pre-Built Agents](#using-pre-built-agents)
4. [Creating Custom Agents](#creating-custom-agents)
5. [Agent Configuration](#agent-configuration)
6. [Running Agents](#running-agents)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What are Agents?

**Agents** are autonomous AI entities that:
- **Reason** about problems and create plans
- **Act** by calling MCP tool servers
- **Observe** results and adapt their approach
- **Iterate** until the task is complete

### Agent vs. Workflow

| Feature | Agent (Autonomous) | Workflow (Deterministic) |
|---------|-------------------|--------------------------|
| **Decision Making** | Dynamic, adaptive | Fixed sequence |
| **Tool Selection** | Chooses best tool | Pre-defined tools |
| **Error Handling** | Self-corrects | Fails on error |
| **Use Case** | Complex, ambiguous tasks | Repeatable processes |

**Example**:
```
Task: "Analyze network security"

Agent:
  - Decides to scan network first
  - Sees interesting ports, decides to probe further
  - Finds vulnerability, decides to research it
  - Creates comprehensive report

Workflow:
  - Step 1: Scan network
  - Step 2: Parse results
  - Step 3: Write report
  - (Fixed, no adaptation)
```

---

## How Agents Work

### ReAct Pattern (Reason + Act + Observe)

Agents follow a continuous loop:

```
1. REASON
   "What should I do next?"
   ↓
2. ACT
   Call MCP tool
   ↓
3. OBSERVE
   Receive result
   ↓
4. REASON
   "Did that work? What's next?"
   ↓
5. Repeat until task complete
```

### Example Execution

**Task**: "Review the code in /workspace/app.py"

```
Iteration 1:
  REASON: "I need to read the file first"
  ACT: file_tools.read_file("/workspace/app.py")
  OBSERVE: File contents received (200 lines of Python)

Iteration 2:
  REASON: "I should analyze for common issues"
  ACT: agent.code(task="Analyze for security issues")
  OBSERVE: Found 3 potential SQL injection points

Iteration 3:
  REASON: "I should check best practices too"
  ACT: agent.think(task="Evaluate code quality")
  OBSERVE: Code lacks error handling, no type hints

Iteration 4:
  REASON: "I should create a comprehensive report"
  ACT: file_tools.write_file(path="/workspace/review.md", content="...")
  OBSERVE: Report written successfully

DONE: "I've completed the code review and saved it to /workspace/review.md"
```

### Observable Execution

Every agent action is logged and visible:

```json
{
  "iteration": 1,
  "reasoning": "I need to read the file first",
  "tool": "file_tools.read_file",
  "params": {"path": "/workspace/app.py"},
  "result": {"content": "#!/usr/bin/env python..."},
  "status": "success"
}
```

---

## Using Pre-Built Agents

ADCL includes several pre-configured agents ready to use.

### Available Agents

#### 1. Code Reviewer
**Purpose**: Analyzes code quality, security, and best practices

**Capabilities**:
- Read source code files
- Identify security vulnerabilities
- Check best practices
- Generate review reports

**Example Tasks**:
```
"Review the code in /workspace/app.py"
"Check /workspace/api.js for security issues"
"Analyze the codebase and create a quality report"
```

**MCP Tools**:
- `file_tools`: Read/write files
- `agent`: AI reasoning

#### 2. Security Analyst
**Purpose**: Network reconnaissance and vulnerability assessment

**Capabilities**:
- Network discovery
- Port scanning
- Service detection
- Vulnerability scanning
- Security reporting

**Example Tasks**:
```
"Scan 192.168.1.0/24 for active hosts"
"Perform a security assessment of 192.168.1.100"
"Find all web servers on the network and check for vulnerabilities"
```

**MCP Tools**:
- `nmap_recon`: Network scanning
- `agent`: Analysis and reasoning
- `file_tools`: Report writing

#### 3. Research Assistant
**Purpose**: Information gathering and synthesis

**Capabilities**:
- Research topics
- Synthesize information
- Create summaries
- Document findings

**Example Tasks**:
```
"Research OAuth 2.0 best practices"
"Summarize the latest security trends"
"Create a report on container security"
```

**MCP Tools**:
- `agent`: Research and synthesis
- `file_tools`: Document creation

#### 4. Linear Issue Analyst
**Purpose**: Analyzes Linear issues and creates action plans

**Capabilities**:
- Fetch Linear issues
- Analyze issue content
- Create action plans
- Update issues with findings

**Example Tasks**:
```
"Analyze Linear issue TEAM-123"
"Create an action plan for resolving TEAM-456"
"Review all open security issues and prioritize them"
```

**MCP Tools**:
- `linear`: Issue tracking operations
- `agent`: Analysis and planning
- `file_tools`: Documentation

---

## Using Agents in Playground

### Step 1: Navigate to Playground

1. Open ADCL web UI: http://localhost:3000
2. Click "Playground" in sidebar

### Step 2: Select an Agent

1. Click the dropdown at the top
2. Select an agent (e.g., "Security Analyst")
3. The agent's persona and capabilities will load

### Step 3: Start a Conversation

Type your task and press Enter:

```
You: "What tools do you have access to?"

Agent: "I have access to the following tools:
- network_discovery: Scan for active hosts
- port_scan: Identify open ports
- service_detection: Determine running services
- vulnerability_scan: Check for common vulnerabilities
- think: AI reasoning for analysis
- write_file: Create reports"
```

### Step 4: Give It a Task

```
You: "Scan 192.168.50.0/24 and tell me what you find"

Agent: "I'll scan that network for you."

[Agent reasoning]: "I should start with network discovery"
[Tool call]: nmap_recon.network_discovery(target="192.168.50.0/24")
[Result]: Found 5 active hosts

[Agent reasoning]: "I should scan these hosts for open ports"
[Tool call]: nmap_recon.port_scan(targets=["192.168.50.1", ...])
[Result]: Host 192.168.50.100 has ports 80, 443, 22 open

[Agent reasoning]: "Port 80 and 443 suggest a web server"
[Tool call]: nmap_recon.service_detection(target="192.168.50.100")
[Result]: Apache 2.4.41 on port 80, OpenSSH 8.2 on port 22

Agent: "I found 5 active hosts on the network. Host 192.168.50.100 is running:
- Apache 2.4.41 web server on ports 80/443
- OpenSSH 8.2 on port 22
Would you like me to check for vulnerabilities?"
```

### Step 5: Continue Conversation

Agents maintain conversation history:

```
You: "Yes, check for vulnerabilities on that host"

Agent: [Continues from previous context]
[Tool call]: nmap_recon.vulnerability_scan(target="192.168.50.100")
...
```

---

## Running Agents Autonomously

### Via Agents Page

1. **Navigate to Agents**:
   - Click "Agents" in sidebar
   - View list of available agents

2. **Select an Agent**:
   - Click on agent card (e.g., "Code Reviewer")

3. **Enter Task**:
   ```
   Review all Python files in /workspace and create a quality report
   ```

4. **Run Task**:
   - Click "Run Task" button
   - Agent executes autonomously

5. **View Execution**:
   - Real-time updates appear below
   - See reasoning, tool calls, and results
   - Execution history preserved

### Via API

```bash
# Run agent task
curl -X POST http://localhost:8000/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "code_reviewer",
    "task": "Review /workspace/app.py"
  }'

# Response
{
  "execution_id": "exec_123",
  "status": "running",
  "websocket_url": "ws://localhost:8000/ws/execute/exec_123"
}

# Connect to WebSocket for real-time updates
wscat -c ws://localhost:8000/ws/execute/exec_123
```

---

## Creating Custom Agents

### Agent Definition Structure

Create a JSON file in `agent-definitions/`:

```json
{
  "name": "my_agent",
  "version": "0.1.0",
  "description": "Brief description of what this agent does",
  "persona": "You are an expert in... Your goal is to... You should...",
  "mcp_servers": [
    "file_tools",
    "agent"
  ],
  "config": {
    "model": "claude-sonnet-4-5",
    "temperature": 0.7,
    "max_tokens": 4096,
    "max_iterations": 10
  },
  "metadata": {
    "author": "Your Name",
    "created": "2025-12-08",
    "tags": ["security", "analysis"]
  }
}
```

### Step-by-Step: Create a Database Analyst Agent

**1. Create Definition File**:

```bash
touch agent-definitions/database_analyst.json
```

**2. Define Agent**:

```json
{
  "name": "database_analyst",
  "version": "0.1.0",
  "description": "Analyzes database schemas and queries for optimization",
  "persona": "You are an expert database administrator and performance analyst. Your goal is to analyze database schemas, queries, and provide optimization recommendations. You should:\n\n1. Examine schema structure for normalization and indexing\n2. Analyze queries for performance issues\n3. Suggest optimizations and best practices\n4. Create detailed reports with specific recommendations\n\nAlways explain your reasoning and provide concrete examples.",
  "mcp_servers": [
    "file_tools",
    "agent"
  ],
  "config": {
    "model": "claude-sonnet-4-5",
    "temperature": 0.5,
    "max_tokens": 8192,
    "max_iterations": 15
  },
  "metadata": {
    "author": "ADCL Team",
    "created": "2025-12-08",
    "tags": ["database", "performance", "optimization"]
  }
}
```

**3. Restart Platform**:

```bash
./clean-restart.sh
```

**4. Use Your Agent**:

1. Go to Playground
2. Select "Database Analyst"
3. Task: "Analyze the schema in /workspace/schema.sql"

---

## Agent Configuration

### Persona Design

The **persona** field is critical - it defines agent behavior:

**Good Persona**:
```json
{
  "persona": "You are an expert code reviewer with 10 years of experience. Your goal is to identify security vulnerabilities, code quality issues, and suggest improvements.

  When reviewing code, you should:
  1. First read the entire file to understand context
  2. Check for common security issues (SQL injection, XSS, etc.)
  3. Evaluate code quality (readability, maintainability)
  4. Suggest specific improvements with examples
  5. Create a structured report with findings

  Be thorough but concise. Focus on actionable feedback."
}
```

**Bad Persona**:
```json
{
  "persona": "You review code."
}
```

### Configuration Options

```json
{
  "config": {
    // Model selection
    "model": "claude-sonnet-4-5",  // or "claude-opus-4-5"

    // Temperature (0-1)
    // Low (0.0-0.3): Deterministic, focused
    // Medium (0.4-0.7): Balanced
    // High (0.8-1.0): Creative, exploratory
    "temperature": 0.7,

    // Maximum tokens per response
    "max_tokens": 4096,  // Increase for longer outputs

    // Maximum ReAct loop iterations
    "max_iterations": 10,  // Prevent infinite loops

    // Stop sequences (optional)
    "stop_sequences": ["</output>"]
  }
}
```

### MCP Server Selection

Choose MCPs based on agent capabilities:

```json
{
  "mcp_servers": [
    "file_tools",      // File operations
    "agent",           // AI reasoning (think, code, review)
    "nmap_recon",      // Network scanning
    "kali",            // Penetration testing
    "history",         // Conversation storage
    "linear"           // Issue tracking
  ]
}
```

**Principle**: Only include MCPs the agent needs. Don't give file access to agents that only do network scanning.

---

## Best Practices

### 1. Clear Personas

**Do**:
```
"You are an expert penetration tester. Your goal is to identify security vulnerabilities. You should:
1. Scan systematically (network → services → vulnerabilities)
2. Document all findings with severity ratings
3. Suggest remediation steps
Always operate within legal and ethical boundaries."
```

**Don't**:
```
"You are a security expert. Do security stuff."
```

### 2. Appropriate MCP Access

**Do**:
```json
// Security agent - only needs network tools
{"mcp_servers": ["nmap_recon", "agent", "file_tools"]}

// Code reviewer - only needs files and analysis
{"mcp_servers": ["file_tools", "agent"]}
```

**Don't**:
```json
// Give all agents all tools
{"mcp_servers": ["*"]}
```

### 3. Reasonable Limits

**Do**:
```json
{
  "max_iterations": 10,      // Prevents runaway execution
  "max_tokens": 4096,        // Reasonable response size
  "temperature": 0.7         // Balanced creativity
}
```

**Don't**:
```json
{
  "max_iterations": 100,     // Too many (expensive)
  "max_tokens": 100000,      // Excessive
  "temperature": 1.0         // Too random
}
```

### 4. Testable Tasks

**Good Tasks**:
```
"Scan 192.168.1.0/24 and create a security report"
"Review /workspace/app.py for security issues"
"List all files in /workspace and categorize them"
```

**Bad Tasks**:
```
"Do security"
"Fix everything"
"Make it better"
```

### 5. Iterative Development

1. Start with simple persona
2. Test with specific tasks
3. Observe agent behavior
4. Refine persona based on results
5. Add more MCPs as needed

---

## Troubleshooting

### Agent Not Responding

**Symptom**: Agent starts but doesn't take action

**Possible Causes**:
1. **API key invalid**: Check `.env` file
2. **MCP server down**: Check `docker-compose ps`
3. **Max iterations reached**: Check logs for loop limit

**Solution**:
```bash
# Check MCP servers
docker-compose ps | grep mcp

# View agent logs
docker-compose logs orchestrator | grep agent

# Restart services
./clean-restart.sh
```

### Agent Keeps Repeating Same Action

**Symptom**: Agent calls same tool over and over

**Possible Causes**:
1. Persona doesn't guide toward completion
2. Agent stuck in loop
3. Tool returning unclear results

**Solution**:
Update persona to include completion criteria:
```json
{
  "persona": "...When you've completed all steps, summarize your findings and stop."
}
```

### Agent Makes Wrong Tool Choices

**Symptom**: Agent uses inappropriate tools

**Possible Causes**:
1. Persona not specific enough
2. Tool descriptions unclear
3. Task ambiguous

**Solution**:
Refine persona with explicit steps:
```json
{
  "persona": "...You should ALWAYS:
  1. First use network_discovery to find hosts
  2. Then use port_scan on found hosts
  3. Finally use service_detection for details
  Do NOT skip steps."
}
```

### High API Costs

**Symptom**: Agent uses too many API calls

**Possible Causes**:
1. Max iterations too high
2. Agent not terminating properly
3. Inefficient reasoning loop

**Solution**:
```json
{
  "config": {
    "max_iterations": 5,      // Lower limit
    "max_tokens": 2048,       // Reduce tokens
    "model": "claude-sonnet-4-5"  // Use efficient model
  }
}
```

---

## Next Steps

- **[Teams Guide](Teams-Guide)** - Combine agents into collaborative teams
- **[MCP Servers Guide](MCP-Servers-Guide)** - Create custom tools for agents
- **[Workflows Guide](Workflows-Guide)** - Build deterministic processes
- **[Configuration Guide](Configuration-Guide)** - Advanced agent configuration

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
