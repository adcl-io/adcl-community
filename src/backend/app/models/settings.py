# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""User settings data models."""

from pydantic import BaseModel, field_validator
from typing import Any

# Allowed settings with type validation
ALLOWED_SETTINGS = {
    "theme": str,
    "log_level": str,
    "mcp_timeout": str,
    "auto_save": bool
}


class UserSettingsUpdate(BaseModel):
    key: str
    value: Any

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if v not in ALLOWED_SETTINGS:
            raise ValueError(f"Invalid setting key. Allowed: {list(ALLOWED_SETTINGS.keys())}")
        return v
