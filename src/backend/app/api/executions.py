# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Execution API Routes

Handles execution tracking and history:
- Retrieve execution status
- List execution history
- Execution persistence management
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.services.execution_service import ExecutionService
from app.core.dependencies import get_execution_service
from app.core.errors import NotFoundError

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    service: ExecutionService = Depends(get_execution_service)
) -> Dict[str, Any]:
    """
    Retrieve past execution state - because history matters (ADCL principle).
    Returns metadata, all events, and final result from disk.
    """
    try:
        return await service.get_execution(execution_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("")
async def list_executions(
    limit: Optional[int] = 100,
    offset: int = 0,
    service: ExecutionService = Depends(get_execution_service)
) -> List[Dict[str, Any]]:
    """
    List all executions from disk (newest first).

    Args:
        limit: Maximum number of executions to return (default: 100)
        offset: Number of executions to skip (default: 0)
    """
    return await service.list_executions(limit=limit, offset=offset)


@router.delete("/{execution_id}")
async def delete_execution(
    execution_id: str,
    service: ExecutionService = Depends(get_execution_service)
) -> Dict[str, str]:
    """Delete an execution from disk"""
    try:
        return await service.delete_execution(execution_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
