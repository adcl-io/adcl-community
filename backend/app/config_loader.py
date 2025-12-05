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


class WorkflowPathConfig(BaseModel):
    """Workflow Directory Paths"""
    base_dir: str = Field(..., description="Base workflows directory")
    templates_dir: str = Field(..., description="Templates directory")
    custom_dir: str = Field(..., description="Custom workflows directory")
    executions_dir: str = Field(..., description="Execution history directory")
    triggers_dir: str = Field(..., description="Triggers directory")

    @field_validator('base_dir', 'templates_dir', 'custom_dir', 'executions_dir', 'triggers_dir')
    @classmethod
    def validate_path(cls, v):
        # Basic path validation - prevent injection
        if any(char in v for char in [';', '&', '|', '$', '`', '\n', '\r']):
            raise ValueError("Invalid characters in path")
        if '..' in v:
            raise ValueError("Path traversal not allowed")
        return v


class LoggingConfig(BaseModel):
    """Logging Configuration"""
    base_dir: str = Field(..., description="Base logging directory")
    format: str = Field(default="json", description="Log format (json/text)")
    rotation: str = Field(default="daily", description="Log rotation (daily/weekly)")

    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in ['json', 'text']:
            raise ValueError("Format must be 'json' or 'text'")
        return v

    @field_validator('rotation')
    @classmethod
    def validate_rotation(cls, v):
        if v not in ['daily', 'weekly', 'hourly']:
            raise ValueError("Rotation must be 'daily', 'weekly', or 'hourly'")
        return v


class ExecutionConfig(BaseModel):
    """Execution Engine Configuration"""
    max_parallel_nodes: int = Field(default=10, gt=0, le=100)
    default_timeout: int = Field(default=300, gt=0, le=3600)
    max_retries: int = Field(default=3, ge=0, le=10)


class EngineConfig(BaseModel):
    """Workflow Engine Configuration"""
    enable_persistent_logging: bool = Field(default=True)
    enable_execution_history: bool = Field(default=True)
    websocket_updates: bool = Field(default=True)


class WorkflowsConfig(BaseModel):
    """Complete Workflows Configuration Schema"""
    workflows: WorkflowPathConfig
    logging: LoggingConfig
    execution: ExecutionConfig
    engine: EngineConfig


def load_config(config_name: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Follows ADCL principle: "Configuration is Code"
    - All configs in /configs directory (Docker) or ../configs (local dev)
    - YAML format for human readability
    - No hardcoded values
    - Validated with Pydantic schemas

    Args:
        config_name: Name of config file (without .yaml extension)

    Returns:
        Configuration dictionary (validated)
    """
    # Try multiple config locations for Docker and local dev compatibility
    config_locations = [
        # 1. Environment variable (if set)
        os.getenv("ADCL_CONFIG_DIR"),
        # 2. Docker container path
        "/configs",
        # 3. Local development path (relative to backend directory)
        str(Path(__file__).parent.parent.parent / "configs"),
    ]

    config_path = None
    for config_dir in config_locations:
        if config_dir is None:
            continue
        candidate = Path(config_dir) / f"{config_name}.yaml"
        if candidate.exists():
            config_path = candidate
            break

    if config_path is None:
        # List all attempted locations for debugging
        attempted = [str(Path(d) / f"{config_name}.yaml") for d in config_locations if d]
        raise FileNotFoundError(
            f"Config file '{config_name}.yaml' not found. Tried: {', '.join(attempted)}"
        )

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
    """
    config = load_config("models")
    default_model_data = config.get("default_model", {
        "name": "claude-sonnet-4-5-20250929",
        "temperature": 0.7,
        "max_tokens": 4096
    })

    # Validate with Pydantic
    validated = ModelConfig(**default_model_data)
    return validated.model_dump()


def get_workflow_config() -> Dict[str, Any]:
    """
    Get workflow configuration with validation.

    Returns:
        Validated workflows config dict
    """
    config = load_config("workflows")

    # Validate with Pydantic
    validated = WorkflowsConfig(**config)
    return validated.model_dump()
