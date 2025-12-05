# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for MCPService

Tests MCP server registry and lifecycle management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.mcp_service import MCPService, MCPServerInfo
from app.core.errors import NotFoundError


@pytest.fixture
def mcp_service():
    """Create MCPService instance"""
    return MCPService()


@pytest.fixture
def sample_server_info():
    """Sample MCP server info"""
    return MCPServerInfo(
        name="nmap",
        endpoint="http://nmap:7001",
        description="Network scanner",
        version="1.0.0"
    )


class TestRegisterServer:
    """Test register_server method"""

    def test_registers_new_server(self, mcp_service, sample_server_info):
        """Should register new MCP server"""
        mcp_service.register_server(sample_server_info)
        
        assert "nmap" in mcp_service.servers
        assert mcp_service.servers["nmap"].endpoint == "http://nmap:7001"


class TestGetServer:
    """Test get_server method"""

    def test_gets_registered_server(self, mcp_service, sample_server_info):
        """Should retrieve registered server"""
        mcp_service.register_server(sample_server_info)
        
        server = mcp_service.get_server("nmap")
        assert server is not None
        assert server.name == "nmap"

    def test_returns_none_for_nonexistent_server(self, mcp_service):
        """Should return None for non-existent server"""
        server = mcp_service.get_server("nonexistent")
        assert server is None


class TestUnregisterServer:
    """Test unregister_server method"""

    def test_unregisters_existing_server(self, mcp_service, sample_server_info):
        """Should unregister existing server"""
        mcp_service.register_server(sample_server_info)
        mcp_service.unregister_server("nmap")
        
        assert "nmap" not in mcp_service.servers

    def test_raises_error_for_nonexistent_server(self, mcp_service):
        """Should raise NotFoundError for non-existent server"""
        with pytest.raises(NotFoundError):
            mcp_service.unregister_server("nonexistent")


class TestListServers:
    """Test list_servers method"""

    def test_lists_all_servers(self, mcp_service, sample_server_info):
        """Should list all registered servers"""
        mcp_service.register_server(sample_server_info)
        mcp_service.register_server(MCPServerInfo("gobuster", "http://gobuster:7002"))
        
        servers = mcp_service.list_servers()
        assert len(servers) == 2


class TestListServerTools:
    """Test list_server_tools method"""

    @pytest.mark.asyncio
    async def test_lists_tools_from_server(self, mcp_service, sample_server_info):
        """Should list tools from MCP server"""
        mcp_service.register_server(sample_server_info)
        
        # Mock HTTP client
        mcp_service.http_client = AsyncMock()
        mcp_service.http_client.post.return_value.json.return_value = {"tools": ["scan"]}
        
        tools = await mcp_service.list_server_tools("nmap")
        assert "tools" in tools

    @pytest.mark.asyncio
    async def test_raises_error_for_nonexistent_server(self, mcp_service):
        """Should raise NotFoundError for non-existent server"""
        with pytest.raises(NotFoundError):
            await mcp_service.list_server_tools("nonexistent")
