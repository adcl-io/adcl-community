# Package Registry

This directory contains the signed package registry following YUM-style architecture.

## Structure

```
registry/
├── publishers/     # Publisher public keys and metadata
├── agents/         # Agent packages (signed)
├── mcps/           # MCP server packages (signed)
└── teams/          # Team packages (signed)
```

## Directory Layouts

### Publishers
```
publishers/
└── {publisher_id}/
    ├── pubkey.asc      # Publisher's public GPG key
    └── metadata.json   # Publisher info (name, email, created_at, description)
```

### Agents
```
agents/
└── {agent_name}/
    └── {version}/
        ├── agent.json      # Agent configuration
        ├── agent.json.asc  # Detached GPG signature
        └── metadata.json   # Package metadata (checksums, publisher, timestamp)
```

### MCPs
```
mcps/
└── {mcp_name}/
    └── {version}/
        ├── mcp.json        # MCP server configuration
        ├── mcp.json.asc    # Detached GPG signature
        └── metadata.json   # Package metadata
```

### Teams
```
teams/
└── {team_name}/
    └── {version}/
        ├── team.json       # Team composition (references to agents/mcps)
        ├── team.json.asc   # Detached GPG signature
        └── metadata.json   # Package metadata (includes dependencies)
```

## Package Verification

All packages must be verified before use:

1. **Signature Verification**: Verify detached `.asc` signature against config file
2. **Checksum Verification**: Verify SHA256/MD5 checksums in metadata
3. **Publisher Trust**: Check publisher is in trusted list
4. **Dependency Verification**: For teams, verify all dependencies recursively

## Publishing Workflow

1. Publisher generates GPG keypair
2. Publisher signs package config file
3. Package + signature + metadata uploaded to registry
4. Publisher's public key registered in `publishers/`

## Usage

See `docs/GPG_PASSPHRASE_SETUP.md` for configuration and usage examples.
