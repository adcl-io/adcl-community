# Frequently Asked Questions (FAQ)

Common questions about ADCL platform.

---

## Table of Contents

1. [General Questions](#general-questions)
2. [Technical Questions](#technical-questions)
3. [Feature Questions](#feature-questions)
4. [Security Questions](#security-questions)
5. [Cost & Pricing Questions](#cost--pricing-questions)
6. [Comparison Questions](#comparison-questions)

---

## General Questions

### What is ADCL?

**ADCL (Autonomous Distributed Command Loop)** is an open-source platform for building and orchestrating autonomous AI agent systems. It enables agents to independently solve complex tasks by reasoning, acting on tools, and collaborating in teams.

**Key Features**:
- Autonomous AI agents with ReAct pattern
- Multi-agent teams for complex workflows
- Visual workflow builder
- MCP-based tool extensibility
- Package registry for teams/triggers
- Webhook and schedule-based automation

---

### What does "autonomous" mean?

**Autonomous agents**:
- Make their own decisions about which tools to use
- Adapt their approach based on results
- Chain multiple tool calls without pre-programming
- Reason through problems dynamically

**Example**:
```
Traditional Automation: "Run scan, then parse, then report"
(Fixed sequence, no adaptation)

Autonomous Agent: "Create security report"
→ Agent decides: Scan network
→ Sees interesting ports, decides: Probe deeper
→ Finds vulnerability, decides: Research CVE
→ Decides: Write comprehensive report
```

---

### Is ADCL free?

**ADCL Platform**: Yes, 100% open source (MIT License)
- Free to use, modify, and distribute
- No platform fees
- No user limits

**Claude API**: You pay Anthropic directly
- Pay only for API usage
- Pricing: https://www.anthropic.com/pricing
- Approximately: $3 per million input tokens, $15 per million output tokens

**Total Cost**: Platform (free) + Claude API usage (pay-as-you-go)

---

### What AI models does ADCL support?

**Currently Supported**:
- **Anthropic Claude**: Sonnet 4.5, Opus 4.5 (recommended)
- **AWS Bedrock**: Claude models via Bedrock
- **OpenAI-Compatible**: Any endpoint with OpenAI-compatible API

**Coming Soon**:
- OpenAI GPT-4
- Google Gemini
- Local models (Ollama, LM Studio)

---

### Can I run ADCL offline?

**Current Version**: No, requires internet for:
- Claude API calls (agents need AI reasoning)
- Package downloads from registry

**Future Plans**:
- Local model support (Ollama, LM Studio)
- Offline package caching
- Air-gapped deployment mode

---

### What is MCP?

**MCP (Model Context Protocol)** is a standard for connecting AI agents to tools.

**How it works**:
```
Agent (AI reasoning) ─MCP Protocol─> MCP Server (tool implementation) ─> External System
```

**Benefits**:
- **Modular**: Each tool is independent
- **Reusable**: One tool, many agents
- **Extensible**: Add new tools without changing agents
- **Secure**: Tools run in isolated containers

**Learn more**: https://modelcontextprotocol.org

---

## Technical Questions

### What are the system requirements?

**Minimum**:
- **OS**: Linux, macOS, Windows (WSL2)
- **Docker**: 20.10+
- **Memory**: 4GB RAM
- **Disk**: 10GB free
- **CPU**: 2 cores

**Recommended**:
- **Memory**: 8GB+ RAM
- **Disk**: 20GB+ free (for logs, history)
- **CPU**: 4+ cores
- **Network**: Broadband internet

---

### Does ADCL require a GPU?

**No.** ADCL uses Claude API for AI reasoning (runs on Anthropic's servers), so GPU is not needed locally.

**GPU only needed for**:
- Local model inference (future feature)
- Custom ML workloads in MCP servers

---

### Can I run ADCL on a Raspberry Pi?

**Theoretically yes**, but not recommended:
- ARM architecture supported by Docker
- But: Limited memory (4GB-8GB)
- Slow performance with many containers

**Better options**:
- Cloud VM (AWS, GCP, Azure)
- Local server with 8GB+ RAM
- Desktop/laptop

---

### How do I backup my data?

**Important directories**:
```bash
# Backup script
tar -czf adcl-backup-$(date +%Y%m%d).tar.gz \
  volumes/ \
  workspace/ \
  agent-definitions/ \
  agent-teams/ \
  workflows/ \
  .env
```

**What to backup**:
- `volumes/`: User data, history, databases
- `workspace/`: Agent outputs, reports
- `agent-definitions/`: Custom agents
- `agent-teams/`: Custom teams
- `workflows/`: Custom workflows
- `.env`: API keys and configuration

---

### How do I upgrade ADCL?

```bash
# 1. Backup data
./backup.sh

# 2. Pull latest code
git pull origin main

# 3. Rebuild containers
./clean-restart.sh

# 4. Verify version
curl http://localhost:8000/version
```

**Note**: Check CHANGELOG.md for breaking changes.

---

### Can I use ADCL in production?

**Current Status**: Community Edition (v0.1.x)
- **Good for**: Development, testing, internal tools
- **Not yet for**: Mission-critical production systems

**Missing for Production**:
- User authentication
- Multi-tenancy
- High availability / clustering
- Enterprise support

**Production-Ready Features** (coming in v1.0):
- JWT authentication
- Role-based access control
- Audit logging
- HA deployment
- Enterprise support

---

## Feature Questions

### What's the difference between Agents, Teams, and Workflows?

| Feature | Agent | Team | Workflow |
|---------|-------|------|----------|
| **Type** | Autonomous | Multi-agent collaboration | Deterministic |
| **Decision** | Dynamic | Partially dynamic | Fixed sequence |
| **Use Case** | Problem-solving | Complex multi-phase tasks | Repeatable processes |

**Example**:

**Agent**: "Figure out why the service is down"
- Agent investigates logs, checks network, tests endpoints
- Makes decisions based on findings

**Team**: "Perform complete security assessment"
- Scanner: Finds hosts
- Analyst: Identifies vulnerabilities
- Reporter: Creates report

**Workflow**: "Deploy and test"
- Step 1: Build code
- Step 2: Run tests
- Step 3: Deploy
- Step 4: Smoke test
- (Always same sequence)

---

### Can agents communicate with each other?

**Yes, via teams**:
- Agents execute in sequence
- Each sees previous agents' responses
- Can share files via `/workspace`

**Example**:
```
Scanner Agent: Writes scan_results.json to /workspace
Analyst Agent: Reads scan_results.json, analyzes
Reporter Agent: Reads analysis, creates report
```

**No direct messaging** (not like Slack):
- Agents don't "chat" with each other
- Communication is via sequential execution + shared files

---

### Can I create custom MCP servers?

**Yes!** MCP servers are easy to create:

```python
# Simple MCP server
from fastapi import FastAPI

app = FastAPI()

@app.post("/call_tool")
async def call_tool(request):
    if request.tool == "my_tool":
        # Do something
        return {"result": "success"}
```

**See**: [MCP Servers Guide](MCP-Servers-Guide#creating-custom-mcp-servers)

---

### Can workflows call other workflows?

**Not directly**, but:

**Workaround 1**: Use agent in workflow
```
Workflow Node 1: agent.think("Execute workflow X")
→ Agent can trigger another workflow via API
```

**Workaround 2**: Shared trigger
```
Workflow A completes → Writes /workspace/done.txt
Workflow B: Watches for /workspace/done.txt → Starts
```

**Future Feature**: Workflow composition (v0.2.0)

---

### Can I schedule agents to run automatically?

**Yes, via schedule triggers**:

```json
{
  "type": "schedule",
  "schedule": "0 2 * * *",  // Daily at 2am
  "execution_type": "team",
  "execution_id": "security_analysis_team"
}
```

**See**: [Triggers Guide](Triggers-Guide#schedule-triggers)

---

### Does ADCL have a Python/JavaScript SDK?

**Not yet**, but:

**Python**:
```python
import httpx

# Call ADCL API
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/agents/run",
        json={"agent_id": "my_agent", "task": "Do something"}
    )
```

**JavaScript**:
```javascript
const response = await fetch('http://localhost:8000/agents/run', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    agent_id: 'my_agent',
    task: 'Do something'
  })
});
```

**Planned**: Official SDKs for Python, JavaScript, Go (v0.3.0)

---

## Security Questions

### Is ADCL secure?

**Security Features**:
- ✅ MCP isolation (containers)
- ✅ File access limited to /workspace
- ✅ Webhook secret verification
- ✅ HTTPS support (via reverse proxy)

**Security Limitations** (current version):
- ❌ No user authentication
- ❌ No role-based access control
- ❌ No audit logging
- ❌ No multi-tenancy isolation

**Recommendation**:
- Use in trusted networks only
- Don't expose to internet without reverse proxy + auth
- For production, wait for v1.0 with authentication

---

### Can agents access my entire filesystem?

**No.** Agents are limited to:
- `/workspace` directory (shared volume)
- MCP server working directories

**Agent cannot**:
- Access host filesystem outside /workspace
- Read ~/.ssh/, /etc/passwd, etc.
- Execute arbitrary system commands
- Break out of Docker containers

---

### Are API keys secure?

**Storage**: API keys in `.env` file (not committed to git)

**Access**: Only backend container has access

**Transmission**: API keys sent to Anthropic over HTTPS

**Best Practices**:
- Never commit `.env` to version control
- Rotate keys periodically
- Use separate keys for dev/prod
- Restrict key permissions (if provider supports)

---

### What about the Kali MCP with penetration testing tools?

**Warning**: Kali MCP is **OPTIONAL** and for:
- ✅ Authorized security testing
- ✅ CTF competitions
- ✅ Security research
- ✅ Educational purposes

**Not for**:
- ❌ Unauthorized penetration testing
- ❌ Attacking systems without permission
- ❌ Any illegal activities

**Legal Responsibility**: You are responsible for legal use.

**Recommendation**:
- Only install if needed
- Use in isolated lab networks
- Obtain written authorization for any testing
- Document all activities

---

## Cost & Pricing Questions

### How much does ADCL cost to run?

**ADCL Platform**: Free (open source)

**Claude API Costs** (approximate):

**Sonnet 4.5**:
- Input: $3 per million tokens (~$0.003 per 1000 tokens)
- Output: $15 per million tokens (~$0.015 per 1000 tokens)

**Typical Usage**:
```
Simple task (1-2 tool calls):
- ~2,000 tokens input, ~500 tokens output
- Cost: ~$0.01

Complex task (10+ tool calls):
- ~10,000 tokens input, ~3,000 tokens output
- Cost: ~$0.07

Daily security scan (scheduled):
- ~5,000 tokens per scan
- Cost: ~30 scans/month = ~$5/month
```

**See**: https://www.anthropic.com/pricing

---

### How can I reduce costs?

**1. Use Sonnet instead of Opus**:
```json
{"model": "claude-sonnet-4-5"}  // 5x cheaper than Opus
```

**2. Reduce max_tokens**:
```json
{"max_tokens": 2048}  // Default is 4096
```

**3. Lower max_iterations**:
```json
{"max_iterations": 5}  // Fewer tool calls
```

**4. Optimize personas**:
```json
{"persona": "Be concise. Use minimum tool calls."}
```

**5. Cache common queries** (if possible)

**6. Use workflows instead of agents** (for deterministic tasks):
- Workflows don't use AI for every step
- Only use agent nodes where needed

---

### Is there a free tier?

**Anthropic** offers:
- Free trial credits (check Anthropic Console)
- Usage-based pricing (no monthly minimum)

**No ADCL fees** - platform is free.

---

## Comparison Questions

### ADCL vs. LangChain?

| Feature | ADCL | LangChain |
|---------|------|-----------|
| **Type** | Full platform | Python library |
| **UI** | Built-in web UI | No UI (code only) |
| **Deployment** | Docker containers | Python runtime |
| **Agent System** | ReAct with MCP | Multiple patterns |
| **Best For** | Complete solution | Custom integrations |

**Use ADCL**: Want ready-to-use platform with UI
**Use LangChain**: Building custom Python application

---

### ADCL vs. AutoGPT?

| Feature | ADCL | AutoGPT |
|---------|------|----------|
| **Focus** | Enterprise workflows | Personal assistant |
| **Tools** | MCP servers (modular) | Built-in + plugins |
| **Teams** | Multi-agent collaboration | Single agent |
| **Workflows** | Visual builder | No workflows |
| **Best For** | Business automation | Personal tasks |

---

### ADCL vs. n8n / Zapier?

| Feature | ADCL | n8n / Zapier |
|---------|------|--------------|
| **Automation** | AI-driven | Rule-based |
| **Flexibility** | Autonomous agents | Fixed workflows |
| **Complexity** | Handles ambiguity | Requires exact rules |
| **Best For** | Dynamic tasks | Deterministic integration |

**Example**:

**ADCL**: "Analyze this codebase and create security report"
- Agent figures out what to check
- Adapts based on findings
- Creates custom report

**n8n/Zapier**: "When GitHub push, run tests, post to Slack"
- Fixed sequence
- Same every time
- No decision-making

---

### ADCL vs. Building from Scratch?

**ADCL Advantages**:
- ✅ Pre-built UI
- ✅ Agent orchestration
- ✅ MCP ecosystem
- ✅ Package registry
- ✅ Tested patterns
- ✅ Active development

**Building from Scratch**:
- ❌ Weeks/months of development
- ❌ Build every component
- ❌ Maintain infrastructure
- ❌ Create agent patterns
- ✅ Ultimate flexibility

**Recommendation**: Start with ADCL, customize as needed.

---

## Still Have Questions?

### Documentation

- [Getting Started](Getting-Started)
- [Platform Overview](Platform-Overview)
- [Troubleshooting](Troubleshooting)

### Community

- **GitHub Issues**: https://github.com/adcl-io/adcl-community/issues
- **GitHub Discussions**: https://github.com/adcl-io/adcl-community/discussions

### Contributing

- **Contributing Guide**: CONTRIBUTING.md
- **Code of Conduct**: CODE_OF_CONDUCT.md

---

**Question not answered?** [Ask on GitHub Discussions](https://github.com/adcl-io/adcl-community/discussions)
