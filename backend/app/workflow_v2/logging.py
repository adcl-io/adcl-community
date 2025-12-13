# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 History MCP Logging

Logs workflow execution events to History MCP for audit trail.
Fails gracefully if History MCP is not available.
"""

import json
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class WorkflowLogger:
    """
    Logs workflow execution to History MCP.
    
    Fails gracefully if History MCP is unavailable.
    """
    
    def __init__(self, history_mcp_url: str):
        self.history_mcp_url = history_mcp_url
        self.client = httpx.AsyncClient(timeout=10.0)
        self.enabled = True  # Will be set to False if History MCP unavailable
    
    async def create_session(self, workflow_id: str, workflow_name: str) -> Optional[str]:
        """
        Create History MCP session for workflow execution.
        
        Returns session_id or None if History MCP unavailable.
        """
        if not self.enabled:
            return None
        
        try:
            response = await self.client.post(
                f"{self.history_mcp_url}/mcp/call_tool",
                json={
                    "tool": "create_session",
                    "arguments": {
                        "title": f"Workflow: {workflow_name}",
                        "metadata": {
                            "type": "workflow_v2",
                            "workflow_id": workflow_id
                        }
                    }
                }
            )
            
            result = response.json()
            content = result.get("content", [{}])[0]
            data = json.loads(content.get("text", "{}"))  # Parse response
            
            if data.get("success"):
                return data.get("session_id")
            
            return None
            
        except Exception as e:
            print(f"[WorkflowLogger] History MCP unavailable: {e}")
            self.enabled = False  # Disable for this execution
            return None
    
    async def log_node_start(
        self,
        session_id: Optional[str],
        node_id: str,
        agent_id: str
    ) -> None:
        """Log node execution start"""
        if not session_id or not self.enabled:
            return
        
        try:
            await self.client.post(
                f"{self.history_mcp_url}/mcp/call_tool",
                json={
                    "tool": "append_message",
                    "arguments": {
                        "session_id": session_id,
                        "type": "system",
                        "content": f"Node '{node_id}' started",
                        "metadata": {
                            "event": "node_start",
                            "node_id": node_id,
                            "agent_id": agent_id,
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                        }
                    }
                }
            )
        except Exception as e:
            print(f"[WorkflowLogger] Failed to log node start: {e}")
            # Continue execution even if logging fails
    
    async def log_node_complete(
        self,
        session_id: Optional[str],
        node_id: str,
        agent_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Log node execution completion"""
        if not session_id or not self.enabled:
            return
        
        try:
            await self.client.post(
                f"{self.history_mcp_url}/mcp/call_tool",
                json={
                    "tool": "append_message",
                    "arguments": {
                        "session_id": session_id,
                        "type": "agent",
                        "content": result.get("answer", ""),
                        "metadata": {
                            "event": "node_complete",
                            "node_id": node_id,
                            "agent_id": agent_id,
                            "status": result.get("status"),
                            "iterations": result.get("iterations"),
                            "tools_used": result.get("tools_used", []),
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                        }
                    }
                }
            )
        except Exception as e:
            print(f"[WorkflowLogger] Failed to log node complete: {e}")
    
    async def log_workflow_complete(
        self,
        session_id: Optional[str],
        workflow_id: str,
        status: str,
        final_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log workflow execution completion"""
        if not session_id or not self.enabled:
            return
        
        try:
            await self.client.post(
                f"{self.history_mcp_url}/mcp/call_tool",
                json={
                    "tool": "append_message",
                    "arguments": {
                        "session_id": session_id,
                        "type": "system",
                        "content": f"Workflow completed with status: {status}",
                        "metadata": {
                            "event": "workflow_complete",
                            "workflow_id": workflow_id,
                            "status": status,
                            "final_result": final_result,
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                        }
                    }
                }
            )
        except Exception as e:
            print(f"[WorkflowLogger] Failed to log workflow complete: {e}")
    
    async def log_error(
        self,
        session_id: Optional[str],
        node_id: str,
        agent_id: str,
        error: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log node execution error"""
        if not session_id or not self.enabled:
            return
        
        try:
            await self.client.post(
                f"{self.history_mcp_url}/mcp/call_tool",
                json={
                    "tool": "append_message",
                    "arguments": {
                        "session_id": session_id,
                        "type": "system",
                        "content": f"Node '{node_id}' failed: {error}",
                        "metadata": {
                            "event": "node_error",
                            "node_id": node_id,
                            "agent_id": agent_id,
                            "error": error,
                            "error_context": error_context,
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
                        }
                    }
                }
            )
        except Exception as e:
            print(f"[WorkflowLogger] Failed to log error: {e}")
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
