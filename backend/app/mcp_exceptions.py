# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Protocol Exception Classes
"""


class MCPInitializationError(Exception):
    """Raised when MCP initialization fails"""
    pass


class MCPSessionExpiredError(Exception):
    """Raised when MCP session has expired (HTTP 404)"""
    pass


class MCPProtocolError(Exception):
    """Raised when MCP protocol violation occurs"""
    pass
