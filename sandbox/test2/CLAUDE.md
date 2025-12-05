# Project Context for Claude Code

## What We're Building
Full AI Red Team platform with persona-based autonomous agents. Each campaign deploys a customizable team of specialist agents (recon, exploitation, post-exploit, reporting) that communicate via MCP (Model Context Protocol). Agents use LLMs for reasoning and call specialized MCP tool servers for actual security operations.

## Tech Stack
- **Backend**: FastAPI (async, WebSocket support)
- **Agent Runtime**: Python with MCP client library
- **Queue System**: Redis (job queue + pub/sub for live updates)
- **Database**: SQLite (campaigns, findings, agent memory)
- **Frontend**: React + WebSocket (live dashboard)
- **Containerization**: Docker (isolated MCP servers)

## Core Architectural Pattern

**Infrastructure**: Actor Model (Erlang/Akka-style)
- Isolated processes communicating via messages
- Fault tolerance through supervision trees
- Concurrent execution by default

**Behavior**: Persona Configuration (LLM-native)
- Agents configured via prompts + tool access
- Same infrastructure, infinite specializations
- User-customizable team compositions

**Result**: Best of both worlds
- Robust, scalable infrastructure (actor model)
- Flexible, configurable behavior (personas)
- Add new capabilities without changing core code

## Architecture Overview

### API Server (`api/main.py`)
```
POST   /campaigns          - Start new scan campaign
GET    /campaigns/{id}     - Campaign status
WS     /campaigns/{id}/ws  - Live update stream
GET    /agents             - Available agent list
GET    /findings           - Vulnerability results
```

### Agent System (`agents/`)

**Hybrid Architecture**: Actor-model infrastructure + Persona-based behavior

**Actor-Model Infrastructure:**
- Each agent instance = isolated worker process
- Redis queue for message passing (task distribution)
- Supervisor process monitors and restarts failed agents
- No shared state between agents
- Concurrent execution with fault tolerance

**Persona-Based Behavior:**
- Same `BaseAgent` class, different configurations
- Personas defined by: system prompt + tool access + parameters
- Campaign specifies team composition dynamically
- Easy to experiment with different agent "personalities"

**BaseAgent Class** (`agents/base.py`):
```python
class BaseAgent:
    """Actor-like worker with persona configuration"""
    def __init__(self, agent_id, persona_config):
        self.id = agent_id
        self.persona = persona_config
        self.llm = self._init_llm(persona_config['model'])
        self.mcp_clients = self._init_mcp(persona_config['mcp_servers'])
        self.memory = AgentMemory(agent_id)

    async def run(self):
        """Main loop - receives tasks from Redis queue"""
        while task := await self.get_next_task():
            await self._execute_with_persona(task)
```

**Available Personas:**

*Recon Phase:*
- `methodical_recon` - Thorough, slow, maps everything
- `fast_recon` - Quick service discovery for time-limited engagements
- `osint_specialist` - Public information gathering

*Red Team Phase:*
- `web_exploit_specialist` - OWASP Top 10, web application focused
- `network_exploit` - Known CVEs, Metasploit modules, service exploitation
- `social_engineer` - Phishing, credential harvesting (if in scope)
- `post_exploit` - Persistence, lateral movement, privilege escalation
- `exfil_specialist` - Data extraction and cleanup

*Support:*
- `report_writer` - Synthesizes findings into deliverable report
- `coordinator` - Manages agent handoffs and workflow

### MCP Tool Servers (`mcp_servers/`)

Each server runs in isolated Docker container with MCP protocol interface. Agents communicate with servers via MCP client, never execute tools directly.

**Recon MCP Servers:**
- `nmap_server/` (port 6000)
  - Tools: port_scan, service_detection, os_detection, version_enum
- `dns_server/` (port 6001)
  - Tools: subdomain_enum, zone_transfer, reverse_lookup
- `osint_server/` (port 6002)
  - Tools: whois_lookup, certificate_search, public_db_search

**Red Team MCP Servers:**
- `web_tools_server/` (port 6100)
  - Tools: sqli_test, xss_test, xxe_test, directory_brute, auth_bypass
- `metasploit_server/` (port 6101)
  - Tools: exploit_search, exploit_execute, payload_generate, session_manage
- `exploit_db_server/` (port 6102)
  - Tools: cve_search, exploit_download, exploit_modify
