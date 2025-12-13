# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Models

Pydantic models for Workflow Engine V2 - agent-only DAG execution.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class WorkflowV2Node(BaseModel):
    """V2 workflow node - agent only"""
    node_id: str
    agent_id: str
    branch_name: Optional[str] = None  # For convergence, defaults to node_id
    timeout: int = 3600  # Default 1 hour


class WorkflowV2Edge(BaseModel):
    """V2 workflow edge"""
    model_config = ConfigDict(populate_by_name=True)  # Allow both 'from' and 'from_'
    
    from_: str = Field(alias="from")
    to: str


class WorkflowV2Definition(BaseModel):
    """V2 workflow definition - agent DAG only"""
    workflow_id: str
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowV2Node]
    edges: List[WorkflowV2Edge]


class NodeExecutionError(BaseModel):
    """Detailed error context when a node fails"""
    node_id: str
    agent_id: str
    error_message: str
    agent_response: Optional[Dict[str, Any]] = None
    reasoning_steps: List[Dict[str, Any]] = []
    tools_used: List[str] = []
    completed_nodes: List[str] = []
    pending_nodes: List[str] = []
    timestamp: str


class ExecutionV2Result(BaseModel):
    """V2 execution result - returned by /v2/workflows/run"""
    execution_id: str
    workflow_id: str
    status: str  # "completed", "failed"
    history_session_id: str  # Query History MCP for execution details
    started_at: str
    completed_at: str
    final_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_context: Optional[NodeExecutionError] = None  # When status="failed"


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow"""
    workflow_id: str
    initial_message: Optional[str] = None  # Initial user message for start nodes
    params: Optional[Dict[str, Any]] = None  # Optional execution parameters
