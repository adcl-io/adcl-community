# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Exceptions

Custom exceptions for Workflow Engine V2.
"""


class WorkflowV2Exception(Exception):
    """Base exception for Workflow V2"""
    pass


class WorkflowValidationError(WorkflowV2Exception):
    """Workflow validation failed"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class WorkflowExecutionError(WorkflowV2Exception):
    """Workflow execution failed"""
    pass


class NodeExecutionException(WorkflowExecutionError):
    """Node execution failed"""
    def __init__(self, node_id: str, agent_id: str, message: str, context: dict = None):
        self.node_id = node_id
        self.agent_id = agent_id
        self.context = context or {}
        super().__init__(f"Node '{node_id}' (agent '{agent_id}') failed: {message}")


class NodeTimeoutException(NodeExecutionException):
    """Node execution exceeded timeout"""
    def __init__(self, node_id: str, agent_id: str, timeout: int):
        super().__init__(
            node_id,
            agent_id,
            f"Execution exceeded timeout ({timeout}s)"
        )
        self.timeout = timeout
