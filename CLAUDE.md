# ADCL Platform Development Guide

## Core Philosophy
ADCL follows Unix philosophy: "Do one thing well, communicate via text streams, compose simple tools into complex systems."

## Architecture Principles

### 1. Configuration is Code
- **ALL** configuration in plain text (JSON/YAML/TOML)
- **NO** binary configs, databases for settings, or UI-only configuration
- **NO** hidden state - everything inspectable via `cat`, `grep`, `jq`
- Configs hot-reloadable without restarts where possible

### 2. Directory Structure (Sacred)
```
adcl/
├── agent-definitions/    # Agent JSON definitions
├── agent-teams/         # Team coordination configs  
├── configs/            # Service configurations
├── logs/              # All logs (*.log, rotated daily)
├── docs/              # Documentation only and all MD creations
├── mcp_servers/       # One directory per MCP server
│   └── {name}/
│       ├── server.py
│       ├── requirements.txt
│       └── README.md
├── packages/          # Downloaded MCP packages
├── registries.conf    # Package sources (yum-style)
└── volumes/          # Persistent data mounts
```

### 3. Modularity Rules
- Each MCP server is **completely independent**
- Communication **only** via MCP protocol (stdio/HTTP)
- **NO** shared libraries between MCPs
- **NO** direct database connections between services
- Each service has own Dockerfile, can run standalone

## Development Standards

### MCP Servers
```python
# Every MCP server follows this pattern:
class YourMCPServer:
    """One responsibility, exposed via tools."""
    
    @tool("tool_name")
    async def tool_name(self, params: dict) -> dict:
        """Clear input → Clear output"""
        # No side effects outside declared scope
        # Log to stdout/stderr only
        # Return JSON-serializable data
```

### Agent Definitions
```json
{
  "name": "agent_name",
  "version": "0.1.0",
  "mcp_servers": ["file_tools", "nmap_recon"],
  "capabilities": ["network_analysis"],
  "config": {
    "// All config here": "No hidden parameters"
  }
}
```

### Error Handling
- Fail fast, fail loudly
- Return meaningful error codes
- Log errors to `logs/{service}-{date}.log`
- Never swallow exceptions silently

## File Operations

### Logs
- Pattern: `logs/{service}-{YYYY-MM-DD}.log`
- JSON structured logging preferred
- Rotate daily, compress after 7 days
- Ship to syslog if configured

### Data Persistence
- User data: `volumes/data/`
- Vector indices: `volumes/vectors/`
- Temporary: `/tmp/adcl/` (cleaned on restart)
- Configs: Version controlled, never auto-modified

## Service Communication

### MCP Protocol Only
```python
# Good - MCP tool call
result = await mcp_client.call("search_code", {
    "query": "security vulnerability"
})

# Bad - Direct function call
result = vector_server.search("security")  # NO!

# Bad - Shared database
db = connect("postgresql://shared")  # NO!
```

### Service Discovery
- Services register in `configs/services.json`
- Health checks via `/health` endpoint
- Port allocation from `configs/ports.conf`

## Testing Standards

### Unit Tests
```bash
# Each MCP server testable in isolation
cd mcp_servers/agent
python -m pytest tests/
```

### Integration Tests
```bash
# Test via MCP protocol only
./tests/integration/test_agent_workflow.sh
```

## Package Management

### Registry Format (YUM-style)
```ini
# registries.conf
[official]
name=ADCL Official Repository
baseurl=http://registry.adcl.io
enabled=1
gpgcheck=0

[community]
name=Community Packages
baseurl=http://community.adcl.io
enabled=1
```

### Package Structure
```
package-name-1.0.0/
├── metadata.json      # Package info
├── server.py         # MCP implementation
├── requirements.txt  # Python deps
├── Dockerfile       # Container definition
└── install.sh      # Installation script
```

## Docker Standards

### One Process Per Container
```dockerfile
# Good
FROM python:3.11-slim
WORKDIR /app
COPY . .
CMD ["python", "server.py"]

# Bad - Multiple services
CMD ["sh", "-c", "python api.py & python worker.py"]
```

### Health Checks Required
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Security Principles

### Least Privilege
- Each MCP runs as non-root user
- Minimal filesystem access
- Network isolation by default
- Secrets via environment variables only

