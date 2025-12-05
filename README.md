# ADCL Platform - Community Edition

AI-Driven Cyber Lab (ADCL) Platform - Open source AI agent orchestration system.

**Version:** 0.1.18

## What is ADCL?

ADCL is a modular platform for orchestrating AI agents with specialized capabilities through MCP (Model Context Protocol) servers. Built on Unix philosophy: simple tools that do one thing well, composed into powerful workflows.

## Quick Start

```bash
mkdir adcl && cd adcl
curl -fsSL https://raw.githubusercontent.com/adcl-io/adcl-community/main/install.sh | bash
```

Access the UI at: **http://localhost:3000**

## Manual Installation

```bash
# Clone the repository
git clone https://github.com/adcl-io/adcl-community.git
cd adcl-community

# Create .env file from example
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or vim, code, etc.

# Start the platform
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Architecture

ADCL consists of three core services:

- **Orchestrator** (port 8000) - Backend API, agent coordination, MCP management
- **Frontend** (port 3000) - Web UI for interacting with agents
- **Registry** (port 9000) - MCP server and workflow registry

On first startup, the orchestrator automatically installs three MCP servers:
- **agent** - AI reasoning and code generation
- **file-tools** - File operations (read/write/list)
- **nmap-recon** - Network reconnaissance

## Configuration

Edit `.env` to configure:

```bash
# Required: Add your API keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Optional: Change ports
ORCHESTRATOR_PORT=8000
FRONTEND_PORT=3000
REGISTRY_PORT=9000
```

## Directory Structure

```
adcl/
├── docker-compose.yml       # Service definitions
├── .env                     # Configuration (API keys, ports)
├── start.sh                 # Start services
├── stop.sh                  # Stop services
├── clean-restart.sh         # Clean restart
├── mcp_servers/            # MCP server source code
├── registry/               # Package registry
├── agent-definitions/      # Agent configurations
├── agent-teams/           # Multi-agent teams
├── workflows/             # Workflow definitions
├── workspace/             # Runtime workspace
└── logs/                  # Application logs
```

## Docker Images

Images are hosted on GitHub Container Registry (GHCR):
- `ghcr.io/adcl-io/adcl-community/orchestrator:0.1.18`
- `ghcr.io/adcl-io/adcl-community/frontend:0.1.18`
- `ghcr.io/adcl-io/adcl-community/registry:0.1.18`

## Usage

### Web UI
Open http://localhost:3000 to:
- Create and manage agents
- Execute workflows
- View MCP servers
- Monitor logs

### API
The orchestrator exposes a REST API at http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Commands

```bash
./start.sh                         # Start all services
./stop.sh                          # Stop all services
./clean-restart.sh                 # Clean restart
docker compose ps                  # Check status
docker compose logs -f             # View all logs
docker compose logs -f orchestrator  # View specific service
```

## Troubleshooting

### Orchestrator fails to start
- Check Docker socket permissions: `ls -la /var/run/docker.sock`
- Ensure Docker daemon is running: `docker ps`
- Check logs: `docker compose logs orchestrator`

### MCP servers not starting
- Check orchestrator logs: `docker compose logs orchestrator`
- Verify registry is running: `docker compose ps registry`
- Check Docker network: `docker network ls | grep adcl`

### API keys not working
- Verify keys in `.env` file: `cat .env`
- Restart orchestrator: `./clean-restart.sh`

## Development

### Adding Custom MCP Servers
1. Add package to `registry/mcps/your-mcp/1.0.0/`
2. Create `mcp.json` and `metadata.json`
3. Add source code to `mcp_servers/your-mcp/`
4. Restart orchestrator to reload registry

### Creating Agents
1. Add JSON definition to `agent-definitions/`
2. Specify required MCP servers and capabilities
3. Reload in UI or restart orchestrator

## License

MIT License - See LICENSE file for details

## Support

- **Issues:** https://github.com/adcl-io/adcl-community/issues
- **Discussions:** https://github.com/adcl-io/adcl-community/discussions
- **Documentation:** https://github.com/adcl-io/adcl-community/wiki

## Enterprise Edition

For enterprise features, support, and SLA:
- Email: enterprise@adcl.io
- Website: https://adcl.io

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.
