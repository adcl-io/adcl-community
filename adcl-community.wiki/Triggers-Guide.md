# Triggers Guide

Learn how to automate workflow and team execution with webhooks and schedules.

---

## Table of Contents

1. [What are Triggers?](#what-are-triggers)
2. [Trigger Types](#trigger-types)
3. [Webhook Triggers](#webhook-triggers)
4. [Schedule Triggers](#schedule-triggers)
5. [Installing Triggers](#installing-triggers)
6. [Managing Triggers](#managing-triggers)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What are Triggers?

**Triggers** are automated execution mechanisms that run workflows or teams based on events:

- **Webhook Triggers**: Execute when HTTP POST is received
- **Schedule Triggers**: Execute at specified times (cron-based)

### Use Cases

**Webhook Triggers**:
- CI/CD integration (trigger on git push)
- Alert response (trigger on monitoring alert)
- External system integration (trigger on external event)

**Schedule Triggers**:
- Daily security scans
- Weekly reports
- Nightly cleanup tasks
- Periodic health checks

---

## Trigger Types

### Webhook Trigger

```
External System                ADCL Platform
      │                             │
      │ POST /trigger/webhook/name  │
      ├────────────────────────────▶│
      │                             │
      │                        Execute workflow/team
      │                             │
      │◀────────200 OK───────────── │
```

**Example**:
```bash
# External system sends webhook
curl -X POST http://localhost:8000/trigger/webhook/deploy-scan \
  -H "Content-Type: application/json" \
  -d '{"environment": "production", "version": "1.2.3"}'

# ADCL executes configured workflow/team
```

### Schedule Trigger

```
Time: 02:00 AM daily
  ↓
Cron: 0 2 * * *
  ↓
Execute workflow/team automatically
```

**Example**:
```json
{
  "schedule": "0 2 * * *",  // Every day at 2am
  "workflow_id": "security_scan",
  "enabled": true
}
```

---

## Webhook Triggers

### Creating a Webhook Trigger

**Step 1: Define Trigger Configuration**

Create `triggers/webhook/my-webhook.json`:

```json
{
  "name": "deploy-scan",
  "type": "webhook",
  "description": "Scan network after deployment",
  "config": {
    "execution_type": "workflow",
    "execution_id": "security_scan_workflow",
    "secret": "your-webhook-secret",
    "parameter_mapping": {
      "target": "$.payload.network",
      "environment": "$.payload.environment"
    }
  }
}
```

**Step 2: Install Trigger**

```bash
# Via UI
Go to Registry → Triggers → Install "Deploy Scan Trigger"

# Via API
curl -X POST http://localhost:8000/triggers/install \
  -H "Content-Type: application/json" \
  -d @triggers/webhook/my-webhook.json
```

**Step 3: Get Webhook URL**

```bash
# List triggers to get URL
curl http://localhost:8000/triggers

# Response
{
  "triggers": [
    {
      "name": "deploy-scan",
      "type": "webhook",
      "url": "http://localhost:8000/trigger/webhook/deploy-scan",
      "status": "active"
    }
  ]
}
```

**Step 4: Send Webhook**

```bash
# From external system
curl -X POST http://localhost:8000/trigger/webhook/deploy-scan \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -d '{
    "payload": {
      "network": "192.168.1.0/24",
      "environment": "production"
    }
  }'

# Response
{
  "status": "triggered",
  "execution_id": "exec_12345"
}
```

### Webhook Configuration

```json
{
  "name": "webhook-name",
  "type": "webhook",
  "description": "Human-readable description",
  "config": {
    // What to execute
    "execution_type": "workflow",  // or "team"
    "execution_id": "workflow_id",  // or team_id

    // Security
    "secret": "webhook-secret",  // Verify sender
    "validate_signature": true,  // Check HMAC signature

    // Parameter mapping (JSONPath)
    "parameter_mapping": {
      "target": "$.payload.network",
      "scan_type": "$.payload.type"
    },

    // Optional filters
    "filter": {
      "environment": "production"  // Only trigger if matches
    },

    // Retry configuration
    "retry": {
      "enabled": true,
      "max_attempts": 3,
      "backoff": "exponential"
    }
  }
}
```

### Webhook Security

**Secret Verification**:
```bash
# Sender includes secret in header
curl -X POST http://localhost:8000/trigger/webhook/deploy-scan \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -d '{"payload": {...}}'
```

**HMAC Signature** (recommended):
```bash
# Sender signs payload with shared secret
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/trigger/webhook/deploy-scan \
  -H "X-Webhook-Signature: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

**IP Allowlist**:
```json
{
  "config": {
    "allowed_ips": ["10.0.1.0/24", "192.168.1.100"]
  }
}
```

### Parameter Mapping

Use JSONPath to extract data from webhook payload:

**Webhook Payload**:
```json
{
  "event": "deployment",
  "payload": {
    "network": "192.168.1.0/24",
    "environment": "production",
    "version": "1.2.3",
    "metadata": {
      "region": "us-west",
      "team": "security"
    }
  }
}
```

**Parameter Mapping**:
```json
{
  "parameter_mapping": {
    "target": "$.payload.network",          // → "192.168.1.0/24"
    "env": "$.payload.environment",         // → "production"
    "version": "$.payload.version",         // → "1.2.3"
    "region": "$.payload.metadata.region"   // → "us-west"
  }
}
```

**Workflow Receives**:
```json
{
  "target": "192.168.1.0/24",
  "env": "production",
  "version": "1.2.3",
  "region": "us-west"
}
```

---

## Schedule Triggers

### Creating a Schedule Trigger

**Step 1: Define Trigger Configuration**

Create `triggers/schedule/nightly-scan.json`:

```json
{
  "name": "nightly-scan",
  "type": "schedule",
  "description": "Daily security scan at 2 AM",
  "config": {
    "schedule": "0 2 * * *",  // Cron expression
    "execution_type": "workflow",
    "execution_id": "security_scan_workflow",
    "timezone": "America/Los_Angeles",
    "parameters": {
      "target": "${env:DEFAULT_SCAN_NETWORK}",
      "scan_type": "comprehensive"
    }
  }
}
```

**Step 2: Install Trigger**

```bash
# Via UI
Go to Registry → Triggers → Install "Nightly Security Scan"

# Via API
curl -X POST http://localhost:8000/triggers/install \
  -H "Content-Type: application/json" \
  -d @triggers/schedule/nightly-scan.json
```

**Step 3: Enable Trigger**

```bash
# Via UI
Go to Triggers → Enable "nightly-scan"

# Via API
curl -X POST http://localhost:8000/triggers/nightly-scan/enable
```

### Cron Expressions

Cron format: `minute hour day month weekday`

**Common Schedules**:

```bash
# Every day at 2 AM
0 2 * * *

# Every Monday at 9 AM
0 9 * * 1

# Every hour
0 * * * *

# Every 15 minutes
*/15 * * * *

# First day of month at midnight
0 0 1 * *

# Every weekday at 8 AM
0 8 * * 1-5

# Every 6 hours
0 */6 * * *
```

**Cron Fields**:
```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

### Schedule Configuration

```json
{
  "name": "schedule-name",
  "type": "schedule",
  "description": "Human-readable description",
  "config": {
    // When to execute
    "schedule": "0 2 * * *",  // Cron expression
    "timezone": "America/Los_Angeles",  // Optional, default UTC

    // What to execute
    "execution_type": "workflow",  // or "team"
    "execution_id": "workflow_id",

    // Parameters (static or from env)
    "parameters": {
      "target": "${env:DEFAULT_SCAN_NETWORK}",
      "scan_type": "full"
    },

    // Optional conditions
    "conditions": {
      "only_if_changed": true,  // Only run if data changed
      "skip_if_running": true   // Skip if previous still running
    },

    // Notifications
    "notifications": {
      "on_success": ["email@example.com"],
      "on_failure": ["ops@example.com"]
    }
  }
}
```

---

## Installing Triggers

### From Registry

**Step 1: Browse Available Triggers**

```
Go to Registry → Triggers tab
View available trigger packages
```

**Step 2: Install Trigger**

```
Click "Install" on desired trigger
Trigger downloads and installs automatically
```

**Step 3: Configure Trigger**

```
Go to Triggers page
Click on installed trigger
Configure parameters:
  - Webhook secret
  - Schedule time
  - Target workflow/team
  - Parameters
```

**Step 4: Enable Trigger**

```
Click "Enable" to activate
Trigger starts listening (webhook) or scheduled (cron)
```

### Manual Installation

**Step 1: Create Trigger Files**

```bash
# For webhook trigger
mkdir -p triggers/webhook/my-trigger
cat > triggers/webhook/my-trigger/config.json <<EOF
{
  "name": "my-trigger",
  "type": "webhook",
  ...
}
EOF

# For schedule trigger
mkdir -p triggers/schedule/my-schedule
cat > triggers/schedule/my-schedule/config.json <<EOF
{
  "name": "my-schedule",
  "type": "schedule",
  ...
}
EOF
```

**Step 2: Restart Platform**

```bash
./clean-restart.sh
```

---

## Managing Triggers

### Viewing Triggers

**Via UI**:
```
Go to Triggers page
View list of installed triggers
Status: Active, Inactive, Error
```

**Via API**:
```bash
# List all triggers
curl http://localhost:8000/triggers

# Get specific trigger
curl http://localhost:8000/triggers/my-trigger
```

### Enabling/Disabling

**Via UI**:
```
Go to Triggers page
Click toggle switch next to trigger
```

**Via API**:
```bash
# Enable trigger
curl -X POST http://localhost:8000/triggers/my-trigger/enable

# Disable trigger
curl -X POST http://localhost:8000/triggers/my-trigger/disable
```

### Execution History

**Via UI**:
```
Go to Triggers page
Click on trigger name
View execution history:
  - Timestamp
  - Status (success/failure)
  - Duration
  - Output
```

**Via API**:
```bash
# Get execution history
curl http://localhost:8000/triggers/my-trigger/history
```

### Uninstalling

**Via UI**:
```
Go to Triggers page
Click "Uninstall" on trigger
Confirm removal
```

**Via API**:
```bash
curl -X DELETE http://localhost:8000/triggers/my-trigger
```

---

## Best Practices

### 1. Use Secrets for Webhooks

**Do**:
```json
{
  "config": {
    "secret": "${env:WEBHOOK_SECRET}",  // From .env
    "validate_signature": true
  }
}
```

**Don't**:
```json
{
  "config": {
    "secret": "plaintext-secret-in-file"  // Insecure
  }
}
```

### 2. Avoid Overlapping Schedules

**Do**:
```
Scan A: 0 2 * * *  (2 AM)
Scan B: 0 3 * * *  (3 AM)
```

**Don't**:
```
Scan A: 0 2 * * *  (2 AM)
Scan B: 0 2 * * *  (2 AM - same time!)
```

### 3. Set Reasonable Timeouts

**Do**:
```json
{
  "config": {
    "timeout": 3600,  // 1 hour max
    "skip_if_running": true
  }
}
```

**Don't**:
```json
{
  "config": {
    "timeout": 86400  // 24 hours - too long
  }
}
```

### 4. Monitor Trigger Executions

**Do**:
- Check execution history regularly
- Set up failure notifications
- Review logs for errors

**Don't**:
- Set-and-forget triggers
- Ignore failed executions

### 5. Use Appropriate Schedules

**Do**:
```
Nightly scan: 0 2 * * *  (Low traffic time)
Business hours check: 0 9-17 * * 1-5
Weekly report: 0 8 * * 1  (Monday morning)
```

**Don't**:
```
Every minute scan: * * * * *  (Too frequent)
Peak hours scan: 0 12 * * *  (High traffic time)
```

---

## Example Triggers

### CI/CD Deployment Webhook

```json
{
  "name": "deployment-webhook",
  "type": "webhook",
  "description": "Scan network after deployment",
  "config": {
    "execution_type": "workflow",
    "execution_id": "security_scan_workflow",
    "secret": "${env:DEPLOY_WEBHOOK_SECRET}",
    "parameter_mapping": {
      "target": "$.deployment.network",
      "environment": "$.deployment.environment"
    },
    "filter": {
      "environment": "production"
    }
  }
}
```

### Nightly Security Scan

```json
{
  "name": "nightly-security-scan",
  "type": "schedule",
  "description": "Comprehensive security scan at 2 AM",
  "config": {
    "schedule": "0 2 * * *",
    "execution_type": "team",
    "execution_id": "security_analysis_team",
    "parameters": {
      "target": "${env:DEFAULT_SCAN_NETWORK}",
      "report_path": "/workspace/reports/nightly-{date}.md"
    },
    "conditions": {
      "skip_if_running": true
    }
  }
}
```

### Weekly Report Generation

```json
{
  "name": "weekly-report",
  "type": "schedule",
  "description": "Generate weekly security report",
  "config": {
    "schedule": "0 8 * * 1",  // Monday 8 AM
    "execution_type": "workflow",
    "execution_id": "generate_report_workflow",
    "parameters": {
      "period": "week",
      "recipients": ["security@company.com"]
    }
  }
}
```

---

## Troubleshooting

### Trigger Not Firing

**Webhook Trigger**:
```bash
# Check trigger is enabled
curl http://localhost:8000/triggers/my-trigger

# Test webhook manually
curl -X POST http://localhost:8000/trigger/webhook/my-trigger \
  -H "X-Webhook-Secret: secret" \
  -d '{"test": true}'

# Check logs
docker-compose logs orchestrator | grep trigger
```

**Schedule Trigger**:
```bash
# Verify cron expression
# Use: https://crontab.guru

# Check trigger is enabled
curl http://localhost:8000/triggers/my-schedule

# View next scheduled execution
curl http://localhost:8000/triggers/my-schedule/next-run

# Check logs
docker-compose logs orchestrator | grep schedule
```

### Webhook Returns 401 Unauthorized

**Cause**: Invalid secret

**Solution**:
```bash
# Verify secret matches
cat .env | grep WEBHOOK_SECRET

# Test with correct secret
curl -X POST http://localhost:8000/trigger/webhook/my-trigger \
  -H "X-Webhook-Secret: correct-secret" \
  -d '{"test": true}'
```

### Schedule Runs at Wrong Time

**Cause**: Timezone mismatch

**Solution**:
```json
{
  "config": {
    "schedule": "0 2 * * *",
    "timezone": "America/Los_Angeles"  // Specify timezone
  }
}
```

---

## Next Steps

- **[Workflows Guide](Workflows-Guide)** - Create workflows to trigger
- **[Teams Guide](Teams-Guide)** - Create teams to trigger
- **[Registry Guide](Registry-Guide)** - Install pre-built triggers
- **[Configuration Guide](Configuration-Guide)** - Advanced trigger configuration

---

**Questions?** Check the [FAQ](FAQ) or [Troubleshooting Guide](Troubleshooting).
