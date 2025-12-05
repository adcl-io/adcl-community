# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Test Fixtures and Utilities for Integration Tests

Provides pytest fixtures for Docker container management, API clients,
and test utilities for trigger system integration testing.
"""

import pytest
import docker
import httpx
import asyncio
import time
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.docker_manager import DockerManager


# ============================================================================
# Docker Client Fixture
# ============================================================================

@pytest.fixture(scope="session")
def docker_client():
    """
    Docker client for container operations.

    Scope: session (reuse across all tests)
    """
    client = docker.from_env()
    yield client
    client.close()


# ============================================================================
# Trigger Cleanup Fixture
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def trigger_cleanup(docker_client):
    """
    Auto-cleanup fixture that removes test trigger containers after each test.

    Runs automatically after every test function to ensure clean state.
    """
    # List of containers to clean up (populated during tests)
    test_containers = []

    yield test_containers

    # Cleanup after test
    for container_name in test_containers:
        try:
            container = docker_client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove(force=True)
            print(f"✓ Cleaned up container: {container_name}")
        except docker.errors.NotFound:
            # Already removed
            pass
        except Exception as e:
            print(f"⚠ Failed to cleanup container {container_name}: {e}")

    # Clean up installed-triggers.json entries
    try:
        from backend.app.docker_manager import DockerManager
        trigger_manager = DockerManager(resource_type="trigger")
        for container_name in test_containers:
            # Extract trigger name from container name (format: trigger-{name})
            if container_name.startswith("trigger-"):
                trigger_name = container_name.replace("trigger-", "")
                if trigger_name in trigger_manager.installed:
                    del trigger_manager.installed[trigger_name]

        # Save updated state
        trigger_manager._save_installed()
    except Exception as e:
        print(f"⚠ Failed to cleanup installed triggers: {e}")


# ============================================================================
# Mock Orchestrator Fixture
# ============================================================================

@pytest.fixture
def mock_orchestrator():
    """
    Mock orchestrator API server for webhook execution tests.

    Returns a mock that tracks calls to workflow/team execution endpoints.
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={
        "id": "exec-test-123",
        "status": "running",
        "workflow_id": "test-workflow"
    })
    mock_response.raise_for_status = Mock()

    with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
        yield mock_post


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def orchestrator_url():
    """Orchestrator API base URL"""
    return os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


@pytest.fixture
def registry_url():
    """Registry API base URL"""
    return os.getenv("REGISTRY_URL", "http://localhost:9000")


@pytest.fixture
async def api_client(orchestrator_url):
    """
    HTTP client for orchestrator API calls.

    Usage:
        async with api_client.post("/triggers/install", json={...}) as response:
            data = await response.json()
    """
    async with httpx.AsyncClient(base_url=orchestrator_url, timeout=30.0) as client:
        yield client


@pytest.fixture
async def registry_client(registry_url):
    """
    HTTP client for registry API calls.
    """
    async with httpx.AsyncClient(base_url=registry_url, timeout=10.0) as client:
        yield client


# ============================================================================
# Helper Utilities
# ============================================================================

