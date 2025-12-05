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
from unittest.mock import MagicMock

from app.services.model_service import ModelService
from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.config import Settings


@pytest.fixture
def temp_models_config():
    """Create temporary YAML config file"""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "models.yaml"
        config_path.write_text(yaml.safe_dump({
            "models": [
                {
                    "id": "claude-sonnet",
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
def mock_settings():
    """Mock Settings object"""
    settings = MagicMock(spec=Settings)
    settings.anthropic_api_key = "test-key"
    settings.openai_api_key = None
    return settings


@pytest.fixture
def model_service(temp_models_config, mock_settings):
    """Create ModelService instance"""
    return ModelService(models_config_path=temp_models_config, settings=mock_settings)


class TestLoadFromConfig:
    """Test load_from_config method"""

    @pytest.mark.asyncio
    async def test_loads_models_from_yaml(self, model_service):
        """Should load models from YAML config"""
        models = await model_service.load_from_config()
        
        assert len(models) == 1
        assert models[0]["id"] == "claude-sonnet"
        assert models[0]["configured"] is True

    @pytest.mark.asyncio
    async def test_handles_missing_config_file(self, mock_settings):
        """Should handle missing config file gracefully"""
        service = ModelService(models_config_path=Path("/nonexistent.yaml"), settings=mock_settings)
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
        await model_service.load_from_config()
        
        with pytest.raises(ValidationError):
            await model_service.delete_model("claude-sonnet")


class TestSetDefaultModel:
    """Test set_default_model method"""

    @pytest.mark.asyncio
    async def test_sets_model_as_default(self, model_service):
        """Should set model as default"""
        await model_service.load_from_config()
        
        # Create second model
        new_model = {
            "name": "GPT-4",
            "provider": "openai",
            "model_id": "gpt-4",
            "configured": True
        }
        await model_service.create_model(new_model)
        
        # Set as default
        result = await model_service.set_default_model("openai-gpt-4")
        assert result["default_model"]["is_default"] is True
