# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Validation

DAG validation using topological sort (Kahn's algorithm).
"""

from typing import List, Set, Dict
from collections import deque

from .models import WorkflowV2Definition
from .exceptions import WorkflowValidationError


def validate_workflow_v2(workflow_def: WorkflowV2Definition, agent_service) -> List[str]:
    """
    Validate workflow structure and agent availability.
    
    Returns topological order of nodes for execution.
    
    Raises WorkflowValidationError if validation fails.
    """
    # 1. Empty workflow check
    if len(workflow_def.nodes) == 0:
        raise WorkflowValidationError("Workflow must have at least one node")
    
    # 2. Duplicate node IDs
    node_ids = [node.node_id for node in workflow_def.nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        raise WorkflowValidationError(f"Duplicate node IDs found: {set(duplicates)}")
    
    # 3. Invalid edge references
    node_id_set = set(node_ids)
    for edge in workflow_def.edges:
        if edge.from_ not in node_id_set:
            raise WorkflowValidationError(
                f"Edge references non-existent node: {edge.from_}",
                field="edges"
            )
        if edge.to not in node_id_set:
            raise WorkflowValidationError(
                f"Edge references non-existent node: {edge.to}",
                field="edges"
            )
    
    # 4. DAG validation (topological sort)
    topological_order = topological_sort(workflow_def)
    
    # 5. Agent existence validation (async, done by caller)
    # This is handled by the service layer
    
    return topological_order


def topological_sort(workflow_def: WorkflowV2Definition) -> List[str]:
    """
    Perform topological sort using Kahn's algorithm.
    
    Detects:
    - Cycles
    - Self-loops
    - Disconnected graphs
    
    Returns list of node IDs in topological order.
    
    Raises WorkflowValidationError if DAG is invalid.
    """
    # Build adjacency list and in-degree count
    graph: Dict[str, List[str]] = {node.node_id: [] for node in workflow_def.nodes}
    in_degree: Dict[str, int] = {node.node_id: 0 for node in workflow_def.nodes}
    
    for edge in workflow_def.edges:
        # Check for self-loops
        if edge.from_ == edge.to:
            raise WorkflowValidationError(
                f"Self-loop not allowed: {edge.from_} -> {edge.to}",
                field="edges"
            )
        
        graph[edge.from_].append(edge.to)
        in_degree[edge.to] += 1
    
    # Find start nodes (no incoming edges)
    queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
    
    if not queue:
        raise WorkflowValidationError(
            "No start nodes found (all nodes have incoming edges - cycle detected)",
            field="edges"
        )
    
    # Check for multiple disconnected start nodes
    if len(queue) > 1:
        # Multiple start nodes could indicate disconnected subgraphs
        # We'll validate connectivity after topological sort
        pass
    
    # Kahn's algorithm
    topological_order = []
    
    while queue:
        node_id = queue.popleft()
        topological_order.append(node_id)
        
        # Reduce in-degree for neighbors
        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Check if all nodes were processed
    if len(topological_order) != len(workflow_def.nodes):
        # Either cycle or disconnected graph
        unprocessed = set(node.node_id for node in workflow_def.nodes) - set(topological_order)
        
        # Check if it's a cycle or disconnected graph
        if any(in_degree[node_id] > 0 for node_id in unprocessed):
            raise WorkflowValidationError(
                f"Cycle detected in workflow graph involving nodes: {unprocessed}",
                field="edges"
            )
        else:
            raise WorkflowValidationError(
                f"Disconnected graph detected - unreachable nodes: {unprocessed}",
                field="edges"
            )
    
    # Additional check: Verify graph connectivity
    # A valid workflow should have a single connected component
    if len(workflow_def.edges) > 0:  # Only check if there are edges
        _verify_connectivity(workflow_def, graph)
    
    return topological_order


def _verify_connectivity(workflow_def: WorkflowV2Definition, graph: Dict[str, List[str]]) -> None:
    """
    Verify that the workflow graph is fully connected.
    
    Uses BFS to check if all nodes are reachable from any start node.
    """
    if len(workflow_def.nodes) <= 1:
        return  # Single node is always connected
    
    # Build undirected graph for connectivity check
    undirected_graph: Dict[str, Set[str]] = {node.node_id: set() for node in workflow_def.nodes}
    for edge in workflow_def.edges:
        undirected_graph[edge.from_].add(edge.to)
        undirected_graph[edge.to].add(edge.from_)
    
    # BFS from first node
    start_node = workflow_def.nodes[0].node_id
    visited = set()
    queue = deque([start_node])
    
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(undirected_graph[node])
    
    # Check if all nodes were visited
    if len(visited) != len(workflow_def.nodes):
        unreachable = set(node.node_id for node in workflow_def.nodes) - visited
        raise WorkflowValidationError(
            f"Disconnected graph detected - nodes not connected: {unreachable}",
            field="edges"
        )


async def validate_agents_exist(workflow_def: WorkflowV2Definition, agent_service) -> None:
    """
    Validate that all referenced agents exist.
    
    Raises WorkflowValidationError if any agent is missing.
    """
    for node in workflow_def.nodes:
        try:
            await agent_service.get_agent(node.agent_id)
        except Exception as e:
            # Catch any NotFoundError (avoid importing from app.core)
            if "not found" in str(e).lower() or "NotFoundError" in type(e).__name__:
                raise WorkflowValidationError(
                    f"Agent '{node.agent_id}' not found",
                    field=f"nodes[{node.node_id}].agent_id"
                )
