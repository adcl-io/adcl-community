# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""MCP Server Registry Service."""

from typing import Dict, List, Optional
from app.models.mcp import MCPServerInfo


class MCPRegistry:
    """Registry of available MCP servers"""

    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}

    def register(self, server: MCPServerInfo):
        """Register an MCP server"""
        self.servers[server.name] = server
        print(f"Registered MCP server: {server.name} at {server.endpoint}")

    def get(self, name: str) -> Optional[MCPServerInfo]:
        """Get MCP server info"""
        return self.servers.get(name)

    def list_all(self) -> List[MCPServerInfo]:
        """List all registered servers"""
        return list(self.servers.values())
