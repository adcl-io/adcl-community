# Project Directory Structure

**Last Updated**: 2025-10-17
**Version**: 2.0.0

This document describes the complete directory structure of the Agent Development Platform with integrated GPG package signing.

---

## Overview

The project follows a clear separation of concerns:

- **`src/`** - Python library code (signing, registry types, utilities)
- **`backend/`** - FastAPI backend service
- **`frontend/`** - React web UI
- **`registry/`** - Package registry (signed packages storage)
- **`.agent-cli/`** - Local client configuration
- **`agent-definitions/`** - Agent source definitions (pre-packaging)
- **`agent-teams/`** - Team source definitions (pre-packaging)
- **`mcp_servers/`** - MCP source definitions (pre-packaging)

---

## Complete Directory Tree

```
test3-dev-team/
├── src/                          # Python Package (library code)
│   ├── __init__.py
│   ├── signing/                  # GPG signing module
│   │   ├── __init__.py
│   │   └── gpg.py               # GPG wrapper functions
│   ├── registry/                 # Package registry types
│   │   ├── __init__.py
│   │   ├── package_types.py     # Package classes (Agent, MCP, Team)
│   │   └── registry_api.py      # Registry API client
│   └── utils.py                  # Utility functions (.env loading, etc.)
│
├── backend/                      # Backend API Server
│   ├── app/
│   │   ├── main.py              # FastAPI application (orchestrator)
│   │   ├── agent_runtime.py     # Autonomous agent execution
│   │   ├── team_runtime.py      # Multi-agent team execution
│   │   ├── mcp_manager.py       # MCP lifecycle management
│   │   └── docker_manager.py    # Docker operations
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                     # Web UI (React + Vite)
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── AgentBuilder/
│   │   │   ├── TeamBuilder/
│   │   │   ├── WorkflowEditor/
│   │   │   └── Chat/
│   │   ├── pages/               # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Agents.jsx
│   │   │   ├── Teams.jsx
│   │   │   └── Registry.jsx
│   │   └── App.jsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── registry/                     # PACKAGE REGISTRY (signed packages)
│   ├── publishers/               # Publisher public keys
│   │   └── {publisher_id}/
│   │       ├── pubkey.asc       # Publisher's public GPG key
│   │       └── metadata.json    # Publisher info
│   ├── agents/                   # Agent packages
│   │   └── {agent_name}/
│   │       └── {version}/
│   │           ├── agent.json   # Agent configuration
│   │           ├── agent.json.asc # GPG signature
│   │           └── metadata.json # Package metadata
│   ├── mcps/                     # MCP packages
│   │   └── {mcp_name}/
│   │       └── {version}/
│   │           ├── mcp.json     # MCP configuration
│   │           ├── mcp.json.asc # GPG signature
│   │           └── metadata.json # Package metadata
│   ├── teams/                    # Team packages
│   │   └── {team_name}/
│   │       └── {version}/
│   │           ├── team.json    # Team composition
│   │           ├── team.json.asc # GPG signature
│   │           └── metadata.json # Package metadata
│   └── README.md
│
├── .agent-cli/                   # LOCAL CLIENT CONFIG (gitignored)
│   ├── config.json              # Registry config, trusted publishers
│   ├── keyring/                 # GPG keyring with publisher keys
│   ├── cache/                   # Downloaded package cache
│   └── README.md
│
├── agent-definitions/            # Agent Source Definitions
│   └── {agent_id}.json          # Agent definition files (pre-packaging)
│
├── agent-teams/                  # Team Source Definitions
│   └── {team_id}.json           # Team definition files (pre-packaging)
│
├── mcp_servers/                  # MCP Source Definitions
│   └── {mcp_name}/              # MCP source code and configs
│       ├── Dockerfile
│       ├── mcp.json
│       └── src/
│
├── registry-server/              # Registry Server
│   ├── server.py                # Legacy registry server (v1)
│   ├── server_v2.py             # New registry server with GPG support
│   ├── Dockerfile
│   └── README.md
│
├── tests/                        # Test Suite
│   ├── test_gpg.py              # GPG module tests
│   ├── test_package_types.py    # Package types tests
│   ├── test_registry_api.py     # Registry API tests (future)
│   └── test_cli.py              # CLI tests (future)
│
├── docs/                         # Documentation
│   ├── specs/
│   │   └── package-signing.md   # Package signing specification
│   ├── GPG_PASSPHRASE_SETUP.md  # GPG configuration guide
│   ├── DIRECTORY_STRUCTURE.md   # This file
│   ├── DIRECTORY_RESTRUCTURE_PLAN.md # Migration plan
│   └── PASSPHRASE_IMPLEMENTATION_SUMMARY.md
│
├── workflows/                    # Workflow Definitions
├── workspace/                    # Runtime Workspace
├── logs/                         # Runtime Logs
│
├── setup.py                      # Python package setup
├── pytest.ini                    # Test configuration
├── requirements-signing.txt      # Signing dependencies
├── migrate_registry.py           # Registry migration script
├── .env                          # Environment config (gitignored)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Multi-service orchestration
└── README.md                     # Project README
```

