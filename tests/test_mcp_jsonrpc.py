# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Unit tests for MCP JSON-RPC message builders"""

import pytest
from backend.app.mcp_jsonrpc import (
    build_initialize_request,
    build_initialized_notification,
    build_list_tools_request,
    build_call_tool_request,
    build_cancel_notification
)


def test_build_initialize_request():
    """Test initialize request builder"""
    client_info = {"name": "test-client", "version": "1.0.0"}
    request = build_initialize_request(1, "2025-11-25", client_info)
    
    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 1
    assert request["method"] == "initialize"
    assert request["params"]["protocolVersion"] == "2025-11-25"
    assert request["params"]["clientInfo"] == client_info
    assert "capabilities" in request["params"]


def test_build_initialized_notification():
    """Test initialized notification builder"""
    notification = build_initialized_notification()
    
    assert notification["jsonrpc"] == "2.0"
    assert notification["method"] == "notifications/initialized"
    assert "id" not in notification  # Notifications don't have IDs


def test_build_list_tools_request():
    """Test list tools request builder"""
    request = build_list_tools_request(2)
    
    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 2
    assert request["method"] == "tools/list"


def test_build_call_tool_request():
    """Test call tool request builder"""
    request = build_call_tool_request(3, "read_file", {"path": "/test.txt"})
    
    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 3
    assert request["method"] == "tools/call"
    assert request["params"]["name"] == "read_file"
    assert request["params"]["arguments"] == {"path": "/test.txt"}


def test_build_cancel_notification():
    """Test cancel notification builder"""
    notification = build_cancel_notification(4, "Timeout")
    
    assert notification["jsonrpc"] == "2.0"
    assert notification["method"] == "notifications/cancelled"
    assert notification["params"]["requestId"] == 4
    assert notification["params"]["reason"] == "Timeout"
    assert "id" not in notification


def test_build_cancel_notification_default_reason():
    """Test cancel notification with default reason"""
    notification = build_cancel_notification(5)
    
    assert notification["params"]["reason"] == "Request timed out"
