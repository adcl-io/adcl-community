# Trigger System Implementation Plan

**Related Issue:** PRD-35 - Create mechanism for trigger work requests from without a human in the loop
**Related Spec:** [TRIGGER_PACKAGE_DEFINITION.md](TRIGGER_PACKAGE_DEFINITION.md)
**Created:** 2025-10-22
**Last Updated:** 2025-10-29
**Status:** ~~Planning~~ **IMPLEMENTED** (See [TRIGGER_IMPLEMENTATION_STATUS.md](TRIGGER_IMPLEMENTATION_STATUS.md))

---

## ⚠️ IMPLEMENTATION NOTE

**This document represents the original implementation plan. The actual implementation diverged from this plan in several key ways:**

1. **No TriggerManager class** - Triggers are managed by `DockerManager` with `resource_type="trigger"` parameter (consolidated approach)
2. **Flattened registry structure** - Triggers use `registries/triggers/{name}-{version}.json` not nested directories
3. **Existing endpoint used** - Triggers call `/teams/run` (existing), not new `/teams/{team_id}/execute` endpoint
4. **Task template system** - Added `TASK_TEMPLATE` (webhooks) and `TASK_DESCRIPTION` (schedule) environment variables
5. **Dedicated TriggersPage** - Created separate page, not just tabs in Registry
6. **Team selector dropdown** - Auto-fetches teams from API instead of manual ID entry
7. **Experimental UI badges** - Added throughout all trigger UI elements

**For actual implementation details, see:**
- [TRIGGER_IMPLEMENTATION_STATUS.md](TRIGGER_IMPLEMENTATION_STATUS.md) - Current status and architecture
- [TRIGGER_PACKAGE_DEFINITION.md](TRIGGER_PACKAGE_DEFINITION.md) - Package structure
- [TRIGGER_TEST_PLAN.md](TRIGGER_TEST_PLAN.md) - Testing approach

**This document is preserved for historical reference showing the original planning process.**

---

## Overview

This document outlines the implementation plan for the trigger system based on the [Trigger Package Definition](TRIGGER_PACKAGE_DEFINITION.md) specification. The trigger system enables autonomous workflow and team execution in response to webhooks, schedules, events, or manual triggers.

### Goals

1. Enable autonomous workflow/team execution without human intervention
2. Support multiple trigger types (webhook, schedule, event, manual)
3. Maintain architectural consistency with MCP package management
4. Provide user-friendly installation and management interface
5. Ensure security and auditability of trigger execution

---

## Architecture Overview

### Trigger System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Trigger Architecture                        │
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   Webhook    │   │  Schedule    │   │    Event     │   │
│  │   Trigger    │   │  Trigger     │   │   Trigger    │   │
│  │  Container   │   │  Container   │   │  Container   │   │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   │
│         │                   │                   │            │
│         └───────────────────┼───────────────────┘            │
│                             │                                │
│                             ▼                                │
│                  ┌──────────────────────┐                   │
│                  │   Orchestrator API   │                   │
│                  │  /workflows/execute  │                   │
│                  └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Mapping to MCP Architecture

| MCP Component | Trigger Component (Planned) | Actual Implementation | Status |
|---------------|----------------------------|----------------------|--------|
| `mcp_manager.py` | `trigger_manager.py` | `DockerManager(resource_type="trigger")` | ✅ Complete |
| `/registries/install/mcp/{id}` | `/registries/install/trigger/{id}` | `/registries/install/trigger/{id}` | ✅ Complete |
| `installed-mcps.json` | `installed-triggers.json` | `installed-triggers.json` | ✅ Complete |
| MCPs tab (UI) | Triggers tab (UI) | Triggers tab + **TriggersPage.jsx** | ✅ Complete |
| Installed MCPs tab (UI) | Installed Triggers tab (UI) | Installed Triggers tab + **TriggersPage.jsx** | ✅ Complete |

**Note:** Implementation consolidated trigger management into `DockerManager` and created a dedicated `TriggersPage.jsx` instead of just tabs.

---

## Implementation Phases

### Phase 1: Core Infrastructure (3-4 days)

**Goal:** Create the foundational trigger management system

**Note:** TriggerManager follows the identical pattern as MCPManager (backend/app/mcp_manager.py). The update() method copies MCPManager.update() directly (lines 411-448).

#### 1.1 Trigger Manager (backend/app/trigger_manager.py)

**File:** `backend/app/trigger_manager.py`

