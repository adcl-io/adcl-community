# Trigger Package Definition

**Related Issue:** PRD-35 - Create mechanism for trigger work requests from without a human in the loop

**Goal:** Define a standard package format for triggers that mirrors the MCP package pattern, allowing triggers to be as simple or complex as needed.

---

## ⚠️ ACTUAL IMPLEMENTATION NOTE

**Registry Structure:** While this document describes a nested directory structure, the **actual implementation uses a flattened structure**:
- **Actual:** `registry-server/registries/triggers/{name}-{version}.json`
- **Not:** `registry/triggers/{name}/{version}/trigger.json`

**Key Implementation Details:**
- Triggers are managed by `DockerManager` (not a separate TriggerManager)
- Triggers call existing `/teams/run` endpoint (not `/teams/{team_id}/execute`)
- Added `TASK_TEMPLATE` env var for webhooks (maps JSON → task strings)
- Added `TASK_DESCRIPTION` env var for schedule triggers

**See:** [TRIGGER_IMPLEMENTATION_STATUS.md](TRIGGER_IMPLEMENTATION_STATUS.md) for actual implementation details.

---

## Overview

Like MCPs, triggers are defined as JSON packages that can be installed from a registry. The trigger package defines:

1. **How it's deployed** (Docker container configuration)
2. **What activates it** (webhook, schedule, event, etc.)
3. **What it executes** (workflow, team, or custom logic)
4. **How data flows** (parameter mapping, conditions - optional)

The trigger system provides the **infrastructure**, but the **trigger author** decides the complexity.

---

## Package Structure

**Planned Location:** `registry/triggers/{name}/{version}/` *(Not implemented)*
**Actual Location:** `registry-server/registries/triggers/{name}-{version}.json` *(Flattened structure)*

**Note:** Original plan was for triggers to follow the same nested, versioned structure as MCPs. The actual implementation uses a simpler flattened structure with version in the filename for easier scanning.

### Minimal Trigger Package

```json
{
  "name": "simple_webhook",
  "version": "1.0.0",
  "description": "Basic webhook trigger",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-simple-webhook:1.0.0",
    "container_name": "trigger-simple-webhook",
    "ports": [
      {
        "host": "${TRIGGER_PORT:-8100}",
        "container": "8100"
      }
    ],
    "environment": {
      "TRIGGER_PORT": "${TRIGGER_PORT:-8100}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "webhook",
    "endpoint": "/webhook"
  },

  "action": {
    "workflow_id": "my-workflow"
  }
}
```

This trigger deploys a container that listens for webhooks and executes a workflow.

---

## Core Fields

### 1. Metadata (Required)

```json
{
  "name": "trigger_name",           // Unique identifier
  "version": "1.0.0",                // Semantic version
  "description": "What this does",   // Human-readable description
  "type": "trigger"                  // Always "trigger"
}
```

**Identical to MCP packages.**

### 2. Deployment (Required)

Defines how the trigger container is deployed.

```json
{
  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-name:1.0.0",
    "container_name": "trigger-name",
    "ports": [
      {
        "host": "${PORT:-8100}",
        "container": "8100"
      }
    ],
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  }
}
```

**Identical structure to MCP packages.** The trigger runs in its own container.

**Note:** The trigger manager automatically injects the following environment variables at install time:
- `ORCHESTRATOR_URL` - URL of the orchestrator API (e.g., `http://orchestrator:8000`)
- `ORCHESTRATOR_WS` - WebSocket URL for event subscriptions (e.g., `ws://orchestrator:8000`)

You don't need to specify these in your package definition - they're provided by the platform.

### 3. Trigger Configuration (Required)

Defines what activates this trigger.

```json
{
  "trigger": {
    "type": "webhook|schedule|event|manual",
    // ... type-specific config
  }
}
```

**Analogous to MCP's "tools" array** - defines what the trigger listens for.

### 4. Action Configuration (Documentation)

