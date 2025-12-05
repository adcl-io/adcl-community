# Agent Teams

This directory contains agent team definitions in JSON format. Each team is a collection of agents with specific roles and capabilities.

## Team Structure

Each team JSON file follows this structure:

```json
{
  "name": "Team Name",
  "description": "What this team does",
  "version": "1.0.0",
  "agents": [
    {
      "name": "Agent Name",
      "role": "Agent Role",
      "mcp_server": "mcp_server_name"
    }
  ]
}
```

## Available MCP Servers

- `agent` - AI Agent with think/code/review capabilities
- `nmap_recon` - Network reconnaissance using Nmap
- `file_tools` - File operations (read/write/list)

## Example Teams

### Security Analysis Team
Comprehensive network security scanning and analysis with:
- Network Scanner (nmap_recon)
- Security Analyst (agent)
- Reporter (file_tools)

### Code Review Team
Collaborative code review and quality assurance with:
- Code Analyzer (agent)
- Documentation Writer (file_tools)

## Creating Custom Teams

1. Create a new JSON file in this directory
2. Follow the structure above
3. Use descriptive names and roles
4. Assign appropriate MCP servers based on capabilities needed
5. Test your team in the UI (Teams page)

## Sharing Teams

Teams are portable and can be shared by:
- Copying JSON files to other installations
- Version controlling this directory
- Importing/exporting via the UI

## Best Practices

- **Name clearly** - Use descriptive team names
- **Define roles** - Give each agent a clear role
- **Match capabilities** - Choose MCP servers that match the agent's role
- **Document purpose** - Add good descriptions explaining what the team does
- **Keep it focused** - 2-4 agents per team works well
