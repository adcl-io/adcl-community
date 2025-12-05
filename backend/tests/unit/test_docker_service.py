# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for DockerService

Tests Docker manager initialization and graceful degradation.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.docker_service import DockerService, DummyManager
from app.core.errors import ServiceUnavailableError


@pytest.fixture
def docker_service():
    """Create DockerService instance"""
    return DockerService()


class TestDummyManager:
    """Test DummyManager"""

    def test_raises_error_on_method_call(self):
        """Should raise ServiceUnavailableError when calling methods"""
        dummy = DummyManager("mcp")
        
        with pytest.raises(ServiceUnavailableError):
            dummy.list_installed()


class TestDockerServiceInit:
    """Test DockerService initialization"""

    def test_initializes_without_managers(self, docker_service):
        """Should initialize with lazy loading"""
        assert docker_service._mcp_manager is None
        assert docker_service._trigger_manager is None


class TestGetMCPManager:
    """Test get_mcp_manager method"""

    @patch('app.services.docker_service.DockerManager')
    def test_creates_mcp_manager_when_docker_available(self, mock_docker_manager, docker_service):
        """Should create MCP manager when Docker is available"""
        manager = docker_service.get_mcp_manager()
        assert manager is not None

    @patch('app.services.docker_service.DockerManager', side_effect=Exception("Docker not available"))
    def test_returns_dummy_when_docker_unavailable(self, mock_docker_manager, docker_service):
        """Should return DummyManager when Docker is unavailable"""
        manager = docker_service.get_mcp_manager()
        assert isinstance(manager, DummyManager)

    def test_caches_manager_instance(self, docker_service):
        """Should cache manager instance after first call"""
        manager1 = docker_service.get_mcp_manager()
        manager2 = docker_service.get_mcp_manager()
        
        assert manager1 is manager2


class TestGetTriggerManager:
    """Test get_trigger_manager method"""

    @patch('app.services.docker_service.DockerManager')
    def test_creates_trigger_manager(self, mock_docker_manager, docker_service):
        """Should create trigger manager when Docker is available"""
        manager = docker_service.get_trigger_manager()
        assert manager is not None


class TestIsDockerAvailable:
    """Test is_docker_available method"""

    @patch('app.services.docker_service.DockerManager')
    def test_returns_true_when_available(self, mock_docker_manager, docker_service):
        """Should return True when Docker is available"""
        assert docker_service.is_docker_available() is True

    @patch('app.services.docker_service.DockerManager', side_effect=Exception("Not available"))
    def test_returns_false_when_unavailable(self, mock_docker_manager, docker_service):
        """Should return False when Docker is unavailable"""
        assert docker_service.is_docker_available() is False


class TestResetManagers:
    """Test reset_managers method"""

    def test_resets_cached_managers(self, docker_service):
        """Should reset cached manager instances"""
        docker_service.get_mcp_manager()
        assert docker_service._mcp_manager is not None
        
        docker_service.reset_managers()
        assert docker_service._mcp_manager is None