**Important:** The `action` field is **documentation only**. It shows the intended use and expected parameters, but the actual target (workflow_id/team_id) is **user-configurable at install time**.

```json
{
  "action": {
    "workflow_id": "code-review-team",  // Example/documentation only
    "params": {
      "pr_number": "${event.pull_request.number}",  // Documents what will be sent
      "repository": "${event.repository.full_name}"
    }
  }
}
```

**At install time, users specify the actual target:**
- The platform injects `WORKFLOW_ID` or `TEAM_ID` as environment variables
- Trigger containers read these to know what to execute
- Same trigger package can be reused with different targets

**Example:**
```bash
# User installs trigger with their chosen target
POST /registries/install/trigger/github-pr-webhook-1.0.0
{
  "workflow_id": "my-custom-review-workflow"
}

# Platform auto-injects:
# WORKFLOW_ID=my-custom-review-workflow
# ORCHESTRATOR_URL=http://orchestrator:8000
```

---

## Trigger Types

### Webhook Trigger

**Minimal:**
```json
{
  "trigger": {
    "type": "webhook",
    "endpoint": "/triggers/my-webhook"
  }
}
```

**With Authentication (Documentation):**

**Note:** The `auth` field is **documentation only** - it describes how the trigger implements authentication, but trigger authors implement the actual verification logic in their container code.

```json
{
  "trigger": {
    "type": "webhook",
    "endpoint": "/triggers/github",
    "auth": {
      "type": "secret",
      "header": "X-Hub-Signature-256",
      "secret": "${GITHUB_WEBHOOK_SECRET}"
    }
  }
}
```

**With Filters/Rate Limiting (Documentation):**

**Note:** `filters` and `rate_limit` fields are **documentation only** - they describe the trigger's behavior, but trigger authors implement the actual logic in their container code.


```json
{
  "trigger": {
    "type": "webhook",
    "endpoint": "/triggers/github",
    "filters": {
      "event.action": ["opened", "synchronize"]
    },
    "rate_limit": {
      "requests": 100,
      "window_seconds": 60,
      "strategy": "per-ip"
    }
  }
}
```

---

### Schedule Trigger

**Simple Cron:**
```json
{
  "trigger": {
    "type": "schedule",
    "cron": "0 2 * * *"
  }
}
```

**With Timezone:**
```json
{
  "trigger": {
    "type": "schedule",
    "cron": "0 9 * * MON-FRI",
    "timezone": "America/New_York"
  }
}
```

---

### Event Trigger

**Listen to Platform Events:**
```json
{
  "trigger": {
    "type": "event",
    "event": "workflow.completed",
    "source": "security-scan"
  }
}
```

**Note:** Event triggers require an event bus implementation in the orchestrator (WebSocket `/ws/events` endpoint). This is planned for Phase 6+ or may be added to Phase 4 scope if needed earlier.

---

### Manual Trigger

**API/UI Triggered:**
```json
{
  "trigger": {
    "type": "manual"
  }
}
```

---

## Action Configuration

### Execute Workflow

```json
{
  "action": {
    "workflow_id": "code-review-workflow"
  }
}
```

### Execute Team

```json
{
  "action": {
    "team_id": "security-team-v2"
  }
}
```

### Execute with Parameters

```json
{
  "action": {
    "workflow_id": "security-scan",
    "params": {
      "scan_target": "192.168.50.0/24",
      "scan_type": "full"
    }
  }
}
```

---

## Parameter Mapping (Documentation)

**Important:** Parameter mapping is **documentation only**. The `params` field documents what parameters the trigger will send, but trigger authors implement the actual extraction and mapping logic in their container code.

### Simple Mapping

```json
{
  "action": {
    "workflow_id": "my-workflow",
    "params": {
      "user": "${event.user_id}",
      "message": "${event.text}"
    }
  }
}
```

### With Environment Variables

