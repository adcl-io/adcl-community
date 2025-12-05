# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for Workflow API Endpoints

Tests workflow save, load, list, and delete operations.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def temp_workflows_dir():
    """Create temporary workflows directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_workflows_path(temp_workflows_dir):
    """Mock the workflows path to use temp directory"""
    with patch('app.main.config.get_workflows_path', return_value=temp_workflows_dir):
        yield temp_workflows_dir


def test_save_workflow(client, mock_workflows_path):
    """Test POST /workflows saves workflow to file"""
    workflow = {
        "name": "Test Workflow",
        "description": "Test description",
        "nodes": [
            {
                "id": "node-1",
                "type": "mcp_call",
                "mcp_server": "agent",
                "tool": "think",
                "params": {"prompt": "test"}
            }
        ],
        "edges": []
    }
    
    response = client.post("/workflows", json=workflow)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Workflow saved"
    assert data["filename"] == "test_workflow.json"
    
    # Verify file was created
    file_path = Path(mock_workflows_path) / "test_workflow.json"
    assert file_path.exists()
    
    # Verify content
    saved_workflow = json.loads(file_path.read_text())
    assert saved_workflow["name"] == "Test Workflow"
    assert len(saved_workflow["nodes"]) == 1


def test_save_workflow_sanitizes_filename(client, mock_workflows_path):
    """Test workflow name is sanitized for filename"""
    workflow = {
        "name": "My/Test Workflow!",
        "nodes": [],
        "edges": []
    }
    
    response = client.post("/workflows", json=workflow)
    
    assert response.status_code == 200
    data = response.json()
    # Sanitization keeps underscores and removes special chars
    assert data["filename"] == "my_test_workflow.json"


def test_list_workflows(client, mock_workflows_path):
    """Test GET /workflows lists all workflows"""
    # Create test workflows
    workflows = [
        {"name": "Workflow 1", "description": "First", "nodes": [], "edges": []},
        {"name": "Workflow 2", "description": "Second", "nodes": [], "edges": []}
    ]
    
    for wf in workflows:
        client.post("/workflows", json=wf)
    
    response = client.get("/workflows")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(w["name"] == "Workflow 1" for w in data)
    assert any(w["name"] == "Workflow 2" for w in data)


def test_list_workflows_empty(client, mock_workflows_path):
    """Test GET /workflows returns empty list when no workflows"""
    response = client.get("/workflows")
    
    assert response.status_code == 200
    assert response.json() == []


def test_delete_workflow(client, mock_workflows_path):
    """Test DELETE /workflows/{filename} removes workflow"""
    workflow = {
        "name": "Delete Me",
        "nodes": [],
        "edges": []
    }
    
    # Create workflow
    save_response = client.post("/workflows", json=workflow)
    filename = save_response.json()["filename"]
    
    # Delete workflow
    response = client.delete(f"/workflows/{filename}")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Workflow deleted"
    
    # Verify file was deleted
    file_path = Path(mock_workflows_path) / filename
    assert not file_path.exists()


def test_delete_nonexistent_workflow(client, mock_workflows_path):
    """Test DELETE /workflows/{filename} returns 404 for missing workflow"""
    response = client.delete("/workflows/nonexistent.json")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"


def test_get_example_workflow(client, mock_workflows_path):
    """Test GET /workflows/examples/{filename} returns workflow"""
    workflow = {
        "name": "Example",
        "nodes": [{"id": "n1", "type": "mcp_call", "mcp_server": "agent", "tool": "think", "params": {}}],
        "edges": []
    }
    
    # Create workflow
    save_response = client.post("/workflows", json=workflow)
    filename = save_response.json()["filename"]
    
    # Get workflow
    response = client.get(f"/workflows/examples/{filename}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Example"
    assert len(data["nodes"]) == 1


def test_get_nonexistent_example_workflow(client, mock_workflows_path):
    """Test GET /workflows/examples/{filename} returns 404 for missing workflow"""
    response = client.get("/workflows/examples/missing.json")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"
