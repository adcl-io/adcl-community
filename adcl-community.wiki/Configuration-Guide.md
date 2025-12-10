# Configuration Guide

Learn how to configure ADCL for your environment and use case.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Port Configuration](#port-configuration)
3. [Model Configuration](#model-configuration)
4. [Network Configuration](#network-configuration)
5. [Security Configuration](#security-configuration)
6. [Storage Configuration](#storage-configuration)
7. [Registry Configuration](#registry-configuration)
8. [Advanced Configuration](#advanced-configuration)

---

## Environment Variables

### Required Variables

**ANTHROPIC_API_KEY** (required):
```bash
# Your Anthropic API key for Claude models
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

Get your key at: https://console.anthropic.com/

### Optional Variables

**DEFAULT_SCAN_NETWORK**:
```bash
# Default network for security scans
DEFAULT_SCAN_NETWORK=192.168.50.0/24
```

**LINEAR_API_KEY**:
```bash
# Linear API key for issue tracking integration
LINEAR_API_KEY=lin_api_your-key-here
```

**AWS Bedrock** (if using AWS models):
```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-west-2
AWS_BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Example .env File

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

# Optional - Security Scanning
DEFAULT_SCAN_NETWORK=192.168.1.0/24

# Optional - Linear Integration
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxx

# Optional - AWS Bedrock
# AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXX
# AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxx
# AWS_REGION=us-west-2

# Optional - Custom Ports
# FRONTEND_PORT=3000
# BACKEND_PORT=8000
# REGISTRY_PORT=9000

# Optional - Logging
# LOG_LEVEL=INFO
# DEBUG=false

# Optional - Execution
# MAX_EXECUTION_TIME=3600
# MAX_ITERATIONS=10
```

---

## Port Configuration

### Default Ports

**Frontend & Backend**:
```bash
FRONTEND_PORT=3000      # Web UI
BACKEND_PORT=8000       # API
REGISTRY_PORT=9000      # Package registry
```

**MCP Servers**:
```bash
AGENT_PORT=7000         # AI reasoning
FILE_TOOLS_PORT=7002    # File operations
NMAP_PORT=7003          # Network scanning
HISTORY_PORT=7004       # Conversation history
KALI_PORT=7005          # Penetration testing
LINEAR_PORT=7006        # Linear integration
```

### Changing Ports

**Edit .env**:
```bash
# Change frontend from 3000 to 3001
FRONTEND_PORT=3001

# Change backend from 8000 to 8080
BACKEND_PORT=8080
```

**Restart platform**:
```bash
./clean-restart.sh
```

**Update firewall rules** (if applicable):
```bash
# Allow new ports
sudo ufw allow 3001/tcp
sudo ufw allow 8080/tcp
```

---

## Model Configuration

### Model Selection

Configure which AI models agents use.

**Via Agent Definition**:
```json
{
  "name": "my_agent",
  "config": {
    "model": "claude-sonnet-4-5",
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

**Available Models**:

**Anthropic Claude**:
```
claude-sonnet-4-5     # Fast, efficient (recommended)
claude-opus-4-5       # Most capable, slower
```

**AWS Bedrock**:
```
anthropic.claude-3-5-sonnet-20241022-v2:0
```

**Custom OpenAI-Compatible**:
```
custom-model-name
```

### Model Parameters

**temperature** (0.0 - 1.0):
```json
{
  "temperature": 0.0   // Deterministic, focused
  "temperature": 0.5   // Balanced
  "temperature": 1.0   // Creative, exploratory
}
```

**max_tokens**:
```json
{
  "max_tokens": 2048   // Short responses
  "max_tokens": 4096   // Standard (default)
  "max_tokens": 8192   // Long responses
  "max_tokens": 16384  // Very long responses
}
```

**max_iterations** (agent loop limit):
```json
{
  "max_iterations": 5    // Quick tasks
  "max_iterations": 10   // Standard (default)
  "max_iterations": 20   // Complex tasks
}
```

### Custom OpenAI-Compatible Endpoints

**Configure endpoint**:
```bash
# .env
OPENAI_API_BASE=https://api.custom-provider.com/v1
OPENAI_API_KEY=your-custom-api-key
```

**Use in agent**:
```json
{
  "config": {
    "model": "gpt-4",
    "api_base": "${env:OPENAI_API_BASE}"
  }
}
```

---

## Network Configuration

### Docker Network

**Default configuration**:
```yaml
# docker-compose.yml
networks:
  adcl_network:
    driver: bridge
```

**Custom network**:
```yaml
networks:
  adcl_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Host Network Mode

Required for network scanning tools (nmap):

```yaml
# docker-compose.yml
  nmap-mcp:
    network_mode: "host"
```

**Note**: Host mode gives container full network access.

### Firewall Configuration

**Allow ADCL ports**:
```bash
# Frontend
sudo ufw allow 3000/tcp

# Backend API
sudo ufw allow 8000/tcp

# Registry
sudo ufw allow 9000/tcp

# Optional: MCP servers (if accessed externally)
sudo ufw allow 7000:7010/tcp
```

---

## Security Configuration

### API Authentication

**Note**: Current version has no authentication (single-user)

**Production setup** (planned feature):
```json
{
  "authentication": {
    "enabled": true,
    "type": "jwt",
    "secret": "${env:JWT_SECRET}",
    "expiry": 3600
  }
}
```

### Webhook Security

**Secret verification**:
```bash
# .env
WEBHOOK_SECRET=your-random-secret-here
```

**Use in trigger**:
```json
{
  "config": {
    "secret": "${env:WEBHOOK_SECRET}",
    "validate_signature": true
  }
}
```

### MCP Access Control

**Limit MCP access per agent**:
```json
{
  "name": "restricted_agent",
  "mcp_servers": ["file_tools"],  // Only file access
  "config": {
    "allowed_paths": ["/workspace"]  // Only /workspace
  }
}
```

### HTTPS/TLS

**Production setup** (behind reverse proxy):

**nginx configuration**:
```nginx
server {
    listen 443 ssl;
    server_name adcl.company.com;

    ssl_certificate /etc/ssl/certs/adcl.crt;
    ssl_certificate_key /etc/ssl/private/adcl.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## Storage Configuration

### Volume Mounts

**Default volumes**:
```yaml
# docker-compose.yml
volumes:
  - ./volumes/data:/data              # User data
  - ./volumes/history:/history        # Conversation history
  - ./workspace:/workspace            # Shared workspace
  - ./logs:/logs                      # Application logs
```

### Data Persistence

**Backup important directories**:
```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf adcl-backup-$DATE.tar.gz \
  volumes/ \
  workspace/ \
  agent-definitions/ \
  agent-teams/ \
  workflows/ \
  .env
```

### Log Rotation

**Configure logrotate**:
```bash
# /etc/logrotate.d/adcl
/path/to/adcl/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 docker docker
}
```

### Disk Space Management

**Monitor disk usage**:
```bash
# Check disk space
df -h

# Check ADCL directories
du -sh volumes/
du -sh logs/
du -sh workspace/
```

**Clean old logs**:
```bash
# Remove logs older than 30 days
find logs/ -name "*.log" -mtime +30 -delete

# Compress old logs
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

---

## Registry Configuration

### registries.conf

**Location**: `./registries.conf`

**Format**: INI

**Example**:
```ini
[official]
name=ADCL Official Repository
baseurl=http://localhost:9000
enabled=1
gpgcheck=0
priority=10

[community]
name=Community Packages
baseurl=http://community.adcl.io
enabled=1
gpgcheck=0
priority=20

[company]
name=Company Internal
baseurl=http://registry.company.internal
enabled=1
gpgcheck=1
gpgkey=http://registry.company.internal/gpg-key.asc
priority=5
```

**Parameters**:
- **name**: Human-readable name
- **baseurl**: Registry server URL
- **enabled**: 1=enabled, 0=disabled
- **gpgcheck**: 1=verify signatures, 0=no verification
- **gpgkey**: URL to GPG public key
- **priority**: Lower = higher priority

---

## Advanced Configuration

### Execution Limits

**Global limits**:
```bash
# .env
MAX_EXECUTION_TIME=3600    # 1 hour max per execution
MAX_ITERATIONS=10          # 10 agent loop iterations max
MAX_CONCURRENT_EXECUTIONS=5  # 5 simultaneous executions
```

**Per-agent limits**:
```json
{
  "name": "my_agent",
  "config": {
    "timeout": 1800,         // 30 minutes
    "max_iterations": 15,
    "max_tool_calls": 50
  }
}
```

### Logging Configuration

**Log levels**:
```bash
# .env
LOG_LEVEL=INFO    # DEBUG, INFO, WARNING, ERROR, CRITICAL
DEBUG=false       # Enable debug mode
```

**Log format**:
```python
# backend/config/logging.py
LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'format': '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/adcl.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    }
}
```

### Performance Tuning

**Docker resource limits**:
```yaml
# docker-compose.yml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

**Database optimization** (if using PostgreSQL):
```sql
-- Increase connection pool
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
```

**Cache configuration**:
```bash
# .env
ENABLE_CACHE=true
CACHE_TTL=3600          # 1 hour
CACHE_MAX_SIZE=1000     # Max items
```

### Custom MCP Server Ports

**Add custom MCP**:
```bash
# .env
WEATHER_MCP_PORT=7010
SLACK_MCP_PORT=7011
EMAIL_MCP_PORT=7012
```

**docker-compose.yml**:
```yaml
  weather-mcp:
    build: ./mcp_servers/weather_mcp
    environment:
      - PORT=${WEATHER_MCP_PORT}
    ports:
      - "${WEATHER_MCP_PORT}:${WEATHER_MCP_PORT}"
```

---

## Configuration Validation

### Check Configuration

```bash
# Validate .env file
./scripts/validate-config.sh

# Check all services configured
docker-compose config

# Verify ports available
netstat -tuln | grep -E '(3000|8000|9000|700[0-9])'

# Test API key
curl -X POST http://localhost:8000/agents/test-api-key
```

### Common Configuration Issues

**Issue**: Port conflict
```bash
# Find conflicting process
lsof -i :3000

# Change port in .env
FRONTEND_PORT=3001
```

**Issue**: Invalid API key
```bash
# Verify key format
echo $ANTHROPIC_API_KEY | grep -E '^sk-ant-api03-'

# Test key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

**Issue**: MCP not accessible
```bash
# Check MCP running
docker-compose ps | grep mcp

# Test MCP health
curl http://localhost:7000/health

# Check network
docker network inspect adcl_network
```

---

## Next Steps

- **[Troubleshooting Guide](Troubleshooting)** - Fix configuration issues
- **[Getting Started](Getting-Started)** - Initial setup guide
- **[Platform Overview](Platform-Overview)** - Understand architecture

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