```json
{
  "action": {
    "workflow_id": "security-scan",
    "params": {
      "target": "${SCAN_TARGET:-192.168.50.0/24}",
      "api_key": "${API_KEY}"
    }
  }
}
```

### Dynamic Workflow Selection

```json
{
  "action": {
    "workflow_id": "${event.workflow_name}",
    "params": {
      "data": "${event.payload}"
    }
  }
}
```

---

## Conditional Execution (Optional)

Only execute if conditions are met.

### Simple Condition

```json
{
  "conditions": [
    {
      "field": "event.action",
      "equals": "opened"
    }
  ]
}
```

### Multiple Conditions (AND)

```json
{
  "conditions": [
    {
      "field": "event.action",
      "in": ["opened", "synchronize"]
    },
    {
      "field": "event.pull_request.base.ref",
      "equals": "main"
    }
  ]
}
```

---

## Response Configuration (Optional)

Control how the trigger responds (for webhooks).

### Async (Default)

```json
{
  "response": {
    "sync": false,
    "status": 202,
    "body": {
      "message": "Workflow triggered"
    }
  }
}
```

### Sync (Wait for completion)

```json
{
  "response": {
    "sync": true,
    "timeout": 300,
    "body": {
      "result": "${execution.result}"
    }
  }
}
```

---

## Complete Examples

### Example 1: Simple GitHub PR Trigger

```json
{
  "name": "github_pr_review",
  "version": "1.0.0",
  "description": "Trigger code review on PR open",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-github-pr:1.0.0",
    "container_name": "trigger-github-pr",
    "ports": [
      {
        "host": "${GITHUB_TRIGGER_PORT:-8100}",
        "container": "8100"
      }
    ],
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "webhook",
    "endpoint": "/webhook"
  },

  "action": {
    "workflow_id": "code-review-team"
  }
}
```

### Example 2: GitHub PR with Auth and Mapping

```json
{
  "name": "github_pr_review_advanced",
  "version": "1.0.0",
  "description": "Advanced GitHub PR trigger with auth and parameter mapping",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-github-pr-advanced:1.0.0",
    "container_name": "trigger-github-pr-advanced",
    "ports": [
      {
        "host": "${GITHUB_TRIGGER_PORT:-8101}",
        "container": "8100"
      }
    ],
    "environment": {
      "GITHUB_WEBHOOK_SECRET": "${GITHUB_WEBHOOK_SECRET}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "webhook",
    "endpoint": "/webhook",
    "auth": {
      "type": "secret",
      "header": "X-Hub-Signature-256",
      "secret": "${GITHUB_WEBHOOK_SECRET}"
    }
  },

  "action": {
    "workflow_id": "code-review-team",
    "params": {
      "pr_number": "${event.pull_request.number}",
      "repository": "${event.repository.full_name}",
      "author": "${event.sender.login}"
    }
  },

  "conditions": [
    {
      "field": "event.action",
      "in": ["opened", "synchronize"]
    }
  ]
}
```

### Example 3: Daily Security Scan

```json
{
  "name": "daily_security_scan",
  "version": "1.0.0",
  "description": "Run security scan every day at 2 AM",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.scheduler"
    },
    "image": "trigger-daily-scan:1.0.0",
    "container_name": "trigger-daily-scan",
    "environment": {
      "SCAN_TARGET": "${SCAN_TARGET:-192.168.50.0/24}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "schedule",
    "cron": "0 2 * * *",
    "timezone": "UTC"
  },

  "action": {
    "team_id": "security-team-v2",
    "params": {
      "scan_target": "${SCAN_TARGET:-192.168.50.0/24}",
      "scan_type": "full",
      "notify_on_completion": true
    }
  }
}
```

### Example 4: Slack Slash Command

