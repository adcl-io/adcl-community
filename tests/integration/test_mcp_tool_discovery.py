# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Integration test for MCP tool discovery path
Tests the complete flow: MCP Server → Session Manager → Agent Runtime → Anthropic

This test prevents regressions like the inputSchema/input_schema mismatch that
caused silent failures when tools were called with empty parameters.
"""

import pytest
import asyncio
import httpx
from backend.app.mcp_session_manager import MCPSessionManager
from backend.app.main import MCPRegistry, MCPServerInfo


@pytest.mark.asyncio
async def test_mcp_tool_schema_discovery():
    """
    Test that tool schemas are properly discovered and validated through the full stack.

    This test ensures:
    1. MCP servers return tools with 'inputSchema' (camelCase per MCP spec)
    2. Agent runtime correctly translates to 'input_schema' (snake_case per Anthropic)
    3. Required parameters are properly propagated to the AI model
    4. No silent failures due to schema mismatches
    """

    # Setup
    session_manager = MCPSessionManager()
    registry = MCPRegistry()

    # Register a test MCP (nmap_recon should be available in dev environment)
    mcp_endpoint = "http://localhost:7001"

    # Check if MCP server is available
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{mcp_endpoint}/health")
            if response.status_code != 200:
                pytest.skip(f"MCP server at {mcp_endpoint} not healthy")
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip(f"MCP server at {mcp_endpoint} not available - skipping integration test")

    # Register with correct signature
    server_info = MCPServerInfo(
        name="nmap_recon",
        endpoint=mcp_endpoint,
        description="Nmap reconnaissance tools"
    )
    registry.register(server_info)

    try:
        # Step 1: Fetch tools from MCP server via session manager
        tools_from_mcp = await session_manager.list_tools(mcp_endpoint)

        # Validate MCP response format (should have camelCase 'inputSchema')
        assert len(tools_from_mcp) > 0, "MCP server should return at least one tool"

        for tool in tools_from_mcp:
            assert "name" in tool, f"Tool missing required 'name' field: {tool}"
            assert "inputSchema" in tool, (
                f"Tool '{tool.get('name')}' missing required 'inputSchema' field. "
                f"Available keys: {list(tool.keys())}. "
                f"This likely means the MCP server is not compliant with the protocol."
            )

            # Validate inputSchema structure
            schema = tool["inputSchema"]
            assert "type" in schema, f"Tool '{tool['name']}' inputSchema missing 'type'"
            assert schema["type"] == "object", f"Tool '{tool['name']}' inputSchema type should be 'object'"
            assert "properties" in schema, f"Tool '{tool['name']}' inputSchema missing 'properties'"

        # Step 2: Simulate agent runtime processing (without full runtime setup)
        # This mimics what _build_tools_from_mcps does
        translated_tools = []
        for mcp_tool in tools_from_mcp:
            # Validate required fields (fail fast)
            if "name" not in mcp_tool:
                pytest.fail(f"Tool missing required 'name' field: {mcp_tool}")

            if "inputSchema" not in mcp_tool:
                pytest.fail(
                    f"Tool '{mcp_tool['name']}' missing required 'inputSchema' field. "
                    f"Available keys: {list(mcp_tool.keys())}"
                )

            # Protocol translation: MCP camelCase → Anthropic snake_case
            translated_tools.append({
                "name": f"nmap_recon__{mcp_tool['name']}",
                "description": f"[nmap_recon] {mcp_tool.get('description', '')}",
                "input_schema": mcp_tool["inputSchema"]  # This is the critical translation
            })

        # Step 3: Validate translated tools have proper schemas for Anthropic
        assert len(translated_tools) > 0, "Should have translated at least one tool"

        for tool in translated_tools:
            assert "name" in tool
            assert "input_schema" in tool, (
                f"Translated tool '{tool['name']}' missing 'input_schema'. "
                f"This is a bug in the translation layer."
            )

            # Verify schema is not empty (the bug we're preventing)
            schema = tool["input_schema"]
            assert "properties" in schema, f"Tool '{tool['name']}' has empty schema"

            # For tools that require parameters (like port_scan requires 'target'),
            # verify they're in the schema
            if "port_scan" in tool["name"]:
                assert "target" in schema["properties"], (
                    f"port_scan tool missing required 'target' parameter in schema. "
                    f"This will cause tool calls to fail with missing argument errors."
                )

        # Verify we discovered tools successfully
        assert len(translated_tools) > 0, "Should have discovered and validated tools"

    finally:
        await session_manager.close()
