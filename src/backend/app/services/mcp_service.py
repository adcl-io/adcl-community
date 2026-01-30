# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Service - Manages MCP server registry and lifecycle.

Single responsibility: MCP server registration, discovery, and lifecycle management.
Follows ADCL principle: Simple registry + Docker-based execution.
"""

import httpx
from typing import List, Dict, Any, Optional

from app.core.errors import NotFoundError
from app.core.logging import get_service_logger

logger = get_service_logger("mcp")


class MCPServerInfo:
    """Information about a registered MCP server."""

    def __init__(self, name: str, endpoint: str, description: str = "", version: str = "1.0.0"):
        self.name = name
        self.endpoint = endpoint
        self.description = description
        self.version = version

    def dict(self) -> Dict[str, Any]:
        """Convert to dict for API responses."""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "description": self.description,
            "version": self.version,
        }


class MCPService:
    """
    Manages MCP server registry and lifecycle.

    Responsibilities:
    - Register MCP servers
    - Discover available MCP servers
    - List tools from MCP servers
    - Query server status
    - Coordinate with MCP Manager for Docker lifecycle (start/stop/restart)

    Note: This is a registry service. Actual MCP execution happens
    in Docker containers managed by MCPManager.
    """

    def __init__(self, mcp_manager=None, global_registry=None, base_dir: str = None):
        """
        Initialize MCPService.

        Args:
            mcp_manager: Optional MCPManager instance for lifecycle operations
            global_registry: Optional global MCP registry from main.py with pre-registered servers
            base_dir: Base directory for configuration files (default: /app)
        """
        # Use global registry if provided, otherwise start empty
        if global_registry is not None and hasattr(global_registry, 'servers'):
            self.servers = global_registry.servers
            logger.info(f"MCPService initialized with global registry ({len(self.servers)} servers)")
        else:
            self.servers: Dict[str, MCPServerInfo] = {}
            logger.info("MCPService initialized with empty registry")

        self.mcp_manager = mcp_manager

        # Get base_dir from parameter, environment, or fail explicitly
        if base_dir is None:
            import os
            base_dir = os.getenv('APP_BASE_DIR')
            if base_dir is None:
                raise ValueError("base_dir must be provided or APP_BASE_DIR environment variable must be set")
        self.base_dir = base_dir

        self.http_client = httpx.AsyncClient(timeout=10.0)

    def register_server(self, server: MCPServerInfo) -> None:
        """
        Register an MCP server in the registry.

        Args:
            server: MCP server information

        Example:
            >>> service = MCPService()
            >>> server = MCPServerInfo("nmap", "http://nmap:7001", "Network scanner")
            >>> service.register_server(server)
        """
        self.servers[server.name] = server
        logger.info(f"Registered MCP server: {server.name} at {server.endpoint}")

    def unregister_server(self, server_name: str) -> None:
        """
        Unregister an MCP server from the registry.

        Args:
            server_name: Name of server to unregister

        Raises:
            NotFoundError: If server not found
        """
        if server_name not in self.servers:
            raise NotFoundError("MCP Server", server_name)

        del self.servers[server_name]
        logger.info(f"Unregistered MCP server: {server_name}")

    def get_server(self, server_name: str) -> Optional[MCPServerInfo]:
        """
        Get MCP server info by name.

        Args:
            server_name: Name of the server

        Returns:
            MCPServerInfo if found, None otherwise
        """
        return self.servers.get(server_name)

    def list_servers(self) -> List[Dict[str, Any]]:
        """
        List all registered MCP servers.

        Returns:
            List of server information dicts
        """
        servers = [server.dict() for server in self.servers.values()]
        logger.debug(f"Listed {len(servers)} MCP servers")
        return servers

    async def list_server_tools(self, server_name: str) -> Dict[str, Any]:
        """
        List tools available on an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Dict with available tools

        Raises:
            NotFoundError: If server not found
        """
        server = self.get_server(server_name)
        if not server:
            raise NotFoundError("MCP Server", server_name)

        try:
            response = await self.http_client.post(f"{server.endpoint}/mcp/list_tools")
            response.raise_for_status()
            tools = response.json()
            logger.info(f"Listed tools for MCP server: {server_name}")
            return tools
        except httpx.HTTPError as e:
            logger.error(f"Failed to list tools from {server_name}: {e}")
            raise

    # MCP Lifecycle Operations (delegate to MCP Manager)

    async def install_mcp(self, mcp_package: Dict[str, Any]) -> Dict[str, str]:
        """
        Install an MCP from package definition.

        Args:
            mcp_package: MCP package definition

        Returns:
            Installation result

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        result = self.mcp_manager.install(mcp_package)
        logger.info(f"Installed MCP: {mcp_package.get('name', 'unknown')}")
        return result

    async def uninstall_mcp(self, mcp_name: str) -> Dict[str, str]:
        """
        Uninstall an MCP (stops and removes Docker container).

        Args:
            mcp_name: Name of MCP to uninstall

        Returns:
            Uninstallation result

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        result = self.mcp_manager.uninstall(mcp_name)

        # Unregister from local registry if successful
        if result.get("status") == "uninstalled" and mcp_name in self.servers:
            del self.servers[mcp_name]

        logger.info(f"Uninstalled MCP: {mcp_name}")
        return result

    async def start_mcp(self, mcp_name: str) -> Dict[str, str]:
        """
        Start an installed MCP container.

        Args:
            mcp_name: Name of MCP to start

        Returns:
            Start result

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        result = self.mcp_manager.start(mcp_name)
        logger.info(f"Started MCP: {mcp_name}")
        return result

    async def stop_mcp(self, mcp_name: str) -> Dict[str, str]:
        """
        Stop a running MCP container.

        Args:
            mcp_name: Name of MCP to stop

        Returns:
            Stop result

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        result = self.mcp_manager.stop(mcp_name)
        logger.info(f"Stopped MCP: {mcp_name}")
        return result

    async def restart_mcp(self, mcp_name: str) -> Dict[str, str]:
        """
        Restart an MCP container.

        Args:
            mcp_name: Name of MCP to restart

        Returns:
            Restart result

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        result = self.mcp_manager.restart(mcp_name)
        logger.info(f"Restarted MCP: {mcp_name}")
        return result

    async def list_installed_mcps(self) -> List[Dict[str, Any]]:
        """
        List all installed MCPs with their status.

        Returns installed packages from both:
        - Registry service (installed-packages.json - declarative state)
        - Running containers (runtime state)

        Merges both sources to show complete picture.

        Returns:
            List of installed MCP information

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        # Get running containers
        running_mcps = self.mcp_manager.list_installed()
        running_by_name = {mcp["name"]: mcp for mcp in running_mcps}

        # Also check registry service for installed packages
        try:
            from pathlib import Path
            import json
            installed_packages_file = Path(self.base_dir) / "configs" / "installed-packages.json"
            if installed_packages_file.exists():
                with open(installed_packages_file) as f:
                    data = json.load(f)

                # Merge registry data with running container data
                result = []
                for name, record in data.get("packages", {}).items():
                    if name in running_by_name:
                        # Already running - use container data
                        result.append(running_by_name[name])
                    else:
                        # Installed but not running - create entry
                        result.append({
                            "name": name,
                            "version": record.get("version", "unknown"),
                            "container_name": f"mcp-{name}",
                            "state": "stopped",
                            "running": False,
                            "installed_at": record.get("installed_at")
                        })

                # Add any running containers not in registry
                for name, mcp in running_by_name.items():
                    if name not in data.get("packages", {}):
                        result.append(mcp)

                logger.debug(f"Listed {len(result)} installed MCPs (merged registry + containers)")
                return result
        except Exception as e:
            logger.warning(f"Failed to read registry installed packages: {e}")

        # Fallback to just running containers
        logger.debug(f"Listed {len(running_mcps)} installed MCPs (containers only)")
        return running_mcps

    async def get_mcp_status(self, mcp_name: str) -> Dict[str, Any]:
        """
        Get detailed status of an installed MCP.

        Args:
            mcp_name: Name of MCP

        Returns:
            Detailed status information

        Raises:
            RuntimeError: If MCP manager not available
        """
        if not self.mcp_manager:
            raise RuntimeError("MCP Manager not available")

        status = self.mcp_manager.get_status(mcp_name)
        logger.debug(f"Retrieved status for MCP: {mcp_name}")
        return status

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self.http_client.aclose()
        logger.info("MCPService closed")