**Implementation:**
```python
class TriggerManager:
    """
    Manages lifecycle of trigger containers
    Similar to MCPManager but for triggers
    """

    def __init__(self, docker_client, installed_triggers_path):
        """Initialize with Docker client and registry path"""

    async def install(self, trigger_package: dict) -> dict:
        """
        Install trigger from package definition

        Steps:
        1. Validate trigger package structure
        2. Build Docker image (if build context provided)
        3. Create volumes and networks
        4. Resolve user environment variables from package
        5. Inject platform environment variables:
           - ORCHESTRATOR_URL (e.g., http://orchestrator:8000)
           - ORCHESTRATOR_WS (e.g., ws://orchestrator:8000)
        6. Create and start container
        7. Save to installed-triggers.json
        8. Return installation status
        """

    async def uninstall(self, name: str) -> dict:
        """Stop and remove trigger container"""

    async def start(self, name: str) -> dict:
        """Start stopped trigger container"""

    async def stop(self, name: str) -> dict:
        """Stop running trigger container"""

    async def restart(self, name: str) -> dict:
        """Restart trigger container"""

    async def get_status(self, name: str) -> dict:
        """Get trigger container status and metadata"""

    async def list_installed(self) -> list:
        """List all installed triggers with status"""

    async def update(self, name: str, new_package: dict) -> dict:
        """Update trigger to new version"""
```

**Key Features:**
- Docker SDK integration (same as mcp_manager.py)
- Environment variable resolution (`${VAR:-default}`)
- Network configuration (mcp-network)
- Volume management
- Container lifecycle management
- Registry tracking (installed-triggers.json)

**Test Plan:**
- Unit tests for each method
- Test trigger package parsing
- Test container creation/deletion
- Test environment variable resolution
- Test error handling (missing images, network issues)

#### 1.2 Trigger Registry Tracking

**File:** `installed-triggers.json` (created at runtime)

**Structure:**
```json
{
  "github_pr_review": {
    "name": "github_pr_review",
    "version": "1.0.0",
    "package_id": "github-pr-review-1.0.0",
    "container_id": "abc123def456",
    "container_name": "trigger-github-pr",
    "installed_at": "2025-10-22T10:30:00Z",
    "enabled": true,
    "last_triggered": "2025-10-22T14:15:00Z",
    "execution_count": 12,
    "trigger_type": "webhook",
    "deployment": {
      "image": "trigger-github-pr:1.0.0",
      "ports": [{"host": "8100", "container": "8100"}],
      "networks": ["mcp-network"]
    }
  }
}
```

#### 1.3 Backend API Endpoints

**File:** `backend/app/main.py` (additions)

**New Routes:**
```python
# Trigger Management API
POST   /registries/install/trigger/{trigger_id}   # Install trigger from registry
DELETE /triggers/{trigger_name}                    # Uninstall trigger
POST   /triggers/{trigger_name}/start              # Start trigger
POST   /triggers/{trigger_name}/stop               # Stop trigger
POST   /triggers/{trigger_name}/restart            # Restart trigger
POST   /triggers/{trigger_name}/update             # Update to latest version
GET    /triggers/installed                         # List installed triggers
GET    /triggers/{trigger_name}/status             # Get trigger status
GET    /triggers/{trigger_name}/history            # Get execution history
```

**Implementation Notes:**
- Follow same pattern as MCP endpoints
- Add authentication/authorization (future)
- Include proper error handling
- Add request validation
- Return consistent response format

#### 1.4 Basic Webhook Trigger Container

**Directory:** `triggers/webhook/`

**Files:**
- `Dockerfile.webhook`
- `webhook_trigger.py`
- `requirements.txt`

**Implementation:**
```python
# webhook_trigger.py
from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Receive webhook and trigger workflow/team
    """
    # Get webhook payload
    payload = await request.json()

    # TODO: Evaluate conditions (Phase 2)
    # TODO: Map parameters (Phase 2)

    # Execute workflow or team
    async with httpx.AsyncClient() as client:
        if WORKFLOW_ID:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/workflows/execute",
                json={"workflow_id": WORKFLOW_ID, "params": payload}
            )
        elif TEAM_ID:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/teams/{TEAM_ID}/execute",
                json={"params": payload}
            )

    return {"status": "triggered", "execution_id": response.json()["id"]}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webhook_trigger.py .

CMD ["uvicorn", "webhook_trigger:app", "--host", "0.0.0.0", "--port", "8100"]
```

**Deliverables:**
- ✅ trigger_manager.py implementation
- ✅ Trigger API endpoints in main.py
- ✅ installed-triggers.json registry format
- ✅ Basic webhook trigger container
- ✅ Unit tests for trigger_manager
- ✅ API endpoint tests

---

### Phase 2: Registry Integration (1-2 days)

**Goal:** Enable trigger installation from registry

#### 2.1 Registry Package Storage

**Directory:** `registry/triggers/{name}/{version}/`

**Note:** Uses the NEW versioned registry structure with GPG signing (not the old flat registry-server/registries/).

**Package Structure:**
```
registry/triggers/
└── {trigger_name}/
    └── {version}/
        ├── trigger.json          # Trigger configuration
        ├── trigger.json.asc      # GPG signature
        └── metadata.json         # Package metadata (publisher, checksums)
```

