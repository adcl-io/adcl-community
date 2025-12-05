# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP API Routes

Handles MCP server management:
- List registered MCP servers
- List tools from MCP servers
- MCP lifecycle operations (install, start, stop, etc.)
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request

from app.services.mcp_service import MCPService
from app.core.dependencies import get_mcp_service
from app.core.errors import NotFoundError

router = APIRouter(tags=["mcp"])


@router.get("/mcp/servers")
async def list_servers(
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> List[Dict[str, Any]]:
    """List all registered MCP servers"""
    return service.list_servers()


@router.get("/mcp/servers/{server_name}/tools")
async def list_server_tools(
    server_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """List tools available on an MCP server"""
    try:
        return await service.list_server_tools(server_name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# MCP Lifecycle Routes
@router.get("/mcps/installed")
async def list_installed_mcps(
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> List[Dict[str, Any]]:
    """List all installed MCPs with their status"""
    try:
        return await service.list_installed_mcps()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/mcps/{mcp_name}/status")
async def get_mcp_status(
    mcp_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, Any]:
    """Get detailed status of an installed MCP"""
    try:
        return await service.get_mcp_status(mcp_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/mcps/{mcp_name}")
async def uninstall_mcp(
    mcp_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, str]:
    """Uninstall an MCP (stops and removes Docker container)"""
    try:
        return await service.uninstall_mcp(mcp_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/mcps/{mcp_name}/start")
async def start_mcp(
    mcp_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, str]:
    """Start an installed MCP container"""
    try:
        return await service.start_mcp(mcp_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/mcps/{mcp_name}/stop")
async def stop_mcp(
    mcp_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, str]:
    """Stop a running MCP container"""
    try:
        return await service.stop_mcp(mcp_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/mcps/{mcp_name}/restart")
async def restart_mcp(
    mcp_name: str,
    request: Request,
    service: MCPService = Depends(get_mcp_service)
) -> Dict[str, str]:
    """Restart an MCP container"""
    try:
        return await service.restart_mcp(mcp_name)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
