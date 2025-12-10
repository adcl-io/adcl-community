# Getting Started with ADCL

This guide will help you install, configure, and start using the ADCL platform.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Starting the Platform](#starting-the-platform)
5. [Accessing the UI](#accessing-the-ui)
6. [First Steps](#first-steps)
7. [Next Steps](#next-steps)

---

## Prerequisites

### System Requirements

**Operating System**:
- Linux (Ubuntu 20.04+, Debian 11+)
- macOS (Intel or Apple Silicon)
- Windows with WSL2

**Software**:
- **Docker**: 20.10+ (required)
- **Docker Compose**: 2.0+ (required)
- **Git**: 2.0+ (for cloning repository)
- **Bash**: 4.0+ (for management scripts)

**Hardware**:
- **CPU**: 2+ cores recommended
- **Memory**: 4GB RAM minimum, 8GB+ recommended
- **Disk**: 10GB free space
- **Network**: Internet connection for API access and package downloads

### API Keys

You'll need an **Anthropic API key** to use Claude AI models:

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Save it securely (you'll need it for configuration)

**Optional API Keys**:
- **Linear API Key** - For Linear issue tracking integration (optional)

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone the ADCL repository
git clone https://github.com/adcl-io/adcl-community.git

# Navigate to the directory
cd adcl-community
```

### Step 2: Verify Docker Installation

```bash
# Check Docker version
docker --version
# Should show: Docker version 20.10.0 or higher

# Check Docker Compose version
docker-compose --version
# Should show: Docker Compose version 2.0.0 or higher

# Verify Docker is running
docker ps
# Should show a list of containers (may be empty)
```

**Troubleshooting Docker**:
- If Docker is not installed, follow the [official Docker installation guide](https://docs.docker.com/get-docker/)
- Ensure your user is in the `docker` group to run Docker without `sudo`:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env
```

### Step 2: Configure API Keys

Edit the `.env` file with your preferred text editor:

```bash
# Open with nano
nano .env

# Or with vim
vim .env

# Or with VS Code
code .env
```

**Required Settings**:

```bash
# REQUIRED: Your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Optional: Default network for security scans
DEFAULT_SCAN_NETWORK=192.168.50.0/24

# Optional: Linear API key for issue tracking
LINEAR_API_KEY=lin_api_your-key-here
```

**Important**:
- Replace `sk-ant-api03-your-actual-key-here` with your actual Anthropic API key
- Never commit your `.env` file to version control
- The `.env` file is already in `.gitignore`

### Step 3: Review Port Configuration (Optional)

Default ports used by ADCL:

```bash
# Web UI
FRONTEND_PORT=3000

# Backend API
BACKEND_PORT=8000

# Registry Server
REGISTRY_PORT=9000

# MCP Servers
AGENT_PORT=7000
FILE_TOOLS_PORT=7002
NMAP_PORT=7003
HISTORY_PORT=7004
KALI_PORT=7005
LINEAR_PORT=7006
```

If these ports conflict with existing services, you can change them in `.env`.

---

## Starting the Platform

### Option 1: Clean Restart (Recommended for First Time)

```bash
# Start with clean state
./clean-restart.sh
```

This script will:
1. Stop any running ADCL containers
2. Remove old containers and volumes
3. Rebuild images with latest changes
4. Start all services
5. Wait for health checks to pass

**Expected output**:
```
Stopping all services...
Removing containers and volumes...
Building images...
Starting services...
✓ Backend API is healthy
✓ Frontend is running
✓ Registry server is healthy
✓ All MCP servers are running

ADCL is ready!
Frontend: http://localhost:3000
Backend API: http://localhost:8000
Registry: http://localhost:9000
```

### Option 2: Standard Start

```bash
# Start all services
./start.sh
```

Use this for subsequent starts after initial setup.

### Option 3: Development Mode

```bash
# Start with auto-reload on code changes
./start.sh --dev
```

Use this if you're developing or modifying ADCL code.

---

## Accessing the UI

### Web Interface

Open your browser and navigate to:

```
http://localhost:3000
```

You should see the ADCL web interface with the following pages:

- **Playground** - Chat with agents and teams
- **History** - View past conversations
- **Agents** - Manage autonomous agents
- **Teams** - Create multi-agent teams
- **MCP Servers** - Browse tool servers
- **Workflows** - Visual workflow builder
- **Triggers** - Automation management
- **Registry** - Install packages
- **Models** - Configure AI models

### API Documentation

Access the interactive API docs at:

```
http://localhost:8000/docs
```

This provides:
- Interactive API testing
- Complete endpoint documentation
- Request/response schemas
- Authentication details

### Health Checks

Verify services are running:

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
{"status": "healthy"}

# Check all services
./status.sh
```

---

## First Steps

### 1. Chat with Your First Agent

Let's test the platform by chatting with an AI agent:

1. **Navigate to Playground**:
   - Open http://localhost:3000
   - Click "Playground" in the sidebar

2. **Select an Agent**:
   - Click the dropdown at the top
   - Select "Security Analyst" or "Code Reviewer"

3. **Start a Conversation**:
   - Type: "What tools do you have access to?"
   - Press Enter or click Send

4. **Observe the Response**:
   - The agent will list available MCP tools
   - You'll see real-time thinking and tool selection

**Example conversation**:
```
You: What tools do you have access to?

Agent: I have access to the following tools:
- network_discovery: Scan network for active hosts
- port_scan: Scan open ports on targets
- service_detection: Identify services and versions
- think: AI reasoning for complex analysis
- code: Generate code solutions
```

### 2. Run an Autonomous Task

Let's have an agent perform a task autonomously:

1. **Navigate to Agents Page**:
   - Click "Agents" in the sidebar
   - You'll see a list of pre-configured agents

2. **Select Code Reviewer**:
   - Click on "Code Reviewer" agent

3. **Run a Task**:
   - In the "Task" field, enter:
     ```
     List the files in /workspace and tell me what you find
     ```
   - Click "Run Task"

4. **Watch Execution**:
   - The agent will autonomously:
     - Call the `list_directory` tool
     - Analyze the results
     - Provide a summary
   - You'll see each tool call and decision in real-time

### 3. Explore MCP Servers

View available tool servers:

1. **Navigate to MCP Servers**:
   - Click "MCP Servers" in the sidebar

2. **Browse Available MCPs**:
   - **agent** (port 7000) - AI reasoning capabilities
   - **file_tools** (port 7002) - File operations
   - **nmap_recon** (port 7003) - Network scanning

3. **Click on a Server**:
   - View available tools
   - See tool descriptions
   - Check server status (running/stopped)

### 4. Create Your First Workflow

Build a simple visual workflow:

1. **Navigate to Workflows**:
   - Click "Workflows" in the sidebar

2. **Create New Workflow**:
   - Click "New Workflow"
   - Give it a name: "Hello World"

3. **Add Nodes**:
   - Drag "agent" MCP from the left panel onto canvas
   - Drag "file_tools" MCP onto canvas

4. **Connect Nodes**:
   - Drag from "agent" output to "file_tools" input
   - This creates a data flow connection

5. **Configure Agent Node**:
   - Click on agent node
   - Set tool: `think`
   - Set input: `{"task": "Generate a hello world message"}`

6. **Configure File Tools Node**:
   - Click on file_tools node
   - Set tool: `write_file`
   - Set path: `/workspace/hello.txt`
   - Set content: `${agent.output}` (references agent output)

7. **Execute Workflow**:
   - Click "Execute" button
   - Watch nodes light up as they execute
   - Check `/workspace/hello.txt` for output

### 5. Install a Package from Registry

Try the package management system:

1. **Navigate to Registry**:
   - Click "Registry" in the sidebar

2. **Browse Teams**:
   - Click "Teams" tab
   - You'll see available team packages

3. **Install a Team**:
   - Find "Security Analysis Team"
   - Click "Install"
   - Wait for installation to complete

4. **Use the Installed Team**:
   - Go to Playground
   - Select the newly installed team
   - Ask it: "What's your team structure?"

---

## Verifying Installation

### Check Services Status

```bash
# View status of all services
./status.sh
```

**Expected output**:
```
✓ orchestrator - running (healthy)
✓ frontend - running
✓ registry - running (healthy)
✓ agent-mcp - running (healthy)
✓ file-tools-mcp - running (healthy)
✓ nmap-mcp - running (healthy)
```

### View Logs

```bash
# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs orchestrator
docker-compose logs frontend
docker-compose logs agent-mcp

# Follow logs in real-time
docker-compose logs -f orchestrator
```

### Test API

```bash
# Test health endpoint
curl http://localhost:8000/health

# List available agents
curl http://localhost:8000/agents

# List MCP servers
curl http://localhost:8000/mcp/servers
```

---

## Troubleshooting Installation

### Issue: Port Already in Use

**Error**: `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solution**:
1. Find and stop the conflicting service:
   ```bash
   # Find process using port 3000
   lsof -i :3000

   # Kill the process (replace PID)
   kill -9 <PID>
   ```

2. Or change ADCL ports in `.env`:
   ```bash
   FRONTEND_PORT=3001
   BACKEND_PORT=8001
   ```

### Issue: API Key Not Working

**Error**: `Authentication error` or `Invalid API key`

**Solution**:
1. Verify your API key in `.env`:
   ```bash
   cat .env | grep ANTHROPIC_API_KEY
   ```

2. Ensure no extra spaces or quotes:
   ```bash
   # Correct
   ANTHROPIC_API_KEY=sk-ant-api03-xxx

   # Incorrect
   ANTHROPIC_API_KEY="sk-ant-api03-xxx"
   ANTHROPIC_API_KEY= sk-ant-api03-xxx
   ```

3. Restart services after changing `.env`:
   ```bash
   ./clean-restart.sh
   ```

### Issue: Services Not Starting

**Error**: Containers exit immediately or health checks fail

**Solution**:
1. Check Docker resources:
   ```bash
   # Ensure Docker has enough memory (4GB minimum)
   docker system info | grep -i memory
   ```

2. View service logs:
   ```bash
   docker-compose logs orchestrator
   docker-compose logs agent-mcp
   ```

3. Clean restart:
   ```bash
   ./clean-restart.sh
   ```

4. Verify Docker network:
   ```bash
   docker network ls
   docker network inspect adcl_default
   ```

### Issue: MCP Servers Not Responding

**Error**: Tools are not available or agents can't call tools

**Solution**:
1. Check MCP server status:
   ```bash
   docker-compose ps | grep mcp
   ```

2. Test MCP server directly:
   ```bash
   curl http://localhost:7000/health  # agent-mcp
   curl http://localhost:7002/health  # file-tools-mcp
   curl http://localhost:7003/health  # nmap-mcp
   ```

3. Restart specific MCP:
   ```bash
   docker-compose restart agent-mcp
   docker-compose logs -f agent-mcp
   ```

### Issue: Frontend Not Loading

**Error**: White screen or "Cannot connect to server"

**Solution**:
1. Check frontend logs:
   ```bash
   docker-compose logs frontend
   ```

2. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check browser console for errors:
   - Open browser DevTools (F12)
   - Look for network or console errors
   - Common issue: CORS errors (should not happen with default config)

4. Hard refresh browser:
   - Chrome/Firefox: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
   - Safari: `Cmd+Option+R`

---

## Stopping the Platform

### Graceful Shutdown

```bash
# Stop all services
./stop.sh
```

This will:
1. Stop all Docker containers
2. Preserve data volumes
3. Allow clean restart later

### Complete Cleanup

```bash
# Stop and remove everything (including data)
docker-compose down -v
```

**Warning**: This removes all data including:
- Conversation history
- Custom agents
- Workflow definitions
- User settings

---

## Next Steps

Now that you have ADCL running, explore these guides:

1. **[Platform Overview](Platform-Overview)** - Understand core concepts and architecture
2. **[Agents Guide](Agents-Guide)** - Learn to create and use autonomous agents
3. **[Workflows Guide](Workflows-Guide)** - Build visual workflows
4. **[MCP Servers Guide](MCP-Servers-Guide)** - Understand tool servers and create custom ones
5. **[Configuration Guide](Configuration-Guide)** - Advanced configuration options

---

## Getting Help

If you encounter issues:

1. **Check [Troubleshooting Guide](Troubleshooting)** - Common issues and solutions
2. **Review [FAQ](FAQ)** - Frequently asked questions
3. **View Logs**: `docker-compose logs -f`
4. **GitHub Issues**: [Report a bug](https://github.com/adcl-io/adcl-community/issues)
5. **Community**: Join discussions on GitHub

---

**Congratulations!** You've successfully installed ADCL. Start by chatting with an agent in the Playground, or dive deeper into the [Platform Overview](Platform-Overview).