**Phase 1 Example Packages:**

1. **github-pr-webhook-1.0.0.json** - GitHub PR webhook trigger
   - Demonstrates: HMAC signature verification (`X-Hub-Signature-256`)
   - Parameter mapping from GitHub PR payload
   - Conditional execution (PR opened/synchronized only)
   - Reference: GitHub webhook documentation

2. **linear-webhook-1.0.0.json** - Linear webhook trigger
   - Demonstrates: Signature verification (`Linear-Signature` header)
   - Duplicate delivery handling (`Linear-Delivery` header)
   - Multiple event types (agentSession, issue assignment)
   - Timestamp verification
   - Reference: https://github.com/adcl-io/linear-agent

3. **daily-scan-1.0.0.json** - Schedule trigger
   - Demonstrates: Cron scheduling (e.g., `0 2 * * *`)
   - Timezone configuration
   - Team execution (not workflow)
   - Environment variable usage for scan target

4. **simple-webhook-1.0.0.json** - Generic webhook trigger
   - Demonstrates: Minimal implementation (no authentication)
   - Basic POST endpoint
   - Template for custom triggers
   - Shows user-configurable target

**Package Format:**
Follow spec from TRIGGER_PACKAGE_DEFINITION.md

**Source Directory:** `triggers/` at project root

Trigger source code (Dockerfiles, Python scripts) lives in `triggers/` before packaging:
```
triggers/
├── webhook/
│   ├── Dockerfile.webhook
│   ├── webhook_trigger.py
│   └── requirements.txt
├── schedule/
│   ├── Dockerfile.scheduler
│   └── schedule_trigger.py
└── event/
    └── event_trigger.py
```

This follows the same pattern as:
- MCPs: `mcp_servers/` (source) → `registry/mcps/` (published)
- Agents: `agent-definitions/` → `registry/agents/`
- Teams: `agent-teams/` → `registry/teams/`

#### 2.2 Registry Server Updates

**File:** `registry-server/server.py`

**New Endpoints:**
```python
@app.get("/triggers")
async def list_trigger_packages():
    """List all trigger packages in registry"""

@app.get("/triggers/{trigger_id}")
async def get_trigger_package(trigger_id: str):
    """Get specific trigger package definition"""
```

#### 2.3 Orchestrator Registry Client

**File:** `backend/app/main.py`

**Implementation:**
```python
@app.post("/registries/install/trigger/{trigger_id}")
async def install_trigger_from_registry(trigger_id: str):
    """
    Install trigger from configured registry

    Steps:
    1. Fetch trigger package from registry
    2. Validate package structure
    3. Call trigger_manager.install()
    4. Return installation status
    """
    # Fetch from registry
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{REGISTRY_URL}/triggers/{trigger_id}")
        trigger_package = response.json()

    # Install
    result = await trigger_manager.install(trigger_package)

    return {
        "status": "installed",
        "trigger": trigger_package["name"],
        "version": trigger_package["version"],
        "container_id": result["container_id"]
    }
```

**Deliverables:**
- ✅ 3 example trigger packages in registry
- ✅ Registry endpoints for triggers
- ✅ Install from registry endpoint
- ✅ Integration tests (registry → orchestrator → Docker)

---

### Phase 3: UI Integration (1-2 days)

**Goal:** Provide user-friendly trigger management interface

#### 3.1 Registry Page - Triggers Tab

**File:** `frontend/src/pages/RegistryPage.jsx`

**Add New Tab:**
```jsx
const [activeTab, setActiveTab] = useState('teams'); // Add 'triggers'

// Tab navigation
<div className="registry-tabs">
  <button onClick={() => setActiveTab('teams')}>Teams</button>
  <button onClick={() => setActiveTab('mcps')}>MCPs</button>
  <button onClick={() => setActiveTab('triggers')}>Triggers</button>  {/* NEW */}
  <button onClick={() => setActiveTab('installed-triggers')}>Installed Triggers</button>  {/* NEW */}
</div>
```

**Triggers Tab Content:**
```jsx
{activeTab === 'triggers' && (
  <div className="triggers-grid">
    {triggerPackages.map(trigger => (
      <div key={trigger.name} className="trigger-card">
        <h3>{trigger.description}</h3>
        <p>Version: {trigger.version}</p>
        <p>Type: {trigger.trigger.type}</p>
        <div className="trigger-tags">
          {trigger.tags?.map(tag => <span key={tag}>{tag}</span>)}
        </div>
        <button onClick={() => installTrigger(trigger.name)}>
          ⬇️ Install
        </button>
      </div>
    ))}
  </div>
)}
```

#### 3.2 Installed Triggers Management

