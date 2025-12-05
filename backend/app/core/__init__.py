# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Core utilities and shared modules for ADCL backend.

This package contains:
- config: Configuration management
- dependencies: Dependency injection
- errors: Custom exceptions
- logging: Structured logging
"""

from app.core.config import settings
from app.core.errors import ADCLError, NotFoundError, ValidationError
from app.core.logging import get_logger

__all__ = [
    "settings",
    "ADCLError",
    "NotFoundError",
    "ValidationError",
    "get_logger",
]
