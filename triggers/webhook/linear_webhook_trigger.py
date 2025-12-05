# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Linear Webhook Trigger
Receives Linear webhooks with signature verification and deduplication
Triggers workflows on agentSession events
"""
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
import httpx
import os
import logging
import hmac
import hashlib
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Linear Webhook Trigger")

# Platform auto-injected environment variables
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
WORKFLOW_ID = os.getenv("WORKFLOW_ID")
TEAM_ID = os.getenv("TEAM_ID")

# User-defined environment variables
LINEAR_WEBHOOK_SECRET = os.getenv("LINEAR_WEBHOOK_SECRET", "")
FILTER_EVENT_TYPES = os.getenv("FILTER_EVENT_TYPES", "AgentSessionEvent,agentSession").split(",")

# Linear OAuth configuration for agent workflow
LINEAR_CLIENT_ID = os.getenv("LINEAR_CLIENT_ID", "")
LINEAR_CLIENT_SECRET = os.getenv("LINEAR_CLIENT_SECRET", "")
LINEAR_REDIRECT_URI = os.getenv("LINEAR_REDIRECT_URI", "")

# TTL-based deduplication cache
# Tracks delivery IDs with timestamps for cleanup
processed_deliveries: Dict[str, datetime] = {}
DELIVERY_TTL_HOURS = 24
TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


def verify_linear_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify Linear webhook signature using HMAC SHA-256

    Args:
        payload_body: Raw request body bytes
        signature_header: Linear-Signature header value

    Returns:
        True if signature is valid
    """
    if not LINEAR_WEBHOOK_SECRET:
        logger.error("LINEAR_WEBHOOK_SECRET not configured - webhook rejected")
        return False

    if not signature_header:
        return False

    # Remove whitespace and ensure hex format
    signature_header = signature_header.strip()

    # Calculate HMAC
    mac = hmac.new(
        LINEAR_WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, signature_header)


def verify_timestamp(timestamp_header: Optional[str]) -> bool:
    """
    Verify webhook timestamp to prevent replay attacks

    Args:
        timestamp_header: Linear-Timestamp header value

    Returns:
        True if timestamp is valid or not provided
    """
    if not timestamp_header:
        # Gracefully handle missing timestamp
        return True

    try:
        webhook_timestamp = int(timestamp_header)
        current_timestamp = int(time.time())
        
        # Check if webhook is within tolerance window
        age = abs(current_timestamp - webhook_timestamp)
        if age > TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning(
                f"Webhook timestamp too old: {age}s (max {TIMESTAMP_TOLERANCE_SECONDS}s)",
                extra={"age_seconds": age, "tolerance": TIMESTAMP_TOLERANCE_SECONDS}
            )
            return False
        
        return True
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid timestamp format: {timestamp_header}", extra={"error": str(e)})
        return False


def cleanup_old_deliveries() -> None:
    """Remove delivery IDs older than TTL to prevent memory growth"""
    cutoff = datetime.now() - timedelta(hours=DELIVERY_TTL_HOURS)
    expired = [
        delivery_id 
        for delivery_id, timestamp in processed_deliveries.items() 
        if timestamp < cutoff
    ]
    for delivery_id in expired:
        del processed_deliveries[delivery_id]
    
    if expired:
        logger.debug(
            f"Cleaned up {len(expired)} expired delivery IDs",
            extra={"expired_count": len(expired), "cache_size": len(processed_deliveries)}
        )


def is_duplicate_delivery(delivery_id: Optional[str]) -> bool:
    """
    Check if webhook delivery is a duplicate

    Args:
        delivery_id: Linear-Delivery header value

    Returns:
        True if delivery has been processed before
    """
    if not delivery_id:
        return False  # No delivery ID, can't deduplicate

    if delivery_id in processed_deliveries:
        return True

    # Add to cache with current timestamp
    processed_deliveries[delivery_id] = datetime.now()

    # Cleanup old entries periodically
    cleanup_old_deliveries()

    return False


