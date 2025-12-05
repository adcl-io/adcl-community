# Architecture - MVP1 (Updated)
## Core Concept
Local network penetration testing with modular agents via MCP protocol, optimized for microservices and future K8s/Ray scaling.
## Tech Stack
- **Backend**: FastAPI (async, WebSocket support)
- **Agent Runtime**: Python with Anthropic MCP Python SDK
- **Queue**: Celery with Redis backend (task orchestration, pub/sub)
- **Storage**: SQLAlchemy (SQLite for MVP, Postgres-ready)
- **Dashboard**: React + WebSocket for live updates
- **Observability**: OpenTelemetry + Jaeger (MCP call tracing)
## Component Design
### API Server (main.py)
/campaigns POST - Start new campaign
/campaigns/{id} GET - Campaign status
/campaigns/{id}/ws WS - Live updates
/agents GET - List available agents
/findings GET - Retrieved vulnerabilities
/auth POST - JWT auth for API access
### Agent System
Base Agent Class (base.py):
- LLM connection (Claude/GPT4 via API keys in env vars)
- MCP client (Anthropic SDK for tool access)
- Memory store per agent (Redis key-value)
- Core reasoning loop (async, Celery tasks)
Agent Registry:
- recon/network_scanner.py # Nmap wrapper
- recon/service_enum.py # Version detection
- exploit/web_exploit.py # OWASP Top 10 (SQLi, XSS)
- report/summary.py # Findings report
### MCP Servers (Modular Tools)
Tool Server Structure:
- nmap_server/server.py # Anthropic MCP SDK
- web_tools/server.py # OWASP ZAP/Nikto wrapper
Each with isolated Docker runtime, TLS-enabled (self-signed certs)
MCP Registry (config.yaml):
- nmap: localhost:6000 (port_scan, service_detection)
- web_tools: localhost:6001 (sqli, xss)
### Campaign Orchestrator (orchestrator.py)
1. Queue recon agents (Celery task)
2. Wait for attack surface (Redis pub/sub)
3. Queue exploit agents based on findings
4. Stream results via WebSocket
5. Trace MCP calls with OpenTelemetry
## Data Flow
User Input → API (JWT-auth) → Campaign Orchestrator → Celery (Redis) → Agent Pool → MCP Tool Servers (SDK) → SQLAlchemy (SQLite) → WebSocket → Dashboard
## MVP1 Scope
### Working Demo
1. User enters IP range (e.g., 192.168.1.0/24)
2. Recon agent discovers services (Nmap)
3. Exploit agent attempts attacks (Nikto)
4. Live results stream to dashboard (React)
5. Generate basic report (PDF)
### Initial Agents (3 total)
- NetworkReconAgent - Maps network (Nmap)
- WebExploitAgent - Tests web services (Nikto)
- ReportAgent - Generates findings summary
### Initial MCP Servers (2 total)
- nmap_server - Network scanning
- web_tools - Basic web attacks (SQLi, XSS)
## File Structure
project/
├── api/
│ ├── main.py # FastAPI app
│ ├── models.py # SQLAlchemy models
│ └── orchestrator.py # Celery task logic
├── agents/
│ ├── base.py # Base agent class
│ ├── recon.py # Recon agents
│ ├── exploit.py # Exploit agents
│ └── report.py # Report agents
├── mcp_servers/
│ ├── nmap/
│ └── web_tools/
├── dashboard/
│ ├── src/
│ └── package.json
├── docker-compose.yml # Local dev environment
└── config.yaml # MCP registry, agent config
## Local Development Setup
docker-compose.yml:
- api: build ./api, ports 8000:8000
- redis: redis:alpine, ports 6379:6379
- nmap_mcp: build ./mcp_servers/nmap, ports 6000:6000
- web_tools_mcp: build ./mcp_servers/web_tools, ports 6001:6001
- postgres: postgres:alpine, ports 5432:5432
- jaeger: jaegertracing/all-in-one, ports 16686:16686
## Key Design Decisions
1. SQLAlchemy over raw SQLite: Preps for Postgres, concurrency-ready
2. Celery with Redis: Fault-tolerant task queue, K8s-ready
3. Anthropic MCP SDK: Standardizes tool comms, reduces custom code
4. JWT auth: Secures API from day one
5. OpenTelemetry: Traces for debugging/scaling
## Success Metrics
- Complete /24 network scan in under 5 minutes
- Identify and exploit 1 vulnerability automatically
- Add new agent without changing core code
- Add new MCP tool server without restart
- Trace 100% of MCP calls via Jaeger
## Next Steps After MVP1
1. Add multi-user auth (OAuth2)
2. Cloud deployment (ECS/K8s)
3. More agent types (e.g., social engineering)
4. Agent memory/learning (Redis persistence)
5. Parallel campaign execution (Celery workers)
