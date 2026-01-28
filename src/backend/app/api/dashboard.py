# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Dashboard API Routes
Endpoints for Red Team Dashboard KPIs and activity feed
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models.red_team import KPIData, ActivityEvent, TopHost
from app.services.dashboard_service import DashboardService
from app.core.config import get_config
from app.core.decorators import requires_feature
from pathlib import Path

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Initialize service
config = get_config()
_dashboard_service = None


def get_dashboard_service() -> DashboardService:
    """Dependency injection for dashboard service."""
    global _dashboard_service
    if _dashboard_service is None:
        base_dir = str(Path(config.volumes_path) / "recon")
        _dashboard_service = DashboardService(base_dir=base_dir)
    return _dashboard_service


@router.get("/kpis", response_model=KPIData)
@requires_feature("red_team", component="red_team_dashboard")
async def get_dashboard_kpis(
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get dashboard KPI metrics.

    Returns:
        KPIData: Dashboard KPIs including hosts discovered, vulnerabilities, active attacks, success rate
    """
    try:
        kpis = await service.get_kpis()
        return kpis
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate KPIs: {str(e)}"
        )


@router.get("/activity", response_model=List[ActivityEvent])
@requires_feature("red_team", component="red_team_dashboard")
async def get_dashboard_activity(
    limit: int = 50,
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get recent activity events.

    Args:
        limit: Maximum number of events to return (default: 50)

    Returns:
        List[ActivityEvent]: Recent activity events
    """
    try:
        events = await service.get_activity(limit=limit)
        return events
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch activity: {str(e)}"
        )


@router.get("/top-hosts", response_model=List[TopHost])
@requires_feature("red_team", component="red_team_dashboard")
async def get_dashboard_top_hosts(
    limit: int = 10,
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get top hosts by risk score.

    Args:
        limit: Maximum number of hosts to return (default: 10)

    Returns:
        List[TopHost]: Top hosts sorted by risk score
    """
    try:
        hosts = await service.get_top_hosts(limit=limit)
        return hosts
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch top hosts: {str(e)}"
        )