---

## Key Directories Explained

### `src/` - Python Library

**Purpose**: Reusable Python code for package management and signing

- **`signing/gpg.py`**: GPG operations (generate keys, sign, verify)
- **`registry/package_types.py`**: Package data structures
- **`registry/registry_api.py`**: Registry client for fetching packages
- **`utils.py`**: Utility functions (.env loading, passphrases)

### `registry/` - Package Registry

**Purpose**: Storage for signed packages (YUM-style registry)

- **Structure**: `{type}/{name}/{version}/{type}.json[.asc]`
- **Publishers**: `/publishers/{id}/pubkey.asc` - Public keys for verification
- **Agents**: `/agents/{name}/{version}/agent.json` - Autonomous agents
- **MCPs**: `/mcps/{name}/{version}/mcp.json` - MCP servers
- **Teams**: `/teams/{name}/{version}/team.json` - Agent teams

**File Types**:
- `{type}.json` - Package configuration
- `{type}.json.asc` - Detached GPG signature
- `metadata.json` - Package metadata (checksums, publisher, timestamp)

### `.agent-cli/` - Client Configuration

**Purpose**: Local client configuration and trust management

- **`config.json`**: Registry URLs, trusted publishers, settings
- **`keyring/`**: GPG home directory with imported publisher keys
- **`cache/`**: Downloaded package cache for faster access

**Security**: Entire directory is gitignored (contains private keys)

### Source Definitions vs. Registry

**Source Definitions** (pre-packaging):
- `agent-definitions/` - Agent JSON files before signing
- `agent-teams/` - Team JSON files before signing
- `mcp_servers/` - MCP source code before building

**Registry** (post-packaging):
- Signed, versioned packages ready for distribution
- Includes metadata and GPG signatures
- Served by registry-server

---

## Package Lifecycle

```
1. DEVELOPMENT
   ↓
   Create agent/mcp/team in source directories
   (agent-definitions/, agent-teams/, mcp_servers/)

2. PACKAGING
   ↓
   Generate GPG keypair (if needed)
   Sign package configuration
   Calculate checksums
   Create metadata.json

3. PUBLISHING
   ↓
   Copy to registry/{type}/{name}/{version}/
   Include config, signature, and metadata
   Register publisher public key

4. DISTRIBUTION
   ↓
   Registry server serves packages via HTTP
   Clients fetch catalog and package data

5. INSTALLATION
   ↓
   Client downloads package
   Imports publisher's public key
   Verifies signature
   Verifies checksums
   Caches locally

6. EXECUTION
   ↓
   Load package from cache
   Execute agent/team with MCPs
```

---

## Migration from Old Structure

The project was migrated from a flat registry structure to a nested, versioned structure:

**Old** (deprecated):
```
registry-server/registries/
├── mcps/
│   └── {name}-{version}.json
└── teams/
    └── {name}-{version}.json
```

**New** (current):
```
registry/
├── publishers/{id}/
├── agents/{name}/{version}/
├── mcps/{name}/{version}/
└── teams/{name}/{version}/
```

**Migration Script**: `migrate_registry.py`

---

## Configuration Files

### `.env`
```bash
# API Keys
ANTHROPIC_API_KEY=your_api_key_here

# GPG Signing
GPG_SIGNING_PASSPHRASE=your_passphrase_here

# Service Ports
AGENT_PORT=7000
FILE_TOOLS_PORT=7002
ORCHESTRATOR_PORT=8000
FRONTEND_PORT=3000
```

