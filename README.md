# ADCL Community Edition

**AI-Driven Command Line** - An open-source platform for building and orchestrating AI-powered security workflows.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/adcl-io/adcl-community)](https://github.com/adcl-io/adcl-community/releases)

## What is ADCL?

ADCL (AI-Driven Command Line) is a powerful platform that combines AI agents with security tools to automate complex workflows. Think of it as a framework for building intelligent automation systems where AI agents can:

- Execute workflows autonomously
- Use tools through MCP (Model Context Protocol) servers
- Collaborate in teams to solve complex problems
- Maintain conversation history and context
- Process files and generate reports

Built on Unix philosophy principles: modular, composable, and text-based.

## Features

### Core Platform
- 🤖 **AI Agent Orchestration** - Deploy and manage multiple AI agents working together
- 🔧 **MCP Servers** - Extensible tool system for agent capabilities
- 📋 **Workflow Engine** - Define multi-step processes with triggers and schedules
- 👥 **Agent Teams** - Configure collaborative agent groups for complex tasks
- 📦 **Package Registry** - Install and manage agents, workflows, and tools
- 🌐 **Web UI** - Modern interface for managing agents and workflows
- 📝 **History Tracking** - Full conversation and execution history

### Included MCPs
- **Agent** - Core AI agent runtime with multi-model support
- **File Tools** - File operations (read, write, search)
- **History** - Conversation and execution tracking

### Community Edition
This community edition includes core platform features for building AI workflows. Looking for advanced security testing capabilities? Check out [ADCL Pro Edition](https://adcl.io/pro).

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum (16GB recommended)
- Linux, macOS, or Windows with WSL2

### Installation

1. **Download the latest release:**
   ```bash
   curl -L https://github.com/adcl-io/adcl-community/releases/latest/download/dist-community.tar.gz | tar xz
   cd adcl-community
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Add your API keys
   ```

   Required: Add your Anthropic API key to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-xxxxx
   ```

3. **Start ADCL:**
   ```bash
   ./adcl start
   ```

4. **Access the UI:**
   ```
   http://localhost:3000
   ```

That's it! ADCL is now running.

### First Steps

1. **Verify installation:**
   ```bash
   ./adcl status
   ```

2. **Create your first agent:**
   - Open http://localhost:3000
   - Navigate to "Agents"
   - Click "Create Agent"
   - Configure with available MCPs (agent, file_tools, history)

3. **Run a workflow:**
   - Go to "Workflows"
   - Try the example workflows
   - Create your own!

## Usage Examples

### CLI Commands

```bash
# Service management
./adcl start              # Start all services
./adcl stop               # Stop all services
./adcl restart            # Restart services
./adcl status             # Show status

# Package management
./adcl install <package>  # Install MCP/workflow/trigger
./adcl list              # List installed packages
./adcl uninstall <name>  # Remove package

# Logs and debugging
./adcl logs              # View all logs
./adcl logs backend      # View specific service logs
```

### Example: Code Review Agent

Create an agent that reviews code:

1. Define agent in `configs/agent-definitions/code-reviewer.json`:
```json
{
  "name": "code-reviewer",
  "description": "Reviews code for best practices and bugs",
  "mcp_servers": ["agent", "file_tools", "history"],
  "model": "claude-sonnet-4",
  "system_prompt": "You are an expert code reviewer. Analyze code for bugs, security issues, and best practices."
}
```

2. Create workflow in `configs/workflows/code-review.yaml`:
```yaml
name: code-review-workflow
trigger: manual
agents:
  - code-reviewer
steps:
  - name: analyze
    agent: code-reviewer
    input: "Review the code in ./src/ and provide feedback"
```

3. Run via CLI or UI:
```bash
./adcl workflow run code-review-workflow
```

### Example: Documentation Generator

```json
{
  "name": "doc-generator",
  "description": "Generates documentation from code",
  "mcp_servers": ["agent", "file_tools"],
  "model": "claude-sonnet-4",
  "system_prompt": "Generate clear, comprehensive documentation from source code."
}
```

## Architecture

```
ADCL Platform
├── Backend (Orchestrator)
│   ├── Agent Management
│   ├── Workflow Engine
│   ├── Package Registry
│   └── API Server
├── Frontend (Web UI)
│   ├── Agent Dashboard
│   ├── Workflow Builder
│   └── History Viewer
└── MCP Servers (Tools)
    ├── Agent Runtime
    ├── File Operations
    └── History Tracking
```

### How It Works

1. **You define agents** with specific capabilities (MCPs)
2. **Agents use MCP servers** to perform actions (read files, execute commands, etc.)
3. **Workflows orchestrate** multi-step processes
4. **Triggers automate** workflow execution (webhooks, schedules)
5. **History tracks** everything for audit and replay

## Configuration

### Directory Structure

```
adcl-community/
├── adcl                    # Main CLI
├── docker-compose.yml      # Service definitions
├── .env                    # Environment configuration
├── configs/
│   ├── agent-definitions/  # Agent configurations
│   ├── agent-teams/        # Team definitions
│   ├── workflows/          # Workflow definitions
│   ├── triggers/           # Trigger configurations
│   └── models.yaml         # AI model settings
├── registry/               # Package definitions
│   ├── mcps/              # MCP packages
│   ├── teams/             # Team packages
│   └── triggers/          # Trigger packages
└── var/                    # Runtime data
    ├── logs/              # Application logs
    ├── volumes/           # Persistent data
    └── workspace/         # Agent workspace
```

### Models Configuration

Edit `configs/models.yaml` to configure AI models:

```yaml
models:
  - id: claude-sonnet-4
    provider: anthropic
    name: claude-sonnet-4-20250514
    enabled: true
    default: true

  - id: claude-opus-4
    provider: anthropic
    name: claude-opus-4-20250514
    enabled: true
```

### Adding Custom MCPs

1. Create MCP server in `src/mcp-servers/your-mcp/`
2. Add package definition in `registry/mcps/your-mcp/`
3. Install: `./adcl install your-mcp`
4. Use in agent definitions

## Community vs Pro

| Feature | Community | Pro |
|---------|-----------|-----|
| AI Agent Orchestration | ✅ | ✅ |
| Core MCP Servers | ✅ | ✅ |
| Workflow Engine | ✅ | ✅ |
| Web UI | ✅ | ✅ |
| Package Registry | ✅ | ✅ |
| Custom MCPs | ✅ | ✅ |
| Red Team Operations | ❌ | ✅ |
| Attack Playground | ❌ | ✅ |
| Kali Linux Tools | ❌ | ✅ |
| Network Scanning | ❌ | ✅ |
| Exploit Database | ❌ | ✅ |
| Enterprise Support | ❌ | ✅ |

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check logs
./adcl logs

# Restart from clean state
./adcl stop
./adcl start
```

### Port already in use

Edit `docker-compose.yml` to change ports:
```yaml
ports:
  - "3001:3000"  # Change 3000 to 3001
```

### Agent errors

```bash
# View agent logs
./adcl logs backend

# Check MCP server status
docker ps | grep mcp-

# Verify API keys in .env
cat .env | grep API_KEY
```

### Need more help?

- 📚 [Documentation](https://docs.adcl.io)
- 💬 [Community Discord](https://discord.gg/adcl)
- 🐛 [Report Issues](https://github.com/adcl-io/adcl-community/issues)
- 📧 [Email Support](mailto:support@adcl.io)

## Development

### Building from Source

```bash
# Clone repository
git clone https://github.com/adcl-io/adcl-community.git
cd adcl-community

# Build services
docker-compose build

# Start
./adcl start
```

### Running Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

### Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Security

ADCL is designed for legitimate security research and automation. Please use responsibly.

- Report security vulnerabilities to security@adcl.io
- Do not use for malicious purposes
- Follow responsible disclosure practices
- Respect system boundaries and permissions

## License

ADCL Community Edition is released under the [MIT License](LICENSE).

## Links

- 🌐 Website: https://adcl.io
- 📖 Documentation: https://docs.adcl.io
- 💼 Pro Edition: https://adcl.io/pro
- 🐙 GitHub: https://github.com/adcl-io/adcl-community
- 💬 Discord: https://discord.gg/adcl
- 🐦 Twitter: https://twitter.com/adcl_io

## Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/claude) - AI models
- [MCP Protocol](https://modelcontextprotocol.io) - Tool integration
- [Docker](https://www.docker.com) - Containerization
- [FastAPI](https://fastapi.tiangolo.com) - Backend framework
- [React](https://react.dev) - Frontend framework

---

**Made with ❤️ by the ADCL community**
