# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
GitHub Webhook Trigger
Receives GitHub webhooks with HMAC signature verification
Triggers workflows on PR events (opened, synchronize)
"""
from fastapi import FastAPI, Request, HTTPException, Header
import httpx
import os
import logging
import hmac
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Webhook Trigger")

# Platform auto-injected environment variables
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")

# User-defined environment variables
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
FILTER_ACTIONS = os.getenv("FILTER_ACTIONS", "opened,synchronize").split(",")


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC SHA-256

    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid
    """
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured - skipping verification")
        return True  # Allow unsigned webhooks if no secret configured

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    # Extract signature from header
    expected_signature = signature_header.replace("sha256=", "")

    # Calculate HMAC
    mac = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)


@app.post("/webhook")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    """
    Receive GitHub webhook and trigger workflow/team

    Verifies HMAC signature and filters by PR action
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_github_signature(body, x_hub_signature_256):
        logger.error("Invalid GitHub webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    payload = await request.json()

    # Extract event info
    action = payload.get("action")
    event_type = x_github_event or "unknown"

    logger.info(
        f"GitHub webhook received: {event_type}/{action}",
        extra={
            "event_type": event_type,
            "action": action,
            "workflow_id": WORKFLOW_ID,
            "team_id": TEAM_ID
        }
    )

    # Filter by action (only process configured actions)
    if action not in FILTER_ACTIONS:
        logger.info(
            f"Ignoring action '{action}' (not in {FILTER_ACTIONS})",
            extra={"action": action, "allowed_actions": FILTER_ACTIONS}
        )
        return {
            "status": "ignored",
            "reason": f"Action '{action}' not in filter list",
            "allowed_actions": FILTER_ACTIONS
        }

    # Extract parameters based on event type
    params = extract_parameters(payload, event_type)

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
                    json={"workflow_id": WORKFLOW_ID, "params": params}
                )
            elif TEAM_ID:
                logger.info(f"Triggering team: {TEAM_ID}")
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/teams/{TEAM_ID}/execute",
                    json={"params": params}
                )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Workflow/team triggered successfully",
                extra={
                    "execution_id": result.get("id"),
                    "workflow_id": WORKFLOW_ID,
                    "team_id": TEAM_ID,
                    "github_action": action
                }
            )

            return {
                "status": "triggered",
                "execution_id": result.get("id"),
                "workflow_id": WORKFLOW_ID,
                "team_id": TEAM_ID,
                "github_event": event_type,
                "github_action": action
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


def extract_parameters(payload: dict, event_type: str) -> dict:
    """
    Extract relevant parameters from GitHub webhook payload

    Args:
        payload: GitHub webhook payload
        event_type: GitHub event type (pull_request, push, etc.)

    Returns:
        Extracted parameters for workflow
    """
    params = {"github_event": event_type}

    if event_type == "pull_request":
        pr = payload.get("pull_request", {})
        params.update({
            "pr_number": pr.get("number"),
            "pr_title": pr.get("title"),
            "pr_author": pr.get("user", {}).get("login"),
            "pr_head_ref": pr.get("head", {}).get("ref"),
            "pr_base_ref": pr.get("base", {}).get("ref"),
            "pr_url": pr.get("html_url"),
            "repository": payload.get("repository", {}).get("full_name"),
            "action": payload.get("action")
        })
    elif event_type == "push":
        params.update({
            "ref": payload.get("ref"),
            "repository": payload.get("repository", {}).get("full_name"),
            "pusher": payload.get("pusher", {}).get("name"),
            "commits": len(payload.get("commits", []))
        })
    else:
        # Generic extraction for other event types
        params.update({
            "repository": payload.get("repository", {}).get("full_name"),
            "sender": payload.get("sender", {}).get("login")
        })

    return params


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "orchestrator_url": ORCHESTRATOR_URL,
        "has_workflow_id": WORKFLOW_ID is not None,
        "has_team_id": TEAM_ID is not None,
        "has_webhook_secret": bool(GITHUB_WEBHOOK_SECRET),
        "filter_actions": FILTER_ACTIONS
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TRIGGER_PORT", "8101"))
    uvicorn.run(app, host="0.0.0.0", port=port)
