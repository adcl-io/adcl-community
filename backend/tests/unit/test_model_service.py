# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for ModelService

Tests model configuration management and YAML persistence.
"""

import pytest
import yaml
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.services.model_service import ModelService
from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.config import Config


@pytest.fixture
def temp_models_config():
    """Create temporary YAML config file"""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "models.yaml"
        config_path.write_text(yaml.safe_dump({
            "models": [
                {
                    "id": "anthropic-claude-sonnet-4",
                    "name": "Claude Sonnet",
                    "provider": "anthropic",
                    "model_id": "claude-sonnet-4",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "description": "Claude Sonnet 4",
                    "is_default": True,
                    "api_key_env": "ANTHROPIC_API_KEY"
                }
            ]
        }))
        yield config_path


@pytest.fixture
def mock_config():
    """Mock Config object"""
    config = MagicMock(spec=Config)
    return config


@pytest.fixture
def model_service(temp_models_config, mock_config):
    """Create ModelService instance"""
    return ModelService(models_config_path=temp_models_config, config=mock_config)


class TestLoadFromConfig:
    """Test load_from_config method"""

    @pytest.mark.asyncio
    async def test_loads_models_from_yaml(self, model_service):
        """Should load models from YAML config"""
        with patch("app.core.config.get_anthropic_api_key", return_value="test-key"):
            models = await model_service.load_from_config()

        assert len(models) == 1
        assert models[0]["id"] == "anthropic-claude-sonnet-4"
        assert models[0]["configured"] is True

    @pytest.mark.asyncio
    async def test_handles_missing_config_file(self, mock_config):
        """Should handle missing config file gracefully"""
        service = ModelService(models_config_path=Path("/nonexistent.yaml"), config=mock_config)
        models = await service.load_from_config()
        
        assert models == []


class TestListModels:
    """Test list_models method"""

    @pytest.mark.asyncio
    async def test_returns_loaded_models(self, model_service):
        """Should return models from cache"""
        await model_service.load_from_config()
        models = await model_service.list_models()
        
        assert len(models) == 1


class TestCreateModel:
    """Test create_model method"""

    @pytest.mark.asyncio
    async def test_creates_new_model(self, model_service):
        """Should create new model configuration"""
        await model_service.load_from_config()
        
        new_model = {
            "name": "GPT-4",
            "provider": "openai",
            "model_id": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        result = await model_service.create_model(new_model)
        assert result["id"] == "openai-gpt-4"

    @pytest.mark.asyncio
    async def test_prevents_duplicate_ids(self, model_service):
        """Should prevent creating duplicate model IDs"""
        with patch("app.core.config.get_anthropic_api_key", return_value="test-key"):
            await model_service.load_from_config()

        duplicate_model = {
            "name": "Claude Sonnet",
            "provider": "anthropic",
            "model_id": "claude-sonnet-4"
        }

        with pytest.raises(ConflictError):
            await model_service.create_model(duplicate_model)


class TestDeleteModel:
    """Test delete_model method"""

    @pytest.mark.asyncio
    async def test_prevents_deleting_default_model(self, model_service):
        """Should prevent deleting default model"""
        with patch("app.core.config.get_anthropic_api_key", return_value="test-key"):
            await model_service.load_from_config()

        with pytest.raises(ValidationError):
            await model_service.delete_model("anthropic-claude-sonnet-4")


class TestSetDefaultModel:
    """Test set_default_model method"""

    @pytest.mark.asyncio
    async def test_sets_model_as_default(self, model_service):
        """Should set model as default"""
        with patch("app.core.config.get_anthropic_api_key", return_value="test-key"):
            await model_service.load_from_config()

        # Create second model with API key to make it configured
        new_model = {
            "name": "GPT-4",
            "provider": "openai",
            "model_id": "gpt-4",
            "api_key": "test-openai-key"
        }
        await model_service.create_model(new_model)

        # Set as default
        result = await model_service.set_default_model("openai-gpt-4")
        assert result["default_model"]["is_default"] is True
