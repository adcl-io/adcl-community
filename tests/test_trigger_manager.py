# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit Tests for DockerManager (Trigger Mode)

Tests trigger lifecycle operations, environment variable injection,
Docker container management, and status tracking.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from pathlib import Path

# Import the DockerManager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.docker_manager import DockerManager


class TestTriggerManagerEnvironmentVariables:
    """Test suite for environment variable injection"""

    @pytest.fixture
    def trigger_manager(self):
        """Create DockerManager instance in trigger mode for testing"""
        return DockerManager(resource_type="trigger")

    def test_environment_variable_auto_injection_workflow(self, trigger_manager):
        """Test that platform variables are auto-injected with workflow_id"""
        trigger_package = {
            "name": "test-trigger",
            "version": "1.0.0",
            "deployment": {
                "environment": {
                    "CUSTOM_VAR": "custom_value"
                }
            }
        }
        user_config = {
            "workflow_id": "test-workflow"
        }

        env_vars = trigger_manager._build_trigger_env_vars(trigger_package, user_config)

        assert "ORCHESTRATOR_URL" in env_vars
        assert env_vars["ORCHESTRATOR_URL"] == "http://orchestrator:8000"
        assert "ORCHESTRATOR_WS" in env_vars
        assert env_vars["ORCHESTRATOR_WS"] == "ws://orchestrator:8000"
        assert "WORKFLOW_ID" in env_vars
        assert env_vars["WORKFLOW_ID"] == "test-workflow"
        assert "CUSTOM_VAR" in env_vars
        assert env_vars["CUSTOM_VAR"] == "custom_value"

    def test_environment_variable_auto_injection_team(self, trigger_manager):
        """Test that platform variables are auto-injected with team_id"""
        trigger_package = {
            "name": "test-trigger",
            "version": "1.0.0",
            "deployment": {
                "environment": {
                    "TRIGGER_SPECIFIC": "value"
                }
            }
        }
        user_config = {
            "team_id": "test-team"
        }

        env_vars = trigger_manager._build_trigger_env_vars(trigger_package, user_config)

        assert "TEAM_ID" in env_vars
        assert env_vars["TEAM_ID"] == "test-team"
        assert "WORKFLOW_ID" not in env_vars

    def test_environment_variable_both_workflow_and_team(self, trigger_manager):
        """Test that both workflow_id and team_id can be set"""
        trigger_package = {
            "name": "test-trigger",
            "version": "1.0.0",
            "deployment": {
                "environment": {}
            }
        }
        user_config = {
            "workflow_id": "workflow-1",
            "team_id": "team-1"
        }

        env_vars = trigger_manager._build_trigger_env_vars(trigger_package, user_config)

        assert env_vars["WORKFLOW_ID"] == "workflow-1"
        assert env_vars["TEAM_ID"] == "team-1"

    def test_environment_variable_substitution(self, trigger_manager):
        """Test that environment variables are resolved from system env"""
        trigger_package = {
            "name": "test-trigger",
            "version": "1.0.0",
            "deployment": {
                "environment": {
                    "WEBHOOK_SECRET": "${WEBHOOK_SECRET}",
                    "DEFAULT_VALUE": "${MISSING_VAR:-default}"
                }
            }
        }
        user_config = {}

        with patch.dict('os.environ', {'WEBHOOK_SECRET': 'secret123'}):
            env_vars = trigger_manager._build_trigger_env_vars(trigger_package, user_config)

        assert env_vars["WEBHOOK_SECRET"] == "secret123"
        assert env_vars["DEFAULT_VALUE"] == "default"


