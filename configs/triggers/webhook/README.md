# Basic Webhook Trigger

A simple webhook trigger that receives HTTP POST requests and triggers workflows or teams.

## Features

- ✅ Receives webhooks via HTTP POST
- ✅ Auto-configured by platform (ORCHESTRATOR_URL, WORKFLOW_ID/TEAM_ID)
- ✅ Structured logging
- ✅ Health check endpoint
- ✅ Minimal dependencies

## Usage

### Install from Registry

```bash
POST /registries/install/trigger/simple-webhook-1.0.0
{
  "workflow_id": "my-workflow"
}
```

### Send Webhook

```bash
curl -X POST http://localhost:8100/webhook \
  -H "Content-Type: application/json" \
  -d '{"data": "test"}'
```

### Health Check

```bash
curl http://localhost:8100/health
```

## Environment Variables

**Platform auto-injected:**
- `ORCHESTRATOR_URL` - Orchestrator API URL (default: http://orchestrator:8000)
- `WORKFLOW_ID` - Target workflow (user-configured at install)
- `TEAM_ID` - Target team (user-configured at install)

**Optional:**
- `TRIGGER_PORT` - Port to listen on (default: 8100)

## Endpoints

- `POST /webhook` - Receive webhook and trigger workflow/team
- `GET /health` - Health check

## Logging

Uses structured logging with context:
- workflow_id
- team_id
- execution_id
- payload_keys

## Building

```bash
docker build -t trigger-webhook:1.0.0 -f Dockerfile.webhook .
```

## Running Locally

```bash
export ORCHESTRATOR_URL=http://localhost:8000
export WORKFLOW_ID=test-workflow
python webhook_trigger.py
```
