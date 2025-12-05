# Linear Webhook Trigger

Linear webhook trigger with HMAC signature verification and deduplication.

## Features

- ✅ HMAC SHA-256 signature verification (Linear-Signature)
- ✅ Deduplication using Linear-Delivery ID
- ✅ Event type filtering (agentSession, issue, etc.)
- ✅ Parameter extraction from Linear payload
- ✅ Constant-time signature comparison
- ✅ In-memory deduplication cache (last 1000 deliveries)

## Usage

### Configure Linear Webhook

1. Go to Linear → Settings → API → Webhooks → Create webhook
2. URL: `http://your-server:8103/webhook`
3. Secret: (set LINEAR_WEBHOOK_SECRET)
4. Resources: Agent sessions (or custom)

### Install from Registry

```bash
POST /registries/install/trigger/linear-webhook-1.0.0
{
  "workflow_id": "agent-handler"
}
```

### Environment Variables

**Platform auto-injected:**
- `ORCHESTRATOR_URL` - Orchestrator API URL
- `WORKFLOW_ID` or `TEAM_ID` - User-configured target

**User-defined (in trigger package):**
- `LINEAR_WEBHOOK_SECRET` - Linear webhook secret for HMAC verification
- `FILTER_EVENT_TYPES` - Comma-separated event types to process (default: agentSession)
- `LINEAR_CLIENT_ID` - Linear OAuth client ID for agent workflow
- `LINEAR_CLIENT_SECRET` - Linear OAuth client secret for agent workflow
- `LINEAR_REDIRECT_URI` - Linear OAuth redirect URI (optional)
- `TRIGGER_PORT` - Port to listen on (default: 8103)

## Security

### Signature Verification

Verifies Linear's HMAC SHA-256 signature:
```
Linear-Signature: <hmac_signature>
```

Uses constant-time comparison to prevent timing attacks.

### Deduplication

Uses `Linear-Delivery` header to prevent duplicate processing:
```
Linear-Delivery: <delivery_id>
```

Maintains in-memory cache of last 1000 delivery IDs. Duplicate deliveries return:
```json
{
  "status": "duplicate",
  "delivery_id": "...",
  "message": "Delivery already processed"
}
```

**Note:** Cache is lost on container restart. For production, use Redis or database.

## Event Filtering

### By Event Type

Only processes events in `FILTER_EVENT_TYPES`:
- `agentSession` - Agent session events (default)
- `issue` - Issue events
- `comment` - Comment events
- `project` - Project events

Default: `agentSession`

Multiple types:
```bash
FILTER_EVENT_TYPES="agentSession,issue"
```

## Parameter Extraction

### Agent Session Events

Extracted parameters for all agentSession events:
- `session_id` - Agent session ID
- `issue_id` - Related issue ID
- `state` - Session state (pending, active, complete)
- `created_at` - Creation timestamp
- `updated_at` - Update timestamp
- `action` - Event action (created, prompted)

Additional parameters for `prompted` events:
- `prompt` - User's prompt text (from agentActivity.content.body)

Optional context fields (when present):
- `guidance` - Guidance from Linear
- `previousComments` - Previous comments for context

### Issue Events

Extracted parameters:
- `issue_id` - Issue ID
- `issue_title` - Issue title
- `issue_state` - Current state
- `assignee` - Assigned user
- `action` - Event action

## OAuth Integration for Agent Workflow

### Configuration

Set OAuth credentials in trigger package environment:
```json
{
  "environment": {
    "LINEAR_CLIENT_ID": "your-client-id",
    "LINEAR_CLIENT_SECRET": "your-client-secret",
    "LINEAR_REDIRECT_URI": "https://your-app.com/oauth/callback"
  }
}
```

### OAuth Credentials in Workflow

When OAuth is configured, credentials are automatically injected into workflow params:
```json
{
  "workflow_id": "agent-handler",
  "params": {
    "linear_event": "agentSession",
    "action": "created",
    "session_id": "session-123",
    "issue_id": "issue-456",
    "state": "active",
    "linear_oauth": {
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "redirect_uri": "https://your-app.com/oauth/callback"
    }
  }
}
```

