# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Node Types - n8n-style node definitions
Supports: conditionals, loops, error handling, sub-workflows, etc.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """
    Supported workflow node types.

    Core:
        MCP_CALL - Call an MCP server tool (existing)

    Control Flow:
        IF - Conditional branch (true/false)
        SWITCH - Multi-way conditional branch
        FOR_EACH - Loop over array items
        WHILE - Loop with condition

    Composition:
        SUB_WORKFLOW - Call another workflow
        MERGE - Combine multiple inputs
        SPLIT - Split into parallel branches

    Error Handling:
        TRY_CATCH - Try/catch/finally pattern
        RETRY - Retry on failure

    Utilities:
        SET - Set variables
        SLEEP - Wait/delay
        WEBHOOK - Make HTTP request
        TRANSFORM - Transform data (map/filter/reduce)
    """
    # Core
    MCP_CALL = "mcp_call"

    # Control Flow
    IF = "if"
    SWITCH = "switch"
    FOR_EACH = "for_each"
    WHILE = "while"

    # Composition
    SUB_WORKFLOW = "sub_workflow"
    MERGE = "merge"
    SPLIT = "split"

    # Error Handling
    TRY_CATCH = "try_catch"
    RETRY = "retry"

    # Utilities
    SET = "set"
    SLEEP = "sleep"
    WEBHOOK = "webhook"
    TRANSFORM = "transform"


# ============================================================================
# Core Nodes
# ============================================================================