class TestTriggerManagerInstall:
    """Test suite for trigger installation"""

    @pytest.fixture
    def trigger_manager(self):
        """Create DockerManager instance in trigger mode for testing"""
        return DockerManager(resource_type="trigger")

    @pytest.fixture
    def sample_trigger_package(self):
        """Sample trigger package configuration"""
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

    def test_install_trigger_creates_container(
        self,
        trigger_manager,
        sample_trigger_package
    ):
        """Test that install creates a Docker container"""
        mock_client = Mock()
        trigger_manager.client = mock_client

        # Mock image build
        mock_image = Mock()
        mock_client.images.build.return_value = (mock_image, [])

        # Mock container creation
        mock_container = Mock(id="container123", name="trigger-simple-webhook")
        mock_client.containers.run.return_value = mock_container

        user_config = {"workflow_id": "test-workflow"}

        # Mock file save operation
        trigger_manager.installed_file = Mock()
        result = trigger_manager.install(sample_trigger_package, user_config)

        assert result["status"] == "installed"
        assert result["name"] == "simple-webhook"
        assert result["version"] == "1.0.0"
        assert "container_name" in result

    def test_install_trigger_with_existing_trigger_fails(
        self,
        trigger_manager,
        sample_trigger_package
    ):
        """Test that installing same trigger twice returns already_installed"""
        mock_client = Mock()
        trigger_manager.client = mock_client

        # Mock image build and container creation
        mock_client.images.build.return_value = (Mock(), [])
        mock_client.containers.run.return_value = Mock(id="container123", name="trigger-simple-webhook")

        trigger_manager.installed_file = Mock()
        # First installation succeeds
        trigger_manager.install(sample_trigger_package, {"workflow_id": "wf1"})

        # Second installation should return already_installed status
        result = trigger_manager.install(sample_trigger_package, {"workflow_id": "wf2"})

        assert result["status"] == "already_installed"
        assert result["name"] == "simple-webhook"

    def test_install_saves_trigger_config(
        self,
        trigger_manager,
        sample_trigger_package
    ):
        """Test that install saves trigger configuration to JSON file"""
        mock_client = Mock()
        trigger_manager.client = mock_client

        # Mock image build and container creation
        mock_client.images.build.return_value = (Mock(), [])
        mock_client.containers.run.return_value = Mock(id="container123", name="trigger-simple-webhook")

        user_config = {"workflow_id": "test-workflow"}

        trigger_manager.installed_file = Mock()
        result = trigger_manager.install(sample_trigger_package, user_config)

        # Verify file was written
        trigger_manager.installed_file.write_text.assert_called_once()

        # Verify trigger was registered in memory
        assert "simple-webhook" in trigger_manager.installed
        assert trigger_manager.installed["simple-webhook"]["version"] == "1.0.0"
        assert trigger_manager.installed["simple-webhook"]["user_config"]["workflow_id"] == "test-workflow"


class TestTriggerManagerLifecycle:
    """Test suite for trigger lifecycle operations"""

    @pytest.fixture
    def trigger_manager(self):
        """Create DockerManager instance in trigger mode"""
        return DockerManager(resource_type="trigger")

    @pytest.fixture
    def installed_trigger(self, trigger_manager):
        """Setup an installed trigger for lifecycle tests"""
        trigger_manager.installed["test-trigger"] = {
            "name": "test-trigger",
            "version": "1.0.0",
            "container_name": "trigger-test-trigger",
            "container_id": "container123",
            "workflow_id": "test-workflow",
            "installed_at": datetime.now().isoformat()
        }
        return "test-trigger"

    def test_start_trigger(self, trigger_manager, installed_trigger):
        """Test starting a stopped trigger"""
        with patch.object(trigger_manager, '_run_docker') as mock_run:
            result = trigger_manager.start(installed_trigger)

            assert result["status"] == "started"
            assert result["name"] == installed_trigger
            mock_run.assert_called_once_with(["start", f"trigger-{installed_trigger}"])

    def test_stop_trigger(self, trigger_manager, installed_trigger):
        """Test stopping a running trigger"""
        with patch.object(trigger_manager, '_run_docker') as mock_run:
            result = trigger_manager.stop(installed_trigger)

            assert result["status"] == "stopped"
            assert result["name"] == installed_trigger
            mock_run.assert_called_once_with(["stop", f"trigger-{installed_trigger}"])

    def test_restart_trigger(self, trigger_manager, installed_trigger):
        """Test restarting a trigger"""
        with patch.object(trigger_manager, '_run_docker') as mock_run:
            result = trigger_manager.restart(installed_trigger)

            assert result["status"] == "restarted"
            assert result["name"] == installed_trigger
            mock_run.assert_called_once_with(["restart", f"trigger-{installed_trigger}"])

    def test_uninstall_trigger(self, trigger_manager, installed_trigger):
        """Test uninstalling a trigger removes container and config"""
        with patch.object(trigger_manager, '_run_docker') as mock_run:
            trigger_manager.installed_file = Mock()
            result = trigger_manager.uninstall(installed_trigger)

            assert result["status"] == "uninstalled"
            assert result["name"] == installed_trigger
            assert mock_run.call_count == 2  # stop and rm
            assert installed_trigger not in trigger_manager.installed

    def test_uninstall_nonexistent_trigger_fails(self, trigger_manager):
        """Test that uninstalling non-existent trigger returns not_installed"""
        result = trigger_manager.uninstall("nonexistent-trigger")
        assert result["status"] == "not_installed"
        assert result["name"] == "nonexistent-trigger"

    def test_get_trigger_status_running(self, trigger_manager, installed_trigger):
        """Test getting status of running trigger"""
        mock_result = Mock()
        mock_result.stdout = "Up 5 minutes"
        
        with patch.object(trigger_manager, '_run_docker', return_value=mock_result):
            status = trigger_manager.get_status(installed_trigger)

            assert status["name"] == installed_trigger
            assert status["state"] == "running"
            assert status["running"] is True

    def test_get_trigger_status_stopped(self, trigger_manager, installed_trigger):
        """Test getting status of stopped trigger"""
        mock_result = Mock()
        mock_result.stdout = "Exited (0) 2 minutes ago"
        
        with patch.object(trigger_manager, '_run_docker', return_value=mock_result):
            status = trigger_manager.get_status(installed_trigger)

            assert status["state"] == "exited"
            assert status["running"] is False


