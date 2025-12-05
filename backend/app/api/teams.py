# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Team API Routes

Handles multi-agent team management:
- CRUD operations for team definitions
- Team export
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.services.team_service import TeamService
from app.core.dependencies import get_team_service
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("")
async def list_teams(
    service: TeamService = Depends(get_team_service)
) -> List[Dict[str, Any]]:
    """List all agent teams from disk"""
    return await service.list_teams()


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    service: TeamService = Depends(get_team_service)
) -> Dict[str, Any]:
    """Get a specific team"""
    try:
        return await service.get_team(team_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_team(
    team_data: Dict[str, Any],
    service: TeamService = Depends(get_team_service)
) -> Dict[str, Any]:
    """Create a new agent team on disk"""
    try:
        return await service.create_team(team_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{team_id}")
async def update_team(
    team_id: str,
    team_data: Dict[str, Any],
    service: TeamService = Depends(get_team_service)
) -> Dict[str, Any]:
    """Update an agent team on disk"""
    try:
        return await service.update_team(team_id, team_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    service: TeamService = Depends(get_team_service)
) -> Dict[str, str]:
    """Delete an agent team from disk"""
    try:
        return await service.delete_team(team_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{team_id}/export")
async def export_team(
    team_id: str,
    service: TeamService = Depends(get_team_service)
) -> Dict[str, Any]:
    """Export a team as JSON for sharing"""
    try:
        return await service.export_team(team_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Team Execution Routes

class TeamRunRequest(BaseModel):
    """Request model for team execution"""
    team_id: str
    task: str
    context: Optional[Dict[str, Any]] = None


@router.post("/run")
async def run_multi_agent_team(
    request_data: TeamRunRequest,
    request: Request,
    service: TeamService = Depends(get_team_service),
):
    """Run a multi-agent team on a task"""
    from app.core.dependencies import get_team_runtime

    print(f"\n👥 /teams/run endpoint called for team: {request_data.team_id}")

    # Load team definition via service
    try:
        team_definition = await service.get_team(request_data.team_id)
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{request_data.team_id}' not found"
        )

    # Validate team has agents
    if not team_definition.get("agents"):
        raise HTTPException(
            status_code=400,
            detail="Team has no agents configured.",
        )

    # Get team_runtime from dependency injection
    team_runtime = get_team_runtime(request)

    # Run team
    try:
        result = await team_runtime.run_team(
            team_definition=team_definition,
            task=request_data.task,
            context=request_data.context,
        )
        return result
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Team execution error: {error_detail}")

        from app.core.errors import sanitize_error_for_user
        raise HTTPException(status_code=500, detail=sanitize_error_for_user(e))


@router.post("/run/stream")
async def run_multi_agent_team_stream(
    request_data: TeamRunRequest,
    request: Request,
    service: TeamService = Depends(get_team_service),
):
    """Run a multi-agent team with streaming updates"""
    # TODO: Wire up streaming team execution with WebSocket
    raise HTTPException(
        status_code=501,
        detail="Team streaming execution not yet implemented. Use POST /teams/run instead."
    )
