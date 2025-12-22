# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Unit tests for MCPSession dataclass"""

import pytest
from datetime import datetime
from backend.app.mcp_session import MCPSession


def test_mcp_session_creation():
    """Test MCPSession creation"""
    now = datetime.now()
    session = MCPSession(
        endpoint="http://localhost:7000",
        protocol_version="2025-11-25",
        session_id="test-session-123",
        server_capabilities={"tools": {}},
        client_capabilities={"roots": {}},
        initialized_at=now
    )
    
    assert session.endpoint == "http://localhost:7000"
    assert session.protocol_version == "2025-11-25"
    assert session.session_id == "test-session-123"
    assert session.initialized_at == now


def test_mcp_session_optional_session_id():
    """Test MCPSession with optional session_id"""
    session = MCPSession(
        endpoint="http://localhost:7000",
        protocol_version="2025-11-25",
        session_id=None,
        server_capabilities={},
        client_capabilities={},
        initialized_at=datetime.now()
    )
    
    assert session.session_id is None
