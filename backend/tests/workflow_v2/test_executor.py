# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for Workflow V2 executor
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.workflow_v2.models import WorkflowV2Definition, WorkflowV2Node, WorkflowV2Edge
from app.workflow_v2.executor import WorkflowExecutor
from app.workflow_v2.exceptions import NodeExecutionException, NodeTimeoutException


@pytest.fixture
def mock_agent_service():
    """Mock AgentService"""
    service = AsyncMock()
    service.get_agent = AsyncMock(return_value={"id": "test-agent", "name": "Test Agent"})
    return service


@pytest.fixture
def mock_agent_runtime():
    """Mock AgentRuntime"""
    runtime = AsyncMock()
    runtime.run_agent = AsyncMock(return_value={
        "status": "completed",
        "answer": "Test result",
        "iterations": 1,
        "tools_used": [],
        "reasoning_steps": []
    })
    return runtime


@pytest.fixture
def executor(mock_agent_service, mock_agent_runtime):
    """Create executor with mocks"""
    return WorkflowExecutor(mock_agent_runtime, mock_agent_service, "http://localhost:7004")


@pytest.mark.asyncio
async def test_single_node_execution(executor):
    """Single node workflow should execute"""
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[]
    )
    
    context = await executor.execute(workflow)
    
    assert context.execution_id is not None
    assert len(context.completed_nodes) == 1
    assert "node1" in context.completed_nodes
    assert context.node_results["node1"]["status"] == "completed"


@pytest.mark.asyncio
async def test_serial_execution(executor):
    """A → B → C should execute in order"""
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
    
    context = await executor.execute(workflow)
    
    assert len(context.completed_nodes) == 3
    assert all(node in context.completed_nodes for node in ["A", "B", "C"])


@pytest.mark.asyncio
async def test_parallel_execution(executor):
    """A → [B, C] → D should execute B and C in parallel"""
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
    
    context = await executor.execute(workflow)
    
    assert len(context.completed_nodes) == 4
    assert all(node in context.completed_nodes for node in ["A", "B", "C", "D"])


@pytest.mark.asyncio
async def test_node_failure(executor, mock_agent_runtime):
    """Node failure should stop workflow"""
    # Make agent fail
    mock_agent_runtime.run_agent = AsyncMock(return_value={
        "status": "error",
        "error": "Agent failed",
        "answer": None
    })
    
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="node1", agent_id="agent1")
        ],
        edges=[]
    )
    
    with pytest.raises(NodeExecutionException, match="Agent failed"):
        await executor.execute(workflow)


@pytest.mark.asyncio
async def test_convergence(mock_agent_service):
    """[A, B] → C should pass both outputs to C"""
    # Track calls to verify context
    calls = []
    
    async def mock_run_agent(agent_definition, task, context):
        calls.append({"agent": agent_definition["id"], "task": task, "context": context})
        return {
            "status": "completed",
            "answer": f"Result from {agent_definition['id']}",
            "iterations": 1,
            "tools_used": [],
            "reasoning_steps": []
        }
    
    # Create runtime with tracking
    mock_runtime = AsyncMock()
    mock_runtime.run_agent = mock_run_agent
    
    # Create executor with tracking runtime
    executor = WorkflowExecutor(mock_runtime, mock_agent_service, "http://localhost:7004")
    
    workflow = WorkflowV2Definition(
        workflow_id="test",
        name="Test",
        nodes=[
            WorkflowV2Node(node_id="A", agent_id="agent1", branch_name="branch_a"),
            WorkflowV2Node(node_id="B", agent_id="agent2", branch_name="branch_b"),
            WorkflowV2Node(node_id="C", agent_id="agent3")
        ],
        edges=[
            WorkflowV2Edge(**{"from": "A", "to": "C"}),
            WorkflowV2Edge(**{"from": "B", "to": "C"})
        ]
    )
    
    context = await executor.execute(workflow)
    
    # Check that the convergence node (C) received both branch outputs
    # The third call should be the convergence node with both inputs
    assert len(calls) == 3, f"Expected 3 calls (A, B, C), got {len(calls)}"
    
    # Last call is the convergence node
    c_call = calls[2]
    assert c_call["task"] == "Synthesize the results"
    assert "branch_a" in c_call["context"]
    assert "branch_b" in c_call["context"]
    # Results contain the agent ID from the mock
    assert "test-agent" in c_call["context"]["branch_a"]
    assert "test-agent" in c_call["context"]["branch_b"]