class TestTriggerManagerUpdate:
    """Test suite for trigger update operations"""

    @pytest.fixture
    def trigger_manager(self):
        """Create DockerManager instance in trigger mode"""
        return DockerManager(resource_type="trigger")

    @pytest.fixture
    def installed_trigger_v1(self, trigger_manager):
        """Setup trigger at version 1.0.0"""
        trigger_manager.installed["test-trigger"] = {
            "version": "1.0.0",
            "package": {"name": "test-trigger", "version": "1.0.0", "deployment": {"environment": {}}},
            "user_config": {"workflow_id": "test-workflow"},
            "container_id": "container123",
            "container_name": "trigger-test-trigger",
            "installed_at": datetime.now().isoformat(),
            "trigger_type": "webhook"
        }
        return "test-trigger"

    @pytest.fixture
    def new_trigger_package_v2(self):
        """New trigger package at version 2.0.0"""
        return {
            "name": "test-trigger",
            "version": "2.0.0",
            "type": "trigger",
            "deployment": {
                "image": "trigger-test:2.0.0",
                "container_name": "trigger-test-trigger",
                "environment": {}
            },
            "trigger": {
                "type": "webhook"
            }
        }

    def test_update_trigger_to_new_version(
        self,
        trigger_manager,
        installed_trigger_v1,
        new_trigger_package_v2
    ):
        """Test updating trigger to new version"""
        with patch.object(trigger_manager, '_run_docker') as mock_run:
            trigger_manager.installed_file = Mock()
            result = trigger_manager.update(installed_trigger_v1, new_trigger_package_v2)

            if result["status"] != "updated":
                print(f"UPDATE ERROR: {result}")
            assert result["status"] == "updated"
            assert result["name"] == installed_trigger_v1
            assert result["old_version"] == "1.0.0"
            assert result["new_version"] == "2.0.0"

            # Verify docker commands were called (stop, rm for uninstall, run for install)
            assert mock_run.call_count >= 3

    def test_update_same_version_no_op(
        self,
        trigger_manager,
        installed_trigger_v1
    ):
        """Test updating to same version is no-op"""
        same_version_package = {
            "name": "test-trigger",
            "version": "1.0.0",
            "deployment": {"environment": {}}
        }

        result = trigger_manager.update(installed_trigger_v1, same_version_package)

        assert result["status"] == "already_latest"
        assert result["name"] == "test-trigger"
        assert result["version"] == "1.0.0"

    def test_update_nonexistent_trigger_fails(self, trigger_manager, new_trigger_package_v2):
        """Test that updating non-existent trigger returns not_installed"""
        result = trigger_manager.update("nonexistent-trigger", new_trigger_package_v2)
        assert result["status"] == "not_installed"
        assert result["name"] == "nonexistent-trigger"


class TestTriggerManagerList:
    """Test suite for listing triggers"""

    @pytest.fixture
    def trigger_manager(self):
        """Create DockerManager instance in trigger mode"""
        return DockerManager(resource_type="trigger")

    @pytest.fixture
    def multiple_triggers(self, trigger_manager):
        """Setup multiple installed triggers"""
        trigger_manager.installed = {
            "webhook-1": {
                "name": "webhook-1",
                "version": "1.0.0",
                "trigger_type": "webhook",
                "container_name": "trigger-webhook-1"
            },
            "schedule-1": {
                "name": "schedule-1",
                "version": "2.0.0",
                "trigger_type": "schedule",
                "container_name": "trigger-schedule-1"
            }
        }

    def test_list_triggers(self, trigger_manager, multiple_triggers):
        """Test listing all installed triggers"""
        triggers = trigger_manager.list_installed()

        assert len(triggers) == 2
        assert any(t["name"] == "webhook-1" for t in triggers)
        assert any(t["name"] == "schedule-1" for t in triggers)

    def test_list_empty_triggers(self, trigger_manager):
        """Test listing when no triggers installed"""
        triggers = trigger_manager.list_installed()

        assert triggers == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
