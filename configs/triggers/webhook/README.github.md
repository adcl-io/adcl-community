# GitHub Webhook Trigger

GitHub webhook trigger with HMAC signature verification and PR event filtering.

## Features

- ✅ HMAC SHA-256 signature verification (X-Hub-Signature-256)
- ✅ Event filtering (pull_request, push, etc.)
- ✅ Action filtering (opened, synchronize)
- ✅ Parameter extraction from GitHub payload
- ✅ Constant-time signature comparison (prevents timing attacks)
- ✅ Structured logging with GitHub context

## Usage

### Configure GitHub Webhook

1. Go to GitHub repo → Settings → Webhooks → Add webhook
2. Payload URL: `http://your-server:8101/webhook`
3. Content type: `application/json`
4. Secret: (set GITHUB_WEBHOOK_SECRET)
5. Events: Pull requests (or custom)

### Install from Registry

```bash
POST /registries/install/trigger/github-pr-webhook-1.0.0
{
  "workflow_id": "code-review"
}
```

### Environment Variables

**Platform auto-injected:**
- `ORCHESTRATOR_URL` - Orchestrator API URL
- `WORKFLOW_ID` or `TEAM_ID` - User-configured target

**User-defined (in trigger package):**
- `GITHUB_WEBHOOK_SECRET` - GitHub webhook secret for HMAC verification
- `FILTER_ACTIONS` - Comma-separated PR actions to process (default: opened,synchronize)
- `TRIGGER_PORT` - Port to listen on (default: 8101)

## Security

### Signature Verification

Verifies GitHub's HMAC SHA-256 signature:
```python
X-Hub-Signature-256: sha256=<signature>
```

Uses constant-time comparison to prevent timing attacks.

### Skipping Verification

If `GITHUB_WEBHOOK_SECRET` is not set, signature verification is skipped (logs warning).
**NOT RECOMMENDED** for production.

## Event Filtering

### By Action

Only processes PR actions in `FILTER_ACTIONS`:
- `opened` - New PR opened
- `synchronize` - PR updated with new commits
- `reopened` - PR reopened
- `closed` - PR closed/merged

Default: `opened,synchronize`

### By Event Type

Supports:
- `pull_request` - PR events (full parameter extraction)
- `push` - Push events (ref, commits)
- Other events (generic parameter extraction)

## Parameter Extraction

### Pull Request Events

Extracted parameters:
- `pr_number` - PR number
- `pr_title` - PR title
- `pr_author` - PR author username
- `pr_head_ref` - Source branch
- `pr_base_ref` - Target branch
- `pr_url` - PR URL
- `repository` - Full repo name
- `action` - GitHub action (opened/synchronize)

### Push Events

Extracted parameters:
- `ref` - Git ref pushed
- `repository` - Full repo name
- `pusher` - Who pushed
- `commits` - Number of commits

## Example Workflow

```json
{
  "workflow_id": "code-review",
  "params": {
    "pr_number": 123,
    "pr_title": "Add new feature",
    "pr_author": "developer",
    "pr_head_ref": "feature-branch",
    "pr_base_ref": "main",
    "repository": "org/repo",
    "action": "opened"
  }
}
```

## Testing

### Test with curl (no signature)

```bash
# Requires GITHUB_WEBHOOK_SECRET to be empty
curl -X POST http://localhost:8101/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 123,
      "title": "Test PR"
    }
  }'
```

### Test with valid signature

```bash
# Calculate HMAC signature
payload='{"action":"opened","pull_request":{"number":123}}'
secret="your-secret"
signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "$secret" | sed 's/^.* //')

curl -X POST http://localhost:8101/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$signature" \
  -H "X-GitHub-Event: pull_request" \
  -d "$payload"
```

## Logging

Structured logging includes:
- `github_event` - Event type
- `github_action` - PR action
- `workflow_id` / `team_id` - Target
- `execution_id` - Workflow execution ID
- Signature verification results
- Filtering decisions

## Health Check

```bash
curl http://localhost:8101/health
```

Returns:
- status
- has_webhook_secret
- filter_actions
- target configuration
