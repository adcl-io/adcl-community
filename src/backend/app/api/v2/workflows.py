# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 API Routes

CRUD operations and execution for V2 workflows.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.workflow_v2.models import WorkflowRunRequest, ExecutionV2Result
from app.services.workflow_v2_service import WorkflowV2Service
from app.core.errors import NotFoundError, ValidationError
from app.core.dependencies import get_current_user_context

router = APIRouter(prefix="/v2/workflows", tags=["workflows-v2"])


# Service instance (initialized in main.py startup)
_workflow_v2_service_instance: Optional[WorkflowV2Service] = None


def get_workflow_v2_service() -> WorkflowV2Service:
    """FastAPI dependency for WorkflowV2Service"""
    if _workflow_v2_service_instance is None:
        raise HTTPException(
            status_code=503,
            detail="Workflow V2 service not initialized"
        )
    return _workflow_v2_service_instance


def set_workflow_v2_service(service: WorkflowV2Service):
    """Initialize the workflow V2 service instance (called from main.py)"""
    global _workflow_v2_service_instance
    _workflow_v2_service_instance = service


@router.get("")
async def list_workflows(
    service: WorkflowV2Service = Depends(get_workflow_v2_service)
) -> List[Dict[str, Any]]:
    """List all V2 workflows"""
    return await service.list_workflows()


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    service: WorkflowV2Service = Depends(get_workflow_v2_service)
) -> Dict[str, Any]:
    """Get a specific workflow definition"""
    try:
        return await service.get_workflow(workflow_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_workflow(
    workflow_data: Dict[str, Any],
    service: WorkflowV2Service = Depends(get_workflow_v2_service)
) -> Dict[str, Any]:
    """Create a new workflow definition"""
    try:
        return await service.create_workflow(workflow_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow_data: Dict[str, Any],
    service: WorkflowV2Service = Depends(get_workflow_v2_service)
) -> Dict[str, Any]:
    """Update an existing workflow definition"""
    try:
        return await service.update_workflow(workflow_id, workflow_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    service: WorkflowV2Service = Depends(get_workflow_v2_service)
) -> Dict[str, str]:
    """Delete a workflow definition"""
    try:
        return await service.delete_workflow(workflow_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/run", response_model=ExecutionV2Result)
async def run_workflow(
    request: WorkflowRunRequest,
    service: WorkflowV2Service = Depends(get_workflow_v2_service),
    security_context=Depends(get_current_user_context)
) -> ExecutionV2Result:
    """Execute a workflow by workflow_id"""
    try:
        return await service.run_workflow(
            request.workflow_id,
            initial_message=request.initial_message,
            params=request.params,
            session_id=request.attack_playground_session_id,
            security_context=security_context
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")