- `post_exploit_server/` (port 6103)
  - Tools: persistence_install, lateral_move, privilege_escalate, credential_dump
- `payload_server/` (port 6104)
  - Tools: payload_generate, obfuscate, deliver, c2_setup

**Support MCP Servers:**
- `report_server/` (port 6200)
  - Tools: finding_template, evidence_format, report_generate

### Campaign Orchestrator (`api/orchestrator.py`)

**Workflow Modes:**

*Sequential (safer, simpler - MVP1):*
1. Spawn recon agents based on campaign config
2. Wait for recon phase completion
3. Analyze attack surface from findings
4. Spawn appropriate red team agents
5. Monitor exploitation attempts
6. Spawn report agent on completion
7. Stream all results via WebSocket to dashboard

*Parallel (faster - post-MVP1):*
1. Spawn recon agents
2. As services discovered → immediately queue exploit agents
3. Exploit agents start attacking while recon continues
4. Continuous feedback loop

**Agent Supervision:**
- Monitor agent health (heartbeat checks)
- Restart crashed agents with state recovery
- Kill runaway agents (timeout enforcement)
- Load balancing across agent pool

### Data Flow
```
User Input → API → Campaign Orchestrator → Redis Queue →
Agent Pool → MCP Tool Servers → Findings DB → WebSocket → Dashboard
```

## File Structure
```
project/
├── api/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic data models
│   ├── orchestrator.py   # Campaign orchestration logic
│   └── supervisor.py     # Agent supervision (actor model)
├── agents/
│   ├── base.py          # BaseAgent class (actor + persona)
│   ├── memory.py        # AgentMemory for state management
│   └── personas.py      # Persona configurations
├── mcp_servers/
│   ├── recon/
│   │   ├── nmap/
│   │   ├── dns/
│   │   └── osint/
│   ├── redteam/
│   │   ├── web_tools/
│   │   ├── metasploit/
│   │   ├── exploit_db/
│   │   ├── post_exploit/
│   │   └── payload/
│   ├── support/
│   │   └── report/
│   └── base_mcp_server.py  # Base MCP server class
├── dashboard/
│   ├── src/
│   └── package.json
├── docker-compose.yml   # Local dev environment
├── config.yaml         # MCP registry
└── personas/           # Persona prompt templates
    ├── recon/
    ├── redteam/
    └── support/
```

## Key Design Decisions

1. **Persona-based agents over rigid agent types**: Flexibility to configure different team compositions per campaign, easy experimentation with prompts
2. **Actor model for infrastructure**: Isolated agent processes, message passing via Redis, fault tolerance through supervision
3. **MCP for ALL tools** (recon + red team): Complete isolation, auditability, safety controls, tool versioning independence
4. **SQLite over PostgreSQL**: Simpler for MVP, no setup required, sufficient for local operations
5. **Redis for queueing + pub/sub**: Lightweight, supports real-time updates and agent message passing
6. **Monolithic API initially**: Faster iteration during MVP, can split into microservices later
7. **Sequential workflow for MVP1**: Recon → Exploit phases; parallel execution in post-MVP

## MVP1 Success Criteria

Working demo flow:
1. User enters IP range (e.g., 192.168.1.0/24)
2. Recon agent discovers active hosts and services
3. Exploit agent attempts appropriate attacks on discovered services
4. Results stream live to dashboard
5. Generate basic findings report

Technical metrics:
- Complete /24 network scan in <5 minutes
- Automatically identify and exploit 1+ vulnerabilities
- Add new agent without modifying core code
- Add new MCP tool server without system restart

## Why Hybrid Architecture? (Actor + Persona)

**Actor Model Benefits:**
- **Fault tolerance**: Agent crashes don't affect others
- **Scalability**: Spawn multiple agent instances easily
- **Concurrency**: Natural parallel execution
- **Supervision**: Monitor and restart failed agents

**Persona Benefits:**
- **Flexibility**: Same codebase, infinite configurations
- **Experimentation**: A/B test different prompts/strategies
- **User customization**: Users define their own red team composition
- **LLM-native**: Leverage strength of language models (behavior via prompts)

**Combined Result:**
- Robust infrastructure (actor model)
- Flexible behavior (persona configuration)
- Easy to add new personas without code changes
- Agents can be specialized yet share common infrastructure

