# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Basic Webhook Trigger
Receives HTTP webhooks and triggers workflows or teams
"""
from fastapi import FastAPI, Request, HTTPException
import httpx
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Webhook Trigger")

# Platform auto-injected environment variables
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")
TASK_TEMPLATE = os.getenv("TASK_TEMPLATE", "Process webhook event: {_raw}")


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Receive webhook and trigger workflow/team

    The platform auto-injects:
    - ORCHESTRATOR_URL: URL of orchestrator API
    - WORKFLOW_ID or TEAM_ID: User-configured target
    """
    # Get webhook payload
    payload = await request.json()

    logger.info(
        f"Webhook received",
        extra={
            "workflow_id": WORKFLOW_ID,
            "team_id": TEAM_ID,
            "payload_keys": list(payload.keys())
        }
    )

    # Validate that we have a target
    if not WORKFLOW_ID and not TEAM_ID:
        raise HTTPException(
            status_code=500,
            detail="No target configured. WORKFLOW_ID or TEAM_ID must be set."
        )

    # Execute workflow or team
    try:
        async with httpx.AsyncClient() as client:
            if WORKFLOW_ID:
                logger.info(f"Triggering workflow: {WORKFLOW_ID}")
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/workflows/execute",
                    json={"workflow_id": WORKFLOW_ID, "params": payload}
                )
            elif TEAM_ID:
                logger.info(f"Triggering team: {TEAM_ID}")

                # Generate task string from template
                try:
                    task = TASK_TEMPLATE.format(**payload, _raw=json.dumps(payload))
                except (KeyError, AttributeError) as e:
                    # Fallback if template references missing keys
                    task = f"Process webhook event: {json.dumps(payload)}"
                    logger.warning(f"Task template error: {e}, using fallback")

                response = await client.post(
                    f"{ORCHESTRATOR_URL}/teams/run",
                    json={
                        "team_id": TEAM_ID,
                        "task": task,
                        "context": payload
                    }
                )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Workflow/team triggered successfully",
                extra={
                    "execution_id": result.get("id"),
                    "workflow_id": WORKFLOW_ID,
                    "team_id": TEAM_ID
                }
            )

            return {
                "status": "triggered",
                "execution_id": result.get("id"),
                "workflow_id": WORKFLOW_ID,
                "team_id": TEAM_ID
            }

    except httpx.HTTPError as e:
        logger.error(
            f"Failed to trigger workflow/team",
            extra={
                "error": str(e),
                "workflow_id": WORKFLOW_ID,
                "team_id": TEAM_ID
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger workflow/team: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "orchestrator_url": ORCHESTRATOR_URL,
        "has_workflow_id": WORKFLOW_ID is not None,
        "has_team_id": TEAM_ID is not None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TRIGGER_PORT", "8100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
