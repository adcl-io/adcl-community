# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""LLM model configuration data models."""

from pydantic import BaseModel, field_validator
from typing import List, Optional
from app.core.config import get_config

config = get_config()


class Model(BaseModel):
    name: str
    provider: str
    model_id: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = config.get_llm_max_tokens()
    description: Optional[str] = ""
    is_default: bool = False


class ModelUpdate(BaseModel):
    name: str
    provider: str
    model_id: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = config.get_llm_max_tokens()
    description: Optional[str] = ""
    is_default: bool = False


class ModelConfigSchema(BaseModel):
    """Schema for validating individual model configs in models.yaml"""
    id: str
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    description: str = ""
    is_default: bool = False
    api_key_env: str = ""

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1 or v > 1000000:
            raise ValueError('max_tokens must be between 1 and 1000000')
        return v

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        # Only include providers actually supported in the codebase
        allowed = ['anthropic', 'openai', 'ollama']
        if v not in allowed:
            raise ValueError(f'provider must be one of: {", ".join(allowed)}')
        return v


class ModelsConfigFile(BaseModel):
    """Schema for validating the entire models.yaml file"""
    models: List[ModelConfigSchema]