async def wait_for_container_health(
    docker_client: docker.DockerClient,
    container_name: str,
    timeout: int = 30
) -> bool:
    """
    Wait for container to be healthy/running.

    Args:
        docker_client: Docker client instance
        container_name: Name of container to check
        timeout: Maximum seconds to wait

    Returns:
        True if healthy, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            container = docker_client.containers.get(container_name)

            # Check if running
            container.reload()
            if container.status == "running":
                # Give it 2 more seconds to start accepting connections
                await asyncio.sleep(2)
                return True

        except docker.errors.NotFound:
            # Container doesn't exist yet
            pass

        await asyncio.sleep(1)

    return False


def generate_webhook_payload(trigger_type: str = "simple") -> Dict[str, Any]:
    """
    Generate mock webhook payload for testing.

    Args:
        trigger_type: Type of trigger ("simple", "github", "linear", "schedule")

    Returns:
        Mock webhook payload dictionary
    """
    if trigger_type == "simple":
        return {
            "test": "data",
            "timestamp": "2025-10-25T12:00:00Z"
        }

    elif trigger_type == "github":
        return {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "head": {"ref": "feature-branch"},
                "base": {"ref": "main"}
            },
            "repository": {"full_name": "test/repo"},
            "sender": {"login": "testuser"}
        }

    elif trigger_type == "linear":
        return {
            "type": "agentSession",
            "action": "created",
            "data": {
                "id": "session-test-123",
                "issueId": "issue-456",
                "state": "active"
            }
        }

    elif trigger_type == "schedule":
        return {
            "trigger": "schedule",
            "cron": "*/1 * * * *",
            "timestamp": "2025-10-25T12:00:00Z"
        }

    else:
        raise ValueError(f"Unknown trigger type: {trigger_type}")


async def get_trigger_logs(
    docker_client: docker.DockerClient,
    container_name: str,
    tail: int = 100
) -> str:
    """
    Fetch container logs for debugging.

    Args:
        docker_client: Docker client instance
        container_name: Name of container
        tail: Number of log lines to retrieve

    Returns:
        Container logs as string
    """
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=tail, timestamps=True)
        return logs.decode('utf-8')
    except docker.errors.NotFound:
        return f"Container {container_name} not found"
    except Exception as e:
        return f"Error fetching logs: {str(e)}"


async def verify_container_env_vars(
    docker_client: docker.DockerClient,
    container_name: str,
    expected_vars: Dict[str, str]
) -> bool:
    """
    Verify container has expected environment variables.

    Args:
        docker_client: Docker client instance
        container_name: Name of container
        expected_vars: Dict of expected environment variables

    Returns:
        True if all expected vars are present with correct values
    """
    try:
        container = docker_client.containers.get(container_name)
        container.reload()

        env_list = container.attrs["Config"]["Env"]
        env_dict = {}
        for env_str in env_list:
            if "=" in env_str:
                key, value = env_str.split("=", 1)
                env_dict[key] = value

        for key, expected_value in expected_vars.items():
            if key not in env_dict:
                print(f"❌ Missing env var: {key}")
                return False
            if env_dict[key] != expected_value:
                print(f"❌ Env var mismatch: {key}={env_dict[key]} (expected {expected_value})")
                return False

        return True

    except Exception as e:
        print(f"❌ Error verifying env vars: {e}")
        return False


# ============================================================================
# TriggerManager Fixture
# ============================================================================

@pytest.fixture
def trigger_manager(tmp_path):
    """
    DockerManager instance in trigger mode with test-specific base directory.

    Uses tmp_path for installed-triggers.json to avoid conflicts.
    """
    return DockerManager(base_dir=str(tmp_path), resource_type="trigger")


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def simple_webhook_package():
    """Sample simple webhook trigger package"""
    return {
        "name": "simple-webhook",
        "version": "1.0.0",
        "type": "trigger",
        "deployment": {
            "image": "trigger-webhook:1.0.0",
            "build": {
                "context": "./triggers/webhook",
                "dockerfile": "Dockerfile.webhook"
            },
            "container_name": "trigger-simple-webhook",
            "restart": "unless-stopped",
            "ports": [
                {"host": "8100", "container": "8100"}
            ],
            "environment": {
                "WEBHOOK_SECRET": "${WEBHOOK_SECRET:-}"
            }
        },
        "trigger": {
            "type": "webhook"
        }
    }


@pytest.fixture
def schedule_trigger_package():
    """Sample schedule trigger package"""
    return {
        "name": "daily-scan",
        "version": "1.0.0",
        "type": "trigger",
        "deployment": {
            "image": "trigger-scheduler:1.0.0",
            "build": {
                "context": "./triggers/schedule",
                "dockerfile": "Dockerfile.scheduler"
            },
            "container_name": "trigger-daily-scan",
            "restart": "unless-stopped",
            "environment": {
                "CRON_EXPRESSION": "${CRON_EXPRESSION}",
                "SCAN_TARGET": "${SCAN_TARGET:-192.168.50.0/24}"
            }
        },
        "trigger": {
            "type": "schedule",
            "cron": "0 0 * * *"
        }
    }


# Export helper functions for use in tests
__all__ = [
    'docker_client',
    'trigger_cleanup',
    'mock_orchestrator',
    'api_client',
    'registry_client',
    'wait_for_container_health',
    'generate_webhook_payload',
    'get_trigger_logs',
    'verify_container_env_vars',
    'simple_webhook_package',
    'schedule_trigger_package',
]