```json
{
  "name": "slack_command",
  "version": "1.0.0",
  "description": "Execute workflow from Slack slash command",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-slack-command:1.0.0",
    "container_name": "trigger-slack-command",
    "ports": [
      {
        "host": "${SLACK_TRIGGER_PORT:-8102}",
        "container": "8100"
      }
    ],
    "environment": {
      "SLACK_VERIFICATION_TOKEN": "${SLACK_VERIFICATION_TOKEN}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "webhook",
    "endpoint": "/webhook",
    "auth": {
      "type": "token",
      "field": "token",
      "secret": "${SLACK_VERIFICATION_TOKEN}"
    }
  },

  "action": {
    "workflow_id": "${command}",
    "params": {
      "text": "${text}",
      "user_id": "${user_id}",
      "response_url": "${response_url}"
    }
  },

  "response": {
    "sync": true,
    "body": {
      "response_type": "in_channel",
      "text": "Processing: ${text}"
    }
  }
}
```

### Example 5: Linear Issue Automation

```json
{
  "name": "linear_issue_trigger",
  "version": "1.0.0",
  "description": "Trigger workflow when Linear issue is labeled 'automation'",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.webhook"
    },
    "image": "trigger-linear-issue:1.0.0",
    "container_name": "trigger-linear-issue",
    "ports": [
      {
        "host": "${LINEAR_TRIGGER_PORT:-8103}",
        "container": "8100"
      }
    ],
    "environment": {
      "LINEAR_WEBHOOK_SECRET": "${LINEAR_WEBHOOK_SECRET}"
    },
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "webhook",
    "endpoint": "/webhook",
    "auth": {
      "type": "bearer",
      "secret": "${LINEAR_WEBHOOK_SECRET}"
    }
  },

  "action": {
    "workflow_id": "issue-processor",
    "params": {
      "issue_id": "${event.data.id}",
      "title": "${event.data.title}",
      "description": "${event.data.description}"
    }
  },

  "conditions": [
    {
      "field": "event.type",
      "equals": "Issue"
    },
    {
      "field": "event.data.labels",
      "contains": "automation"
    }
  ]
}
```

### Example 6: Workflow Chaining

```json
{
  "name": "post_scan_report",
  "version": "1.0.0",
  "description": "Generate report after security scan completes",
  "type": "trigger",

  "deployment": {
    "build": {
      "context": "./triggers",
      "dockerfile": "Dockerfile.event"
    },
    "image": "trigger-post-scan:1.0.0",
    "container_name": "trigger-post-scan",
    "networks": ["mcp-network"],
    "restart": "unless-stopped"
  },

  "trigger": {
    "type": "event",
    "event": "workflow.completed",
    "source": "security-scan"
  },

  "action": {
    "workflow_id": "report-generator",
    "params": {
      "scan_results": "${event.result}",
      "scan_id": "${event.execution_id}"
    }
  }
}
```

---

## Optional Metadata Fields

### Requirements

```json
{
  "requirements": {
    "secrets": ["API_KEY", "WEBHOOK_SECRET"],
    "min_memory": "128M"
  }
}
```

### Tags

```json
{
  "tags": ["webhook", "github", "automation"]
}
```

### Author Information

```json
{
  "author": "Platform Team",
  "license": "MIT",
  "repository": "https://github.com/org/repo"
}
```

---

## Template Syntax Reference

### Event Data

```
${event.field.path}          # Access nested event data
${event.user.name}           # Example: user name from event
${event.pull_request.number} # Example: PR number
```

### Environment Variables

```
${ENV_VAR}                   # Environment variable
${ENV_VAR:-default}          # With default value
```

### Special Variables

```
${now}                       # Current timestamp
${execution.id}              # Execution ID (in response)
${execution.result}          # Execution result (in response)
```

---

## Comparison to MCP Packages

| Aspect | MCP Package | Trigger Package |
|--------|-------------|-----------------|
| **Purpose** | Add capabilities | Initiate workflows |
| **Defines** | Tools and handlers | Activation and action |
| **Deployment** | Docker container | Docker container |
| **Location** | `registry/mcps/{name}/{version}/` | `registry/triggers/{name}/{version}/` |
| **Install** | Build + deploy container | Build + deploy container |
| **Structure** | metadata + deployment + tools | metadata + deployment + trigger + action |
| **Signing** | GPG-signed (mcp.json.asc) | GPG-signed (trigger.json.asc) |