**Installed Triggers Tab:**
```jsx
{activeTab === 'installed-triggers' && (
  <div className="installed-triggers">
    {installedTriggers.map(trigger => (
      <div key={trigger.name} className="installed-trigger-card">
        <div className="trigger-header">
          <h3>{trigger.name}</h3>
          <span className={`status ${trigger.state}`}>
            {trigger.running ? '🟢 Running' : '🔴 Stopped'}
          </span>
        </div>

        <div className="trigger-info">
          <p>Version: {trigger.version}</p>
          <p>Type: {trigger.trigger_type}</p>
          <p>Container: {trigger.container_name}</p>
          <p>Installed: {new Date(trigger.installed_at).toLocaleString()}</p>
          <p>Executions: {trigger.execution_count}</p>
          {trigger.last_triggered && (
            <p>Last Triggered: {new Date(trigger.last_triggered).toLocaleString()}</p>
          )}
        </div>

        <div className="trigger-actions">
          {trigger.running ? (
            <>
              <button onClick={() => stopTrigger(trigger.name)}>⏸️ Stop</button>
              <button onClick={() => restartTrigger(trigger.name)}>🔄 Restart</button>
            </>
          ) : (
            <button onClick={() => startTrigger(trigger.name)}>▶️ Start</button>
          )}
          <button onClick={() => updateTrigger(trigger.name)}>⬆️ Update</button>
          <button onClick={() => uninstallTrigger(trigger.name)} className="danger">
            🗑️ Uninstall
          </button>
        </div>
      </div>
    ))}
  </div>
)}
```

#### 3.3 API Client Functions

```jsx
const installTrigger = async (triggerId) => {
  try {
    const response = await fetch(
      `${API_URL}/registries/install/trigger/${triggerId}`,
      { method: 'POST' }
    );
    const result = await response.json();
    setNotification({ type: 'success', message: `Installed ${result.trigger}` });
    loadInstalledTriggers(); // Refresh list
  } catch (error) {
    setNotification({ type: 'error', message: error.message });
  }
};

const startTrigger = async (name) => {
  const response = await fetch(`${API_URL}/triggers/${name}/start`, { method: 'POST' });
  loadInstalledTriggers();
};

const stopTrigger = async (name) => {
  const response = await fetch(`${API_URL}/triggers/${name}/stop`, { method: 'POST' });
  loadInstalledTriggers();
};

// Similar for restart, update, uninstall
```

**Deliverables:**
- ✅ Triggers tab in Registry page
- ✅ Installed Triggers management tab
- ✅ Install/uninstall UI flows
- ✅ Start/stop/restart controls
- ✅ Status indicators
- ✅ Success/error notifications

---

### Phase 4: Trigger Types Implementation (3-4 days)

**Goal:** Support all trigger types from specification

#### 4.1 Enhanced Webhook Triggers

**Features to Add:**
- Authentication (secret, bearer, token)
- Signature verification
- Filters
- Conditional execution

**File:** `triggers/webhook/webhook_trigger.py`

**Authentication Implementation:**
```python
def verify_signature(request: Request, secret: str, header: str):
    """Verify webhook signature"""
    signature = request.headers.get(header)
    payload = await request.body()

    if header == "X-Hub-Signature-256":
        # GitHub-style HMAC verification
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    # Add other signature types...

def evaluate_conditions(payload: dict, conditions: list) -> bool:
    """Evaluate trigger conditions"""
    for condition in conditions:
        field_value = get_nested_value(payload, condition["field"])

        if "equals" in condition:
            if field_value != condition["equals"]:
                return False
        elif "in" in condition:
            if field_value not in condition["in"]:
                return False
        elif "contains" in condition:
            if condition["contains"] not in field_value:
                return False

    return True
```

#### 4.2 Schedule Triggers

**Directory:** `triggers/schedule/`

**Files:**
- `Dockerfile.scheduler`
- `schedule_trigger.py`

**Implementation:**
```python
# schedule_trigger.py
import asyncio
from croniter import croniter
from datetime import datetime
import httpx
import os

CRON_EXPRESSION = os.getenv("CRON_EXPRESSION")
TIMEZONE = os.getenv("TIMEZONE", "UTC")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")

async def main():
    """Run scheduled trigger"""
    cron = croniter(CRON_EXPRESSION, datetime.now())

    while True:
        next_run = cron.get_next(datetime)
        wait_seconds = (next_run - datetime.now()).total_seconds()

        print(f"Next execution at: {next_run}")
        await asyncio.sleep(wait_seconds)

        # Execute workflow
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/workflows/execute",
                json={"workflow_id": WORKFLOW_ID}
            )
            print(f"Execution triggered: {response.json()}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### 4.3 Event Triggers

**Status:** ⚠️ **Deferred to Phase 6+ OR requires event bus implementation in Phase 4**

**Reason:** Event triggers require a WebSocket event bus in the orchestrator (`/ws/events` endpoint) that does not currently exist.

**Options:**
1. **Defer event triggers** to Phase 6+ (after event bus exists)
2. **Add event bus to Phase 4 scope** (3-4 days → 5-6 days)

**If implementing event bus in Phase 4:**

**Directory:** `triggers/event/`

**Orchestrator changes needed:**
```python
# backend/app/main.py - Add WebSocket event bus

