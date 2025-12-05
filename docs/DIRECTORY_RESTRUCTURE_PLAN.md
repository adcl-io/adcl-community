# Directory Restructure Plan

**Date**: 2025-10-17
**Purpose**: Align directory structure with GPG package signing architecture

---

## Current Structure Issues

1. **Fragmented registry**: `registry-server/registries/` separate from `src/registry/`
2. **Missing publisher management**: No publisher directory structure
3. **Missing agents directory**: Agents not integrated into registry
4. **Inconsistent paths**: Backend references need updating
5. **No client-side structure**: Missing `~/.agent-cli/` equivalent for dev/testing

---

## Proposed New Structure

```
test3-dev-team/
├── backend/                      # Backend API server
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── agent_runtime.py     # Agent execution
│   │   ├── team_runtime.py      # Team execution
│   │   ├── mcp_manager.py       # MCP management
│   │   └── docker_manager.py    # Docker operations
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                     # Web UI
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.jsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── src/                          # Python package (library code)
│   ├── __init__.py
│   ├── signing/                  # GPG signing module
│   │   ├── __init__.py
│   │   └── gpg.py               # GPG wrapper functions
│   ├── registry/                 # Package type definitions
│   │   ├── __init__.py
│   │   ├── package_types.py     # Package classes
│   │   └── registry_api.py      # Registry API client (new)
│   ├── cli/                      # CLI commands (new)
│   │   ├── __init__.py
│   │   ├── commands.py          # CLI command implementations
│   │   └── config.py            # CLI configuration
│   └── utils.py                  # Utility functions
│
├── registry/                     # PACKAGE REGISTRY (file-based)
│   ├── publishers/               # Publisher public keys
│   │   └── {publisher_id}/
│   │       ├── pubkey.asc       # Publisher's public GPG key
│   │       └── metadata.json    # Publisher info (name, email, created)
│   ├── agents/                   # Agent packages
│   │   └── {agent_name}/
│   │       └── {version}/
│   │           ├── agent.json   # Agent configuration
│   │           ├── agent.json.asc # Detached GPG signature
│   │           └── metadata.json # Package metadata
│   ├── mcps/                     # MCP packages
│   │   └── {mcp_name}/
│   │       └── {version}/
│   │           ├── mcp.json     # MCP configuration
│   │           ├── mcp.json.asc # Detached GPG signature
│   │           └── metadata.json # Package metadata
│   └── teams/                    # Team packages
│       └── {team_name}/
│           └── {version}/
│               ├── team.json    # Team composition
│               ├── team.json.asc # Detached GPG signature
│               └── metadata.json # Package metadata
│
├── .agent-cli/                   # LOCAL CLIENT CONFIG (dev/testing)
│   ├── config.json              # User config with trusted publishers
│   ├── keyring/                 # Imported publisher public keys (GPG home dir)
│   └── cache/                   # Downloaded packages cache
│
├── agent-definitions/            # Agent source definitions (pre-packaging)
│   └── {agent_name}/
│       └── agent.json
│
├── agent-teams/                  # Team source definitions (pre-packaging)
│   └── {team_name}/
│       └── team.json
│
├── mcp_servers/                  # MCP source definitions (pre-packaging)
│   └── {mcp_name}/
│       └── mcp.json
│
├── tests/                        # Test suite
│   ├── test_gpg.py
│   ├── test_package_types.py
│   ├── test_registry_api.py     # (new)
│   └── test_cli.py              # (new)
│
├── docs/                         # Documentation
│   ├── specs/
│   │   └── package-signing.md
│   ├── GPG_PASSPHRASE_SETUP.md
│   ├── DIRECTORY_STRUCTURE.md   # (new)
│   └── API_REFERENCE.md         # (new)
│
├── workflows/                    # CI/CD workflows
├── workspace/                    # Runtime workspace
├── logs/                         # Runtime logs
│
├── setup.py                      # Python package setup
├── pytest.ini                    # Test configuration
├── requirements-signing.txt      # Signing dependencies
├── .env                          # Environment config (gitignored)
├── .env.example                  # Environment template
└── docker-compose.yml            # Multi-service orchestration
```

---

## Migration Steps

### Phase 1: Create New Registry Structure ✅
1. Create `registry/` directory with subdirectories
2. Create `.agent-cli/` directory for client config
3. Migrate existing packages from `registry-server/registries/`

### Phase 2: Update Source Code ✅
1. Update backend to reference new `registry/` path
2. Create registry API client in `src/registry/registry_api.py`
3. Update path references in all Python modules

### Phase 3: Add CLI Support (Future)
1. Create `src/cli/` module
2. Implement CLI commands (keygen, sign, publish, trust, pull, verify)
3. Create CLI entry point

### Phase 4: Documentation (Future)
1. Create comprehensive directory structure docs
2. Update README with new paths
3. Create API reference documentation

---

## Key Benefits

✅ **Clear Separation**: Source definitions vs. signed packages
✅ **Standard Structure**: Aligns with YUM/APT package management
✅ **Publisher Support**: Dedicated publisher key management
✅ **Version Management**: Explicit version directories
✅ **Client Isolation**: Local config separate from registry
✅ **Testability**: Clear separation of concerns

---

## Backward Compatibility

- Old `registry-server/registries/` will be deprecated
- Migration script will move existing packages
- Backend API will support both paths during transition (with deprecation warnings)

---

## Next Actions

1. ✅ Create directory structure
2. ✅ Migrate existing packages
3. ✅ Update backend path references
4. Create registry API client
5. Update documentation
6. Create migration script for existing deployments
