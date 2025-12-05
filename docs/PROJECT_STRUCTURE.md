# Project Structure & Organization

## Overview

The MCP Agent Platform follows a clear directory structure to organize code, tests, documentation, and runtime artifacts.

```
test3-dev-team/
├── README.md                   # Main project documentation
├── QUICK_START.md             # Quick reference guide
├── arch.md                    # Architecture documentation
├── .env                       # Environment configuration
├── .gitignore                 # Git ignore rules
├── docker-compose.yml         # Docker orchestration
│
├── backend/                   # FastAPI Orchestrator
│   ├── app/
│   │   └── main.py           # Main API and workflow engine
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                  # React UI
│   ├── src/
│   │   ├── App.jsx           # Main UI component
│   │   └── App.css          # Styles
│   ├── Dockerfile
│   └── package.json
│
├── mcp_servers/              # MCP Server Implementations
│   ├── base_server.py        # Base MCP server class
│   ├── agent/                # AI Agent MCP server
│   │   └── agent_server.py
│   ├── file_tools/           # File operations MCP server
│   │   └── file_server.py
│   ├── nmap/                 # Network scanning MCP server
│   │   └── nmap_server.py
│   ├── Dockerfile.agent
│   ├── Dockerfile.file_tools
│   ├── Dockerfile.nmap
│   └── requirements.txt
│
├── workflows/                # Workflow Definitions
│   ├── nmap_recon.json       # Nmap reconnaissance workflow
│   ├── full_recon.json       # Full reconnaissance workflow
│   ├── hello_world.json      # Hello world example
│   └── code_review.json      # Code review workflow
│
├── docs/                     # Detailed Documentation
│   ├── INDEX.md              # Documentation index
│   ├── *.md                  # Bug fixes, guides, troubleshooting
│   └── *.txt                 # Quick references
│
├── tests/                    # Test Files
│   ├── test_param_substitution.py
│   ├── test_nmap_workflow.py
│   ├── test_agent_response.py
│   ├── check_results.py
│   └── test_frontend_rendering.html
│
├── logs/                     # Runtime Logs (mapped from containers)
│   ├── orchestrator/         # Orchestrator logs
│   ├── agent/                # Agent logs
│   ├── file_tools/           # File tools logs
│   ├── nmap_recon/           # Nmap logs
│   └── frontend/             # Frontend logs
│
├── workspace/                # File Operations Workspace
│   └── (user-generated files)
│
└── scripts/                  # Management Scripts
    ├── start.sh              # Start all services
    ├── stop.sh               # Stop all services
    ├── clean-restart.sh      # Clean restart
    ├── status.sh             # Check status
    ├── logs.sh               # View logs
    ├── restart-api.sh        # Restart orchestrator
    ├── restart-agent.sh      # Restart agent
    └── restart-frontend.sh   # Restart frontend
```

## Directory Purposes

### Root Directory

**Main Documentation:**
- `README.md` - Project overview, quick start, usage instructions
- `QUICK_START.md` - Quick reference for common operations
- `arch.md` - Architecture and design decisions

**Configuration:**
- `.env` - Environment variables (API keys, ports, network config)
- `.gitignore` - Files and directories to exclude from Git
- `docker-compose.yml` - Docker service orchestration

**Management Scripts:**
- `*.sh` - Scripts for starting, stopping, and managing services

### Backend (`backend/`)

FastAPI-based orchestrator that:
- Manages MCP server registry
- Executes workflows
- Provides REST API
- Handles real-time WebSocket updates

**Key Files:**
- `app/main.py` - Main application with workflow engine
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container image definition

### Frontend (`frontend/`)

React-based UI that:
- Provides visual workflow builder (React Flow)
- Shows real-time execution progress
- Displays results with custom renderers
- Manages workflow execution

**Key Files:**
- `src/App.jsx` - Main UI component with workflow logic
- `src/App.css` - Styling
- `package.json` - Node dependencies
- `Dockerfile` - Container image definition

