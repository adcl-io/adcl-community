# Quick Start Guide

## 🚀 Starting the Platform

```bash
./start.sh
```

**Access points:**
- 🌐 **Frontend:** http://localhost:3000
- 🔌 **API:** http://localhost:8000
- 🤖 **Agent:** http://localhost:7000
- 📁 **File Tools:** http://localhost:7002
- 🔍 **Nmap:** http://localhost:7003

---

## 📊 Checking Status

```bash
./status.sh
```

Shows:
- Container status (Up/Down)
- Health checks for all services
- Useful commands

---

## 📋 Viewing Logs

```bash
# All services
./logs.sh

# Specific service
./logs.sh api
./logs.sh agent
./logs.sh frontend
./logs.sh file_tools
./logs.sh nmap_recon
```

Press `Ctrl+C` to exit logs.

---

## 🔄 Restarting Services

### Clean Restart (Recommended)
```bash
./clean-restart.sh      # Clean restart everything
```
**Why use this:** Prevents ContainerConfig errors by stopping and removing containers before restarting.

### Restart Individual Services
```bash
./restart-api.sh        # Restart API server
./restart-agent.sh      # Restart agent
./restart-frontend.sh   # Restart frontend
```

---

## 🛑 Stopping the Platform

```bash
./stop.sh
```

---

## 💡 Common Tasks

### Run a Workflow

1. Open http://localhost:3000
2. Click "🔍 Nmap Recon" or "Hello World"
3. Click "Execute Workflow"
4. Watch real-time execution
5. View results in sidebar

### Check API Health

```bash
curl http://localhost:8000/health
```

### View MCP Servers

```bash
curl http://localhost:8000/mcp/servers | jq
```

### Execute Workflow via API

```bash
curl -X POST http://localhost:8000/workflows/execute \
  -H "Content-Type: application/json" \
  -d @workflows/hello_world.json
```

---

## 🔧 Troubleshooting

### ContainerConfig Error?

```bash
./clean-restart.sh       # Clean restart fixes this!
```

### Service Down?

```bash
./status.sh              # Check what's down
./logs.sh [service]      # View error logs
./clean-restart.sh       # Clean restart usually fixes it
```

### Complete Reset

```bash
./stop.sh
docker-compose down -v
./start.sh
```

### View Specific Errors

```bash
# Last 50 lines of API logs
docker-compose logs --tail=50 orchestrator

# Follow agent logs
docker-compose logs -f agent
```

---

## 📚 More Help

- **Full Documentation:** [README.md](README.md)
- **Script Reference:** [SCRIPTS.md](SCRIPTS.md)
- **Architecture:** [arch.md](arch.md)
- **Nmap Integration:** [NMAP_INTEGRATION.md](NMAP_INTEGRATION.md)
- **ContainerConfig Fix:** [CONTAINERCONFIG_ERROR_FIXED.md](CONTAINERCONFIG_ERROR_FIXED.md)
- **Parameter Substitution:** [PARAMETER_SUBSTITUTION_FIXED.md](PARAMETER_SUBSTITUTION_FIXED.md)

---

**Need Help?**
1. Run `./status.sh` to check service status
2. Run `./logs.sh [service]` to view error logs
3. Check [SCRIPTS.md](SCRIPTS.md) for troubleshooting

---

**Version:** 1.0
**Last Updated:** 2025-10-13
