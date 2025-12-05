# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow API Routes

Handles workflow management and execution:
- CRUD operations for workflow definitions
- Workflow execution (streaming and non-streaming)
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.workflow_service import WorkflowService
from app.core.dependencies import get_workflow_service
from app.core.errors import NotFoundError, ValidationError
from app.workflow_models import WorkflowDefinition, ExecutionResult

router = APIRouter(prefix="/workflows", tags=["workflows"])


# Request Models
class ExecutionRequest(BaseModel):
    """Request to execute a workflow"""
    workflow: Optional[WorkflowDefinition] = None
    workflow_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


# Workflow CRUD Routes
@router.get("")
async def list_workflows(
    service: WorkflowService = Depends(get_workflow_service)
) -> List[Dict[str, Any]]:
    """List all saved workflows"""
    return await service.list_workflows()


@router.get("/examples")
async def list_example_workflows(
    service: WorkflowService = Depends(get_workflow_service)
) -> List[Dict[str, str]]:
    """List example workflows"""
    return await service.list_example_workflows()


@router.get("/examples/{filename}")
async def get_example_workflow(
    filename: str,
    service: WorkflowService = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """Get an example workflow"""
    try:
        return await service.get_workflow(filename)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def save_workflow(
    workflow: WorkflowDefinition,
    service: WorkflowService = Depends(get_workflow_service)
) -> Dict[str, str]:
    """Save a workflow to the workflows directory"""
    try:
        return await service.save_workflow(workflow)
    except ValidationError as e:
        raise HTTPException(status_code=413 if "too large" in str(e).lower() else 400, detail=str(e))


@router.delete("/{filename}")
async def delete_workflow(
    filename: str,
    service: WorkflowService = Depends(get_workflow_service)
) -> Dict[str, str]:
    """Delete a saved workflow"""
    try:
        return await service.delete_workflow(filename)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Workflow Execution Routes
# Note: These are placeholders until WorkflowService is fully wired up

@router.post("/execute", response_model=ExecutionResult)
async def execute_workflow(
    request: ExecutionRequest,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Execute a workflow (non-streaming)"""
    # Handle both workflow definition and workflow_id
    if request.workflow:
        workflow = request.workflow
    elif request.workflow_id:
        # Load workflow by ID (add .json if not present)
        filename = request.workflow_id if request.workflow_id.endswith('.json') else f"{request.workflow_id}.json"
        workflow_data = await service.get_workflow(filename)
        workflow = WorkflowDefinition(**workflow_data)
    else:
        raise HTTPException(status_code=400, detail="Either workflow or workflow_id must be provided")
    
    # Execute workflow via the engine
    return await service.execute_workflow(
        workflow=workflow,
        params=request.params or {},
        trigger_type="webhook" if request.workflow_id else "api"
    )


@router.post("/execute/{workflow_id}", response_model=ExecutionResult)
async def execute_workflow_by_id(
    workflow_id: str,
    params: Dict[str, Any] = {},
    service: WorkflowService = Depends(get_workflow_service),
):
    """Execute a workflow by ID with parameters"""
    # Load workflow from file
    filename = workflow_id if workflow_id.endswith('.json') else f"{workflow_id}.json"
    workflow_data = await service.get_workflow(filename)
    workflow = WorkflowDefinition(**workflow_data)
    
    # Execute with params
    return await service.execute_workflow(
        workflow=workflow,
        params=params,
        trigger_type="webhook"
    )