### MCP Servers (`mcp_servers/`)

Independent MCP server implementations:

**base_server.py** - Base class for all MCP servers
- Tool registration
- Request handling
- Response formatting

**agent/** - AI Agent MCP Server
- `think` - Reasoning and analysis
- `code` - Code generation
- `review` - Code review

**file_tools/** - File Operations MCP Server
- `read_file` - Read file contents
- `write_file` - Write to files
- `list_files` - Directory listing

**nmap/** - Network Reconnaissance MCP Server
- `port_scan` - Port scanning
- `service_detection` - Service identification
- `os_detection` - OS fingerprinting
- `vulnerability_scan` - Vulnerability detection
- `network_discovery` - Network mapping
- `full_recon` - Comprehensive reconnaissance

### Workflows (`workflows/`)

JSON-based workflow definitions:
- Nodes (MCP calls)
- Edges (execution order)
- Parameter references (${node-id.field})

**Example Workflows:**
- `nmap_recon.json` - Quick network reconnaissance
- `full_recon.json` - Comprehensive security assessment
- `hello_world.json` - Simple demonstration
- `code_review.json` - Code generation and review

### Documentation (`docs/`)

Detailed technical documentation:

**INDEX.md** - Complete documentation index

**Categories:**
- Setup & Configuration
- Integration Guides
- Bug Fixes & Troubleshooting
- Comprehensive Summaries

**All documentation is categorized and indexed** - See `docs/INDEX.md` for complete list

### Tests (`tests/`)

Automated and manual tests:

**Python Tests:**
- `test_param_substitution.py` - Parameter resolution tests
- `test_nmap_workflow.py` - Workflow execution tests
- `test_agent_response.py` - Agent response validation
- `check_results.py` - Result validation utilities

**HTML Tests:**
- `test_frontend_rendering.html` - Frontend rendering tests

**Running Tests:**
```bash
# Individual test
python3 tests/test_param_substitution.py

# Nmap workflow test
python3 tests/test_nmap_workflow.py

# Agent response test
python3 tests/test_agent_response.py
```

### Logs (`logs/`)

Runtime logs from Docker containers:

**Structure:**
```
logs/
├── orchestrator/     # API server logs
├── agent/            # Agent MCP logs
├── file_tools/       # File tools logs
├── nmap_recon/       # Nmap recon logs
└── frontend/         # Frontend logs
```

**Log Volume Mapping:**
Each service writes logs to `/app/logs` inside the container, which is mapped to `./logs/<service>/` on the host.

**Viewing Logs:**
```bash
# Via script (live stream)
./logs.sh orchestrator

# Via docker-compose (live stream)
docker-compose logs -f orchestrator

# Via file system (historical)
cat logs/orchestrator/*.log

# All services
./logs.sh
```

**Log Rotation:**
Logs are managed by Docker and can be configured via docker-compose logging settings. The `logs/` directory is excluded from Git via `.gitignore`.

### Workspace (`workspace/`)

Shared directory for file operations:
- Files created by `file_tools.write_file`
- Files read by `file_tools.read_file`
- Report outputs from workflows
- User-generated content

**Persistence:**
The workspace directory is mounted as a volume and persists between container restarts.

**Security:**
The workspace is excluded from Git (except .gitkeep) to prevent accidental commits of sensitive data.

## Git Configuration

### `.gitignore` Rules

```
# Logs
*.log
logs/
*.log.*

# Workspace (user-generated files)
workspace/
!workspace/.gitkeep

# Test outputs
tests/__pycache__/
tests/*.pyc
tests/output/
tests/results/

# Environment
.env
.env.local

# Dependencies
node_modules/
__pycache__/
*.pyc
```

### Tracked vs Ignored

**Tracked (in Git):**
- Source code (backend, frontend, mcp_servers)
- Workflow definitions
- Documentation
- Tests
- Scripts
- .gitkeep files (preserve empty directories)

**Ignored (not in Git):**
- Logs and log files
- Workspace files
- Test outputs
- Environment files
- Dependencies (node_modules, __pycache__)

## Docker Volume Mappings

### Current Mappings

| Service | Container Path | Host Path | Purpose |
|---------|---------------|-----------|---------|
| orchestrator | /app/workflows | ./workflows | Workflow definitions |
| orchestrator | /app/logs | ./logs/orchestrator | Runtime logs |
| agent | /app/logs | ./logs/agent | Runtime logs |
| file_tools | /workspace | ./workspace | File operations |
| file_tools | /app/logs | ./logs/file_tools | Runtime logs |
| nmap_recon | /app/logs | ./logs/nmap_recon | Runtime logs |
| frontend | /app/logs | ./logs/frontend | Runtime logs |

### Why Volume Mapping?

**Workflows:**
- Edit workflows without rebuilding containers
- Version control workflow changes
- Share workflows across team

**Logs:**
- Persist logs between container restarts
- Analyze logs from host
- Centralized log storage

**Workspace:**
- Access generated files from host
- Backup user data
- Share files with host tools

## Best Practices

### Documentation

- **README.md** - Keep concise, link to detailed docs
- **docs/** - Detailed technical documentation
- **CODE_COMMENTS** - Explain why, not what

### Testing

- **tests/** - All tests in dedicated directory
- **Test files** - Prefix with `test_` or suffix with `_test.py`
- **Manual tests** - Documented in test files or docs

### Logging

- **Structured logs** - Use consistent format
- **Log levels** - DEBUG, INFO, WARNING, ERROR
- **Rotation** - Configure via docker-compose if needed

### Workflow Organization

- **workflows/** - All workflow definitions
- **Naming** - Descriptive names (e.g., `nmap_recon.json`)
- **Documentation** - Comment complex workflows

### Development

- **Hot reload** - Frontend and backend support code changes
- **Logs** - Check logs for errors during development
- **Tests** - Run tests before committing

## Environment Configuration

### `.env` Structure

```bash
# LLM API Keys
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>

# Service Ports
AGENT_PORT=7000
NMAP_PORT=7003
FILE_TOOLS_PORT=7002
ORCHESTRATOR_PORT=8000
FRONTEND_PORT=3000

# Network Configuration
ALLOWED_SCAN_NETWORKS=192.168.50.0/24,10.0.0.0/8
```

### Port Allocation

| Service | Default Port | Configurable |
|---------|-------------|--------------|
| Frontend | 3000 | Yes |
| API | 8000 | Yes |
| Agent | 7000 | Yes |
| File Tools | 7002 | Yes |
| Nmap Recon | 7003 | Yes |

## Maintenance

### Log Cleanup

```bash
# Clear all logs
rm -rf logs/*/.log*

# Clear specific service logs
rm -rf logs/orchestrator/*.log

# Keep directory structure
find logs -name "*.log" -delete
```

### Workspace Cleanup

```bash
# Clear all workspace files
rm -rf workspace/*

# Keep .gitkeep
find workspace -type f ! -name '.gitkeep' -delete
```

### Test Output Cleanup

```bash
# Clear test outputs
rm -rf tests/output/
rm -rf tests/results/
find tests -name "__pycache__" -type d -exec rm -rf {} +
```

## Summary

**Organized Structure:**
- ✅ Source code in logical directories
- ✅ Tests in dedicated `tests/` directory
- ✅ Documentation in `docs/` with index
- ✅ Logs mapped to `logs/` with subdirectories
- ✅ Workspace for user files
- ✅ Scripts in root for easy access

**Benefits:**
- Clear separation of concerns
- Easy to navigate
- Git-friendly organization
- Docker volume mapping for persistence
- Comprehensive documentation

**Next Steps:**
- Check `README.md` for usage instructions
- Review `docs/INDEX.md` for documentation
- Run `./start.sh` to get started
- Check `./status.sh` for service health

---

**Date:** 2025-10-14
**Version:** 1.0
**Status:** Production structure ✅
