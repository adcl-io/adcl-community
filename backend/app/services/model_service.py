# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Model Service - Manages AI model configurations.

Single responsibility: Model configuration management (CRUD + persistence).
Follows ADCL principle: All config in text files (configs/models.yaml).
"""

import asyncio
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.logging import get_service_logger

logger = get_service_logger("model")


class ModelService:
    """
    Manages AI model configurations stored in YAML config file.

    Responsibilities:
    - Load models from configs/models.yaml
    - Save models to config file
    - CRUD operations on models
    - Validate model configurations
    - Manage default model
    - Thread-safe access to models

    Note: API keys are never stored in config file (security).
    API keys come from environment variables only.
    """

    def __init__(self, models_config_path: Path, settings: Settings):
        """
        Initialize ModelService.

        Args:
            models_config_path: Path to models.yaml config file
            settings: Application settings for API key checking
        """
        self.models_config_path = models_config_path
        self.settings = settings
        self.models = []  # In-memory cache
        self.lock = asyncio.Lock()  # Thread safety
        logger.info(f"ModelService initialized with config: {models_config_path}")

    async def load_from_config(self) -> List[Dict[str, Any]]:
        """
        Load model configurations from YAML config file.

        Returns:
            List of model configurations

        Raises:
            ValidationError: If config file is invalid
        """
        async with self.lock:
            try:
                if not self.models_config_path.exists():
                    logger.warning(f"Models config not found at {self.models_config_path}")
                    self.models = []
                    return []

                with open(self.models_config_path, "r") as f:
                    config_data = yaml.safe_load(f)

                if not config_data or "models" not in config_data:
                    logger.warning("No models section in config file")
                    self.models = []
                    return []

                # Parse and validate models
                models = []
                model_ids = []

                for model_config in config_data["models"]:
                    # Check for duplicate IDs
                    if model_config["id"] in model_ids:
                        raise ValidationError(
                            f"Duplicate model ID: {model_config['id']}",
                            field="id"
                        )
                    model_ids.append(model_config["id"])

                    # Determine if model is configured based on environment
                    api_key_env = model_config.get("api_key_env", "")
                    if api_key_env == "ANTHROPIC_API_KEY":
                        configured = bool(self.settings.anthropic_api_key)
                    elif api_key_env == "OPENAI_API_KEY":
                        configured = bool(self.settings.openai_api_key)
                    else:
                        configured = False

                    model_data = {
                        "id": model_config["id"],
                        "name": model_config["name"],
                        "provider": model_config["provider"],
                        "model_id": model_config["model_id"],
                        "temperature": model_config.get("temperature", 0.7),
                        "max_tokens": model_config.get("max_tokens", 4096),
                        "description": model_config.get("description", ""),
                        "is_default": model_config.get("is_default", False),
                        "configured": configured,
                        "api_key": "***configured***" if configured else None,
                    }
                    models.append(model_data)

                # Validate exactly one default model
                default_models = [m for m in models if m.get("is_default")]
                if len(default_models) == 0 and len(models) > 0:
                    # Set first configured model as default
                    for m in models:
                        if m.get("configured"):
                            m["is_default"] = True
                            break
                elif len(default_models) > 1:
                    raise ValidationError(
                        f"Multiple default models found ({len(default_models)}). Only one allowed.",
                        field="is_default"
                    )

                self.models = models
                logger.info(f"Loaded {len(models)} models from config")
                return models

            except yaml.YAMLError as e:
                raise ValidationError(f"Invalid YAML in config file: {e}", field="config")
            except Exception as e:
                logger.error(f"Failed to load models from config: {e}")
                raise

    async def save_to_config(self, models: List[Dict[str, Any]]) -> bool:
        """
        Save model configurations to YAML config file.

        NOTE: This method does NOT acquire the lock. Caller must hold the lock.

        Args:
            models: List of model configurations

        Returns:
            True if saved successfully

        Raises:
            ValidationError: If save fails
        """
        try:
            # Load existing config to preserve other sections
            existing_config = {}
            if self.models_config_path.exists():
                with open(self.models_config_path, "r") as f:
                    existing_config = yaml.safe_load(f) or {}

            # Update models section
            config_models = []
            for model in models:
                # Determine api_key_env based on provider
                if model["provider"] == "anthropic":
                    api_key_env = "ANTHROPIC_API_KEY"
                elif model["provider"] == "openai":
                    api_key_env = "OPENAI_API_KEY"
                else:
                    api_key_env = f"{model['provider'].upper()}_API_KEY"

                config_model = {
                    "id": model["id"],
                    "name": model["name"],
                    "provider": model["provider"],
                    "model_id": model["model_id"],
                    "temperature": model.get("temperature", 0.7),
                    "max_tokens": model.get("max_tokens", 4096),
                    "description": model.get("description", ""),
                    "is_default": model.get("is_default", False),
                    "api_key_env": api_key_env,
                }
                config_models.append(config_model)

            existing_config["models"] = config_models

            # Write back to file
            with open(self.models_config_path, "w") as f:
                yaml.safe_dump(existing_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved {len(models)} models to config")
            return True

        except Exception as e:
            logger.error(f"Failed to save models to config: {e}")
            raise ValidationError(f"Failed to save models: {e}", field="config")

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all configured models.

        Returns:
            List of model configurations
        """
        # Lazy load models from config if not already loaded
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            return self.models.copy()

    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """
        Get a specific model configuration.

        Args:
            model_id: Model identifier

        Returns:
            Model configuration

        Raises:
            NotFoundError: If model not found
        """
        # Lazy load - use list_models which handles locking
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            for model in self.models:
                if model["id"] == model_id:
                    return model.copy()

            raise NotFoundError("Model", model_id)

    async def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new model configuration.

        Args:
            model_data: Model configuration data

        Returns:
            Created model configuration

        Raises:
            ValidationError: If model data invalid
            ConflictError: If model ID already exists
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Generate slug from provider and model_id
            slug = f"{model_data['provider']}-{model_data['model_id']}".replace("/", "-").replace("_", "-").lower()
            # Remove double dashes
            while "--" in slug:
                slug = slug.replace("--", "-")

            # Check for duplicate IDs
            if any(m["id"] == slug for m in self.models):
                raise ConflictError(
                    "Model",
                    slug,
                    details={"message": "Model with this ID already exists"}
                )

            model_data["id"] = slug
            model_data["configured"] = bool(model_data.get("api_key"))

            # API keys stored in environment only, not in config file
            if model_data.get("api_key"):
                model_data["api_key"] = "***configured***"

            self.models.append(model_data)

            # Persist to config file
            await self.save_to_config(self.models)

            logger.info(f"Created model: {slug}")
            return model_data.copy()

    async def update_model(self, model_id: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing model configuration.

        Args:
            model_id: Model identifier
            model_data: Updated model data

        Returns:
            Updated model configuration

        Raises:
            NotFoundError: If model not found
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            for i, m in enumerate(self.models):
                if m["id"] == model_id:
                    model_data["id"] = model_id
                    model_data["configured"] = bool(model_data.get("api_key")) or m.get("configured", False)

                    # Handle API key updates
                    if model_data.get("api_key"):
                        model_data["api_key"] = "***configured***"
                    else:
                        # Keep existing configuration status
                        model_data["api_key"] = m.get("api_key")

                    self.models[i] = model_data

                    # Persist to config file
                    await self.save_to_config(self.models)

                    logger.info(f"Updated model: {model_id}")
                    return model_data.copy()

            raise NotFoundError("Model", model_id)

    async def delete_model(self, model_id: str) -> Dict[str, str]:
        """
        Delete a model configuration.

        Args:
            model_id: Model identifier

        Returns:
            Deletion status

        Raises:
            NotFoundError: If model not found
            ValidationError: If trying to delete last model or default model
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Don't allow deleting the last model
            if len(self.models) == 1:
                raise ValidationError(
                    "Cannot delete the last model",
                    field="model_id"
                )

            for i, m in enumerate(self.models):
                if m["id"] == model_id:
                    # Don't allow deleting the default model
                    if m.get("is_default"):
                        raise ValidationError(
                            "Cannot delete default model. Set another model as default first.",
                            field="is_default"
                        )

                    self.models.pop(i)

                    # Persist to config file
                    await self.save_to_config(self.models)

                    logger.info(f"Deleted model: {model_id}")
                    return {"status": "deleted", "id": model_id}

            raise NotFoundError("Model", model_id)

    async def set_default_model(self, model_id: str) -> Dict[str, Any]:
        """
        Set a model as the default.

        Args:
            model_id: Model identifier to set as default

        Returns:
            Updated default model configuration

        Raises:
            NotFoundError: If model not found
            ValidationError: If model is not configured
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Find target model
            target_model = None
            for m in self.models:
                if m["id"] == model_id:
                    target_model = m
                    break

            if not target_model:
                raise NotFoundError("Model", model_id)

            if not target_model.get("configured"):
                raise ValidationError(
                    "Cannot set unconfigured model as default",
                    field="configured"
                )

            # Remove default from all models
            for m in self.models:
                m["is_default"] = False

            # Set new default
            target_model["is_default"] = True

            # Persist to config file
            await self.save_to_config(self.models)

            logger.info(f"Set default model: {model_id}")
            return {"status": "success", "default_model": target_model.copy()}
