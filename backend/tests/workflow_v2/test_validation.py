# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for Workflow V2 validation
"""

import pytest
from app.workflow_v2.models import WorkflowV2Definition, WorkflowV2Node, WorkflowV2Edge
from app.workflow_v2.validation import validate_workflow_v2, topological_sort
from app.workflow_v2.exceptions import WorkflowValidationError


def test_empty_workflow():
    """Empty workflow should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[],
        edges=[]
    )
    
    with pytest.raises(WorkflowValidationError, match="at least one node"):
        validate_workflow_v2(workflow, None)


def test_duplicate_node_ids():
    """Duplicate node IDs should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1"),
            WorkflowV2Node(node_id="node1", agent_id="agent2")  # Duplicate
        ],
        edges=[]
    )
    
    with pytest.raises(WorkflowValidationError, match="Duplicate node IDs"):
        validate_workflow_v2(workflow, None)


def test_invalid_edge_from():
    """Edge with invalid 'from' node should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "nonexistent", "to": "node1"})
        ]
    )
    
    with pytest.raises(WorkflowValidationError, match="non-existent node"):
        validate_workflow_v2(workflow, None)


def test_invalid_edge_to():
    """Edge with invalid 'to' node should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "node1", "to": "nonexistent"})
        ]
    )
    
    with pytest.raises(WorkflowValidationError, match="non-existent node"):
        validate_workflow_v2(workflow, None)


def test_self_loop():
    """Self-loop should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "node1", "to": "node1"})
        ]
    )
    
    with pytest.raises(WorkflowValidationError, match="Self-loop"):
        validate_workflow_v2(workflow, None)


def test_cycle_detection():
    """Cycle should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1"),
            WorkflowV2Node(node_id="node2", agent_id="agent2"),
            WorkflowV2Node(node_id="node3", agent_id="agent3")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "node1", "to": "node2"}),
            WorkflowV2Edge(**{"from": "node2", "to": "node3"}),
            WorkflowV2Edge(**{"from": "node3", "to": "node1"})  # Cycle
        ]
    )
    
    with pytest.raises(WorkflowValidationError, match="cycle"):
        validate_workflow_v2(workflow, None)


def test_disconnected_graph():
    """Disconnected graph should raise ValidationError"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1"),
            WorkflowV2Node(node_id="node2", agent_id="agent2"),
            WorkflowV2Node(node_id="node3", agent_id="agent3")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "node1", "to": "node2"})
            # node3 is disconnected - no edges to/from it
        ]
    )
    
    with pytest.raises(WorkflowValidationError, match="Disconnected|not connected"):
        validate_workflow_v2(workflow, None)


def test_simple_serial_dag():
    """A → B → C should validate successfully"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="A", agent_id="agent1"),
            WorkflowV2Node(node_id="B", agent_id="agent2"),
            WorkflowV2Node(node_id="C", agent_id="agent3")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "A", "to": "B"}),
            WorkflowV2Edge(**{"from": "B", "to": "C"})
        ]
    )
    
    order = validate_workflow_v2(workflow, None)
    assert order == ["A", "B", "C"]


def test_simple_parallel_dag():
    """A → [B, C] → D should validate successfully"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="A", agent_id="agent1"),
            WorkflowV2Node(node_id="B", agent_id="agent2"),
            WorkflowV2Node(node_id="C", agent_id="agent3"),
            WorkflowV2Node(node_id="D", agent_id="agent4")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "A", "to": "B"}),
            WorkflowV2Edge(**{"from": "A", "to": "C"}),
            WorkflowV2Edge(**{"from": "B", "to": "D"}),
            WorkflowV2Edge(**{"from": "C", "to": "D"})
        ]
    )
    
    order = validate_workflow_v2(workflow, None)
    assert order[0] == "A"  # A must be first
    assert order[-1] == "D"  # D must be last
    assert set(order[1:3]) == {"B", "C"}  # B and C in middle (any order)


def test_single_node():
    """Single node workflow should validate"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[]
    )
    
    order = validate_workflow_v2(workflow, None)
    assert order == ["node1"]
