# Linear MCP Server

Linear API integration via OAuth 2.0 client credentials flow.

## Tools

1. **get_issue** - Get issue by ID
2. **create_agent_activity** - Create agent session activity
3. **set_issue_delegate** - Assign agent as delegate
4. **update_issue_state** - Update issue workflow state
5. **get_team_workflow_states** - Get team workflow states
6. **create_comment** - Add comment to issue
7. **get_current_user** - Get current user/agent info
8. **execute_query** - Execute raw GraphQL query

## Configuration

Required environment variables:
- `LINEAR_CLIENT_ID` - OAuth client ID
- `LINEAR_CLIENT_SECRET` - OAuth client secret
- `LINEAR_PORT` - Port (default: 7005)

## Usage

```bash
# Build
docker build -t mcp-linear:1.0.0 .

# Run
docker run -p 7005:7005 \
  -e LINEAR_CLIENT_ID=xxx \
  -e LINEAR_CLIENT_SECRET=yyy \
  mcp-linear:1.0.0

# Health check
curl http://localhost:7005/health

# List tools
curl -X POST http://localhost:7005/mcp/list_tools

# Call tool
curl -X POST http://localhost:7005/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_current_user", "arguments": {}}'
```

## OAuth Tokens

Tokens are automatically managed and stored in `/app/volumes/credentials/linear-tokens.json`.

## Part of PRD-16

This MCP server is the foundation layer for the Linear agent migration (PRD-16).