## Directory Structure Alignment

Triggers follow the same organizational pattern as other package types:

```
demo-sandbox/
├── triggers/                         # Source code (pre-packaging)
│   ├── webhook/
│   │   ├── Dockerfile.webhook
│   │   ├── webhook_trigger.py
│   │   └── requirements.txt
│   ├── schedule/
│   │   ├── Dockerfile.scheduler
│   │   └── schedule_trigger.py
│   └── event/
│       └── event_trigger.py
│
└── registry/                         # Published packages (post-packaging)
    ├── triggers/
    │   └── {name}/
    │       └── {version}/
    │           ├── trigger.json      # Trigger configuration
    │           ├── trigger.json.asc  # GPG signature
    │           └── metadata.json     # Package metadata
    ├── mcps/{name}/{version}/        # Same structure
    ├── teams/{name}/{version}/       # Same structure
    └── publishers/{id}/              # Publisher public keys
```

This mirrors the pattern used for:
- **MCPs:** `mcp_servers/` (source) → `registry/mcps/` (published)
- **Agents:** `agent-definitions/` (source) → `registry/agents/` (published)
- **Teams:** `agent-teams/` (source) → `registry/teams/` (published)

---

## Trigger Implementation Guidelines

Triggers are **Docker containers you build**. The trigger package defines the deployment, but **you decide the implementation**.

### What You Control

As a trigger author, you have full control over:

1. **Container implementation** - Any language, any framework
2. **Webhook validation** - Signature verification, authentication, filtering
3. **Business logic** - Condition evaluation, parameter mapping, response handling
4. **Error handling** - Retries, logging, failure modes
5. **Security** - Rate limiting, input validation, network restrictions

### What the Platform Provides

The trigger package system provides:

1. **Deployment infrastructure** - Build and deploy your container
2. **Network connectivity** - Connect to orchestrator API
3. **Auto-injected environment variables**:
   - `ORCHESTRATOR_URL` - Orchestrator API endpoint (e.g., `http://orchestrator:8000`)
   - `ORCHESTRATOR_WS` - WebSocket endpoint for events (e.g., `ws://orchestrator:8000`)
4. **User-defined environment variables** - Configuration via `.env` and package definition
5. **Container lifecycle** - Start, stop, restart, update
6. **Registry distribution** - Package and share your triggers

### Minimal Contract

Your trigger container must:

1. **Listen on configured port** (for webhooks) OR run continuously (for schedules/events)
2. **Call orchestrator API** to execute workflows/teams:
   ```
   POST http://orchestrator:8000/workflows/execute
   {
     "workflow_id": "your-workflow",
     "params": {...}
   }
   ```
3. **Provide health check** (optional but recommended):
   ```
   GET /health → 200 OK
   ```

Everything else is up to you.

### Example: Minimal Webhook Trigger

**Your implementation** (Python/FastAPI):
```python
from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    # YOU decide how to validate
    # YOU decide what to do with payload
    payload = await request.json()

    # Call orchestrator to execute workflow
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{os.getenv('ORCHESTRATOR_URL')}/workflows/execute",
            json={
                "workflow_id": os.getenv("WORKFLOW_ID"),
                "params": payload
            }
        )

    return {"status": "triggered"}
```

**Your package definition**:
```json
{
  "name": "my_webhook",
  "version": "1.0.0",
  "deployment": {
    "build": {"context": "./triggers", "dockerfile": "Dockerfile.webhook"},
    "image": "my-webhook:1.0.0",
    "container_name": "trigger-my-webhook",
    "ports": [{"host": "8100", "container": "8100"}],
    "environment": {
      "ORCHESTRATOR_URL": "http://orchestrator:8000",
      "WORKFLOW_ID": "${WORKFLOW_ID}"
    },
    "networks": ["mcp-network"]
  },
  "trigger": {"type": "webhook", "endpoint": "/webhook"},
  "action": {"workflow_id": "${WORKFLOW_ID}"}
}
```

