# ADCL Platform Wiki

Comprehensive end-user documentation for the ADCL (Autonomous Distributed Command Loop) platform.

---

## Documentation Overview

This wiki provides complete documentation for installing, configuring, and using ADCL to build autonomous AI agent systems.

### Quick Navigation

| Getting Started | Core Features | Advanced Topics |
|----------------|---------------|-----------------|
| [Home](Home) | [Agents Guide](Agents-Guide) | [Configuration](Configuration-Guide) |
| [Getting Started](Getting-Started) | [Teams Guide](Teams-Guide) | [Troubleshooting](Troubleshooting) |
| [Platform Overview](Platform-Overview) | [Workflows Guide](Workflows-Guide) | [FAQ](FAQ) |

---

## Documentation Structure

### 📚 Foundation

**[Home](Home.md)**
- Platform introduction
- Quick links to all documentation
- Key capabilities and use cases
- System requirements

**[Getting Started](Getting-Started.md)**
- Prerequisites and installation
- Configuration setup
- First steps and examples
- Verification and testing

**[Platform Overview](Platform-Overview.md)**
- Core concepts (agents, teams, MCPs)
- Architecture (three-tier design)
- Design philosophy (Unix principles)
- Component relationships

---

### 🤖 Core Features

**[Agents Guide](Agents-Guide.md)**
- What are autonomous agents?
- Pre-built agents (Code Reviewer, Security Analyst)
- Creating custom agents
- Agent configuration and best practices

**[Teams Guide](Teams-Guide.md)**
- Multi-agent collaboration
- Team structure and roles
- Pre-built teams (Security Analysis, Code Review)
- Creating custom teams

**[Workflows Guide](Workflows-Guide.md)**
- Visual workflow builder
- Node-based composition
- Parameter resolution
- Workflow vs. Agent vs. Team

**[MCP Servers Guide](MCP-Servers-Guide.md)**
- Model Context Protocol overview
- Available MCP servers (agent, file_tools, nmap, kali, linear)
- Creating custom MCP servers
- MCP configuration and deployment

**[Triggers Guide](Triggers-Guide.md)**
- Webhook triggers (CI/CD integration)
- Schedule triggers (cron-based automation)
- Installing and managing triggers
- Security best practices

**[Registry Guide](Registry-Guide.md)**
- Package management system
- Browsing and installing packages (teams, triggers)
- Creating and publishing packages
- Managing multiple registries

---

### ⚙️ Configuration & Operations

**[Configuration Guide](Configuration-Guide.md)**
- Environment variables
- Port configuration
- Model configuration (Claude, Bedrock)
- Network, security, and storage settings
- Advanced configuration options

**[Troubleshooting](Troubleshooting.md)**
- Installation issues
- Service and agent issues
- MCP server problems
- Network and performance issues
- Debug information collection

**[FAQ](FAQ.md)**
- General questions
- Technical questions
- Feature questions
- Security questions
- Cost and pricing
- Comparisons with other tools

---

## Documentation by Use Case

### 🚀 Getting Started

