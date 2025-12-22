# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
JSON-RPC 2.0 Message Builders for MCP Protocol
"""

from typing import Dict, Any


def build_initialize_request(request_id: int, protocol_version: str, client_info: Dict[str, Any]) -> Dict:
    """Build JSON-RPC initialize request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
                "elicitation": {"form": {}, "url": {}}
            },
            "clientInfo": client_info
        }
    }


def build_initialized_notification() -> Dict:
    """Build JSON-RPC initialized notification"""
    return {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }


def build_list_tools_request(request_id: int) -> Dict:
    """Build JSON-RPC tools/list request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/list"
    }


def build_call_tool_request(request_id: int, tool_name: str, arguments: Dict) -> Dict:
    """Build JSON-RPC tools/call request"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }


def build_cancel_notification(request_id: int, reason: str = "Request timed out") -> Dict:
    """Build JSON-RPC cancellation notification"""
    return {
        "jsonrpc": "2.0",
        "method": "notifications/cancelled",
        "params": {
            "requestId": request_id,
            "reason": reason
        }
    }
