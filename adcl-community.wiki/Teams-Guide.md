# Teams Guide

Learn how to create and use multi-agent teams for complex collaborative tasks.

---

## Table of Contents

1. [What are Agent Teams?](#what-are-agent-teams)
2. [When to Use Teams](#when-to-use-teams)
3. [How Teams Work](#how-teams-work)
4. [Using Pre-Built Teams](#using-pre-built-teams)
5. [Creating Custom Teams](#creating-custom-teams)
6. [Team Configuration](#team-configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What are Agent Teams?

**Agent Teams** are collections of autonomous agents with different roles and specializations that collaborate to complete complex tasks.

### Team vs. Single Agent

| Aspect | Single Agent | Agent Team |
|--------|-------------|-----------|
| **Specialization** | Generalist | Multiple specialists |
| **Complexity** | Simple to moderate tasks | Complex, multi-phase tasks |
| **Response** | Single perspective | Multiple perspectives |
| **Tools** | Limited set | Distributed across roles |

**Example**:
```
Task: "Perform a complete security assessment"

Single Agent:
  - Tries to do everything
  - May miss specialized insights
  - One perspective

Agent Team:
  Scanner Agent:
    - Specializes in network reconnaissance
    - Only has nmap_recon tools
    - Finds all hosts and services

  Analyst Agent:
    - Specializes in vulnerability analysis
    - Has agent (AI) and file_tools
    - Interprets scan results
    - Identifies security issues

  Reporter Agent:
    - Specializes in documentation
    - Has file_tools only
    - Creates formatted reports
    - Summarizes findings
```

---

## When to Use Teams

### Use Teams For:

✅ **Multi-phase workflows** - Tasks requiring different skills at each phase
```
Example: "Security assessment"
  Phase 1: Scanning (Scanner)
  Phase 2: Analysis (Analyst)
  Phase 3: Reporting (Reporter)
```

✅ **Specialized perspectives** - Tasks benefiting from different viewpoints
```
Example: "Code review"
  Perspective 1: Security expert
  Perspective 2: Performance expert
  Perspective 3: Style/readability expert
```

✅ **Tool separation** - When different phases need different tools
```
Example: "Penetration test"
  Phase 1: Reconnaissance (nmap_recon)
  Phase 2: Exploitation (kali tools)
  Phase 3: Documentation (file_tools)
```

### Use Single Agent For:

❌ **Simple tasks** - Single-phase tasks
```
Example: "Read a file and summarize it"
```

❌ **Homogeneous tasks** - Same type of work throughout
```
Example: "Review code quality"
```

❌ **Quick queries** - Conversational Q&A
```
Example: "What's the status of this issue?"
```

---

## How Teams Work

### Execution Flow

Teams execute agents in **sequence**, with each agent contributing to the task:

```
User Task: "Scan 192.168.1.0/24 and create security report"

1. User submits task
   ↓
2. Team receives task
   ↓
3. Scanner Agent executes
   - Scans network with nmap_recon
   - Finds 10 active hosts
   - Returns: List of hosts with open ports
   ↓
4. Analyst Agent executes
   - Receives scanner results
   - Analyzes vulnerabilities
   - Returns: Security issues with severity ratings
   ↓
5. Reporter Agent executes
   - Receives analysis results
   - Creates formatted report
   - Writes to /workspace/security_report.md
   - Returns: "Report saved"
   ↓
6. Team completes
   - User sees all agent responses
   - Final report available
```

### Context Passing

Each agent sees:
- **Original user task**
- **Previous agents' responses**
- **Shared workspace** (/workspace)

```json
// Scanner Agent context
{
  "task": "Scan 192.168.1.0/24 and create security report",
  "previous_responses": []
}

// Analyst Agent context
{
  "task": "Scan 192.168.1.0/24 and create security report",
  "previous_responses": [
    {
      "agent": "scanner",
      "response": "Found 10 hosts with following services..."
    }
  ]
}

// Reporter Agent context
{
  "task": "Scan 192.168.1.0/24 and create security report",
  "previous_responses": [
    {
      "agent": "scanner",
      "response": "Found 10 hosts..."
    },
    {
      "agent": "analyst",
      "response": "Identified 3 critical vulnerabilities..."
    }
  ]
}
```

---

## Using Pre-Built Teams

### Available Teams

#### 1. Security Analysis Team

**Purpose**: Complete security assessment workflow

**Team Structure**:
```json
{
  "name": "security_analysis_team",
  "agents": [
    {
      "role": "scanner",
      "description": "Network reconnaissance",
      "mcp_servers": ["nmap_recon"]
    },
    {
      "role": "analyst",
      "description": "Vulnerability analysis",
      "mcp_servers": ["agent", "file_tools"]
    },
    {
      "role": "reporter",
      "description": "Report generation",
      "mcp_servers": ["file_tools"]
    }
  ]
}
```

**Example Tasks**:
```
"Scan 192.168.50.0/24 and create a security report"
"Perform a security assessment of 10.0.1.0/24"
"Check network security and document findings"
```

**Expected Output**:
- Scanner: List of active hosts and services
- Analyst: Vulnerability assessment with priorities
- Reporter: Formatted security report in /workspace/

#### 2. Code Review Team

**Purpose**: Comprehensive code quality assessment

**Team Structure**:
```json
{
  "name": "code_review_team",
  "agents": [
    {
      "role": "analyzer",
      "description": "Code quality analysis",
      "mcp_servers": ["file_tools", "agent"]
    },
    {
      "role": "documenter",
      "description": "Documentation creation",
      "mcp_servers": ["file_tools", "agent"]
    }
  ]
}
```

**Example Tasks**:
```
"Review the code in /workspace/app.py"
"Analyze all Python files in /workspace"
"Check code quality and create improvement plan"
```

**Expected Output**:
- Analyzer: Security, quality, and style issues
- Documenter: Detailed review report with recommendations

### Using Teams in Playground

**Step 1**: Navigate to Playground
```
http://localhost:3000 → Playground
```

**Step 2**: Select Team
```
Click dropdown → Select "Security Analysis Team"
```

**Step 3**: Give Task
```
You: "Scan 192.168.50.0/24 and create security report"
```

**Step 4**: Observe Execution
```
Scanner Agent: "I'll scan the network..."
[Executes network scan]
Scanner Agent: "Found 5 active hosts with these services..."

Analyst Agent: "I'll analyze these findings..."
[Analyzes results]
Analyst Agent: "Identified 2 critical issues..."

Reporter Agent: "I'll create the report..."
[Writes file]
Reporter Agent: "Report saved to /workspace/security_report.md"
```

---

## Creating Custom Teams

### Team Definition Structure

Create a JSON file in `agent-teams/`:

```json
{
  "name": "my_team",
  "version": "0.1.0",
  "description": "Brief description of team purpose",
  "agents": [
    {
      "role": "role_name",
      "agent_id": "agent_definition_id",
      "description": "What this role does",
      "persona": "Role-specific instructions",
      "mcp_servers": ["list", "of", "mcps"],
      "config": {
        "model": "claude-sonnet-4-5",
        "temperature": 0.7,
        "max_tokens": 4096
      }
    }
  ],
  "metadata": {
    "author": "Your Name",
    "created": "2025-12-08",
    "tags": ["category", "type"]
  }
}
```

### Step-by-Step: Create a Research Team

Let's create a team that researches topics and creates documentation.

**1. Create Team File**:

```bash
touch agent-teams/research_team.json
```

**2. Define Team**:

```json
{
  "name": "research_team",
  "version": "0.1.0",
  "description": "Research topics and create comprehensive documentation",
  "agents": [
    {
      "role": "researcher",
      "agent_id": "research_assistant",
      "description": "Gathers information on topics",
      "persona": "You are a research specialist. Your role is to:\n1. Research the given topic thoroughly\n2. Gather key information and insights\n3. Identify important concepts and relationships\n4. Provide a comprehensive summary\n\nFocus on accuracy and relevance.",
      "mcp_servers": ["agent", "file_tools"],
      "config": {
        "model": "claude-sonnet-4-5",
        "temperature": 0.6,
        "max_tokens": 8192
      }
    },
    {
      "role": "synthesizer",
      "agent_id": "research_assistant",
      "description": "Synthesizes information into insights",
      "persona": "You are a synthesis specialist. Your role is to:\n1. Review the researcher's findings\n2. Identify patterns and connections\n3. Create structured insights\n4. Highlight key takeaways\n\nProvide clear, actionable insights.",
      "mcp_servers": ["agent"],
      "config": {
        "model": "claude-opus-4-5",
        "temperature": 0.7,
        "max_tokens": 8192
      }
    },
    {
      "role": "documenter",
      "agent_id": "research_assistant",
      "description": "Creates formatted documentation",
      "persona": "You are a documentation specialist. Your role is to:\n1. Take research findings and insights\n2. Create well-structured markdown documentation\n3. Include sections: Overview, Key Concepts, Details, References\n4. Write clearly and professionally\n\nCreate comprehensive, easy-to-read documentation.",
      "mcp_servers": ["file_tools", "agent"],
      "config": {
        "model": "claude-sonnet-4-5",
        "temperature": 0.5,
        "max_tokens": 16384
      }
    }
  ],
  "metadata": {
    "author": "ADCL Team",
    "created": "2025-12-08",
    "tags": ["research", "documentation", "analysis"]
  }
}
```

**3. Restart Platform**:

```bash
./clean-restart.sh
```

**4. Use Team**:

```
Go to Playground → Select "Research Team"
Task: "Research Kubernetes security best practices"

Expected flow:
1. Researcher: Gathers information on K8s security
2. Synthesizer: Creates structured insights
3. Documenter: Writes comprehensive guide to /workspace/
```

---

## Team Configuration

### Role Design

Each role should have:

**1. Clear Responsibility**
```json
{
  "role": "scanner",
  "description": "Performs network reconnaissance only"
}
```

**2. Specific Persona**
```json
{
  "persona": "You are a network scanner. Your ONLY job is to:\n1. Scan the network with nmap_recon tools\n2. Report findings clearly\n3. Do NOT analyze or interpret\nLeave analysis to the analyst role."
}
```

**3. Appropriate Tools**
```json
{
  "mcp_servers": ["nmap_recon"]  // Only what this role needs
}
```

**4. Suitable Configuration**
```json
{
  "config": {
    "model": "claude-sonnet-4-5",     // Fast for simple tasks
    "temperature": 0.3,               // Low for deterministic
    "max_tokens": 2048                // Reasonable limit
  }
}
```

### Agent Order

Order matters! Agents execute sequentially:

**Good Order**:
```json
{
  "agents": [
    {"role": "scanner"},      // 1. Gather data
    {"role": "analyst"},      // 2. Analyze data
    {"role": "reporter"}      // 3. Document findings
  ]
}
```

**Bad Order**:
```json
{
  "agents": [
    {"role": "reporter"},     // Can't report without data!
    {"role": "scanner"},      // Too late
    {"role": "analyst"}       // Too late
  ]
}
```

### Model Selection per Role

Choose models based on role complexity:

```json
{
  "agents": [
    {
      "role": "scanner",
      "config": {
        "model": "claude-sonnet-4-5"  // Fast, efficient for simple tasks
      }
    },
    {
      "role": "analyst",
      "config": {
        "model": "claude-opus-4-5"    // Powerful for complex analysis
      }
    },
    {
      "role": "reporter",
      "config": {
        "model": "claude-sonnet-4-5"  // Good for structured writing
      }
    }
  ]
}
```

---

## Best Practices

### 1. Single Responsibility per Role

**Do**:
```json
{
  "role": "scanner",
  "persona": "You ONLY scan networks. Report results. Do NOT analyze."
}
```

**Don't**:
```json
{
  "role": "everything",
  "persona": "You scan, analyze, report, and do whatever else needed."
}
```

### 2. Clear Handoffs

**Do**:
```json
{
  "role": "analyst",
  "persona": "Review the scanner's findings (in previous_responses). Analyze vulnerabilities..."
}
```

**Don't**:
```json
{
  "role": "analyst",
  "persona": "Analyze something."
}
```

### 3. Minimal MCP Access

**Do**:
```json
// Each role only gets what it needs
{"role": "scanner", "mcp_servers": ["nmap_recon"]}
{"role": "analyst", "mcp_servers": ["agent"]}
{"role": "reporter", "mcp_servers": ["file_tools"]}
```

**Don't**:
```json
// Everyone gets everything
{"role": "scanner", "mcp_servers": ["nmap_recon", "agent", "file_tools", "kali"]}
```

### 4. Proper Team Size

**Good Sizes**:
- **2-3 agents**: Most common, manageable
- **4-5 agents**: Complex workflows
- **6+ agents**: Rare, only for very complex tasks

**Example 3-Agent Team**:
```
1. Data Gatherer
2. Data Processor
3. Output Creator
```

### 5. Shared Workspace

Use `/workspace` for inter-agent file sharing:

```
Scanner Agent:
  - Writes scan results to /workspace/scan_results.json

Analyst Agent:
  - Reads /workspace/scan_results.json
  - Writes analysis to /workspace/analysis.json

Reporter Agent:
  - Reads /workspace/analysis.json
  - Creates /workspace/final_report.md
```

---

## Troubleshooting

### Team Not Responding

**Symptom**: Team starts but agents don't execute

**Possible Causes**:
1. Agent definition missing
2. MCP server unavailable
3. API key invalid

**Solution**:
```bash
# Check agent definitions exist
ls agent-definitions/

# Check MCP servers running
docker-compose ps | grep mcp

# View logs
docker-compose logs orchestrator
```

### Agents Ignoring Previous Responses

**Symptom**: Each agent starts from scratch

**Possible Causes**:
1. Persona doesn't reference previous responses
2. Agents not configured to read context

**Solution**:
Update personas to explicitly reference context:
```json
{
  "persona": "Review the previous agent's findings (in previous_responses). Then analyze..."
}
```

### One Agent Doing Everything

**Symptom**: First agent completes entire task

**Possible Causes**:
1. Role not clearly constrained
2. Agent has access to all tools
3. Persona too general

**Solution**:
```json
{
  "role": "scanner",
  "persona": "You ONLY scan networks. Your job ENDS after reporting scan results. Do NOT analyze or create reports - other team members will do that.",
  "mcp_servers": ["nmap_recon"]  // Remove extra tools
}
```

### Team Takes Too Long

**Symptom**: Team execution very slow

**Possible Causes**:
1. Too many agents
2. High max_iterations per agent
3. Using Opus for simple tasks

**Solution**:
```json
{
  "agents": [
    {
      "role": "scanner",
      "config": {
        "model": "claude-sonnet-4-5",  // Use faster model
        "max_iterations": 5,            // Lower limit
        "max_tokens": 2048              // Reduce tokens
      }
    }
  ]
}
```

---

## Advanced Patterns

### Parallel Experts

Multiple agents analyze from different perspectives:

```json
{
  "name": "code_review_team",
  "agents": [
    {"role": "security_expert", "persona": "Focus on security only"},
    {"role": "performance_expert", "persona": "Focus on performance only"},
    {"role": "style_expert", "persona": "Focus on code style only"},
    {"role": "synthesizer", "persona": "Combine all reviews"}
  ]
}
```

### Validation Chain

Each agent validates the previous:

```json
{
  "name": "research_validation_team",
  "agents": [
    {"role": "researcher", "persona": "Research topic"},
    {"role": "fact_checker", "persona": "Verify researcher's facts"},
    {"role": "editor", "persona": "Improve fact-checked content"},
    {"role": "publisher", "persona": "Format and publish"}
  ]
}
```

### Branching Logic (via File Sharing)

Agents can coordinate via shared files:

```
Scanner writes: /workspace/scan_critical.json (if critical issues found)

Analyst checks:
  - If /workspace/scan_critical.json exists → deep analysis
  - Else → standard analysis
```

---

## Next Steps

- **[Agents Guide](Agents-Guide)** - Create agents to use in teams
- **[Workflows Guide](Workflows-Guide)** - Alternative to teams for deterministic flows
- **[MCP Servers Guide](MCP-Servers-Guide)** - Create tools for team agents
- **[Registry Guide](Registry-Guide)** - Install pre-built teams

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