### No Hardcoded Secrets
```python
# Good
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY required")

# Bad
api_key = "sk-ant-xxxxx"  # NEVER
```

## Code Review Checklist

Before ANY merge:
- [ ] Follows single responsibility principle
- [ ] Configuration in text files
- [ ] Logs to correct directory
- [ ] No hardcoded paths/ports/secrets
- [ ] Dockerfile included if new service
- [ ] Health check endpoint exists
- [ ] Unit tests pass
- [ ] No cross-service imports
- [ ] Documentation updated

## Mandatory Agent Reviews

### When to Run Agent Reviews

**ALWAYS** run these agent reviews after completing code changes:

#### 1. code-nitpicker-9000 Agent
Run this agent **proactively** after:
- Any code modifications or new features
- Bug fixes or refactoring
- Type system changes (adding/modifying types, interfaces, classes)
- Changes affecting more than 3 files
- Any modification to MCP servers

**Purpose**: Quality assurance, test coverage validation, linting verification

#### 2. linus-torvalds Agent
Run this agent **proactively** after:
- Architectural changes or new service additions
- Modifications to MCP server implementations
- Changes to agent definitions or configurations
- Cross-service communication patterns
- Any deviation from Unix philosophy
- Type system refactoring (changing core types, data models)
- Database schema or data structure changes

**Purpose**: Ensure adherence to Unix philosophy, ADCL principles, and architectural soundness

### Agent Review Workflow

```bash
# After making significant changes:
1. Complete your implementation
2. Run code-nitpicker-9000 for QA review
3. Address any issues found
4. Run linus-torvalds for architectural review
5. Address any architectural concerns
6. Only then proceed to commit/merge
```

### Critical: Type System Changes

For **any changes involving type definitions**, data models, or interfaces:
- **MUST** run both agents before committing
- Type changes affect system contracts and architecture
- Get feedback from both QA (nitpicker) and architecture (linus) perspectives
- Document type migration strategy if breaking changes

### Examples Requiring Agent Review

**Requires both agents:**
- Changing API request/response types
- Modifying database models or schemas
- Refactoring shared type definitions
- Adding new agent capabilities or tools
- Creating new MCP server implementations

**Requires linus-torvalds only:**
- Pure architectural decisions
- Service communication pattern changes
- Configuration structure modifications

**Requires code-nitpicker-9000 only:**
- Minor bug fixes in existing code
- Adding unit tests
- Formatting/linting corrections

## Platform Evolution

### Adding New MCP Servers
1. Create `mcp_servers/{name}/`
2. Implement MCP protocol
3. Add to `registries.conf`
4. Write integration test
5. Update `docs/mcp-servers.md`

### Deprecation Policy
- Mark deprecated in metadata.json
- Log warnings for 2 versions
- Remove after 3 versions
- Migration guide required

## Performance Guidelines

### Async Everything
```python
# Good
async def process_task(task_id: str):
    result = await fetch_data()
    return await process(result)

# Bad
def process_task(task_id: str):
    result = fetch_data()  # Blocks!
    return process(result)
```

### Resource Limits
- Memory: Set container limits
- CPU: Use cgroups
- Disk: Monitor volumes/
- Network: Rate limit external calls

## Monitoring & Observability

### Metrics Export
- Prometheus format at `/metrics`
- OpenTelemetry traces if configured
- Structured logs with correlation IDs

### Debug Mode
```bash
# Enable verbose logging
DEBUG=1 ./start.sh

# Inspect MCP communication
MCP_DEBUG=stdio ./mcp_servers/agent/server.py
```

## Common Pitfalls to Avoid

1. **State in UI** - All state in backend/files
2. **Circular dependencies** - Use events/queues
3. **Vendor lock-in** - Abstract cloud services
4. **Monolithic growth** - Split early, split often
5. **Config sprawl** - One source of truth per setting
6. **Log noise** - Log actionable events only

## Questions to Ask

Before implementing:
- Can this be a standalone MCP server?
- Is the config human-readable/editable?
- Will this work without the UI?
- Can I test this in isolation?
- Does this follow Unix philosophy?

## Remember

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

Keep it simple. Keep it modular. Keep it text.
