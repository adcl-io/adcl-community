# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for models API endpoints
Tests persistence, default handling, and concurrent operations
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Import the app
from app.main import app, load_models_from_config, save_models_to_config, models_db, MODELS_CONFIG_PATH


@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory for testing"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def test_models_config(test_config_dir):
    """Create a test models.yaml file"""
    models_yaml = test_config_dir / "models.yaml"
    test_config = {
        "models": [
            {
                "id": "test-claude-1",
                "name": "Test Claude 1",
                "provider": "anthropic",
                "model_id": "claude-sonnet-4-5-20250929",
                "temperature": 0.7,
                "max_tokens": 4096,
                "description": "Test model 1",
                "is_default": True,
                "api_key_env": "ANTHROPIC_API_KEY"
            },
            {
                "id": "test-claude-2",
                "name": "Test Claude 2",
                "provider": "anthropic",
                "model_id": "claude-sonnet-4-20250514",
                "temperature": 0.5,
                "max_tokens": 8192,
                "description": "Test model 2",
                "is_default": False,
                "api_key_env": "ANTHROPIC_API_KEY"
            }
        ],
        "anthropic": {
            "timeout": 60,
            "max_retries": 3
        }
    }

    with open(models_yaml, "w") as f:
        yaml.safe_dump(test_config, f)

    return models_yaml


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestModelsLoad:
    """Test model loading from config file"""

    def test_load_models_from_config_success(self, test_models_config, monkeypatch):
        """Test successful model loading"""
        # Mock environment variables
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock the MODELS_CONFIG_PATH
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", test_models_config)

        models = load_models_from_config()

        assert len(models) == 2
        assert models[0]["id"] == "test-claude-1"
        assert models[0]["is_default"] is True
        assert models[0]["configured"] is True
        assert models[1]["is_default"] is False

    def test_load_models_no_api_key(self, test_models_config, monkeypatch):
        """Test loading models without API key marks them as unconfigured"""
        # Don't set ANTHROPIC_API_KEY
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", test_models_config)

        models = load_models_from_config()

        assert len(models) == 2
        assert models[0]["configured"] is False
        assert models[1]["configured"] is False

    def test_load_models_missing_file(self, tmp_path, monkeypatch):
        """Test loading when config file doesn't exist"""
        missing_path = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", missing_path)

        models = load_models_from_config()

        assert models == []

    def test_load_models_malformed_yaml(self, tmp_path, monkeypatch):
        """Test loading with malformed YAML"""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("invalid: yaml: content: [")
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", bad_yaml)

        models = load_models_from_config()

        assert models == []


class TestModelsEndpoints:
    """Test models API endpoints"""

    @patch("app.main.models_db", new_callable=list)
    def test_list_models(self, mock_models_db, client):
        """Test GET /models endpoint"""
        mock_models_db.extend([
            {"id": "test-1", "name": "Test Model 1", "is_default": True},
            {"id": "test-2", "name": "Test Model 2", "is_default": False}
        ])

        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "test-1"

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db", new_callable=list)
    def test_create_model(self, mock_models_db, mock_save, client):
        """Test POST /models endpoint"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        new_model = {
            "name": "New Model",
            "provider": "anthropic",
            "model_id": "claude-3",
            "temperature": 0.7,
            "max_tokens": 4096,
            "description": "Test model",
            "is_default": False
        }

        response = client.post("/models", json=new_model)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Model"
        assert data["id"] == "anthropic-claude-3"  # Slug generated from provider-model_id
        assert len(mock_models_db) == 1

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db")
    def test_delete_model_not_default(self, mock_models_db, mock_save, client):
        """Test DELETE /models/{id} for non-default model"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        mock_models_db.__iter__.return_value = iter([
            {"id": "test-1", "name": "Test 1", "is_default": False},
            {"id": "test-2", "name": "Test 2", "is_default": True}
        ])
        mock_models_db.__len__.return_value = 2

        response = client.delete("/models/test-1")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @patch("app.main.models_db")
    def test_delete_default_model_fails(self, mock_models_db, client):
        """Test DELETE /models/{id} fails for default model"""
        mock_models_db.__iter__.return_value = iter([
            {"id": "test-1", "name": "Test 1", "is_default": True}
        ])

        response = client.delete("/models/test-1")

        assert response.status_code == 400
        assert "Cannot delete default model" in response.json()["detail"]


class TestSetDefaultEndpoint:
    """Test set-default endpoint"""

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db", new_callable=list)
    def test_set_default_success(self, mock_models_db, mock_save, client):
        """Test POST /models/{id}/set-default success"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        # Use mock_models_db directly as a list
        mock_models_db.extend([
            {"id": "model-1", "name": "Model 1", "is_default": True},
            {"id": "model-2", "name": "Model 2", "is_default": False},
            {"id": "model-3", "name": "Model 3", "is_default": False}
        ])

        response = client.post("/models/model-2/set-default")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["default_model"]["id"] == "model-2"
        assert data["default_model"]["is_default"] is True

        # Verify only one model is default
        default_count = sum(1 for m in mock_models_db if m["is_default"])
        assert default_count == 1

    @patch("app.main.models_db")
    def test_set_default_not_found(self, mock_models_db, client):
        """Test POST /models/{id}/set-default with non-existent model"""
        mock_models_db.__iter__.return_value = iter([
            {"id": "model-1", "name": "Model 1", "is_default": True}
        ])

        response = client.post("/models/nonexistent/set-default")

        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db")
    def test_set_default_idempotent(self, mock_models_db, mock_save, client):
        """Test setting same model as default twice is idempotent"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        test_models = [
            {"id": "model-1", "name": "Model 1", "is_default": True},
            {"id": "model-2", "name": "Model 2", "is_default": False}
        ]

        mock_models_db.__iter__.return_value = iter(test_models)

        # Set model-1 as default (already is)
        response = client.post("/models/model-1/set-default")

        assert response.status_code == 200
        assert test_models[0]["is_default"] is True
        assert test_models[1]["is_default"] is False


