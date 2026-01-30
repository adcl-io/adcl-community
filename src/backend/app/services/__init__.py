# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Service layer for ADCL backend.

This package contains business logic services:
- agent_service: Agent lifecycle management
- workflow_service: Workflow orchestration
- team_service: Team coordination
- execution_service: Execution tracking and state management
- model_service: Model configuration management
- mcp_service: MCP server registry management
- docker_service: Docker container lifecycle management

Each service follows single responsibility principle and is independently testable.
Services communicate via dependency injection, not direct imports.
"""

__all__ = []

# Services will be added in Phase 2
# from app.services.agent_service import AgentService
# from app.services.workflow_service import WorkflowService
# from app.services.team_service import TeamService
# from app.services.execution_service import ExecutionService
# from app.services.model_service import ModelService
# from app.services.mcp_service import MCPService
# from app.services.docker_service import DockerService