@app.websocket("/ws/events")
async def event_bus(websocket: WebSocket):
    """WebSocket endpoint for event subscriptions"""
    await websocket.accept()

    # Register subscriber
    # Broadcast events to subscribed connections
```

**Event trigger implementation:**
```python
# triggers/event/event_trigger.py
import asyncio
import websockets
import json

EVENT_TYPE = os.getenv("EVENT_TYPE")
EVENT_SOURCE = os.getenv("EVENT_SOURCE")
ORCHESTRATOR_WS = os.getenv("ORCHESTRATOR_WS", "ws://orchestrator:8000/ws/events")

async def main():
    """Listen for platform events"""
    async with websockets.connect(ORCHESTRATOR_WS) as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "event_type": EVENT_TYPE,
            "source": EVENT_SOURCE
        }))

        async for message in ws:
            event = json.loads(message)

            # Trigger workflow based on event
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{os.getenv('ORCHESTRATOR_URL')}/workflows/execute",
                    json={
                        "workflow_id": os.getenv("WORKFLOW_ID"),
                        "params": event
                    }
                )
```

**Decision needed:** Defer or implement event bus?

#### 4.4 Manual Triggers

**Implementation:**
Manual triggers don't need a separate container - they're just API endpoints in the orchestrator:

```python
@app.post("/triggers/{trigger_name}/execute")
async def execute_manual_trigger(trigger_name: str, params: dict = None):
    """Execute a manual trigger"""
    trigger = get_installed_trigger(trigger_name)

    if trigger["trigger_type"] != "manual":
        raise HTTPException(400, "Not a manual trigger")

    # Execute associated workflow/team
    result = await execute_workflow(
        workflow_id=trigger["action"]["workflow_id"],
        params=params
    )

    return result
```

**Deliverables:**
- ✅ Enhanced webhook triggers with auth
- ✅ Schedule trigger implementation
- ✅ Event trigger implementation (basic)
- ✅ Manual trigger endpoints
- ✅ Tests for each trigger type

---

### Phase 5: Advanced Features (2-3 days)

**Goal:** Implement optional advanced features

**Note:** Prometheus metrics are OUT OF SCOPE (confirmed). Use structured logging instead.

#### 5.1 Synchronous Response Support

**Question:** Should synchronous webhooks (wait for workflow completion) be supported?

**Decision:** ✅ **Implement in Phase 5 (deferred from Phase 1)**

**Rationale:**
- Keep Phase 1 simple - focus on async webhooks (fire-and-forget)
- Most use cases (GitHub, Linear, etc.) are async
- Add sync support when use cases emerge (Slack commands, etc.)
- Requires WebSocket connection management and timeout handling

**Implementation:**

For synchronous triggers that wait for completion:

**Trigger Configuration (documentation):**
```json
{
  "trigger": {
    "type": "webhook",
    "response": {
      "sync": true,
      "timeout": 300
    }
  }
}
```

**Trigger Container Implementation:**
```python
async def handle_sync_webhook(request: Request):
    """Handle webhook with synchronous response"""
    payload = await request.json()

    # Execute workflow
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('ORCHESTRATOR_URL')}/workflows/execute",
            json={"workflow_id": WORKFLOW_ID, "params": payload}
        )
        execution_id = response.json()["id"]

    # Wait for completion via WebSocket
    async with websockets.connect(
        f"ws://{os.getenv('ORCHESTRATOR_WS')}/ws/execute/{execution_id}"
    ) as ws:
        async for message in ws:
            event = json.loads(message)
            if event["type"] == "execution_complete":
                result = event["result"]
                break

    # Return workflow result
    return JSONResponse(content={"status": "completed", "result": result})
```

#### 5.2 Parameter Mapping Examples

**Note:** Parameter mapping is implemented by trigger authors (Decision #0).
This section provides reference implementations for common patterns.

**Template Resolution Reference:**
```python
def resolve_template(template: str, context: dict) -> str:
    """
    Resolve template variables like ${event.field.path}

    Supports:
    - ${event.field.path} - Nested event data
    - ${ENV_VAR:-default} - Environment variables with defaults
    - ${now} - Current timestamp
    """
    import re
    from datetime import datetime

    def replace_var(match):
        var = match.group(1)

        # Special variables
        if var == "now":
            return datetime.now().isoformat()

        # Environment variable
        if ":-" in var:
            env_var, default = var.split(":-")
            return os.getenv(env_var, default)

        # Event data
        if var.startswith("event."):
            path = var[6:].split(".")
            value = context.get("event", {})
            for key in path:
                value = value.get(key, {})
            return str(value)

        return match.group(0)

    return re.sub(r'\$\{([^}]+)\}', replace_var, template)