class MCPCallNode(BaseModel):
    """
    Call an MCP server tool (existing functionality).

    Example:
        {
            "id": "scan-network",
            "type": "mcp_call",
            "mcp_server": "nmap_recon",
            "tool": "network_discovery",
            "params": {"network": "${input.target}"}
        }
    """
    id: str
    type: str = NodeType.MCP_CALL
    mcp_server: str = Field(..., description="MCP server name")
    tool: str = Field(..., description="Tool name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


# ============================================================================
# Control Flow Nodes
# ============================================================================

class IfNode(BaseModel):
    """
    Conditional branch - executes true_branch or false_branch based on condition.

    Condition syntax supports:
        - Comparisons: ${value} > 5, ${status} == "success"
        - Boolean: ${enabled}, not ${disabled}
        - Functions: len(${hosts}) > 0, any(${results})

    Example:
        {
            "id": "check-critical",
            "type": "if",
            "condition": "${scan.critical_vulns} > 0",
            "true_branch": "send-alert",
            "false_branch": "write-report"
        }
    """
    id: str
    type: str = NodeType.IF
    condition: str = Field(..., description="Boolean expression to evaluate")
    true_branch: str = Field(..., description="Node ID if condition is true")
    false_branch: Optional[str] = Field(None, description="Node ID if condition is false")


class SwitchNode(BaseModel):
    """
    Multi-way conditional branch - like switch/case statement.

    Example:
        {
            "id": "route-severity",
            "type": "switch",
            "value": "${scan.severity}",
            "cases": {
                "critical": "immediate-response",
                "high": "alert-team",
                "medium": "log-warning",
                "low": "write-report"
            },
            "default": "no-action"
        }
    """
    id: str
    type: str = NodeType.SWITCH
    value: str = Field(..., description="Value to switch on")
    cases: Dict[str, str] = Field(..., description="Map of case value to node ID")
    default: Optional[str] = Field(None, description="Default node ID if no case matches")


class ForEachNode(BaseModel):
    """
    Loop over array items - executes sub_workflow for each item.
    Supports parallel execution with configurable concurrency.

    Example:
        {
            "id": "scan-each-host",
            "type": "for_each",
            "items": "${discover.hosts}",
            "item_var": "host",
            "index_var": "host_index",
            "sub_workflow": "vulnerability_scan",
            "max_parallel": 5,
            "collect_results": true
        }

    Access current item in sub-workflow: ${host}, ${host_index}
    """
    id: str
    type: str = NodeType.FOR_EACH
    items: str = Field(..., description="Array reference to iterate over")
    item_var: str = Field(default="item", description="Variable name for current item")
    index_var: str = Field(default="index", description="Variable name for current index")
    sub_workflow: str = Field(..., description="Workflow name to execute for each item")
    max_parallel: int = Field(default=5, description="Max concurrent executions")
    collect_results: bool = Field(default=True, description="Collect results into array")
    stop_on_error: bool = Field(default=False, description="Stop iteration if any item fails")


class WhileNode(BaseModel):
    """
    Loop while condition is true - executes sub_workflow repeatedly.

    ⚠️ WARNING: Can create infinite loops! Always have a condition that will become false.

    Example:
        {
            "id": "poll-until-ready",
            "type": "while",
            "condition": "${status.state} != 'ready'",
            "sub_workflow": "check_status",
            "max_iterations": 100,
            "sleep_between": 5
        }
    """
    id: str
    type: str = NodeType.WHILE
    condition: str = Field(..., description="Boolean expression - loop while true")
    sub_workflow: str = Field(..., description="Workflow to execute each iteration")
    max_iterations: int = Field(default=100, description="Safety limit for iterations")
    sleep_between: int = Field(default=0, description="Seconds to sleep between iterations")


# ============================================================================
# Composition Nodes
# ============================================================================

class SubWorkflowNode(BaseModel):
    """
    Call another workflow - enables workflow composition and reuse.

    Example:
        {
            "id": "run-security-audit",
            "type": "sub_workflow",
            "workflow": "security_audit",
            "params": {
                "target": "${input.network}",
                "severity_filter": "high"
            },
            "timeout": 300
        }
    """
    id: str
    type: str = NodeType.SUB_WORKFLOW
    workflow: str = Field(..., description="Workflow name to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    category: str = Field(default="templates", description="Workflow category (templates/custom)")


class MergeNode(BaseModel):
    """
    Merge multiple input branches - waits for all inputs before continuing.
    Useful after parallel execution (SPLIT).

    Example:
        {
            "id": "combine-results",
            "type": "merge",
            "inputs": ["scan-1", "scan-2", "scan-3"],
            "merge_mode": "array"
        }

    Merge modes:
        - "array": Combine into single array [result1, result2, result3]
        - "object": Combine into object {"scan-1": result1, ...}
        - "first": Return first result
        - "last": Return last result
    """
    id: str
    type: str = NodeType.MERGE
    inputs: List[str] = Field(..., description="List of node IDs to wait for")
    merge_mode: str = Field(default="array", description="How to combine results")
    timeout: Optional[int] = Field(None, description="Max wait time in seconds")


class SplitNode(BaseModel):
    """
    Split execution into parallel branches - all branches execute concurrently.
    Use MERGE to wait for all branches to complete.

    Example:
        {
            "id": "parallel-scans",
            "type": "split",
            "branches": ["scan-ports", "scan-vulns", "scan-services"]
        }
    """
    id: str
    type: str = NodeType.SPLIT
    branches: List[str] = Field(..., description="List of node IDs to execute in parallel")


# ============================================================================
# Error Handling Nodes
# ============================================================================

class TryCatchNode(BaseModel):
    """
    Try/catch/finally pattern for error handling.

    Example:
        {
            "id": "safe-scan",
            "type": "try_catch",
            "try_node": "scan-network",
            "catch_node": "log-error",
            "finally_node": "cleanup",
            "error_var": "scan_error"
        }

    Error variable contains: {"message": "...", "type": "...", "node_id": "..."}
    """
    id: str
    type: str = NodeType.TRY_CATCH
    try_node: str = Field(..., description="Node to attempt")
    catch_node: Optional[str] = Field(None, description="Node if error occurs")
    finally_node: Optional[str] = Field(None, description="Node always executed")
    error_var: str = Field(default="error", description="Variable name for error details")
    catch_exceptions: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Exception types to catch (* for all)"
    )


class RetryNode(BaseModel):
    """
    Retry a node on failure - exponential backoff supported.

    Example:
        {
            "id": "retry-scan",
            "type": "retry",
            "node": "scan-network",
            "max_attempts": 3,
            "retry_delay": 5,
            "exponential_backoff": true,
            "retry_on": ["timeout", "connection_error"]
        }

    Backoff: 5s, 10s, 20s with exponential_backoff=true
    """
    id: str
    type: str = NodeType.RETRY
    node: str = Field(..., description="Node to retry")
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, description="Seconds between retries")
    exponential_backoff: bool = Field(default=False, description="Double delay each retry")
    retry_on: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Error types to retry on (* for all)"
    )