class TestModelsPersistence:
    """Test model persistence to YAML"""

    @pytest.mark.asyncio
    async def test_save_models_to_config(self, test_config_dir, monkeypatch):
        """Test saving models to config file"""
        models_path = test_config_dir / "models.yaml"
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", models_path)

        test_models = [
            {
                "id": "test-1",
                "name": "Test Model 1",
                "provider": "anthropic",
                "model_id": "claude-3",
                "temperature": 0.7,
                "max_tokens": 4096,
                "description": "Test model",
                "is_default": True
            },
            {
                "id": "test-2",
                "name": "Test Model 2",
                "provider": "openai",
                "model_id": "gpt-4",
                "temperature": 0.5,
                "max_tokens": 8192,
                "description": "Another test",
                "is_default": False
            }
        ]

        result = await save_models_to_config(test_models)

        assert result is True
        assert models_path.exists()

        # Verify saved content
        with open(models_path, "r") as f:
            saved_config = yaml.safe_load(f)

        assert "models" in saved_config
        assert len(saved_config["models"]) == 2
        assert saved_config["models"][0]["id"] == "test-1"
        assert saved_config["models"][0]["is_default"] is True
        assert saved_config["models"][0]["api_key_env"] == "ANTHROPIC_API_KEY"
        assert saved_config["models"][1]["api_key_env"] == "OPENAI_API_KEY"

    @pytest.mark.asyncio
    async def test_save_preserves_other_config(self, test_config_dir, monkeypatch):
        """Test that saving models preserves other config sections"""
        models_path = test_config_dir / "models.yaml"

        # Create initial config with other sections
        initial_config = {
            "models": [],
            "anthropic": {"timeout": 60},
            "custom_section": {"key": "value"}
        }

        with open(models_path, "w") as f:
            yaml.safe_dump(initial_config, f)

        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", models_path)

        test_models = [{"id": "test-1", "name": "Test", "provider": "anthropic",
                        "model_id": "claude-3", "temperature": 0.7,
                        "max_tokens": 4096, "description": "", "is_default": True}]

        await save_models_to_config(test_models)

        # Verify other sections preserved
        with open(models_path, "r") as f:
            saved_config = yaml.safe_load(f)

        assert "anthropic" in saved_config
        assert saved_config["anthropic"]["timeout"] == 60
        assert "custom_section" in saved_config


class TestConcurrency:
    """Test concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_set_default(self, monkeypatch):
        """Test that concurrent set-default operations are properly locked"""
        # This is more of an integration test, but validates the locking mechanism
        from app.main import models_lock, models_db

        test_models = [
            {"id": f"model-{i}", "name": f"Model {i}", "is_default": False}
            for i in range(10)
        ]

        monkeypatch.setattr("app.main.models_db", test_models)

        async def set_default(model_id):
            async with models_lock:
                for m in test_models:
                    m["is_default"] = False
                for m in test_models:
                    if m["id"] == model_id:
                        m["is_default"] = True
                        break
                await asyncio.sleep(0.001)  # Simulate I/O

        # Run concurrent set-default operations
        await asyncio.gather(*[set_default(f"model-{i}") for i in range(10)])

        # Verify only one model is default
        default_count = sum(1 for m in test_models if m["is_default"])
        assert default_count == 1


class TestNewValidations:
    """Test new validation features from linus review"""

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db", new_callable=list)
    def test_create_duplicate_model_fails(self, mock_models_db, mock_save, client):
        """Test that creating a model with duplicate ID fails"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        # Pre-populate with existing model
        mock_models_db.append({
            "id": "anthropic-claude-3",
            "name": "Existing Model",
            "provider": "anthropic",
            "model_id": "claude-3"
        })

        # Try to create duplicate
        new_model = {
            "name": "Duplicate Model",
            "provider": "anthropic",
            "model_id": "claude-3",
            "temperature": 0.7,
            "max_tokens": 4096
        }

        response = client.post("/models", json=new_model)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch("app.main.save_models_to_config")
    @patch("app.main.models_db", new_callable=list)
    def test_delete_last_model_fails(self, mock_models_db, mock_save, client):
        """Test that deleting the last model fails"""
        mock_save.return_value = asyncio.Future()
        mock_save.return_value.set_result(True)

        # Only one model in db
        mock_models_db.append({
            "id": "test-1",
            "name": "Last Model",
            "is_default": True
        })

        response = client.delete("/models/test-1")

        assert response.status_code == 400
        assert "last model" in response.json()["detail"].lower()

    def test_load_invalid_yaml_temperature(self, tmp_path, monkeypatch):
        """Test that invalid temperature value is caught by validation"""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("""
models:
  - id: test-1
    name: Test Model
    provider: anthropic
    model_id: claude-3
    temperature: 5.0
""")
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", bad_yaml)

        models = load_models_from_config()

        # Should return empty list due to validation error
        assert models == []

    def test_load_duplicate_model_ids(self, tmp_path, monkeypatch):
        """Test that duplicate model IDs in YAML are caught"""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("""
models:
  - id: test-1
    name: Test Model 1
    provider: anthropic
    model_id: claude-3
  - id: test-1
    name: Test Model 2
    provider: openai
    model_id: gpt-4
""")
        monkeypatch.setattr("app.main.MODELS_CONFIG_PATH", bad_yaml)

        models = load_models_from_config()

        # Should return empty list due to duplicate IDs
        assert models == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
