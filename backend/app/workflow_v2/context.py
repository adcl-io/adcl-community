# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Execution Context

Tracks execution state for a workflow run.
"""

from typing import Dict, Any, Set
from datetime import datetime, timezone


class ExecutionContext:
    """
    Execution context for a workflow run.
    
    Tracks:
    - Node results
    - Completed nodes
    - Execution metadata
    """
    
    def __init__(self, execution_id: str, workflow_id: str):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.started_at = datetime.now(timezone.utc).isoformat() + "Z"
        self.completed_at = None
        self.history_session_id = None  # Set by executor if History MCP available
        self.initial_message = None  # Initial user message for start nodes
        
        # Node execution tracking
        self.node_results: Dict[str, Any] = {}  # node_id -> agent response
        self.completed_nodes: Set[str] = set()
        
    def mark_completed(self, node_id: str, result: Dict[str, Any]) -> None:
        """Mark a node as completed with its result"""
        self.node_results[node_id] = result
        self.completed_nodes.add(node_id)
    
    def is_completed(self, node_id: str) -> bool:
        """Check if a node has completed"""
        return node_id in self.completed_nodes
    
    def get_result(self, node_id: str) -> Dict[str, Any]:
        """Get result for a completed node"""
        return self.node_results.get(node_id)
    
    def finalize(self) -> None:
        """Mark execution as complete"""
        self.completed_at = datetime.now(timezone.utc).isoformat() + "Z"
