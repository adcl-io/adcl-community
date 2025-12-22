# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Session Data Structure
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class MCPSession:
    """Represents an initialized MCP connection"""
    endpoint: str
    protocol_version: str
    session_id: Optional[str]
    server_capabilities: Dict[str, Any]
    client_capabilities: Dict[str, Any]
    initialized_at: datetime
