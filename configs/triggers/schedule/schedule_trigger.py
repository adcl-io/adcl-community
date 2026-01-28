# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Schedule Trigger
Executes workflows on a schedule using cron expressions
"""
import asyncio
import httpx
import os
import logging
from datetime import datetime
from croniter import croniter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Platform auto-injected environment variables
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")

# User-defined environment variables
CRON_EXPRESSION = os.getenv("CRON_EXPRESSION", "0 0 * * *")  # Daily at midnight
TIMEZONE = os.getenv("TIMEZONE", "UTC")
TASK_DESCRIPTION = os.getenv("TASK_DESCRIPTION", "Execute scheduled task")


async def execute_workflow():
    """Execute the configured workflow or team"""
    if not WORKFLOW_ID and not TEAM_ID:
        logger.error("No target configured. WORKFLOW_ID or TEAM_ID must be set.")
        return

    params = {
        "triggered_at": datetime.now().isoformat(),
        "trigger_type": "schedule",
        "cron_expression": CRON_EXPRESSION
    }

    try:
        async with httpx.AsyncClient() as client:
            if WORKFLOW_ID:
                logger.info(f"Triggering workflow: {WORKFLOW_ID}")
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/workflows/execute",
                    json={"workflow_id": WORKFLOW_ID, "params": params}
                )
            elif TEAM_ID:
                logger.info(f"Triggering team: {TEAM_ID}")
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/teams/run",
                    json={
                        "team_id": TEAM_ID,
                        "task": TASK_DESCRIPTION,
                        "context": params
                    }
                )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Scheduled workflow/team triggered successfully",
                extra={
                    "execution_id": result.get("id"),
                    "workflow_id": WORKFLOW_ID,
                    "team_id": TEAM_ID,
                    "cron_expression": CRON_EXPRESSION
                }
            )

    except httpx.HTTPError as e:
        logger.error(
            f"Failed to trigger workflow/team",
            extra={
                "error": str(e),
                "workflow_id": WORKFLOW_ID,
                "team_id": TEAM_ID
            }
        )


async def scheduler_loop():
    """Main scheduler loop - checks cron schedule and executes"""
    logger.info(
        f"Schedule trigger started",
        extra={
            "cron_expression": CRON_EXPRESSION,
            "timezone": TIMEZONE,
            "workflow_id": WORKFLOW_ID,
            "team_id": TEAM_ID
        }
    )

    # Validate cron expression
    try:
        cron = croniter(CRON_EXPRESSION, datetime.now())
    except Exception as e:
        logger.error(f"Invalid cron expression: {CRON_EXPRESSION} - {e}")
        return

    while True:
        try:
            # Get current time and next execution time
            now = datetime.now()
            cron = croniter(CRON_EXPRESSION, now)
            next_run = cron.get_next(datetime)
            wait_seconds = (next_run - now).total_seconds()

            logger.info(
                f"Next execution scheduled",
                extra={
                    "next_run": next_run.isoformat(),
                    "wait_seconds": wait_seconds,
                    "cron_expression": CRON_EXPRESSION
                }
            )

            # Wait until next execution time
            await asyncio.sleep(wait_seconds)

            # Execute workflow
            await execute_workflow()

        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            # Wait 60 seconds before retrying on error
            await asyncio.sleep(60)


if __name__ == "__main__":
    # Run scheduler loop
    asyncio.run(scheduler_loop())
