# Kali MCP Installation Guide

The Kali MCP is **not included in auto-install** due to its long build time (~15-20 minutes). This prevents it from blocking the orchestrator API startup.

## Why Manual Installation?

The Kali Linux base image is large (~1GB+) and includes many penetration testing tools that take significant time to download and install. Auto-installing it would delay the entire platform startup.

## Installation Methods

### Option 1: Manual Docker Build (Recommended)

Build the Kali MCP image and let the orchestrator manage it:

```bash
# From the project root
cd mcp_servers/kali

# Build the image (this will take 15-20 minutes)
docker build -t mcp-kali:1.0.0 .

# The orchestrator will detect and start it automatically on next restart
docker-compose restart orchestrator
```

### Option 2: Install via API

Use the orchestrator's MCP installation endpoint:

```bash
# Get the kali package from registry
curl -X POST http://localhost:8000/mcps/install \
  -H "Content-Type: application/json" \
  -d '{"name": "kali", "version": "1.0.0"}'
```

### Option 3: Add to Auto-Install

If you don't mind longer startup times, add it back to auto-install:

**Edit `.env`:**
```bash
AUTO_INSTALL_MCPS=agent,file_tools,nmap_recon,kali,history
```

**Edit `configs/orchestrator.yaml`:**
```yaml
auto_install:
  mcps:
    - "agent"
    - "file_tools"
    - "nmap_recon"
    - "kali"  # Add this line
    - "history"
```

Then restart:
```bash
docker-compose restart orchestrator
```

**⚠️ Warning**: The orchestrator will block during Kali's build, delaying API availability.

## Verify Installation

Check if Kali MCP is installed and running:

```bash
# Check container status
docker ps | grep kali

# Check via API
curl http://localhost:8000/mcps/installed | jq '.[] | select(.name=="kali")'

# Test Kali MCP directly
curl http://localhost:7005/health
```

## Build Progress Monitoring

The Kali build process downloads and installs many tools. You can monitor progress:

```bash
# Watch orchestrator logs
docker logs -f demo-sandbox_orchestrator_1

# Or if building manually
docker logs -f mcp-kali
```

## What Gets Installed

The Kali MCP includes these tools:

- **nikto** - Web server scanner
- **dirb** - Web content scanner
- **sqlmap** - SQL injection testing
- **metasploit-framework** - Exploitation framework
- **hydra** - Network authentication cracker
- **wpscan** - WordPress scanner
- **dnsenum** - DNS enumeration
- **sublist3r** - Subdomain discovery

Plus all required Python dependencies.

## Troubleshooting

### Build Fails

If the build fails due to network issues:

```bash
# Clean up partial images
docker image prune -f

# Retry the build
docker build --no-cache -t mcp-kali:1.0.0 mcp_servers/kali/
```

### Container Won't Start

Check logs for issues:

```bash
docker logs mcp-kali
```

Common issues:
- Port 7005 already in use
- Insufficient disk space (needs ~2GB)
- Missing capabilities (NET_RAW, NET_ADMIN)

### Tools Not Working

Test individual tools inside the container:

```bash
# Enter container
docker exec -it mcp-kali bash

# Test a tool
nikto -Version
```

## Performance Considerations

**Build Time**: 15-20 minutes (depends on internet speed and system)
**Image Size**: ~1.5GB
**Memory**: Minimum 512MB, recommended 1GB
**Disk Space**: ~2GB total (includes base image)

## Alternative: Pre-built Image

If you use Kali MCP frequently, consider:

1. Build once and save the image:
```bash
docker save mcp-kali:1.0.0 | gzip > kali-mcp.tar.gz
```

2. Load on other systems:
```bash
gunzip -c kali-mcp.tar.gz | docker load
```

This avoids rebuilding on every deployment.

## Security Notice

Remember: **DEFENSIVE USE ONLY**

Only use Kali MCP on:
- Systems you own
- Systems you have written authorization to test
- Authorized penetration testing engagements

Unauthorized use of penetration testing tools is illegal.

## Support

For issues:
1. Check logs: `docker logs mcp-kali`
2. Verify tools: `docker exec mcp-kali which nikto`
3. Check GitHub issues for the ADCL project
4. Review the main [README.md](README.md) for tool usage

---

**Quick Start Summary**:

```bash
# Build Kali MCP
cd mcp_servers/kali && docker build -t mcp-kali:1.0.0 .

# Restart orchestrator to detect it
cd ../.. && docker-compose restart orchestrator

# Verify
curl http://localhost:7005/health
```