@app.post("/webhook")
async def handle_linear_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    linear_signature: str = Header(None),
    linear_delivery: str = Header(None),
    linear_timestamp: str = Header(None)
):
    """
    Receive Linear webhook and trigger workflow/team

    Verifies signature, timestamp, deduplicates, and filters by event type
    Returns immediately to Linear, executes workflow in background
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_linear_signature(body, linear_signature):
        logger.error("Invalid Linear webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Verify timestamp to prevent replay attacks
    if not verify_timestamp(linear_timestamp):
        logger.error("Webhook timestamp verification failed")
        raise HTTPException(status_code=401, detail="Webhook timestamp too old or invalid")

    # Check for duplicate delivery
    if is_duplicate_delivery(linear_delivery):
        logger.info(
            f"Duplicate delivery ignored: {linear_delivery}",
            extra={"delivery_id": linear_delivery}
        )
        return {
            "status": "duplicate",
            "delivery_id": linear_delivery,
            "message": "Delivery already processed"
        }

    # Parse payload
    payload = await request.json()

    # Extract event info
    event_type = payload.get("type")
    action = payload.get("action")

    logger.info(
        f"Linear webhook received: {event_type}/{action}",
        extra={
            "event_type": event_type,
            "action": action,
            "delivery_id": linear_delivery,
            "workflow_id": WORKFLOW_ID,
            "team_id": TEAM_ID
        }
    )

    # Filter by event type
    if event_type not in FILTER_EVENT_TYPES:
        logger.info(
            f"Ignoring event type '{event_type}' (not in {FILTER_EVENT_TYPES})",
            extra={"event_type": event_type, "allowed_types": FILTER_EVENT_TYPES}
        )
        return {
            "status": "ignored",
            "reason": f"Event type '{event_type}' not in filter list",
            "allowed_types": FILTER_EVENT_TYPES
        }

    # Extract parameters
    params = extract_parameters(payload, event_type)

    # Add OAuth credentials for Linear agent workflow
    if LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET:
        params["linear_oauth"] = {
            "client_id": LINEAR_CLIENT_ID,
            "client_secret": LINEAR_CLIENT_SECRET,
            "redirect_uri": LINEAR_REDIRECT_URI
        }
        logger.info("Added Linear OAuth credentials to workflow params")

    # Validate that we have a target
    if not WORKFLOW_ID and not TEAM_ID:
        raise HTTPException(
            status_code=500,
            detail="No target configured. WORKFLOW_ID or TEAM_ID must be set."
        )

    # Execute workflow in background (fire-and-forget)
    background_tasks.add_task(
        execute_workflow_async,
        WORKFLOW_ID,
        TEAM_ID,
        params,
        event_type,
        linear_delivery
    )

    logger.info(
        f"Workflow/team queued for execution",
        extra={
            "workflow_id": WORKFLOW_ID,
            "team_id": TEAM_ID,
            "linear_event": event_type,
            "delivery_id": linear_delivery
        }
    )

    # Return immediately to Linear
    return {
        "status": "accepted",
        "workflow_id": WORKFLOW_ID,
        "team_id": TEAM_ID,
        "linear_event": event_type,
        "linear_action": action,
        "delivery_id": linear_delivery
    }


def extract_parameters(payload: dict, event_type: str) -> dict:
    """
    Extract relevant parameters from Linear webhook payload

    Args:
        payload: Linear webhook payload
        event_type: Linear event type (agentSession, issue, etc.)

    Returns:
        Extracted parameters for workflow
    """
    params = {
        "linear_event": event_type,
        "action": payload.get("action")
    }

    if event_type == "agentSession" or event_type == "AgentSessionEvent":
        # Extract from agentSession field (AgentSessionEventWebhookPayload)
        agent_session = payload.get("agentSession", {})
        params.update({
            "session_id": agent_session.get("id"),
            "issue_id": agent_session.get("issueId"),
            "state": agent_session.get("state"),
            "created_at": agent_session.get("createdAt"),
            "updated_at": agent_session.get("updatedAt")
        })
        
        # Extract prompt from agentActivity for prompted events
        if payload.get("action") == "prompted":
            agent_activity = payload.get("agentActivity", {})
            content = agent_activity.get("content", {})
            if isinstance(content, dict):
                params["prompt"] = content.get("body", "")
            else:
                params["prompt"] = str(content) if content else ""
        
        # Extract optional context fields
        if "guidance" in payload:
            params["guidance"] = payload.get("guidance")
        if "previousComments" in payload:
            params["previousComments"] = payload.get("previousComments")
            
    elif event_type == "issue":
        issue = payload.get("data", {})
        params.update({
            "issue_id": issue.get("id"),
            "issue_title": issue.get("title"),
            "issue_state": issue.get("state", {}).get("name"),
            "assignee": issue.get("assignee", {}).get("name")
        })
    else:
        # Generic extraction for other event types
        params.update({
            "data_id": payload.get("data", {}).get("id")
        })

    return params


async def execute_workflow_async(
    workflow_id: str,
    team_id: str,
    params: dict,
    event_type: str,
    delivery_id: str
):
    """
    Execute workflow asynchronously in background.
    Logs success/failure but doesn't block webhook response.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if workflow_id:
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/workflows/execute",
                    json={"workflow_id": workflow_id, "params": params}
                )
            elif team_id:
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/teams/{team_id}/execute",
                    json={"params": params}
                )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                f"Workflow/team completed successfully",
                extra={
                    "execution_id": result.get("id"),
                    "status": result.get("status"),
                    "workflow_id": workflow_id,
                    "team_id": team_id,
                    "linear_event": event_type,
                    "delivery_id": delivery_id
                }
            )
    except Exception as e:
        logger.error(
            f"Workflow/team execution failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "workflow_id": workflow_id,
                "team_id": team_id,
                "linear_event": event_type,
                "delivery_id": delivery_id
            }
        )