### Usage in Workflow

The workflow/team can use OAuth credentials to:
1. **Authenticate with Linear API**
   - Use client_id and client_secret for OAuth flow
   - Exchange authorization code for access token

2. **Access Linear Resources**
   - Read issue details
   - Update issue status
   - Add comments
   - Create new issues

3. **Agent Session Management**
   - Update agent session state
   - Post agent responses to Linear

### Example: Agent Workflow with OAuth

```python
# In your workflow/agent
def handle_linear_agent_session(params):
    oauth_config = params.get("linear_oauth", {})

    if oauth_config:
        # Initialize Linear client with OAuth
        linear_client = LinearClient(
            client_id=oauth_config["client_id"],
            client_secret=oauth_config["client_secret"]
        )

        # Get access token (if you have auth code)
        # access_token = linear_client.exchange_code(auth_code)

        # Or use client credentials for server-to-server
        # access_token = linear_client.get_client_credentials_token()

        # Read issue details
        issue_id = params["issue_id"]
        issue = linear_client.get_issue(issue_id)

        # Process with agent...
        agent_response = process_with_agent(issue)

        # Update Linear with agent response
        linear_client.add_comment(issue_id, agent_response)
```

### OAuth Flow Types

**1. Authorization Code Flow (User Authorization)**
- User authorizes app via redirect
- Exchange code for access token
- Access user's Linear data

**2. Client Credentials Flow (Server-to-Server)**
- No user interaction required
- App authenticates directly
- Access organization data

**Note:** Trigger provides credentials; workflow implements OAuth flow.

## Example Workflow

## Testing

### Test with curl (no signature)

```bash
# Requires LINEAR_WEBHOOK_SECRET to be empty
curl -X POST http://localhost:8103/webhook \
  -H "Content-Type: application/json" \
  -H "Linear-Delivery: test-delivery-1" \
  -d '{
    "type": "agentSession",
    "action": "created",
    "data": {
      "id": "session-123",
      "issueId": "issue-456"
    }
  }'
```

### Test with valid signature

```bash
payload='{"type":"agentSession","action":"created"}'
secret="your-secret"
signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$secret" | sed 's/^.* //')

curl -X POST http://localhost:8103/webhook \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: $signature" \
  -H "Linear-Delivery: test-delivery-2" \
  -d "$payload"
```

### Test deduplication

```bash
# Send same delivery ID twice
curl -X POST http://localhost:8103/webhook \
  -H "Linear-Delivery: duplicate-test" \
  -d '{"type":"agentSession","action":"created"}'

# First request: status="triggered"
# Second request: status="duplicate"
```

## Logging

Structured logging includes:
- `linear_event` - Event type
- `linear_action` - Event action
- `delivery_id` - Deduplication ID
- `workflow_id` / `team_id` - Target
- `execution_id` - Workflow execution ID
- Deduplication decisions

## Health Check

```bash
curl http://localhost:8103/health
```

Returns:
- status
- has_webhook_secret
- filter_event_types
- cache_size (number of cached delivery IDs)
- target configuration

## Limitations

### In-Memory Cache

Deduplication cache is in-memory:
- ✅ Fast
- ✅ No external dependencies
- ❌ Lost on restart
- ❌ Not shared across multiple instances

For production, consider:
- Redis-backed cache
- Database-backed deduplication log
- Distributed cache (Memcached)

### Cache Size

Default cache holds 1000 delivery IDs. Adjust if needed:
```python
MAX_CACHE_SIZE = 5000  # Increase for higher volume
```

## Production Recommendations

1. **Use Redis for deduplication:**
```python
import redis
r = redis.Redis(host='localhost', port=6379)

def is_duplicate_delivery(delivery_id):
    if r.exists(f"linear:delivery:{delivery_id}"):
        return True
    r.setex(f"linear:delivery:{delivery_id}", 86400, "1")  # 24h TTL
    return False
```

2. **Configure webhook secret:**
Always set `LINEAR_WEBHOOK_SECRET` in production.

3. **Monitor cache size:**
Alert if cache grows unexpectedly (indicates high duplicate rate).

4. **Set up alerting:**
Monitor signature verification failures.
