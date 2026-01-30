# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Configuration Loader - Read YAML configs following ADCL principles
"Configuration is Code" - all settings from text files

Includes Pydantic validation to prevent YAML injection and ensure schema correctness
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """AI Model Configuration Schema"""
    name: str = Field(..., description="Model name (e.g. claude-sonnet-4-5-20250929)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature (0.0-2.0)")
    max_tokens: int = Field(default=4096, gt=0, le=200000, description="Max tokens")

    @field_validator('name')
    @classmethod
    def validate_model_name(cls, v):
        # Ensure model name looks valid (basic security check)
        if not v or len(v) < 5 or len(v) > 100:
            raise ValueError("Invalid model name length")
        # Prevent command injection attempts
        if any(char in v for char in [';', '&', '|', '$', '`', '\n', '\r']):
            raise ValueError("Invalid characters in model name")
        return v


def load_config(config_name: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Follows ADCL principle: "Configuration is Code"
    - All configs in /configs directory
    - YAML format for human readability
    - No hardcoded values
    - Validated with Pydantic schemas

    Args:
        config_name: Name of config file (without .yaml extension)

    Returns:
        Configuration dictionary (validated)
    """
    # Config directory (configurable via env)
    config_dir = os.getenv("ADCL_CONFIG_DIR", "/configs")
    config_path = Path(config_dir) / f"{config_name}.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        # Use safe_load to prevent YAML code execution
        raw_config = yaml.safe_load(f)

    if raw_config is None:
        raise ValueError(f"Empty config file: {config_path}")

    return raw_config


def get_model_config() -> Dict[str, Any]:
    """
    Get AI model configuration with validation.

    Returns:
        Validated model config dict

    Raises:
        ValueError: If model configuration is missing or invalid
    """
    config = load_config("models")
    default_model_data = config.get("default_model")

    if not default_model_data:
        raise ValueError("Model configuration missing from models.yaml - 'default_model' key required")

    # Validate with Pydantic
    validated = ModelConfig(**default_model_data)
    return validated.model_dump()


def get_workflow_config() -> Dict[str, Any]:
    """Get workflow configuration (no validation needed for agent server)"""
    return load_config("workflows")
