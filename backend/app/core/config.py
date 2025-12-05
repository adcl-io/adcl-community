# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Configuration management for ADCL backend.

Loads configuration from environment variables and config files.
Follows ADCL principle: Configuration is Code.
"""

import os
from pathlib import Path
from typing import Optional

try:
    # pydantic v2
    from pydantic_settings import BaseSettings
except ImportError:
    # pydantic v1 fallback
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment and config files."""

    # Application
    app_name: str = "ADCL Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = ""

    # CORS
    cors_origins: list = ["*"]
    cors_credentials: bool = True
    cors_methods: list = ["*"]
    cors_headers: list = ["*"]

    # Directories (ADCL sacred structure)
    # __file__ is /app/app/core/config.py -> parent.parent.parent = /app
    base_dir: Path = Path(__file__).parent.parent.parent
    agent_definitions_dir: Path = base_dir / "agent-definitions"
    agent_teams_dir: Path = base_dir / "agent-teams"
    workflows_dir: Path = base_dir / "workflows"
    # Configs mounted at /configs in Docker - hardcode it, don't use env var
    # (ADCL_CONFIG_DIR is used by other components for user-specific configs)
    configs_dir: Path = Path("/configs")
    logs_dir: Path = base_dir / "logs"
    volumes_dir: Path = base_dir / "volumes"
    packages_dir: Path = base_dir / "packages"

    # API Keys (from environment)
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Model Configuration
    models_config_path: Path = configs_dir / "models.yaml"
    pricing_config_path: Path = configs_dir / "pricing.json"

    # Execution
    max_execution_time: int = 600  # seconds
    max_concurrent_executions: int = 10

    # Docker
    docker_enabled: bool = os.getenv("DOCKER_ENABLED", "True").lower() == "true"
    docker_network: str = "adcl-network"

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "json"  # json or text

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings: Application configuration
    """
    return settings
