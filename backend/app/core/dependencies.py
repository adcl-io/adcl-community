# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Dependency injection for ADCL backend.

Provides FastAPI dependencies for services and utilities.
Follows ADCL principle: Modular architecture with clear dependencies.
"""

from typing import Generator
from pathlib import Path
from fastapi import Depends, HTTPException, Request, status
from app.core.config import Config, get_config
from app.core.logging import get_logger

# Logger
logger = get_logger(__name__)


# Configuration dependency
def get_current_config() -> Config:
    """
    Get current application configuration.

    Returns:
        Config: Application configuration
    """
    return get_config()


# Service dependencies (Phase 3: Dependency Injection)

def get_agent_service(
    config: Config = Depends(get_current_config)
):
    """Get AgentService instance."""
    from app.services.agent_service import AgentService
    return AgentService(agents_dir=Path(config.agent_definitions_path))


def get_workflow_service(
    request: Request,
    config: Config = Depends(get_current_config)
):
    """Get WorkflowService instance."""
    from app.services.workflow_service import WorkflowService
    # Get workflow engine from app.state (initialized at startup)
    engine = request.app.state.workflow_engine
    return WorkflowService(
        workflows_dir=Path(config.workflows_path),
        workflow_engine=engine
    )


def get_team_service(
    config: Config = Depends(get_current_config)
):
    """Get TeamService instance."""
    from app.services.team_service import TeamService
    return TeamService(teams_dir=Path(config.agent_teams_path))


def get_execution_service(
    config: Config = Depends(get_current_config)
):
    """Get ExecutionService instance."""
    from app.services.execution_service import ExecutionService
    return ExecutionService(executions_dir=Path(config.volumes_path) / "executions")


def get_model_service(
    config: Config = Depends(get_current_config)
):
    """Get ModelService instance."""
    from app.services.model_service import ModelService
    # Note: This creates a new instance per request
    # For production, consider singleton pattern with async initialization
    service = ModelService(
        models_config_path=Path(config.models_config_path),
        config=config
    )
    return service


def get_mcp_service(request: Request):
    """Get MCPService instance with access to global registry."""
    from app.services.mcp_service import MCPService
    # Get the global registry from app.state (initialized at startup)
    # This gives MCPService access to the servers registered in main.py
    global_registry = getattr(request.app.state, "mcp_registry", None)
    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    return MCPService(mcp_manager=mcp_manager, global_registry=global_registry)


def get_docker_service():
    """Get DockerService instance."""
    from app.services.docker_service import DockerService
    return DockerService()


def get_agent_runtime(request: Request):
    """Get AgentRuntime instance."""
    # Get agent_runtime from app.state (initialized at startup)
    return request.app.state.agent_runtime


def get_team_runtime(request: Request):
    """Get TeamRuntime instance."""
    # Get team_runtime from app.state (initialized at startup)
    return request.app.state.team_runtime


# Database session dependency (if needed in future)
# def get_db() -> Generator:
#     """Get database session."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# Authentication dependency (placeholder for future)
def get_current_user(
    # auth_token: str = Depends(oauth2_scheme)
) -> dict:
    """
    Get current authenticated user.

    Note: Authentication not implemented yet.
    Returns mock user for now.

    Returns:
        dict: User information
    """
    # TODO: Implement actual authentication
    return {
        "user_id": "system",
        "username": "system",
        "roles": ["admin"]
    }


# Request ID for tracing
def get_request_id() -> str:
    """
    Get or generate request ID for tracing.

    Returns:
        str: Request ID
    """
    import uuid
    return str(uuid.uuid4())


# Pagination dependency
class PaginationParams:
    """Pagination parameters for list endpoints."""

    def __init__(self, skip: int = 0, limit: int = 100):
        """
        Initialize pagination parameters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
        """
        self.skip = max(0, skip)
        self.limit = min(1000, max(1, limit))  # Cap at 1000


def get_pagination_params(
    skip: int = 0,
    limit: int = 100
) -> PaginationParams:
    """
    Get pagination parameters from query string.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        PaginationParams: Pagination parameters
    """
    return PaginationParams(skip=skip, limit=limit)
