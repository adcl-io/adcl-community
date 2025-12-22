# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Unit tests for MCPSessionManager"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.mcp_session_manager import MCPSessionManager
from backend.app.mcp_exceptions import MCPInitializationError, MCPProtocolError


@pytest.fixture
async def session_manager():
    """Create a session manager instance"""
    manager = MCPSessionManager()
    yield manager
    await manager.close()


async def test_session_manager_initialization(session_manager):
    """Test session manager initializes correctly"""
    assert session_manager.protocol_version == "2025-11-25"
    assert session_manager.sessions == {}
    assert session_manager.request_id_counter == 0
    assert session_manager._http_session is None


async def test_next_request_id(session_manager):
    """Test request ID generation"""
    id1 = session_manager._next_request_id()
    id2 = session_manager._next_request_id()
    id3 = session_manager._next_request_id()
    
    assert id1 == 1
    assert id2 == 2
    assert id3 == 3


async def test_build_headers_without_session(session_manager):
    """Test header building without session"""
    headers = session_manager._build_headers()
    
    assert headers["Accept"] == "application/json, text/event-stream"
    assert headers["Content-Type"] == "application/json"
    assert "MCP-Protocol-Version" not in headers
    assert "MCP-Session-Id" not in headers


async def test_build_headers_with_session(session_manager):
    """Test header building with session"""
    from backend.app.mcp_session import MCPSession
    from datetime import datetime
    
    session = MCPSession(
        endpoint="http://localhost:7000",
        protocol_version="2025-11-25",
        session_id="test-123",
        server_capabilities={},
        client_capabilities={},
        initialized_at=datetime.now()
    )
    
    headers = session_manager._build_headers(session)
    
    assert headers["MCP-Protocol-Version"] == "2025-11-25"
    assert headers["MCP-Session-Id"] == "test-123"


@pytest.mark.asyncio
async def test_get_http_session_creates_session(session_manager):
    """Test HTTP session creation"""
    http_session = await session_manager._get_http_session()
    
    assert http_session is not None
    assert session_manager._http_session is http_session


@pytest.mark.asyncio
async def test_get_http_session_reuses_session(session_manager):
    """Test HTTP session reuse"""
    session1 = await session_manager._get_http_session()
    session2 = await session_manager._get_http_session()
    
    assert session1 is session2


@pytest.mark.asyncio
async def test_close_cleans_up(session_manager):
    """Test close cleans up resources"""
    await session_manager._get_http_session()
    assert session_manager._http_session is not None
    
    await session_manager.close()
    
    assert session_manager.sessions == {}


@pytest.mark.asyncio
async def test_concurrent_initialization_same_endpoint():
    """Test that session manager has locking mechanism for concurrent initialization"""
    manager = MCPSessionManager()
    
    # Verify lock dictionaries exist
    assert hasattr(manager, 'init_locks')
    assert isinstance(manager.init_locks, dict)
    assert hasattr(manager, 'request_locks')
    assert isinstance(manager.request_locks, dict)
    
    await manager.close()
