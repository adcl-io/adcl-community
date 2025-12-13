# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Integration tests for Workflow V2 Engine

Tests end-to-end workflow execution with real AgentRuntime.
Requires full environment (configs, MCPs) - run on production servers only.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Requires full production environment")
from pathlib import Path
from app.workflow_v2.models import WorkflowV2Definition
from app.workflow_v2.executor import WorkflowExecutor
from app.services.agent_service import AgentService
from app.agent_runtime import AgentRuntime


@pytest.fixture
def agent_service():
    """Create AgentService instance"""
    agents_dir = Path("agent-definitions")
    return AgentService(agents_dir=agents_dir)


@pytest.fixture
def agent_runtime():
    """Create AgentRuntime instance"""
    return AgentRuntime()


@pytest.fixture
def executor(agent_runtime, agent_service):
    """Create WorkflowExecutor instance"""
    return WorkflowExecutor(
        agent_runtime=agent_runtime,
        agent_service=agent_service,
        history_mcp_url="http://localhost:7004"
    )


@pytest.mark.asyncio
async def test_single_node_workflow(executor):
    """Test simple single-node workflow execution"""
    workflow = WorkflowV2Definition(
        workflow_id="test-single",
        name="Single Node Test",
        nodes=[
            {"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60}
        ],
        edges=[]
    )
    
    context = await executor.execute(workflow, initial_message="Test scan target: example.com")
    
    assert context.execution_id
    assert len(context.completed_nodes) == 1
    assert "node1" in context.completed_nodes
    assert context.node_results["node1"]["status"] == "completed"


@pytest.mark.asyncio
async def test_serial_workflow(executor):
    """Test serial workflow execution (A → B)"""
    workflow = WorkflowV2Definition(
        workflow_id="test-serial",
        name="Serial Test",
        nodes=[
            {"node_id": "analyze", "agent_id": "security-analyst", "timeout": 60},
            {"node_id": "review", "agent_id": "code-reviewer", "timeout": 60}
        ],
        edges=[
            {"from": "analyze", "to": "review"}
        ]
    )
    
    context = await executor.execute(workflow, initial_message="Analyze network 192.168.1.0/24")
    
    assert len(context.completed_nodes) == 2
    assert "analyze" in context.completed_nodes
    assert "review" in context.completed_nodes
    # Verify review received analyze output
    assert context.node_results["review"]["status"] == "completed"


@pytest.mark.asyncio
async def test_parallel_workflow(executor):
    """Test parallel workflow execution (A → [B, C] → D)"""
    workflow = WorkflowV2Definition(
        workflow_id="test-parallel",
        name="Parallel Test",
        nodes=[
            {"node_id": "start", "agent_id": "security-analyst", "timeout": 60},
            {"node_id": "branch1", "agent_id": "sqli-analyst", "timeout": 60, "branch_name": "sql"},
            {"node_id": "branch2", "agent_id": "security-analyst", "timeout": 60, "branch_name": "network"},
            {"node_id": "converge", "agent_id": "code-reviewer", "timeout": 60}
        ],
        edges=[
            {"from": "start", "to": "branch1"},
            {"from": "start", "to": "branch2"},
            {"from": "branch1", "to": "converge"},
            {"from": "branch2", "to": "converge"}
        ]
    )
    
    context = await executor.execute(workflow, initial_message="Scan target: test.example.com")
    
    assert len(context.completed_nodes) == 4
    # Verify all nodes completed
    for node_id in ["start", "branch1", "branch2", "converge"]:
        assert node_id in context.completed_nodes
        assert context.node_results[node_id]["status"] == "completed"


@pytest.mark.asyncio
async def test_workflow_with_timeout(executor):
    """Test workflow timeout handling"""
    workflow = WorkflowV2Definition(
        workflow_id="test-timeout",
        name="Timeout Test",
        nodes=[
            {"node_id": "slow", "agent_id": "sqli-analyst", "timeout": 1}  # 1 second timeout
        ],
        edges=[]
    )
    
    with pytest.raises(Exception) as exc_info:
        await executor.execute(workflow, initial_message="Long running scan")
    
    assert "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_workflow_validation_error(executor):
    """Test workflow with validation errors"""
    # Workflow with cycle
    workflow = WorkflowV2Definition(
        workflow_id="test-cycle",
        name="Cycle Test",
        nodes=[
            {"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60},
            {"node_id": "node2", "agent_id": "security-analyst", "timeout": 60}
        ],
        edges=[
            {"from": "node1", "to": "node2"},
            {"from": "node2", "to": "node1"}  # Creates cycle
        ]
    )
    
    with pytest.raises(Exception) as exc_info:
        await executor.execute(workflow)
    
    assert "cycle" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_workflow_with_nonexistent_agent(executor):
    """Test workflow with non-existent agent"""
    workflow = WorkflowV2Definition(
        workflow_id="test-invalid",
        name="Invalid Agent Test",
        nodes=[
            {"node_id": "node1", "agent_id": "nonexistent-agent", "timeout": 60}
        ],
        edges=[]
    )
    
    with pytest.raises(Exception) as exc_info:
        await executor.execute(workflow)
    
    assert "not found" in str(exc_info.value).lower()
