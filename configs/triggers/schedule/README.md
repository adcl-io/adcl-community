# Schedule Trigger

Cron-based schedule trigger for executing workflows at configured times.

## Features

- ✅ Cron expression support (standard 5-field format)
- ✅ Timezone support
- ✅ Automatic scheduling loop
- ✅ Error recovery and retry
- ✅ Structured logging with schedule context

## Usage

### Install from Registry

```bash
POST /registries/install/trigger/daily-scan-1.0.0
{
  "team_id": "security-team"
}
```

### Environment Variables

**Platform auto-injected:**
- `ORCHESTRATOR_URL` - Orchestrator API URL
- `WORKFLOW_ID` or `TEAM_ID` - User-configured target

**User-defined (in trigger package):**
- `CRON_EXPRESSION` - Cron schedule (default: "0 0 * * *" - daily at midnight)
- `TIMEZONE` - Timezone for schedule (default: UTC)

## Cron Expression Format

Standard 5-field cron format:
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sun=0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Examples

```bash
# Every minute
CRON_EXPRESSION="* * * * *"

# Every hour at minute 0
CRON_EXPRESSION="0 * * * *"

# Daily at 2:30 AM
CRON_EXPRESSION="30 2 * * *"

# Every Monday at 9 AM
CRON_EXPRESSION="0 9 * * 1"

# First day of every month at midnight
CRON_EXPRESSION="0 0 1 * *"

# Every 15 minutes
CRON_EXPRESSION="*/15 * * * *"
```

## How It Works

1. Parse cron expression on startup
2. Calculate next execution time
3. Sleep until execution time
4. Execute workflow/team
5. Calculate next execution time
6. Repeat

## Parameter Injection

Workflow receives:
```json
{
  "triggered_at": "2025-10-25T10:00:00Z",
  "trigger_type": "schedule",
  "cron_expression": "0 */6 * * *"
}
```

## Logging

Logs include:
- Next scheduled execution time
- Wait duration
- Cron expression
- Target (workflow_id/team_id)
- Execution results

## Error Handling

- Invalid cron expression: Logs error and exits
- Network errors: Logs error, waits 60s, retries
- Workflow execution errors: Logs error, continues to next schedule

## Examples

### Daily Security Scan

```json
{
  "name": "daily-scan",
  "deployment": {
    "environment": {
      "CRON_EXPRESSION": "0 2 * * *",
      "TIMEZONE": "America/New_York"
    }
  }
}
```

Executes every day at 2:00 AM EST.

### Hourly Health Check

```json
{
  "environment": {
    "CRON_EXPRESSION": "0 * * * *"
  }
}
```

Executes every hour on the hour.

### Weekly Report

```json
{
  "environment": {
    "CRON_EXPRESSION": "0 9 * * 1"
  }
}
```

Executes every Monday at 9:00 AM.

## Monitoring

Check container logs:
```bash
docker logs trigger-daily-scan

# Output:
# INFO: Schedule trigger started
# INFO: Next execution scheduled at 2025-10-26T02:00:00Z
# INFO: Triggering team: security-team
# INFO: Scheduled workflow/team triggered successfully
```

## Testing

### Test Immediately

Set cron to run every minute for testing:
```bash
CRON_EXPRESSION="* * * * *"
```

### Dry Run

Check next execution time without running:
```python
from croniter import croniter
from datetime import datetime

cron = croniter("0 2 * * *", datetime.now())
print(f"Next run: {cron.get_next(datetime)}")
```

## Limitations

- **No missed execution recovery:** If container is down during scheduled time, execution is skipped
- **Single execution:** Does not queue multiple executions if workflow takes longer than schedule interval
- **No timezone DST handling:** Uses simple UTC offsets

For more complex scheduling needs, consider using external schedulers (Kubernetes CronJobs, etc.) to call workflows via API.
