# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Unit tests for BaseMCPServer adapter layer"""

import pytest
from mcp_servers.base_server import BaseMCPServer


@pytest.fixture
def mcp_server():
    """Create a test MCP server"""
    server = BaseMCPServer(name="test-server", port=7999, description="Test server")
    
    # Register a test tool
    def test_tool(message: str) -> str:
        return f"Echo: {message}"
    
    server.register_tool(
        name="test_tool",
        handler=test_tool,
        description="Test tool",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"]
        }
    )
    
    return server


def test_server_initialization(mcp_server):
    """Test server initializes with MCP protocol support"""
    assert mcp_server.protocol_version == "2025-11-25"
    assert mcp_server.server_info["name"] == "test-server"
    assert "tools" in mcp_server.capabilities
    assert mcp_server.sessions == {}


def test_build_error_response(mcp_server):
    """Test JSON-RPC error response builder"""
    error = mcp_server._build_error_response(1, -32600, "Invalid request")
    
    assert error["jsonrpc"] == "2.0"
    assert error["id"] == 1
    assert error["error"]["code"] == -32600
    assert error["error"]["message"] == "Invalid request"


def test_build_error_response_with_data(mcp_server):
    """Test error response with additional data"""
    error = mcp_server._build_error_response(
        2, -32602, "Invalid params", {"expected": "string"}
    )
    
    assert error["error"]["data"] == {"expected": "string"}


def test_is_valid_origin_localhost(mcp_server):
    """Test origin validation for localhost"""
    assert mcp_server._is_valid_origin("http://localhost:3000")
    assert mcp_server._is_valid_origin("http://127.0.0.1:8080")
    assert mcp_server._is_valid_origin("http://[::1]:3000")


def test_is_valid_origin_dns_rebinding_attack(mcp_server):
    """Test origin validation prevents DNS rebinding"""
    assert not mcp_server._is_valid_origin("http://localhost.evil.com")
    assert not mcp_server._is_valid_origin("http://127.0.0.1.evil.com")
    assert not mcp_server._is_valid_origin("http://evil.com")


def test_is_valid_origin_malformed(mcp_server):
    """Test origin validation handles malformed URLs"""
    assert not mcp_server._is_valid_origin("not-a-url")
    assert not mcp_server._is_valid_origin("")


def test_tool_registration(mcp_server):
    """Test tool is registered correctly"""
    assert "test_tool" in mcp_server.tools
    assert len(mcp_server.tool_definitions) == 1
    assert mcp_server.tool_definitions[0].name == "test_tool"
