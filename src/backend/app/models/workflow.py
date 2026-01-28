# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Workflow execution data models."""

from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class WorkflowNode(BaseModel):
    id: str
    type: str  # "mcp_call"
    mcp_server: str
    tool: str
    params: Dict[str, Any]


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowDefinition(BaseModel):
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class ExecutionRequest(BaseModel):
    workflow: WorkflowDefinition


class ExecutionLog(BaseModel):
    timestamp: str
    node_id: Optional[str] = None
    level: str  # "info", "success", "error"
    message: str


class NodeState(BaseModel):
    node_id: str
    status: str  # "pending", "running", "completed", "error"
    result: Optional[Any] = None
    error: Optional[str] = None


class ExecutionResult(BaseModel):
    status: str
    results: Dict[str, Any]
    errors: List[str] = []
    logs: List[ExecutionLog] = []
    node_states: Dict[str, str] = {}  # node_id -> status
