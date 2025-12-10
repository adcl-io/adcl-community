# ADCL Platform Documentation

Welcome to the **ADCL (Autonomous Distributed Command Loop)** documentation. ADCL is an open-source, MCP-based AI agent orchestration platform that enables you to build, deploy, and manage autonomous AI agents and multi-agent teams for complex tasks.

**Current Version**: 0.1.26 (Community Edition)

---

## Quick Links

### Getting Started
- [Platform Overview](Platform-Overview) - Understand what ADCL is and how it works
- [Getting Started Guide](Getting-Started) - Installation and first steps
- [Configuration Guide](Configuration-Guide) - Set up your environment

### Core Features
- [Agents Guide](Agents-Guide) - Create and use autonomous AI agents
- [Teams Guide](Teams-Guide) - Build multi-agent collaborative systems
- [Workflows Guide](Workflows-Guide) - Visual workflow builder
- [MCP Servers Guide](MCP-Servers-Guide) - Understanding tool servers
- [Triggers Guide](Triggers-Guide) - Automate with webhooks and schedules
- [Registry Guide](Registry-Guide) - Package management system

### Reference
- [Configuration Guide](Configuration-Guide) - Environment variables and settings
- [Troubleshooting](Troubleshooting) - Common issues and solutions
- [FAQ](FAQ) - Frequently asked questions

---

## What is ADCL?

ADCL is a complete ecosystem for building autonomous AI agent systems that can:

✅ **Execute Complex Tasks Autonomously** - Agents chain tool calls using the ReAct pattern (Reason → Act → Observe)

✅ **Collaborate in Teams** - Multiple agents with different specializations work together

✅ **Build Visual Workflows** - Drag-and-drop node-based workflow composition

✅ **Automate with Triggers** - Schedule tasks or respond to webhooks

✅ **Use MCP Tool Servers** - Extensible tool ecosystem via Model Context Protocol

✅ **Follow Unix Philosophy** - Text-based configuration, composable tools, no hidden state

---

## Key Capabilities

### Autonomous AI Agents
Pre-built agents ready to use:
- **Security Analyst** - Network reconnaissance and vulnerability assessment
- **Code Reviewer** - Code quality, security, and best practices analysis
- **Research Assistant** - Information gathering and synthesis
- **Linear Issue Analyst** - Analyzes Linear issues and creates action plans

### Multi-Agent Teams
Collaborate multiple agents on complex tasks:
- **Security Analysis Team** - Scanner + Analyst + Reporter
- **Code Review Team** - Analyzer + Documentation Writer

### MCP Tool Servers
Extend agent capabilities with tools:
- **Agent MCP** - AI reasoning via Claude API
- **File Tools MCP** - File system operations
- **Nmap Recon MCP** - Network security scanning
- **Kali Linux MCP** - Penetration testing tools (optional)
- **History MCP** - Conversation persistence
- **Linear MCP** - Issue tracking integration

### Visual Workflows
Create deterministic processes:
- Drag-and-drop node editor
- Connect MCP servers with data flow
- Real-time execution visualization
- Parameter resolution from previous steps

### Package Registry
Install teams, triggers, and MCPs:
- Yum/apt-style package management
- One-click installation
- Version tracking
- Multi-registry support

---

## Platform Architecture

ADCL follows a three-tier architecture:

**Tier 1: Frontend ↔ Backend API**
- React UI with real-time WebSocket updates
- REST API for all operations
- Ports: Frontend (3000), Backend (8000)

**Tier 2: Backend Services**
- FastAPI orchestrator
- Docker Manager for container lifecycle
- File-based configuration (JSON/YAML)

**Tier 3: AI Agents ↔ MCP Tool Servers**
- Model Context Protocol for agent-tool communication
- Each MCP runs in isolated Docker container
- Agents autonomously call tools to complete tasks

---

## Use Cases

### Security Assessment
```
User: "Scan 192.168.50.0/24 and create security report"
→ Agent uses Nmap MCP to scan network
→ Analyzes results with AI reasoning
→ Writes formatted report to file
```

### Code Review
```
User: "Review the code in /workspace/app.py"
→ Agent reads file with File Tools MCP
→ Analyzes quality, security, best practices
→ Writes review with recommendations
```

### Automated Workflow
```
Webhook receives deployment notification
→ Triggers workflow execution
→ Runs test suite
→ Scans for vulnerabilities
→ Posts results to Linear
```

---

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS (Intel/Apple Silicon), Windows (WSL2)
- **Docker**: 20.10+ with Docker Compose
- **Memory**: 4GB RAM minimum, 8GB+ recommended
- **Disk**: 10GB free space
- **Network**: Internet connection for API access

### Required API Keys
- **Anthropic API Key** (required) - For Claude AI models
- **Linear API Key** (optional) - For Linear integration

---

## Getting Help

- **Documentation**: You're reading it!
- **GitHub Issues**: [Report bugs or request features](https://github.com/adcl-io/adcl-community/issues)
- **Community**: Join discussions on GitHub Discussions

---

## Philosophy

ADCL follows Unix philosophy:

1. **Do one thing well** - Each MCP has a single responsibility
2. **Text streams** - All config and data in plain text (JSON/YAML)
3. **Composability** - Tools compose into workflows and teams
4. **No hidden state** - Everything inspectable via `cat`, `grep`, `jq`
5. **Configuration as code** - All settings in version-controlled files

---

## Next Steps

1. [Install ADCL](Getting-Started#installation)
2. [Understand Core Concepts](Platform-Overview)
3. [Chat with Your First Agent](Agents-Guide#using-agents-in-playground)
4. [Create a Workflow](Workflows-Guide#creating-your-first-workflow)
5. [Install a Package from Registry](Registry-Guide#installing-packages)

---

**Ready to get started?** → [Installation Guide](Getting-Started)
