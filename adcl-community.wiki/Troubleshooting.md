# Troubleshooting Guide

Common issues and solutions for ADCL platform.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Service Issues](#service-issues)
3. [Agent Issues](#agent-issues)
4. [MCP Server Issues](#mcp-server-issues)
5. [Network Issues](#network-issues)
6. [Performance Issues](#performance-issues)
7. [Data Issues](#data-issues)
8. [Getting Help](#getting-help)

---

## Installation Issues

### Docker Not Running

**Symptom**:
```
Cannot connect to the Docker daemon
```

**Solutions**:
```bash
# Check Docker status
sudo systemctl status docker

# Start Docker
sudo systemctl start docker

# Enable Docker on boot
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port Already in Use

**Symptom**:
```
Error: Bind for 0.0.0.0:3000 failed: port is already allocated
```

**Solutions**:
```bash
# Find process using port
lsof -i :3000
sudo netstat -tulpn | grep :3000

# Kill the process
kill -9 <PID>

# Or change ADCL port in .env
FRONTEND_PORT=3001
```

### API Key Not Working

**Symptom**:
```
Authentication error: Invalid API key
```

**Solutions**:
```bash
# Verify API key format
echo $ANTHROPIC_API_KEY | grep -E '^sk-ant-api03-'

# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Ensure no spaces or quotes
# Correct: ANTHROPIC_API_KEY=sk-ant-api03-xxx
# Wrong:   ANTHROPIC_API_KEY="sk-ant-api03-xxx"
# Wrong:   ANTHROPIC_API_KEY= sk-ant-api03-xxx

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Restart after fixing
./clean-restart.sh
```

### Docker Compose Fails

**Symptom**:
```
ERROR: Version in "./docker-compose.yml" is unsupported
```

**Solutions**:
```bash
# Check Docker Compose version
docker-compose --version

# Should be 2.0+
# If not, upgrade:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## Service Issues

### Services Not Starting

**Symptom**:
```
Container exits immediately or health check fails
```

**Diagnosis**:
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs orchestrator
docker-compose logs frontend
docker-compose logs agent-mcp

# Check specific container
docker logs adcl-orchestrator
```

**Common Causes & Solutions**:

**1. Missing Environment Variables**:
```bash
# Check .env exists
ls -la .env

# Verify required variables
grep ANTHROPIC_API_KEY .env

# Restart after adding
./clean-restart.sh
```

**2. Port Conflicts**:
```bash
# Check ports in use
netstat -tulpn | grep -E '(3000|8000|9000)'

# Change ports in .env if needed
FRONTEND_PORT=3001
BACKEND_PORT=8001
```

**3. Resource Limits**:
```bash
# Check Docker resources
docker system info | grep -i memory

# Increase in Docker Desktop settings
# Or in daemon.json:
{
  "memory": "4G",
  "cpus": 2
}
```

### Backend API Not Responding

**Symptom**:
```
curl http://localhost:8000/health
curl: (7) Failed to connect
```

**Solutions**:
```bash
# Check backend running
docker-compose ps orchestrator

# View backend logs
docker-compose logs -f orchestrator

# Check port correct
grep BACKEND_PORT .env

# Restart backend
docker-compose restart orchestrator

# Full restart
./clean-restart.sh
```

### Frontend Not Loading

**Symptom**:
- White screen
- "Cannot connect to server"
- Loading forever

**Solutions**:
```bash
# Check frontend running
docker-compose ps frontend

# Check backend accessible
curl http://localhost:8000/health

# View frontend logs
docker-compose logs -f frontend

# Check browser console
# Open DevTools (F12) → Console tab
# Look for errors

# Hard refresh browser
# Chrome/Firefox: Ctrl+Shift+R
# Safari: Cmd+Option+R

# Clear browser cache
# Settings → Privacy → Clear browsing data

# Try different browser
```

### Registry Server Issues

**Symptom**:
```
Cannot fetch packages from registry
```

**Solutions**:
```bash
# Check registry running
docker-compose ps registry

# Test registry health
curl http://localhost:9000/health

# View registry logs
docker-compose logs registry

# Check registries.conf
cat registries.conf

# Refresh registry cache
curl -X POST http://localhost:8000/registries/refresh
```

---

## Agent Issues

### Agent Not Responding

**Symptom**:
- Agent starts but doesn't take action
- No tool calls happening
- Execution hangs

**Diagnosis**:
```bash
# View execution logs
docker-compose logs orchestrator | grep -i agent

# Check agent definition exists
ls agent-definitions/
cat agent-definitions/my_agent.json | jq

# Test API key
curl http://localhost:8000/agents/test-api-key
```

**Solutions**:

**1. Invalid API Key**:
```bash
# Verify key in .env
cat .env | grep ANTHROPIC_API_KEY

# Test key works
# See "API Key Not Working" section above
```

**2. MCP Server Down**:
```bash
# Check required MCPs running
docker-compose ps | grep mcp

# Restart MCPs
docker-compose restart agent-mcp file-tools-mcp
```

**3. Max Iterations Reached**:
```bash
# Check agent config
cat agent-definitions/my_agent.json | jq '.config.max_iterations'

# Increase if needed
{
  "config": {
    "max_iterations": 20  # Increase from default 10
  }
}
```

### Agent Making Wrong Tool Choices

**Symptom**:
- Agent uses inappropriate tools
- Agent ignores available tools
- Agent repeats same failed action

**Solutions**:

**1. Improve Persona**:
```json
{
  "persona": "You are an expert network analyst. When analyzing networks, you MUST:\n1. ALWAYS start with network_discovery\n2. THEN use port_scan on found hosts\n3. FINALLY use service_detection\nDo NOT skip steps. Do NOT guess."
}
```

**2. Verify MCP Access**:
```bash
# Check agent has access to required MCPs
cat agent-definitions/my_agent.json | jq '.mcp_servers'

# Verify MCPs are running
docker-compose ps | grep mcp
```

**3. Check Tool Descriptions**:
```bash
# View MCP tool list
curl http://localhost:7003/tools

# Ensure descriptions are clear
```

### Agent Loop / Infinite Execution

**Symptom**:
- Agent keeps repeating same actions
- Execution never completes
- Hits max_iterations

**Solutions**:

**1. Add Completion Criteria to Persona**:
```json
{
  "persona": "...When you have completed all analysis and written the report, STOP and return your findings. Do NOT continue indefinitely."
}
```

**2. Lower max_iterations**:
```json
{
  "config": {
    "max_iterations": 5  # Force early stop
  }
}
```

**3. Add Explicit Stop Condition**:
```json
{
  "persona": "...After writing the file, your task is COMPLETE. Return success message and STOP."
}
```

---

## MCP Server Issues

### MCP Not Starting

**Symptom**:
```
docker-compose ps
mcp-server  Exit 1
```

**Diagnosis**:
```bash
# View MCP logs
docker-compose logs my-mcp

# Check MCP files exist
ls mcp_servers/my_mcp/

# Verify Dockerfile
cat mcp_servers/my_mcp/Dockerfile
```

**Common Issues**:

**1. Python Dependencies**:
```bash
# Check requirements.txt
cat mcp_servers/my_mcp/requirements.txt

# Rebuild MCP
docker-compose build my-mcp
docker-compose up -d my-mcp
```

**2. Syntax Errors**:
```bash
# Validate Python syntax
python3 -m py_compile mcp_servers/my_mcp/server.py

# Check for errors in logs
docker-compose logs my-mcp | grep -i error
```

**3. Port Configuration**:
```bash
# Check port in .env
grep MY_MCP_PORT .env

# Check port in docker-compose.yml
grep -A5 "my-mcp:" docker-compose.yml
```

### MCP Tools Not Available

**Symptom**:
- Agent says "Tool X not found"
- MCP health check passes but tools don't work

**Solutions**:
```bash
# Test MCP directly
curl http://localhost:7000/tools

# Test tool call
curl -X POST http://localhost:7000/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool":"think","params":{"task":"test"}}'

# Check tool registered in server.py
grep "@tool" mcp_servers/my_mcp/server.py

# Verify tool name matches exactly
```

### MCP Permission Errors

**Symptom**:
```
Permission denied: /workspace/file.txt
```

**Solutions**:
```bash
# Check volume permissions
ls -la workspace/

# Fix ownership
sudo chown -R $USER:$USER workspace/

# Or run MCP as correct user
# In Dockerfile:
USER 1000:1000
```

---

## Network Issues

### Cannot Scan Network

**Symptom**:
- Nmap scans fail
- "Network unreachable"
- No hosts found

**Solutions**:

**1. Check Network Mode**:
```yaml
# docker-compose.yml
  nmap-mcp:
    network_mode: "host"  # Required for network scanning
```

**2. Verify Target Network Accessible**:
```bash
# Test from host
ping 192.168.1.1
nmap -sn 192.168.1.0/24

# Test from container
docker exec -it nmap-mcp ping 192.168.1.1
```

**3. Check Firewall**:
```bash
# Check firewall rules
sudo iptables -L

# Allow ICMP (ping)
sudo iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT
```

### WebSocket Connection Failed

**Symptom**:
- Real-time updates not working
- "WebSocket disconnected"
- Execution updates delayed

**Solutions**:
```bash
# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws/execute/test

# Verify backend WebSocket support
docker-compose logs orchestrator | grep -i websocket

# Check reverse proxy (if using)
# Ensure proxy passes Upgrade header:
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

---

## Performance Issues

### Slow Agent Execution

**Symptom**:
- Agent takes very long to respond
- High API costs
- Timeout errors

**Solutions**:

**1. Use Faster Model**:
```json
{
  "config": {
    "model": "claude-sonnet-4-5"  // Faster than opus
  }
}
```

**2. Reduce max_tokens**:
```json
{
  "config": {
    "max_tokens": 2048  // Reduce from 4096
  }
}
```

**3. Lower max_iterations**:
```json
{
  "config": {
    "max_iterations": 5  // Reduce from 10
  }
}
```

**4. Optimize Persona**:
```json
{
  "persona": "Be concise. Use minimum tool calls needed."
}
```

### High Memory Usage

**Symptom**:
```
docker stats
CONTAINER   CPU %   MEM USAGE
orchestrator 45%   3.5GB / 4GB
```

**Solutions**:
```bash
# Set memory limits
# docker-compose.yml:
services:
  orchestrator:
    deploy:
      resources:
        limits:
          memory: 2G

# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory: 8GB

# Clean up old containers
docker system prune -a
```

### Database Performance

**Symptom**:
- Slow queries
- High disk I/O
- Timeouts

**Solutions**:
```bash
# Clean old executions
curl -X DELETE http://localhost:8000/executions?older_than=30d

# Vacuum database (if PostgreSQL)
docker exec -it postgres psql -U adcl -c "VACUUM ANALYZE;"

# Add indexes (if missing)
docker exec -it postgres psql -U adcl -c "CREATE INDEX idx_execution_created ON executions(created_at);"
```

---

## Data Issues

### Lost Conversation History

**Symptom**:
- Previous conversations not showing
- History page empty

**Solutions**:
```bash
# Check history files exist
ls -la volumes/history/

# Check history MCP running
docker-compose ps history-mcp

# Test history MCP
curl http://localhost:7004/health

# Verify JSONL files readable
cat volumes/history/*.jsonl | jq
```

### Workspace Files Missing

**Symptom**:
- Agent can't find files in /workspace
- "File not found" errors

**Solutions**:
```bash
# Check workspace mounted
docker inspect adcl-orchestrator | grep -A10 Mounts

# Verify files exist on host
ls -la workspace/

# Check file permissions
sudo chown -R $USER:$USER workspace/

# Test file_tools MCP
curl -X POST http://localhost:7002/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool":"list_directory","params":{"path":"/workspace"}}'
```

---

## Getting Help

### Collect Debug Information

```bash
# 1. Service status
docker-compose ps > debug-status.txt

# 2. Service logs
docker-compose logs > debug-logs.txt

# 3. Configuration
cat .env > debug-env.txt
cat registries.conf > debug-registries.txt

# 4. Agent definitions
ls -la agent-definitions/ > debug-agents.txt

# 5. System info
docker version > debug-docker.txt
docker-compose version >> debug-docker.txt
uname -a >> debug-docker.txt

# Create archive
tar -czf adcl-debug-$(date +%Y%m%d).tar.gz debug-*.txt
```

### Report Issue on GitHub

1. Go to: https://github.com/adcl-io/adcl-community/issues
2. Click "New Issue"
3. Include:
   - **Description**: What happened vs. what you expected
   - **Steps to Reproduce**: Detailed steps
   - **Logs**: Relevant log snippets
   - **Environment**: OS, Docker version, ADCL version
   - **Configuration**: .env settings (redact secrets!)

### Join Community Discussions

- **GitHub Discussions**: https://github.com/adcl-io/adcl-community/discussions
- **Discord** (if available): See README for invite link

---

## Quick Fixes

### Nuclear Option: Clean Restart

```bash
# Stop everything
docker-compose down

# Remove all containers and volumes
docker-compose down -v

# Clean Docker system
docker system prune -a

# Rebuild from scratch
./clean-restart.sh
```

**Warning**: This deletes all data including conversation history.

### Reset to Defaults

```bash
# Backup current config
cp .env .env.backup
cp registries.conf registries.conf.backup

# Reset .env
cp .env.example .env
# Edit and add your API key

# Restart
./clean-restart.sh
```

---

## Next Steps

- **[FAQ](FAQ)** - Frequently asked questions
- **[Configuration Guide](Configuration-Guide)** - Advanced configuration
- **[Getting Started](Getting-Started)** - Setup guide

---

**Still stuck?** [Open an issue on GitHub](https://github.com/adcl-io/adcl-community/issues)