The platform handles deployment, you handle the logic.

### Example: Advanced Webhook with Validation

**Your implementation** with signature verification:
```python
import hmac
import hashlib

@app.post("/webhook")
async def webhook(request: Request):
    # YOU implement signature verification
    signature = request.headers.get("X-Hub-Signature-256")
    body = await request.body()

    expected = hmac.new(
        os.getenv("WEBHOOK_SECRET").encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(401, "Invalid signature")

    # YOU implement filtering
    payload = json.loads(body)
    if payload.get("action") not in ["opened", "synchronize"]:
        return {"status": "ignored"}

    # Execute workflow
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{os.getenv('ORCHESTRATOR_URL')}/workflows/execute",
            json={"workflow_id": "code-review", "params": payload}
        )

    return {"status": "triggered"}
```

**Your package definition** (same format, different implementation):
```json
{
  "deployment": {
    "environment": {
      "WEBHOOK_SECRET": "${GITHUB_WEBHOOK_SECRET}"
    }
  }
}
```

### Recommended Patterns

**For security-sensitive triggers:**
- Implement signature verification in your container
- Store secrets in environment variables
- Log all execution attempts
- Implement rate limiting

**For schedule triggers:**
- Use cron libraries (croniter, node-cron, etc.)
- Handle timezone conversions in your code
- Implement execution windows
- Add retry logic

**For event triggers:**
- Subscribe to orchestrator events via WebSocket
- Filter events in your container
- Handle reconnection logic
- Buffer events if needed

### Common Pitfalls

**Don't:**
- ❌ Hardcode orchestrator URL (use environment variable)
- ❌ Store secrets in package JSON (use environment variables)
- ❌ Assume network connectivity (implement retries)
- ❌ Skip error handling (log failures)

**Do:**
- ✅ Use environment variables for configuration
- ✅ Implement health checks
- ✅ Log execution attempts
- ✅ Handle network failures gracefully
- ✅ Validate input in your container

---

## For Trigger Authors: Additional Resources

See [TRIGGER_AUTHOR_GUIDE.md](TRIGGER_AUTHOR_GUIDE.md) for:
- Security best practices
- Testing strategies
- Example implementations
- Common patterns
- Troubleshooting tips

---

## Summary

The trigger package definition mirrors MCP packages:

✅ **Same deployment model** - Docker containers deployed from registry
✅ **4 required sections** - metadata, deployment, trigger, action
✅ **Author controls implementation** - Build it however you want
✅ **Platform provides infrastructure** - Auto-injects ORCHESTRATOR_URL, WORKFLOW_ID/TEAM_ID
✅ **User-configurable targets** - Same trigger package works with any workflow/team
✅ **Documentation fields** - `action`, `params`, `auth`, `filters`, `rate_limit` document behavior
✅ **Git-friendly** - JSON format, version controlled
✅ **Registry-based** - Install exactly like MCP packages

### Key Principles

**Platform Responsibilities:**
- Deploy trigger containers
- Auto-inject environment variables (ORCHESTRATOR_URL, WORKFLOW_ID/TEAM_ID)
- Manage container lifecycle (start, stop, restart, update)
- Provide network connectivity

**Trigger Author Responsibilities:**
- Implement webhook authentication/signature verification
- Implement parameter extraction and mapping
- Implement rate limiting (if needed)
- Implement filtering/conditional logic
- Call orchestrator API to execute workflows/teams

This separation allows trigger authors maximum flexibility while the platform handles infrastructure, enabling anything from a simple "webhook → workflow" trigger to complex conditional automation with dynamic routing and parameter transformation.