# ============================================================================
# Utility Nodes
# ============================================================================

class SetNode(BaseModel):
    """
    Set variables in workflow context - useful for intermediate values.

    Example:
        {
            "id": "prepare-vars",
            "type": "set",
            "variables": {
                "scan_time": "${timestamp()}",
                "target_count": "${len(input.targets)}",
                "severity_threshold": 7
            }
        }

    Access later: ${scan_time}, ${target_count}, ${severity_threshold}
    """
    id: str
    type: str = NodeType.SET
    variables: Dict[str, Any] = Field(..., description="Variables to set")


class SleepNode(BaseModel):
    """
    Wait/delay execution - useful for rate limiting or polling.

    Example:
        {
            "id": "wait-for-scan",
            "type": "sleep",
            "duration": 60,
            "reason": "Wait for scan to complete"
        }
    """
    id: str
    type: str = NodeType.SLEEP
    duration: int = Field(..., description="Seconds to sleep", ge=0)
    reason: Optional[str] = Field(None, description="Why we're sleeping (for logs)")


class WebhookNode(BaseModel):
    """
    Make HTTP request - call external APIs or webhooks.

    Example:
        {
            "id": "send-alert",
            "type": "webhook",
            "url": "https://alerts.example.com/api/notify",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer ${env:ALERT_TOKEN}"
            },
            "body": {
                "severity": "critical",
                "message": "${scan.summary}"
            },
            "timeout": 30
        }
    """
    id: str
    type: str = NodeType.WEBHOOK
    url: str = Field(..., description="HTTP endpoint URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    body: Optional[Any] = Field(None, description="Request body (auto-JSON encoded)")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_on_failure: bool = Field(default=False, description="Retry on HTTP errors")


class TransformNode(BaseModel):
    """
    Transform data using expressions - map, filter, reduce operations.

    Example:
        {
            "id": "extract-ips",
            "type": "transform",
            "input": "${discover.hosts}",
            "operation": "map",
            "expression": "item.ip",
            "output_var": "ip_list"
        }

    Operations:
        - "map": Transform each item
        - "filter": Keep items matching condition
        - "reduce": Combine items into single value
        - "sort": Sort items by key
        - "unique": Remove duplicates
    """
    id: str
    type: str = NodeType.TRANSFORM
    input: str = Field(..., description="Data to transform")
    operation: str = Field(..., description="Transform operation")
    expression: Optional[str] = Field(None, description="Transform expression")
    output_var: str = Field(default="result", description="Variable name for output")


# ============================================================================
# Node Type Registry
# ============================================================================

NODE_TYPE_CLASSES = {
    NodeType.MCP_CALL: MCPCallNode,
    NodeType.IF: IfNode,
    NodeType.SWITCH: SwitchNode,
    NodeType.FOR_EACH: ForEachNode,
    NodeType.WHILE: WhileNode,
    NodeType.SUB_WORKFLOW: SubWorkflowNode,
    NodeType.MERGE: MergeNode,
    NodeType.SPLIT: SplitNode,
    NodeType.TRY_CATCH: TryCatchNode,
    NodeType.RETRY: RetryNode,
    NodeType.SET: SetNode,
    NodeType.SLEEP: SleepNode,
    NodeType.WEBHOOK: WebhookNode,
    NodeType.TRANSFORM: TransformNode,
}


def parse_node(node_data: Dict[str, Any]) -> BaseModel:
    """
    Parse node data into appropriate node type class.

    Args:
        node_data: Node definition dict

    Returns:
        Typed node instance

    Raises:
        ValueError: If node type is unknown
    """
    node_type = node_data.get("type")

    if node_type not in NODE_TYPE_CLASSES:
        raise ValueError(f"Unknown node type: {node_type}")

    node_class = NODE_TYPE_CLASSES[node_type]
    return node_class(**node_data)
