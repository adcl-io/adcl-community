# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Agent API Routes

Handles autonomous agent management:
- CRUD operations for agent definitions
- Agent execution
- Agent export
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.services.agent_service import AgentService
from app.core.dependencies import get_agent_service
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response Models
class AgentRunRequest(BaseModel):
    """Request to run an autonomous agent"""
    agent_id: str
    task: str
    context: Optional[Dict[str, Any]] = None


# CRUD Routes
@router.get("")
async def list_agents(
    service: AgentService = Depends(get_agent_service)
) -> List[Dict[str, Any]]:
    """List all autonomous agents from disk"""
    return await service.list_agents()


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """Get a specific agent definition"""
    try:
        return await service.get_agent(agent_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_agent(
    agent_data: Dict[str, Any],
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """Create a new autonomous agent on disk"""
    try:
        return await service.create_agent(agent_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    agent_data: Dict[str, Any],
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """Update an autonomous agent on disk"""
    try:
        return await service.update_agent(agent_id, agent_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, str]:
    """Delete an autonomous agent from disk"""
    try:
        return await service.delete_agent(agent_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{agent_id}/export")
async def export_agent(
    agent_id: str,
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """Export an agent definition as JSON for sharing"""
    try:
        return await service.export_agent(agent_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Agent Execution Routes
# Note: Execution logic still needs agent_runtime which is initialized in main.py
# This will be wired up during dependency injection phase

@router.post("/run")
async def run_autonomous_agent(
    request_data: AgentRunRequest,
    request: Request,
    service: AgentService = Depends(get_agent_service),
):
    """
    Run an autonomous agent on a task.
    The agent will autonomously use MCPs to complete the task.
    """
    from app.core.dependencies import get_agent_runtime
    import traceback
    import sys

    # Load agent definition via service
    try:
        agent_definition = await service.get_agent(request_data.agent_id)
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{request_data.agent_id}' not found"
        )

    # Validate agent has available MCPs
    if not agent_definition.get("available_mcps"):
        raise HTTPException(
            status_code=400,
            detail="Agent has no MCPs configured. Add 'available_mcps' to agent definition.",
        )

    # Get agent_runtime from dependency injection
    agent_runtime = get_agent_runtime(request)

    sys.stderr.write(
        f"\n🎯 /agents/run endpoint called for agent: {request_data.agent_id}\n"
    )
    sys.stderr.flush()

    # Run agent autonomously
    try:
        result = await agent_runtime.run_agent(
            agent_definition=agent_definition,
            task=request_data.task,
            context=request_data.context,
        )
        return result
    except Exception as e:
        # Log full traceback for debugging
        error_detail = traceback.format_exc()
        print(f"Agent execution error: {error_detail}")

        # Send sanitized error to user
        from app.core.errors import sanitize_error_for_user
        raise HTTPException(status_code=500, detail=sanitize_error_for_user(e))