### `.agent-cli/config.json`
```json
{
  "version": "1.0.0",
  "trusted_publishers": ["publisher_fingerprint_here"],
  "registries": [
    {
      "name": "local",
      "url": "file://./registry",
      "enabled": true,
      "priority": 1
    }
  ],
  "keyring_dir": "./.agent-cli/keyring",
  "cache_dir": "./.agent-cli/cache",
  "auto_verify": true,
  "allow_unsigned": false
}
```

### `registries.conf` (Backend)
```ini
[local]
name=Local Registry
url=http://localhost:9000
enabled=true
priority=1
```

---

## API Endpoints

### Registry Server (v2)

- **`GET /catalog`** - Full catalog (publishers, agents, mcps, teams)
- **`GET /publishers`** - List publishers
- **`GET /publishers/{id}/pubkey`** - Get publisher public key
- **`GET /agents`** - List all agents
- **`GET /agents/{name}`** - List versions of agent
- **`GET /agents/{name}/{version}`** - Get specific agent package
- **`GET /mcps`** - List all MCPs
- **`GET /mcps/{name}/{version}`** - Get specific MCP package
- **`GET /teams`** - List all teams
- **`GET /teams/{name}/{version}`** - Get specific team package

### Backend (Orchestrator)

- **`GET /registries`** - List configured registries
- **`GET /registries/catalog`** - Combined catalog from all registries
- **`POST /registries/install/agent/{id}`** - Install agent from registry
- **`POST /registries/install/mcp/{id}`** - Install MCP from registry
- **`POST /registries/install/team/{id}`** - Install team from registry
- **`GET /agents`** - List installed agents
- **`POST /agents/run`** - Run autonomous agent
- **`GET /teams`** - List installed teams
- **`POST /teams/run`** - Run multi-agent team

---

## Security Model

### Trust Chain

1. **Publisher Generates Keys**
   - Creates GPG keypair
   - Publishes public key to registry
   - Keeps private key secure

2. **Package Signing**
   - Publisher signs package with private key
   - Uploads package + signature to registry
   - Registry stores signature alongside package

3. **User Trust**
   - User imports publisher's public key
   - Adds publisher to trusted list
   - Client verifies signatures before install

4. **Verification**
   - Client downloads package + signature
   - Verifies signature using publisher's public key
   - Verifies checksums match
   - Only installs if verification succeeds

### Security Best Practices

✅ **DO**:
- Use strong passphrases (20+ characters)
- Store passphrases in .env (gitignored)
- Rotate keys and passphrases regularly
- Use separate keys for different environments
- Keep .agent-cli/ directory gitignored
- Verify signatures before installing packages

❌ **DON'T**:
- Commit passphrases or private keys
- Share private keys
- Allow unsigned packages in production (`allow_unsigned: false`)
- Use weak passphrases
- Reuse passphrases across keys

---

## Development Workflow

### Creating a New Agent

```bash
# 1. Create agent definition
vi agent-definitions/my-agent.json

# 2. Test locally
# (Use backend API to run agent)

# 3. Sign and package
python -c "
from src.signing import gpg
from src.utils import load_env_file

load_env_file()

# Sign the agent config
gpg.sign_file(
    'agent-definitions/my-agent.json',
    'YOUR_KEY_ID'
)
"

# 4. Publish to registry
# (Copy to registry/agents/my-agent/1.0.0/)
```

### Installing a Package

```bash
# Using registry API client
python -c "
from src.registry.registry_api import load_client

client = load_client('.agent-cli/config.json')

# Trust publisher first
client.trust_publisher('PUBLISHER_FINGERPRINT')

# Download package
client.download_package('agent', 'security-analyst', '1.0.0')
"
```

---

## Testing

```bash
# Install dependencies
pip install -e .

# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_gpg.py -v
pytest tests/test_package_types.py -v
```

---

## References

- [GPG Passphrase Setup](./GPG_PASSPHRASE_SETUP.md)
- [Package Signing Specification](./specs/package-signing.md)
- [Directory Restructure Plan](./DIRECTORY_RESTRUCTURE_PLAN.md)
- [Passphrase Implementation](./PASSPHRASE_IMPLEMENTATION_SUMMARY.md)

---

**For Questions or Issues**: See project README.md