```

#### 5.3 Response Configuration

For synchronous triggers that wait for completion:

```python
async def handle_sync_webhook(request: Request, trigger_config: dict):
    """Handle webhook with synchronous response"""
    payload = await request.json()

    # Execute workflow
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORCHESTRATOR_URL}/workflows/execute",
            json={"workflow_id": trigger_config["action"]["workflow_id"]}
        )
        execution_id = response.json()["id"]

    # Wait for completion via WebSocket
    async with websockets.connect(
        f"ws://{ORCHESTRATOR_URL}/ws/execute/{execution_id}"
    ) as ws:
        async for message in ws:
            event = json.loads(message)
            if event["type"] == "execution_complete":
                result = event["result"]
                break

    # Format response using template
    response_body = resolve_template(
        trigger_config["response"]["body"],
        {"execution": result}
    )

    return JSONResponse(content=response_body)
```

#### 5.4 Execution History Tracking

**Add to installed-triggers.json:**
```json
{
  "github_pr_review": {
    "execution_history": [
      {
        "timestamp": "2025-10-22T14:15:00Z",
        "trigger_data": {"pr_number": 123},
        "workflow_id": "code-review",
        "execution_id": "exec-abc123",
        "status": "success",
        "duration_ms": 2500
      }
    ]
  }
}
```

**API Endpoint:**
```python
@app.get("/triggers/{trigger_name}/history")
async def get_trigger_history(trigger_name: str, limit: int = 50):
    """Get execution history for trigger"""
    trigger = get_installed_trigger(trigger_name)
    history = trigger.get("execution_history", [])
    return history[:limit]
```

**Deliverables:**
- ✅ Parameter mapping implementation
- ✅ Response configuration for sync triggers
- ✅ Execution history tracking
- ✅ History API endpoint
- ✅ UI for viewing history

---

## Testing Strategy

### Unit Tests

**Files:**
- `tests/test_trigger_manager.py`
- `tests/test_webhook_trigger.py`
- `tests/test_schedule_trigger.py`
- `tests/test_parameter_mapping.py`

**Coverage:**
- Trigger package parsing
- Container lifecycle operations
- Environment variable resolution
- Condition evaluation
- Parameter template resolution
- Authentication verification

### Integration Tests

**Files:**
- `tests/integration/test_trigger_install.py`
- `tests/integration/test_webhook_flow.py`
- `tests/integration/test_schedule_flow.py`

**Coverage:**
- Registry → Orchestrator → Docker flow
- End-to-end webhook trigger
- End-to-end schedule trigger
- Workflow execution from triggers

### Security Tests

**Files:**
- `tests/security/test_webhook_auth.py`
- `tests/security/test_rate_limiting.py`

**Coverage:**
- Signature verification
- Invalid authentication rejection
- Rate limiting enforcement
- Unauthorized access attempts

### Manual Testing Checklist

- [ ] Install trigger from registry UI
- [ ] Verify container starts successfully
- [ ] Send test webhook payload
- [ ] Verify workflow executes
- [ ] Stop trigger via UI
- [ ] Start trigger via UI
- [ ] Update trigger to new version
- [ ] Uninstall trigger
- [ ] Test schedule trigger execution
- [ ] Test manual trigger execution

---

## Open Questions & Decisions

### ✅ Resolved: Update Mechanism

**Question:** How should trigger updates and version management work?

**Decision:** ✅ **Follow MCPManager.update() pattern exactly (lines 411-448)**

**Implementation:**
```python
def update(self, name: str, new_package: Dict[str, Any]) -> Dict[str, Any]:
    """Update trigger to new version"""
    # 1. Check if installed
    # 2. Compare versions
    # 3. Uninstall old version
    # 4. Install new version
    # 5. Return result with old_version and new_version
```

**Notes:**
- No rollback mechanism in MVP (same as MCPs)
- If new install fails, old version is lost
- See Linear issue for future enhancement: "Add rollback support for MCP/Trigger updates"

---

### 0. Parameter Mapping and Target Configuration

**Question:** Where does parameter mapping happen, and how is the trigger target (workflow/team) configured?

**Decision:** ✅ **Target is user-configurable at install time; parameter mapping is implemented by trigger authors**

**Rationale:**
- Maximum flexibility - users decide what workflow/team to trigger
- Same trigger package can be reused with different targets
- Platform auto-injects target at install time (like ORCHESTRATOR_URL)
- Authors implement parameter extraction logic for flexibility
- The `action` field in package JSON is **documentation only** (shows intended use)

**Implementation:**

**1. Target Configuration (User Provides at Install):**

Package JSON (documentation only):
```json
{
  "name": "github_pr_webhook",
  "action": {
    "workflow_id": "code-review-team",  // Example/documentation only
    "params": {
      "pr_number": "${event.pull_request.number}",  // Documents what will be sent
      "repository": "${event.repository.full_name}"
    }
  }
}
```

User installs with target:
```bash
# Install trigger and specify target
POST /registries/install/trigger/github-pr-webhook-1.0.0
{
  "workflow_id": "my-custom-review-workflow"
}