def validate_webhook_config() -> bool:
    """
    Validate webhook configuration on startup

    Returns:
        True if properly configured, False otherwise
    """
    if not LINEAR_WEBHOOK_SECRET:
        logger.error("LINEAR_WEBHOOK_SECRET not configured - webhook authentication will fail")
        return False
    
    if len(LINEAR_WEBHOOK_SECRET) < 32:
        logger.warning("LINEAR_WEBHOOK_SECRET seems short - ensure it's the correct value")
    
    logger.info("Webhook authentication properly configured")
    return True


@app.get("/health")
async def health():
    """Health check endpoint"""
    config_valid = validate_webhook_config()
    
    return {
        "status": "healthy" if config_valid else "degraded",
        "orchestrator_url": ORCHESTRATOR_URL,
        "has_workflow_id": WORKFLOW_ID is not None,
        "has_team_id": TEAM_ID is not None,
        "has_webhook_secret": bool(LINEAR_WEBHOOK_SECRET),
        "webhook_secret_length": len(LINEAR_WEBHOOK_SECRET) if LINEAR_WEBHOOK_SECRET else 0,
        "has_oauth_config": bool(LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET),
        "filter_event_types": FILTER_EVENT_TYPES,
        "cache_size": len(processed_deliveries),
        "timestamp_tolerance_seconds": TIMESTAMP_TOLERANCE_SECONDS,
        "delivery_ttl_hours": DELIVERY_TTL_HOURS
    }


if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration on startup
    if not validate_webhook_config():
        logger.error("Webhook configuration validation failed - starting anyway but webhooks will be rejected")
    
    port = int(os.getenv("TRIGGER_PORT", "8103"))
    uvicorn.run(app, host="0.0.0.0", port=port)
