# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
API Integration tests for Workflow V2 Engine

Tests V2 API endpoints end-to-end.
Requires full environment (configs, MCPs) - run on production servers only.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Requires full production environment")
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_list_workflows(client):
    """GET /v2/workflows should list workflows"""
    response = client.get("/v2/workflows")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_get_workflow(client):
    """POST and GET workflow"""
    workflow = {
        "workflow_id": "test-api-workflow",
        "name": "API Test Workflow",
        "description": "Test workflow for API",
        "nodes": [
            {"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60}
        ],
        "edges": []
    }
    
    # Create workflow
    response = client.post("/v2/workflows", json=workflow)
    assert response.status_code == 200
    
    # Get workflow
    response = client.get("/v2/workflows/test-api-workflow")
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "test-api-workflow"
    assert data["name"] == "API Test Workflow"


def test_update_workflow(client):
    """PUT /v2/workflows/{id} should update workflow"""
    workflow_id = "test-update-workflow"
    
    # Create initial workflow
    workflow = {
        "workflow_id": workflow_id,
        "name": "Original Name",
        "nodes": [{"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60}],
        "edges": []
    }
    client.post("/v2/workflows", json=workflow)
    
    # Update workflow
    updated = {
        "workflow_id": workflow_id,
        "name": "Updated Name",
        "description": "Updated description",
        "nodes": [{"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 120}],
        "edges": []
    }
    response = client.put(f"/v2/workflows/{workflow_id}", json=updated)
    assert response.status_code == 200
    
    # Verify update
    response = client.get(f"/v2/workflows/{workflow_id}")
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"


def test_delete_workflow(client):
    """DELETE /v2/workflows/{id} should delete workflow"""
    workflow_id = "test-delete-workflow"
    
    # Create workflow
    workflow = {
        "workflow_id": workflow_id,
        "name": "To Delete",
        "nodes": [{"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60}],
        "edges": []
    }
    client.post("/v2/workflows", json=workflow)
    
    # Delete workflow
    response = client.delete(f"/v2/workflows/{workflow_id}")
    assert response.status_code == 200
    
    # Verify deleted
    response = client.get(f"/v2/workflows/{workflow_id}")
    assert response.status_code == 404


def test_run_workflow(client):
    """POST /v2/workflows/run should execute workflow"""
    workflow_id = "test-run-workflow"
    
    # Create workflow
    workflow = {
        "workflow_id": workflow_id,
        "name": "Run Test",
        "nodes": [{"node_id": "node1", "agent_id": "sqli-analyst", "timeout": 60}],
        "edges": []
    }
    client.post("/v2/workflows", json=workflow)
    
    # Run workflow
    response = client.post("/v2/workflows/run", json={
        "workflow_id": workflow_id,
        "initial_message": "Test scan: example.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] in ["completed", "failed"]
    assert "execution_id" in data


def test_get_nonexistent_workflow(client):
    """GET non-existent workflow should return 404"""
    response = client.get("/v2/workflows/nonexistent")
    assert response.status_code == 404


def test_create_invalid_workflow(client):
    """POST invalid workflow should return 400"""
    invalid_workflow = {
        "workflow_id": "invalid",
        "name": "Invalid",
        "nodes": [],  # Empty nodes
        "edges": []
    }
    response = client.post("/v2/workflows", json=invalid_workflow)
    assert response.status_code == 400


def test_run_nonexistent_workflow(client):
    """Run non-existent workflow should return 404"""
    response = client.post("/v2/workflows/run", json={
        "workflow_id": "nonexistent",
        "initial_message": "Test"
    })
    assert response.status_code == 404