# OR with team instead
POST /registries/install/trigger/github-pr-webhook-1.0.0
{
  "team_id": "security-team-v2"
}
```

Platform auto-injects:
```bash
ORCHESTRATOR_URL=http://orchestrator:8000
ORCHESTRATOR_WS=ws://orchestrator:8000
WORKFLOW_ID=my-custom-review-workflow  # From user at install time
```

**2. Parameter Mapping (Author Implements):**

Trigger container code:
```python
# Platform-injected (automatically available)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    # Author implements parameter extraction
    params = {
        "pr_number": payload["pull_request"]["number"],
        "repository": payload["repository"]["full_name"],
        "author": payload["sender"]["login"]
    }

    # Call user-configured target
    if WORKFLOW_ID:
        await client.post(
            f"{ORCHESTRATOR_URL}/workflows/execute",
            json={"workflow_id": WORKFLOW_ID, "params": params}
        )
    elif TEAM_ID:
        await client.post(
            f"{ORCHESTRATOR_URL}/teams/{TEAM_ID}/execute",
            json={"params": params}
        )
```

**3. Install API:**
```python
@app.post("/registries/install/trigger/{trigger_id}")
async def install_trigger(
    trigger_id: str,
    config: dict  # {"workflow_id": "...", "team_id": "..."}
):
    """Install trigger with user-specified target"""
    package = fetch_from_registry(trigger_id)

    # User must provide target (required)
    if not config.get("workflow_id") and not config.get("team_id"):
        raise HTTPException(400, "Must specify workflow_id or team_id")

    # Build environment variables
    env_vars = {
        # Platform auto-injected
        "ORCHESTRATOR_URL": "http://orchestrator:8000",
        "ORCHESTRATOR_WS": "ws://orchestrator:8000",
        "WORKFLOW_ID": config.get("workflow_id"),
        "TEAM_ID": config.get("team_id"),

        # User-defined from package
        **resolve_env_vars(package["deployment"]["environment"])
    }

    await trigger_manager.install(package, env_vars)
```

**Future Enhancement (Phase 6+):**
- Validate target exists at install time
- Fetch target workflow/team parameter schema
- Compare with trigger's documented `params` from package JSON
- Warn if parameter mismatch detected

**Example Validation:**
```
Installing: github-pr-webhook
Target: code-review-team (workflow)

Checking parameter compatibility...
✓ pr_number - accepted by workflow
✓ repository - accepted by workflow
⚠ author - not expected by workflow (will be ignored)

Continue? [Y/n]
```

---

### 1. Event Bus Implementation

**Question:** How should event-based triggers subscribe to platform events?

**Options:**
- A. In-memory event dispatcher in orchestrator
- B. Redis Pub/Sub for event distribution
- C. WebSocket subscriptions from triggers to orchestrator

**Decision:** ✅ **WebSocket subscriptions (Option C)**

**Rationale:**
- Consistent with existing orchestrator WebSocket pattern (workflow execution streaming)
- No new infrastructure dependencies
- Real-time event delivery
- Simple for MVP, can migrate to Redis for multi-instance scaling later

**Implementation:**
- Orchestrator provides `/ws/events` WebSocket endpoint
- Event triggers connect and subscribe to specific event types
- Orchestrator broadcasts events to subscribed WebSocket connections
- Triggers handle reconnection logic in their containers

---

### 2. Trigger Execution Context

**Question:** Should triggers execute in the same Docker network as workflows?

**Current State:** Triggers use `mcp-network`

**Decision:** ✅ Yes - use same network for simplicity

---

### 3. Secrets Management

**Question:** How should webhook secrets and API keys be stored?

**Options:**
- A. Environment variables (current approach)
- B. Docker secrets
- C. External secrets manager (Vault, AWS Secrets Manager)

**Recommendation:** Start with A, document migration path to C

**Decision:** ✅ Use environment variables for Phase 1

---

### 4. Rate Limiting

**Question:** Should rate limiting be implemented by the platform or by trigger authors?

**Decision:** ✅ **Trigger authors implement (Option A)**

**Rationale:**
- Consistent with "trigger authors control implementation" philosophy
- Flexibility for different rate limiting strategies (per-IP, per-token, per-repository, etc.)
- Keeps platform simple - focused on deployment, not enforcement
- Some triggers (internal/trusted) may not need rate limiting

**Implementation:**
- The `rate_limit` field in trigger package JSON is **metadata/documentation only**
- Platform does NOT read or enforce rate limiting
- Trigger authors implement rate limiting in their container code
- TRIGGER_AUTHOR_GUIDE.md provides comprehensive examples and best practices
- Future: Can add optional helper library for convenience (Phase 6+)

**Example in package (documentation only):**
```json
{
  "trigger": {
    "type": "webhook",
    "rate_limit": {
      "requests": 100,
      "window_seconds": 60,
      "strategy": "per-ip"
    }
  }
}
```

**Example in trigger container (author implements):**
```python
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

