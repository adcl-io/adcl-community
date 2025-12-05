# Architecture - MVP1

## Core Concept
Local network penetration testing with modular agents via MCP protocol.

## Tech Stack
- **Backend**: FastAPI (async, websockets built-in)
- **Agent Runtime**: Python with MCP client
- **Queue**: Redis (simple, works locally)
- **Storage**: SQLite (campaigns, findings)
- **Dashboard**: React + WebSocket for live updates

## Component Design

### API Server (main.py)
/campaigns          POST   - Start new campaign
/campaigns/{id}     GET    - Campaign status
/campaigns/{id}/ws  WS     - Live updates
/agents             GET    - List available agents
/findings           GET    - Retrieved vulnerabilities

### Agent System

Base Agent Class:
- LLM connection (Claude/GPT4)
- MCP client for tool access
- Memory store per agent
- Core reasoning loop

Agent Registry:
- recon/network_scanner.py    # nmap wrapper
- recon/service_enum.py       # version detection
- exploit/metasploit_agent.py # exploit launcher
- exploit/web_exploit.py      # OWASP top 10
- post/persistence.py         # maintain access
- post/exfil.py              # data extraction

### MCP Servers (Modular Tools)

Tool Server Structure:
- nmap_server/server.py      # MCP protocol implementation
- metasploit_server/server.py
- custom_exploits/server.py
Each with isolated Docker runtime

MCP Registry (config.yaml):
- nmap: localhost:6000 (port_scan, service_detection)
- metasploit: localhost:6001 (exploit, payload)
- web_tools: localhost:6002 (sqli, xss, xxe)

### Campaign Orchestrator
1. Queue recon agents
2. Wait for attack surface
3. Queue exploit agents based on findings
4. Stream results via websocket

## Data Flow
User Input → API → Campaign Orchestrator → Redis Queue → Agent Pool → MCP Tool Servers → Findings Database → WebSocket → Dashboard

## MVP1 Scope

### Working Demo
1. User enters IP range (e.g., 192.168.1.0/24)
2. Recon agent discovers services
3. Exploit agent attempts appropriate attacks
4. Live results stream to dashboard
5. Generate basic report

### Initial Agents (3 total)
- NetworkReconAgent - Maps network
- WebExploitAgent - Tests web services
- ReportAgent - Generates findings summary

### Initial MCP Servers (2 total)
- nmap_server - Network scanning
- web_tools - Basic web attacks (SQLi, XSS)

## File Structure
project/
├── api/
│   ├── main.py           # FastAPI app
│   ├── models.py          # Pydantic models
│   └── orchestrator.py    # Campaign logic
├── agents/
│   ├── base.py           # Base agent class
│   ├── recon.py          # Recon agents
│   └── exploit.py        # Exploit agents
├── mcp_servers/
│   ├── nmap/
│   └── web_tools/
├── dashboard/
│   ├── src/
│   └── package.json
├── docker-compose.yml     # Local dev environment
└── config.yaml           # MCP registry, agent config

## Local Development Setup
docker-compose.yml:
- api: build ./api, ports 8000:8000
- redis: redis:alpine, ports 6379:6379
- nmap_mcp: build ./mcp_servers/nmap, ports 6000:6000
- web_tools_mcp: build ./mcp_servers/web_tools, ports 6001:6001

## Key Design Decisions
1. SQLite over PostgreSQL: Simple, no setup, fine for MVP
2. Redis for queue: Simple, supports pub/sub for live updates
3. MCP over direct integration: Modularity from day 1
4. Monolithic API: Faster to iterate, split later

## Success Metrics
- Complete scan of /24 network in under 5 minutes
- Identify and exploit 1 vulnerability automatically
- Add new agent without changing core code
- Add new MCP tool server without restart

## Next Steps After MVP1
1. Add authentication/multi-user
2. Cloud deployment (ECS/K8s)
3. More agent types
4. Agent memory/learning
5. Parallel campaign execution

