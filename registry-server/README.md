# MCP Registry Server

A package registry for MCP servers and agent teams, similar to yum/apt repositories.

## Overview

This registry server hosts MCPs and teams as downloadable packages, allowing platforms to:
- Browse available MCPs and teams
- Install new packages
- Update existing packages
- Manage multiple registry sources

## Architecture

```
registry-server/
├── server.py           # FastAPI registry server
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image
└── registries/
    ├── mcps/          # MCP package definitions
    │   ├── agent-1.0.0.json
    │   ├── file-tools-1.0.0.json
    │   └── nmap-recon-1.0.0.json
    └── teams/         # Team package definitions
        ├── security-team-1.0.0.json
        └── code-review-team-1.0.1.json
```

## Package Format

### MCP Package
```json
{
  "name": "mcp_name",
  "version": "1.0.0",
  "description": "Description",
  "type": "mcp",
  "docker_image": "image:tag",
  "port": 7000,
  "environment": {},
  "tools": [],
  "tags": [],
  "author": "",
  "license": "MIT"
}
```

### Team Package
```json
{
  "name": "Team Name",
  "description": "Description",
  "version": "1.0.0",
  "agents": [
    {
      "name": "Agent Name",
      "role": "Role",
      "mcp_server": "mcp_name"
    }
  ]
}
```

## API Endpoints

- `GET /` - Registry information
- `GET /catalog` - Full catalog of packages
- `GET /mcps` - List MCP packages
- `GET /mcps/{mcp_id}` - Get specific MCP
- `GET /teams` - List team packages
- `GET /teams/{team_id}` - Get specific team
- `GET /health` - Health check

## Running

### Docker
```bash
docker build -t mcp-registry:1.0.0 .
docker run -p 9000:9000 mcp-registry:1.0.0
```

### Local
```bash
pip install -r requirements.txt
python server.py
```

## Adding Packages

### Add MCP
1. Create JSON file in `registries/mcps/`
2. Name format: `{mcp-name}-{version}.json`
3. Restart server to refresh catalog

### Add Team
1. Create JSON file in `registries/teams/`
2. Name format: `{team-name}-{version}.json`
3. Restart server to refresh catalog

## Usage with Platform

Configure registry in platform's `registries.conf`:
```ini
[default]
name=Default MCP Registry
url=http://localhost:9000
enabled=true
```

Then use the Registry UI page to:
- Browse packages
- Install MCPs and teams
- Update to newer versions

## Versioning

All packages use semantic versioning (semver):
- `major.minor.patch` (e.g., `1.0.0`)
- Breaking changes increment major version
- New features increment minor version
- Bug fixes increment patch version