@app.post("/webhook")
async def webhook(request: Request):
    if not rate_limiter.is_allowed(request.client.host):
        raise HTTPException(429, "Rate limit exceeded")
    # Process webhook...
```

---

### 4. Execution History Storage

**Question:** How should trigger execution history be stored and managed?

**Decision:** ✅ **Use orchestrator logs only (Option C)**

**Rationale:**
- Simple - no new storage mechanism needed
- Logs already exist and are collected by orchestrator
- Standard log tooling for querying and analysis
- Avoid premature optimization - add structured storage if needed later

**Implementation:**

Triggers log execution attempts:
```python
# In trigger container
logger.info(
    f"Triggering workflow: {WORKFLOW_ID}",
    extra={
        "trigger": "github-pr-webhook",
        "workflow_id": WORKFLOW_ID,
        "params": params
    }
)
```

Orchestrator logs execution results:
```python
# In orchestrator
logger.info(
    f"Workflow triggered by: {trigger_name}",
    extra={
        "trigger": trigger_name,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "status": "started"
    }
)
```

Users query via logs:
```bash
# View trigger activity
docker-compose logs orchestrator | grep "trigger=github-pr-webhook"

# Or use standard log tools
kubectl logs orchestrator | jq 'select(.trigger)'
```

**Future Enhancement (Phase 6+):**
- Add structured execution history (SQLite or database)
- API endpoint for querying history
- Metrics dashboard showing trigger statistics

---

### 5. Trigger Monitoring

**Question:** What metrics should be tracked?

**Proposed Metrics:**
- Execution count
- Success/failure rate
- Average execution time
- Last triggered timestamp

**Decision:** ✅ Track via orchestrator logs for Phase 1

**Implementation:**
- All metrics available via log analysis
- Can aggregate using standard log tools (grep, jq, etc.)
- Future: Add metrics endpoint if needed

---

## Dependencies

### New Package Dependencies

**Backend:**
```
# requirements.txt additions
croniter==2.0.1      # For schedule triggers
```

**Trigger Containers:**
```
# webhook trigger
fastapi==0.104.1
httpx==0.25.0
python-multipart==0.0.6

# schedule trigger
croniter==2.0.1
httpx==0.25.0
```

### Infrastructure Dependencies

- Docker SDK (already installed)
- mcp-network (already exists)
- Registry server (already running)

---

## Rollout Plan

### Stage 1: Internal Testing (Week 1)

- Deploy to development environment
- Install sample triggers
- Test all trigger types
- Fix critical bugs

### Stage 2: Documentation (Week 1-2)

- Complete API documentation
- Write user guides
- Create tutorial videos
- Update platform README

### Stage 3: Beta Release (Week 2)

- Deploy to staging
- Enable for beta users
- Gather feedback
- Iterate on UI/UX

### Stage 4: Production Release (Week 3)

- Final security review
- Performance testing
- Deploy to production
- Monitor metrics

---

## Success Metrics

### Technical Metrics

- [ ] 100% of trigger types implemented
- [ ] >90% test coverage
- [ ] <100ms trigger response time (webhooks)
- [ ] Zero security vulnerabilities
- [ ] Container startup time <5 seconds

### User Metrics

- [ ] Trigger installation success rate >95%
- [ ] Average time to install trigger <30 seconds
- [ ] User satisfaction score >4/5
- [ ] <5 support tickets in first month

---

## Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Core Infrastructure | 3-4 days | 📋 Planning |
| Phase 2: Registry Integration | 1-2 days | 📋 Planning |
| Phase 3: UI Integration | 1-2 days | 📋 Planning |
| Phase 4: Trigger Types | 3-4 days | 📋 Planning |
| Phase 5: Advanced Features | 2-3 days | 📋 Planning |
| **Total** | **11-16 days** | |

**Target Completion:** 3 weeks from start date

---

## Related Documents

- [TRIGGER_PACKAGE_DEFINITION.md](TRIGGER_PACKAGE_DEFINITION.md) - Package specification
- [MCP_PACKAGE_MANAGEMENT.md](MCP_PACKAGE_MANAGEMENT.md) - Reference architecture
- [arch.md](../arch.md) - Platform architecture
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Variable resolution

---

## Next Steps

1. Review and approve this implementation plan
2. Create Linear/GitHub issues for each phase
3. Assign development resources
4. Set target dates for each phase
5. Begin Phase 1 implementation

**Status:** ✅ Plan complete - Ready for approval