## Development Approach

### MVP1 - Phase 1: Foundation (Week 1)
1. Set up FastAPI server with basic endpoints
2. Configure Redis (job queue + pub/sub) and SQLite
3. Implement WebSocket streaming for live updates
4. Create base docker-compose.yml

### MVP1 - Phase 2: First Vertical Slice - RECON (Week 2)
1. Build `BaseAgent` class with:
   - Actor-model worker (Redis task queue)
   - Persona configuration loader
   - MCP client integration
   - Basic reasoning loop

2. Implement first MCP server: `nmap_server`
   - MCP protocol implementation
   - Tools: port_scan, service_detection
   - Docker container setup

3. Create first persona: `methodical_recon`
   - Prompt template
   - Configuration (mcp_servers: [nmap])

4. Build supervisor process:
   - Spawn agents based on campaign config
   - Monitor agent health
   - Message passing via Redis

5. Test end-to-end: Campaign Config → API → Spawn Agent → MCP Call → Results → DB → WebSocket

### MVP1 - Phase 3: Add Red Team Capability (Week 3)
1. Implement `web_tools_server` MCP server
   - Basic SQLi, XSS testing tools
   - Docker container

2. Create `web_exploit_specialist` persona
   - Aggressive testing prompt
   - Configuration (mcp_servers: [web_tools])

3. Build campaign orchestrator:
   - Sequential workflow: Recon → Analyze → Spawn Exploiters
   - Agent handoff logic

4. Test: Recon discovers web service → Spawns web exploit agent → Attempts SQLi/XSS → Reports findings

### MVP1 - Phase 4: Dashboard + Reporting (Week 4)
1. React dashboard with WebSocket
   - Live campaign progress
   - Agent status display
   - Findings as they're discovered

2. Create `report_writer` persona
   - Synthesizes findings into report
   - Uses `report_server` MCP

3. End-to-end demo ready

### Post-MVP1: Expand Capabilities
1. Add more recon MCP servers (dns, osint)
2. Add more red team servers (metasploit, post_exploit)
3. Create additional personas
4. Implement parallel workflow mode
5. Agent memory and learning
6. Human-in-the-loop approval gates

## Important Notes

- This is a **defensive security tool** for authorized penetration testing
- All agents should log actions for audit trails
- MCP servers must be isolated (Docker containers)
- Focus on modularity - agents and MCP servers should be pluggable
- Prioritize live feedback - WebSocket streaming is core to UX

## Configuration Files

### config.yaml - MCP Server Registry
```yaml
mcp_servers:
  # Recon servers
  nmap:
    url: localhost:6000
    docker_image: mcp/nmap:latest
    tools: [port_scan, service_detection, os_detection, version_enum]
  dns:
    url: localhost:6001
    docker_image: mcp/dns:latest
    tools: [subdomain_enum, zone_transfer, reverse_lookup]

  # Red team servers
  web_tools:
    url: localhost:6100
    docker_image: mcp/web_tools:latest
    tools: [sqli_test, xss_test, xxe_test, directory_brute, auth_bypass]
  metasploit:
    url: localhost:6101
    docker_image: mcp/metasploit:latest
    tools: [exploit_search, exploit_execute, payload_generate, session_manage]
  post_exploit:
    url: localhost:6103
    docker_image: mcp/post_exploit:latest
    tools: [persistence_install, lateral_move, privilege_escalate, credential_dump]

  # Support servers
  report:
    url: localhost:6200
    docker_image: mcp/report:latest
    tools: [finding_template, evidence_format, report_generate]
```

### Campaign Configuration (Persona-Based)

