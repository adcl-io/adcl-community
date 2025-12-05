# Environment Variables in Workflows

This document explains how to use environment variables in workflow definitions.

## Overview

Workflows can reference environment variables defined in `.env` using the `${env:VARIABLE_NAME}` syntax. This allows you to:
- Configure scan targets without hardcoding IP addresses
- Maintain different configurations for dev/staging/prod environments
- Share common settings across multiple workflows
- Keep sensitive configuration separate from workflow definitions

## Syntax

Use the following syntax to reference environment variables in workflow parameters:

```json
{
  "params": {
    "target": "${env:DEFAULT_SCAN_TARGET}",
    "network": "${env:DEFAULT_SCAN_NETWORK}"
  }
}
```

## Available Variables

The following environment variables are configured in `.env` and available to workflows:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `DEFAULT_SCAN_NETWORK` | Default network range for network-wide scans | `192.168.50.0/24` |
| `DEFAULT_SCAN_TARGET` | Default single host target for testing | `192.168.50.1` |
| `ALLOWED_SCAN_NETWORKS` | Comma-separated list of allowed networks | `192.168.50.0/24` |

## Examples

### Single Host Scan

```json
{
  "name": "Quick Port Scan",
  "nodes": [
    {
      "id": "scan-host",
      "type": "mcp_call",
      "mcp_server": "nmap_recon",
      "tool": "port_scan",
      "params": {
        "target": "${env:DEFAULT_SCAN_TARGET}",
        "scan_type": "quick"
      }
    }
  ],
  "edges": []
}
```

This will scan the host specified in `DEFAULT_SCAN_TARGET` (e.g., `192.168.50.1`).

### Network-Wide Discovery

```json
{
  "name": "Network Discovery",
  "nodes": [
    {
      "id": "discover-hosts",
      "type": "mcp_call",
      "mcp_server": "nmap_recon",
      "tool": "network_discovery",
      "params": {
        "network": "${env:DEFAULT_SCAN_NETWORK}"
      }
    }
  ],
  "edges": []
}
```

This will scan all hosts in the network range specified in `DEFAULT_SCAN_NETWORK` (e.g., `192.168.50.0/24`).

### String Interpolation

Environment variables can be embedded in strings:

```json
{
  "params": {
    "prompt": "Scan the network ${env:DEFAULT_SCAN_NETWORK} and analyze results"
  }
}
```

## Configuration

### Adding New Environment Variables

1. Add the variable to `.env`:
```bash
MY_CUSTOM_TARGET=10.0.0.1
```

2. Add it to the orchestrator service in `docker-compose.yml`:
```yaml
orchestrator:
  environment:
    - MY_CUSTOM_TARGET=${MY_CUSTOM_TARGET:-10.0.0.1}
```

3. Restart the orchestrator:
```bash
docker-compose stop orchestrator
docker-compose rm -f orchestrator
docker-compose up -d orchestrator
```

4. Use it in workflows:
```json
{
  "params": {
    "target": "${env:MY_CUSTOM_TARGET}"
  }
}
```

## Error Handling

If you reference a non-existent environment variable, the workflow will fail with an error:

```
❌ Node failed: Environment variable not found: VARIABLE_NAME
```

To fix this:
1. Check the variable name in your workflow
2. Verify the variable exists in `.env`
3. Confirm it's added to orchestrator's environment in `docker-compose.yml`
4. Recreate the orchestrator container to pick up new variables

## Implementation Details

Environment variable substitution happens in the orchestrator's `_resolve_params` method before executing each workflow node. The substitution supports:

1. **Direct substitution**: `${env:VARIABLE_NAME}` → value
2. **String embedding**: `"text ${env:VAR} more text"` → `"text value more text"`
3. **Type preservation**: Single references return the actual value type

## Benefits

✅ **No Hardcoding** - IP addresses and networks configurable via `.env`
✅ **Environment-Specific** - Different values for dev/staging/prod
✅ **Centralized** - One place to update configuration
✅ **Version Control Safe** - Keep `.env` out of git, commit workflow definitions
✅ **Flexible** - Combine with node result references (`${node-id.result}`)

## Example Workflows

The following built-in workflows use environment variables:

- `workflows/network_discovery.json` - Uses `DEFAULT_SCAN_NETWORK`
- `workflows/nmap_recon.json` - Uses both `DEFAULT_SCAN_NETWORK` and `DEFAULT_SCAN_TARGET`

## See Also

- [Workflow System Documentation](WORKFLOWS.md)
- [Nmap Configuration](NMAP_CONFIGURATION.md)
- [Environment Configuration](.env)
