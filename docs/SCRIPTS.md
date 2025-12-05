# Management Scripts

Convenient shell scripts for managing the MCP Agent Platform.

## Quick Reference

```bash
./start.sh              # Start all services
./stop.sh               # Stop all services
./status.sh             # Check service status
./logs.sh [service]     # View logs
./restart-api.sh        # Restart API server
./restart-agent.sh      # Restart agent MCP
./restart-frontend.sh   # Restart frontend
```

## Main Scripts

### `start.sh` - Start Platform

Starts all services in detached mode (runs in background).

```bash
./start.sh
```

**What it does:**
- Checks if Docker is running
- Creates `.env` file if it doesn't exist
- Builds and starts all containers with `docker-compose up -d --build`
- Shows service status
- Displays access URLs

**Services started:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Agent MCP: http://localhost:7000
- File Tools: http://localhost:7002
- Nmap Recon: http://localhost:7003

---

### `stop.sh` - Stop Platform

Stops all running services (without removing containers).

```bash
./stop.sh
```

**What it does:**
- Checks if Docker is running
- Stops all containers with `docker-compose stop`
- Preserves container state

**To fully remove containers:**
```bash
docker-compose down
```

---

### `status.sh` - Check Status

Comprehensive status check of all services.

```bash
./status.sh
```

**What it shows:**
- Container status (Up/Down)
- Service endpoints
- Health check results
- Useful commands

**Example output:**
```
📊 Container Status:
test3-dev-team_agent_1          Up      0.0.0.0:7000->7000/tcp
test3-dev-team_orchestrator_1   Up      0.0.0.0:8000->8000/tcp
...

🔍 Health Checks:
  ✅ API Server (port 8000) - UP
  ✅ Agent MCP (port 7000) - UP
  ✅ File Tools (port 7002) - UP
  ✅ Nmap Recon (port 7003) - UP
  ✅ Frontend (port 3000) - UP
```

---

### `logs.sh` - View Logs

View logs for specific services or all services.

```bash
# View all logs
./logs.sh

# View specific service
./logs.sh api
./logs.sh agent
./logs.sh frontend
./logs.sh file_tools
./logs.sh nmap_recon
```

**Available services:**
- `all` (default) - All services
- `api` - API server (orchestrator)
- `agent` - Agent MCP server
- `frontend` - React frontend
- `file_tools` - File operations MCP
- `nmap_recon` - Nmap reconnaissance MCP

**Examples:**
```bash
# Follow all logs
./logs.sh

# Just API server logs
./logs.sh api

# Agent logs
./logs.sh agent
```

Press `Ctrl+C` to exit log view.

---

## Service-Specific Scripts

### `restart-api.sh` - Restart API Server

Restarts the orchestrator (API server) service.

```bash
./restart-api.sh
```

**Use when:**
- Backend code changes
- Configuration updates
- API server issues

---

### `restart-agent.sh` - Restart Agent MCP

Restarts the agent MCP server.

```bash
./restart-agent.sh
```

**Use when:**
- Agent code changes
- API key updates
- Agent server issues

---

### `restart-frontend.sh` - Restart Frontend

Restarts the React frontend.

```bash
./restart-frontend.sh
```

**Use when:**
- Frontend code changes (if not hot-reloading)
- Frontend container issues

---

## Troubleshooting

### Scripts Not Working

**Issue:** `Permission denied` when running scripts

**Fix:**
```bash
chmod +x *.sh
```

**Issue:** `docker-compose: command not found`

**Fix:** Install Docker Compose or use `docker compose` (without hyphen) on newer Docker versions.

Edit scripts to replace `docker-compose` with `docker compose`:
```bash
sed -i 's/docker-compose/docker compose/g' *.sh
```

---

### Services Not Starting

**Check Docker:**
```bash
docker info
```

**Check ports in use:**
```bash
netstat -tulpn | grep -E '3000|7000|7002|7003|8000'
```

**View detailed logs:**
```bash
./logs.sh [service]
```

---

### Container Issues

**Rebuild specific service:**
```bash
docker-compose build --no-cache [service]
docker-compose up -d [service]
```

**Remove and recreate all containers:**
```bash
docker-compose down
./start.sh
```

**Full cleanup:**
```bash
docker-compose down -v  # Removes volumes too
./start.sh
```

---

## Common Workflows

### Development Workflow

```bash
# Start platform
./start.sh

# Check status
./status.sh

# Make code changes...

# Restart affected service
./restart-api.sh        # If backend changed
./restart-frontend.sh   # If frontend changed
./restart-agent.sh      # If agent changed

# View logs
./logs.sh api

# Stop when done
./stop.sh
```

---

### Debugging Issues

```bash
# Check overall status
./status.sh

# View logs for failing service
./logs.sh api

# Restart service
./restart-api.sh

# If still failing, view detailed logs
docker-compose logs --tail=100 orchestrator

# Check container health
docker-compose ps
docker inspect test3-dev-team_orchestrator_1
```

---

### Clean Start

```bash
# Stop everything
./stop.sh

# Remove containers and volumes
docker-compose down -v

# Rebuild and start fresh
./start.sh
```

---

## Advanced Usage

### Individual Service Management

```bash
# Stop specific service
docker-compose stop orchestrator

# Start specific service
docker-compose start orchestrator

# Restart with rebuild
docker-compose up -d --build orchestrator

# View service logs (last 50 lines)
docker-compose logs --tail=50 orchestrator

# Follow logs in real-time
docker-compose logs -f orchestrator
```

---

### Docker Compose Commands

```bash
# List containers
docker-compose ps

# List all containers (including stopped)
docker-compose ps -a

# Execute command in container
docker-compose exec orchestrator bash

# View resource usage
docker-compose top

# Validate compose file
docker-compose config

# Pull latest images
docker-compose pull

# Remove unused images
docker image prune
```

---

## Script Customization

All scripts use `docker-compose` command. If you're using newer Docker with `docker compose` (no hyphen), you can:

1. Use sed to replace in all scripts:
```bash
sed -i 's/docker-compose/docker compose/g' *.sh
```

2. Or create an alias:
```bash
alias docker-compose='docker compose'
```

---

## Environment Variables

Scripts respect environment variables from `.env` file:

```bash
ANTHROPIC_API_KEY=sk-...   # For real AI responses
AGENT_PORT=7000             # Agent MCP port
FILE_TOOLS_PORT=7002        # File tools port
NMAP_PORT=7003              # Nmap port
```

Edit `.env` to customize ports and API keys.

---

## CI/CD Integration

These scripts can be used in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Start services
  run: ./start.sh

- name: Wait for services
  run: |
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

- name: Run tests
  run: pytest

- name: Stop services
  run: ./stop.sh
```

---

## Support

For issues with scripts:
1. Check Docker is running: `docker info`
2. Check logs: `./logs.sh [service]`
3. Check status: `./status.sh`
4. Try clean restart: `docker-compose down && ./start.sh`

---

**Last Updated:** 2025-10-13
**Version:** 1.0
