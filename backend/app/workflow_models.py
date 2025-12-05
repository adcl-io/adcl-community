# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Models - Shared data models to prevent circular imports
Extracted from main.py to break circular dependency between main.py and workflow_engine.py
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional


# ============================================================================
# Workflow Definition Models
# ============================================================================

class WorkflowNode(BaseModel):
    """Single node in a workflow"""
    id: str
    type: str  # "mcp_call", "if", "for_each", etc.
    mcp_server: Optional[str] = None  # For mcp_call nodes
    tool: Optional[str] = None  # For mcp_call nodes
    params: Dict[str, Any] = {}


class WorkflowEdge(BaseModel):
    """Connection between workflow nodes"""
    source: str
    target: str


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


# ============================================================================
# Execution Models
# ============================================================================

class ExecutionLog(BaseModel):
    """Single log entry during workflow execution"""
    timestamp: str
    node_id: Optional[str] = None
    level: str  # "info", "success", "error", "warning"
    message: str


class NodeState(BaseModel):
    """State of a workflow node during execution"""
    node_id: str
    status: str  # "pending", "running", "completed", "error"
    result: Optional[Any] = None
    error: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of workflow execution"""
    id: Optional[str] = None  # Execution ID
    status: str  # "completed", "failed"
    results: Dict[str, Any]  # node_id -> result
    errors: List[str] = []
    logs: List[ExecutionLog] = []
    node_states: Dict[str, str] = {}  # node_id -> status


class ExecutionRequest(BaseModel):
    """Request to execute a workflow"""
    workflow: WorkflowDefinition
