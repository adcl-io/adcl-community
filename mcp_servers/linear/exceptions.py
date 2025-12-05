# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Linear MCP Custom Exceptions

Provides structured error handling for Linear MCP operations.
"""


class LinearMCPError(Exception):
    """Base exception for all Linear MCP errors."""
    pass


class LinearConfigError(LinearMCPError):
    """Configuration error (missing credentials, invalid config)."""
    pass


class LinearAPIError(LinearMCPError):
    """API communication error (network, HTTP errors)."""
    pass


class LinearAuthError(LinearMCPError):
    """Authentication/authorization error (OAuth failures)."""
    pass


class LinearValidationError(LinearMCPError):
    """Input validation error (invalid parameters)."""
    pass