1. [Install ADCL](Getting-Started.md#installation)
2. [Configure API keys](Getting-Started.md#configuration)
3. [Start the platform](Getting-Started.md#starting-the-platform)
4. [Chat with your first agent](Getting-Started.md#first-steps)

### 🔧 Building Autonomous Agents

1. [Understand how agents work](Agents-Guide.md#how-agents-work)
2. [Use pre-built agents](Agents-Guide.md#using-pre-built-agents)
3. [Create custom agents](Agents-Guide.md#creating-custom-agents)
4. [Configure agent behavior](Agents-Guide.md#agent-configuration)

### 👥 Multi-Agent Systems

1. [Understand agent teams](Teams-Guide.md#what-are-agent-teams)
2. [Use pre-built teams](Teams-Guide.md#using-pre-built-teams)
3. [Create custom teams](Teams-Guide.md#creating-custom-teams)
4. [Design role specialization](Teams-Guide.md#team-configuration)

### 🎨 Visual Workflows

1. [Understand workflows](Workflows-Guide.md#what-are-workflows)
2. [Create your first workflow](Workflows-Guide.md#creating-your-first-workflow)
3. [Configure nodes and parameters](Workflows-Guide.md#node-configuration)
4. [Monitor execution](Workflows-Guide.md#execution-and-monitoring)

### 🔌 Extending with MCPs

1. [Understand MCP architecture](MCP-Servers-Guide.md#how-mcp-works)
2. [Use available MCPs](MCP-Servers-Guide.md#available-mcp-servers)
3. [Create custom MCP](MCP-Servers-Guide.md#creating-custom-mcp-servers)
4. [Deploy and configure](MCP-Servers-Guide.md#mcp-server-configuration)

### 🤖 Automation

1. [Understand triggers](Triggers-Guide.md#what-are-triggers)
2. [Create webhook trigger](Triggers-Guide.md#webhook-triggers)
3. [Create schedule trigger](Triggers-Guide.md#schedule-triggers)
4. [Manage triggers](Triggers-Guide.md#managing-triggers)

---

## Documentation Standards

### Organization

Each guide follows this structure:
- **Table of Contents**: Quick navigation
- **Conceptual Overview**: What is it?
- **How It Works**: Technical explanation
- **Getting Started**: Basic usage
- **Advanced Usage**: Power features
- **Best Practices**: Recommendations
- **Troubleshooting**: Common issues

### Examples

All guides include:
- ✅ Real-world examples
- ✅ Code snippets with syntax highlighting
- ✅ Command-line examples
- ✅ Configuration examples
- ✅ Troubleshooting scenarios

### Cross-References

Documentation is heavily cross-referenced:
- Related guides linked at bottom of each page
- Inline links to relevant sections
- Progressive disclosure (basics → advanced)

---

## Quick Reference

### Essential Commands

```bash
# Start ADCL
./start.sh

# Clean restart
./clean-restart.sh

# Stop ADCL
./stop.sh

# View logs
docker-compose logs -f

# Check status
./status.sh
```

### Key URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Registry**: http://localhost:9000

### Important Files

- **Environment**: `.env`
- **Agents**: `agent-definitions/*.json`
- **Teams**: `agent-teams/*.json`
- **Workflows**: `workflows/*.json`
- **Registries**: `registries.conf`

---

## Documentation Versions

| Version | Release Date | Status |
|---------|-------------|--------|
| 0.1.26 | 2025-12-08 | Current |
| 0.1.24 | 2025-12-06 | Deprecated |

**Note**: Documentation reflects current version (0.1.26). For older versions, see git history.

---

## Contributing to Documentation

### Found an Issue?

- **Typo or error**: [Open an issue](https://github.com/adcl-io/adcl-community/issues)
- **Unclear section**: [Start a discussion](https://github.com/adcl-io/adcl-community/discussions)
- **Missing content**: [Request documentation](https://github.com/adcl-io/adcl-community/issues/new?template=documentation.md)

### Want to Contribute?

1. Fork the repository
2. Create a branch: `git checkout -b docs/improve-agents-guide`
3. Make changes to `docs/wiki/*.md`
4. Submit pull request

**Style Guide**:
- Use clear, concise language
- Include examples
- Follow existing structure
- Test all commands
- Add cross-references

---

## Wiki Maintenance

### Last Updated

- **Date**: 2025-12-08
- **Version**: 0.1.26
- **Maintainer**: ADCL Team

### Recent Changes

- ✅ Initial comprehensive documentation created
- ✅ All 12 guides completed
- ✅ Cross-references added
- ✅ Examples and troubleshooting included

### Planned Updates

- [ ] Video tutorials
- [ ] Interactive examples
- [ ] API reference documentation
- [ ] Architecture deep-dives

---

## External Resources

### Official Links

- **GitHub**: https://github.com/adcl-io/adcl-community
- **Website**: https://adcl.io (coming soon)
- **Blog**: https://blog.adcl.io (coming soon)

### Related Resources

- **Model Context Protocol**: https://modelcontextprotocol.org
- **Anthropic Claude**: https://www.anthropic.com
- **Docker Documentation**: https://docs.docker.com

---

## Getting Help

### Documentation Issues

If you can't find what you need:

1. **Search the wiki**: Use browser search (Ctrl+F)
2. **Check FAQ**: [Frequently Asked Questions](FAQ.md)
3. **Try Troubleshooting**: [Troubleshooting Guide](Troubleshooting.md)
4. **Ask the community**: [GitHub Discussions](https://github.com/adcl-io/adcl-community/discussions)

### Technical Support

- **Bug reports**: [GitHub Issues](https://github.com/adcl-io/adcl-community/issues)
- **Feature requests**: [GitHub Issues](https://github.com/adcl-io/adcl-community/issues/new?template=feature_request.md)
- **Security issues**: security@adcl.io

---

## License

Documentation is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Code examples in documentation are licensed under MIT License (same as ADCL platform).

---

**Ready to get started?** → [Installation Guide](Getting-Started.md)

**Need help?** → [FAQ](FAQ.md) | [Troubleshooting](Troubleshooting.md)

**Want to contribute?** → [CONTRIBUTING.md](../../CONTRIBUTING.md)
