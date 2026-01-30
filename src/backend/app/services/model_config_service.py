# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""Model configuration management service."""

import asyncio
import yaml
from pathlib import Path
from typing import List, Dict, Any
from app.models.model import ModelsConfigFile
from app.core.config import get_config

config = get_config()

# Models database (loaded from configs/models.yaml)
models_db: List[Dict[str, Any]] = []
models_lock = asyncio.Lock()
MODELS_CONFIG_PATH = Path("/configs/models.yaml")


def load_models_from_config() -> List[Dict[str, Any]]:
    """
    Load model configurations from configs/models.yaml
    Following ADCL principle: All config in text files
    """
    try:
        if not MODELS_CONFIG_PATH.exists():
            print(f"  ⚠️  Models config not found at {MODELS_CONFIG_PATH}")
            return []

        with open(MODELS_CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data or "models" not in config_data:
            print("  ⚠️  No models section in config file")
            return []

        # Validate config structure with Pydantic
        try:
            validated_config = ModelsConfigFile(**config_data)
        except Exception as validation_error:
            print(f"  ❌ Config validation error in {MODELS_CONFIG_PATH}:")
            print(f"     {validation_error}")
            return []

        # Check for duplicate model IDs
        model_ids = [m.id for m in validated_config.models]
        if len(model_ids) != len(set(model_ids)):
            duplicates = [id for id in model_ids if model_ids.count(id) > 1]
            print(f"  ❌ Duplicate model IDs found in config: {set(duplicates)}")
            return []

        # Check for multiple default models
        default_count = sum(1 for m in validated_config.models if m.is_default)
        if default_count > 1:
            print(f"  ❌ Multiple default models found in config ({default_count}). Only one allowed.")
            return []

        models = []
        anthropic_key = config.get_anthropic_api_key()
        openai_key = config.get_openai_api_key()

        for model_config in validated_config.models:
            # Determine if model is configured based on environment variables
            api_key_env = model_config.api_key_env
            if api_key_env == "ANTHROPIC_API_KEY":
                configured = bool(anthropic_key)
            elif api_key_env == "OPENAI_API_KEY":
                configured = bool(openai_key)
            elif api_key_env == "OLLAMA_API_KEY":
                # Ollama doesn't require API key for local instances
                configured = True
            else:
                configured = False

            model_data = {
                "id": model_config.id,
                "name": model_config.name,
                "provider": model_config.provider,
                "model_id": model_config.model_id,
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_tokens,
                "description": model_config.description,
                "is_default": model_config.is_default,
                "configured": configured,
                "api_key": "***configured***" if configured else None,
            }
            models.append(model_data)

        print(f"  ✅ Loaded {len(models)} models from {MODELS_CONFIG_PATH}")

        # Ensure exactly one default model
        default_models = [m for m in models if m.get("is_default")]
        if len(default_models) == 0 and len(models) > 0:
            print("  ⚠️  No default model set, setting first configured model as default")
            for m in models:
                if m.get("configured"):
                    m["is_default"] = True
                    break
        elif len(default_models) > 1:
            print(f"  ⚠️  Multiple default models found, keeping only first one")
            for i, m in enumerate(models):
                if m.get("is_default") and i > 0:
                    m["is_default"] = False

        return models

    except yaml.YAMLError as e:
        print(f"  ❌ YAML parsing error in {MODELS_CONFIG_PATH}: {e}")
        return []
    except FileNotFoundError:
        print(f"  ❌ Config file not found: {MODELS_CONFIG_PATH}")
        return []
    except Exception as e:
        print(f"  ❌ Unexpected error loading models: {e}")
        return []


async def save_models_to_config(models: List[Dict[str, Any]]) -> bool:
    """
    Save model configurations to configs/models.yaml
    Following ADCL principle: All config persisted in text files
    """
    try:
        # Load existing config to preserve other sections
        existing_config = {}
        if MODELS_CONFIG_PATH.exists():
            with open(MODELS_CONFIG_PATH, "r") as f:
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
        with open(MODELS_CONFIG_PATH, "w") as f:
            yaml.safe_dump(existing_config, f, default_flow_style=False, sort_keys=False)

        print(f"  💾 Saved {len(models)} models to {MODELS_CONFIG_PATH}")
        return True

    except Exception as e:
        print(f"  ❌ Failed to save models to config: {e}")
        return False