**Example: Full red team engagement**
```yaml
campaign:
  name: "Internal Network Assessment"
  target: "192.168.1.0/24"
  mode: "sequential"  # or "parallel"

  team:
    # Recon phase
    - persona: methodical_recon
      count: 1
      config:
        system_prompt: "You are a thorough reconnaissance specialist. Map the entire network methodically. Document every service, version, and potential entry point. Take your time - accuracy over speed."
        mcp_servers: [nmap, dns]
        llm_model: claude-sonnet-4
        temperature: 0.3
        max_tasks: 10
        timeout_minutes: 30

    # Exploitation phase (spawned after recon)
    - persona: web_exploit_specialist
      count: 2  # Spawn 2 instances for parallel testing
      config:
        system_prompt: "You are an aggressive web application pentester. Focus on OWASP Top 10. Try every vulnerability quickly. Document successes and failures."
        mcp_servers: [web_tools]
        llm_model: claude-sonnet-4
        temperature: 0.7
        max_tasks: 20
        timeout_minutes: 45

    - persona: network_exploit
      count: 1
      config:
        system_prompt: "You specialize in network service exploitation. Search for known CVEs, test default credentials, attempt common exploits. Metasploit is your primary tool."
        mcp_servers: [metasploit, exploit_db]
        llm_model: claude-sonnet-4
        temperature: 0.5
        max_tasks: 15
        timeout_minutes: 60

    # Post-exploitation (spawned after successful exploit)
    - persona: post_exploit
      count: 1
      config:
        system_prompt: "You handle post-exploitation. Establish persistence, attempt lateral movement, escalate privileges. Be methodical and document every step."
        mcp_servers: [post_exploit, payload]
        llm_model: claude-sonnet-4
        temperature: 0.4
        max_tasks: 10
        timeout_minutes: 45

    # Reporting
    - persona: report_writer
      count: 1
      config:
        system_prompt: "Synthesize all findings into a professional penetration test report. Categorize by severity, provide remediation recommendations."
        mcp_servers: [report]
        llm_model: claude-sonnet-4
        temperature: 0.6
        max_tasks: 5
        timeout_minutes: 20

  safety:
    require_approval_for: [post_exploit, payload]  # Human-in-loop for destructive actions
    max_concurrent_agents: 5
    global_timeout_hours: 8
```

**Example: Fast recon-only campaign**
```yaml
campaign:
  name: "Quick Network Survey"
  target: "10.0.0.0/24"
  mode: "parallel"

  team:
    - persona: fast_recon
      count: 3
      config:
        system_prompt: "Fast network discovery. Identify live hosts and major services only. Speed over thoroughness."
        mcp_servers: [nmap]
        llm_model: claude-sonnet-4
        temperature: 0.4
        max_tasks: 5
        timeout_minutes: 10
```

### docker-compose.yml services
```yaml
services:
  api:
    build: ./api
    ports: ["8000:8000"]

  redis:
    image: redis:alpine
    ports: ["6379:6379"]

  # Recon MCP servers
  nmap_mcp:
    build: ./mcp_servers/recon/nmap
    ports: ["6000:6000"]

  dns_mcp:
    build: ./mcp_servers/recon/dns
    ports: ["6001:6001"]

  # Red team MCP servers
  web_tools_mcp:
    build: ./mcp_servers/redteam/web_tools
    ports: ["6100:6100"]

  metasploit_mcp:
    build: ./mcp_servers/redteam/metasploit
    ports: ["6101:6101"]
    privileged: true  # Metasploit may need elevated permissions

  post_exploit_mcp:
    build: ./mcp_servers/redteam/post_exploit
    ports: ["6103:6103"]

  # Support MCP servers
  report_mcp:
    build: ./mcp_servers/support/report
    ports: ["6200:6200"]
```

## Roadmap Beyond MVP1

### V2 - Advanced Red Team Capabilities
1. Additional MCP servers:
   - `metasploit_server` - Full Metasploit integration
   - `exploit_db_server` - Known exploit database
   - `post_exploit_server` - Persistence, lateral movement
   - `payload_server` - Custom payload generation

2. Additional personas:
   - `network_exploit` - Service-level exploitation
   - `post_exploit` - Post-compromise operations
   - `social_engineer` - Phishing/OSINT (if applicable)
   - `coordinator` - Multi-agent orchestration

3. Parallel workflow mode (exploit as you discover)

### V3 - Enterprise Features
1. Authentication and multi-user support
2. Multi-campaign management (run multiple engagements concurrently)
3. Cloud deployment (ECS/Kubernetes)
4. Agent memory and learning (improve over time)
5. Human-in-the-loop approval gates for destructive actions
6. Advanced reporting (PDF export, executive summaries, remediation tracking)

### V4 - AI Red Team Platform
1. Marketplace for custom personas
2. User-defined personas via UI
3. Agent collaboration (agents communicate with each other)
4. Automated penetration testing as a service
5. Integration with vulnerability management platforms
6. Continuous security validation (scheduled campaigns)
