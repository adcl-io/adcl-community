# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Custom exceptions for ADCL backend.

All exceptions inherit from ADCLError for consistent error handling.
"""

from typing import Optional, Any


class ADCLError(Exception):
    """Base exception for all ADCL errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict] = None
    ):
        """
        Initialize ADCL error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert error to dictionary for API response."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


class NotFoundError(ADCLError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str, details: Optional[dict] = None):
        """
        Initialize not found error.

        Args:
            resource: Type of resource (e.g., "Agent", "Workflow")
            identifier: Resource identifier
            details: Additional error details
        """
        message = f"{resource} not found: {identifier}"
        super().__init__(message, status_code=404, details=details)
        self.resource = resource
        self.identifier = identifier


class ValidationError(ADCLError):
    """Validation failed."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize validation error.

        Args:
            message: Validation error message
            field: Field that failed validation
            details: Additional error details
        """
        super().__init__(message, status_code=400, details=details)
        self.field = field


class ConfigurationError(ADCLError):
    """Configuration error."""

    def __init__(self, message: str, config_file: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize configuration error.

        Args:
            message: Configuration error message
            config_file: Configuration file path
            details: Additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.config_file = config_file


class ExecutionError(ADCLError):
    """Execution error."""

    def __init__(self, message: str, execution_id: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize execution error.

        Args:
            message: Execution error message
            execution_id: Execution identifier
            details: Additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.execution_id = execution_id


class DockerError(ADCLError):
    """Docker operation error."""

    def __init__(self, message: str, container_id: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize Docker error.

        Args:
            message: Docker error message
            container_id: Container identifier
            details: Additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.container_id = container_id


class MCPError(ADCLError):
    """MCP server error."""

    def __init__(self, message: str, server_id: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize MCP error.

        Args:
            message: MCP error message
            server_id: MCP server identifier
            details: Additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.server_id = server_id


class UnauthorizedError(ADCLError):
    """Unauthorized access."""

    def __init__(self, message: str = "Unauthorized", details: Optional[dict] = None):
        """
        Initialize unauthorized error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, status_code=401, details=details)


class ForbiddenError(ADCLError):
    """Forbidden access."""

    def __init__(self, message: str = "Forbidden", resource: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize forbidden error.

        Args:
            message: Error message
            resource: Resource being accessed
            details: Additional error details
        """
        super().__init__(message, status_code=403, details=details)
        self.resource = resource


class ConflictError(ADCLError):
    """Resource conflict."""

    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize conflict error.

        Args:
            message: Error message
            resource: Conflicting resource
            details: Additional error details
        """
        super().__init__(message, status_code=409, details=details)
        self.resource = resource


class ServiceUnavailableError(ADCLError):
    """Service unavailable."""

    def __init__(self, message: str, service: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize service unavailable error.

        Args:
            message: Error message
            service: Service that is unavailable
            details: Additional error details
        """
        super().__init__(message, status_code=503, details=details)
        self.service = service


# Error Message Utilities

def sanitize_error_for_user(error: Exception, include_type: bool = True) -> str:
    """
    Sanitize error messages for user display.
    Removes stack traces and sensitive information.

    Args:
        error: The exception to sanitize
        include_type: Whether to include exception type

    Returns:
        User-friendly error message without stack trace
    """
    error_msg = str(error).strip()

    # Remove common sensitive paths
    error_msg = error_msg.replace("/app/", "")
    error_msg = error_msg.replace("/configs/", "")

    # Limit message length
    if len(error_msg) > 500:
        error_msg = error_msg[:500] + "..."

    if include_type:
        return f"{error.__class__.__name__}: {error_msg}"

    return error_msg
