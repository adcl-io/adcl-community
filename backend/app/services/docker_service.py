# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Docker Service - Manages Docker-based resource lifecycle (MCP servers, triggers).

Single responsibility: Docker manager initialization and dependency injection.
Follows ADCL principle: Lazy loading, graceful degradation, clear error handling.
"""

from typing import Optional, Any

from app.core.errors import ServiceUnavailableError
from app.core.logging import get_service_logger

logger = get_service_logger("docker")


class DummyManager:
    """
    Dummy manager that raises errors when Docker is unavailable.
    Provides graceful degradation when Docker CLI is not accessible.
    """

    def __init__(self, resource_type: str):
        self.resource_type = resource_type

    def __getattr__(self, name: str) -> Any:
        raise ServiceUnavailableError(
            f"{self.resource_type.title()} Manager",
            details={
                "reason": "Docker CLI not accessible",
                "message": f"{self.resource_type} installation features are disabled",
            },
        )


class DockerService:
    """
    Manages Docker-based resource lifecycle (MCPs and triggers).

    Responsibilities:
    - Lazy initialization of Docker managers
    - Graceful degradation when Docker unavailable
    - Dependency injection for manager instances
    - Error handling for Docker operations

    This service wraps DockerManager instances and provides a clean
    interface for Docker-based operations across the application.
    """

    def __init__(self):
        """Initialize DockerService with lazy loading."""
        self._mcp_manager: Optional[Any] = None
        self._trigger_manager: Optional[Any] = None
        self._docker_available: Optional[bool] = None
        logger.info("DockerService initialized (lazy loading)")

    def _check_docker_available(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            True if Docker CLI is accessible

        Note: This is cached after first check.
        """
        if self._docker_available is not None:
            return self._docker_available

        try:
            # Try importing DockerManager to check availability
            from app.docker_manager import DockerManager

            # Try creating a test instance
            test_manager = DockerManager()
            self._docker_available = True
            logger.info("Docker CLI is available")
            return True
        except Exception as e:
            logger.warning(f"Docker CLI not available: {e}")
            self._docker_available = False
            return False

    def get_mcp_manager(self) -> Any:
        """
        Get or initialize MCP manager (lazy loading).

        Returns:
            DockerManager instance for MCPs (or DummyManager if Docker unavailable)

        Example:
            >>> service = DockerService()
            >>> manager = service.get_mcp_manager()
            >>> mcps = manager.list_installed()
        """
        if self._mcp_manager is not None:
            return self._mcp_manager

        # Check Docker availability
        if not self._check_docker_available():
            logger.warning("Docker unavailable - MCP features disabled")
            self._mcp_manager = DummyManager("mcp")
            return self._mcp_manager

        try:
            from app.docker_manager import DockerManager

            self._mcp_manager = DockerManager()
            logger.info("MCP Manager initialized successfully")
            return self._mcp_manager

        except Exception as e:
            logger.error(f"Failed to initialize MCP Manager: {e}")
            self._mcp_manager = DummyManager("mcp")
            return self._mcp_manager

    def get_trigger_manager(self) -> Any:
        """
        Get or initialize Trigger manager (lazy loading).

        Returns:
            DockerManager instance for triggers (or DummyManager if Docker unavailable)

        Example:
            >>> service = DockerService()
            >>> manager = service.get_trigger_manager()
            >>> triggers = manager.list_installed()
        """
        if self._trigger_manager is not None:
            return self._trigger_manager

        # Check Docker availability
        if not self._check_docker_available():
            logger.warning("Docker unavailable - Trigger features disabled")
            self._trigger_manager = DummyManager("trigger")
            return self._trigger_manager

        try:
            from app.docker_manager import DockerManager

            self._trigger_manager = DockerManager(resource_type="trigger")
            logger.info("Trigger Manager initialized successfully")
            return self._trigger_manager

        except Exception as e:
            logger.error(f"Failed to initialize Trigger Manager: {e}")
            self._trigger_manager = DummyManager("trigger")
            return self._trigger_manager

    def is_docker_available(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            True if Docker CLI is accessible
        """
        return self._check_docker_available()

    def reset_managers(self) -> None:
        """
        Reset manager instances (useful for testing or re-initialization).

        This forces re-initialization on next access.
        """
        self._mcp_manager = None
        self._trigger_manager = None
        self._docker_available = None
        logger.info("Docker managers reset")
