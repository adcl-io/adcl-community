# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Agent Service - Manages agent definitions and lifecycle.

Single responsibility: Agent CRUD operations on disk.
Follows ADCL principle: Do one thing well.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.logging import get_service_logger

logger = get_service_logger("agent")


class AgentService:
    """
    Manages agent definitions stored as JSON files.

    Responsibilities:
    - Load agents from disk
    - Create new agents
    - Update existing agents
    - Delete agents
    - Validate agent definitions
    """

    def __init__(self, agents_dir: Path):
        """
        Initialize AgentService.

        Args:
            agents_dir: Directory containing agent JSON files
        """
        self.agents_dir = agents_dir
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"AgentService initialized with directory: {agents_dir}")

    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all agent definitions from disk.

        Returns:
            List of agent definitions

        Example:
            >>> service = AgentService(Path("agent-definitions"))
            >>> agents = await service.list_agents()
            >>> len(agents)
            5
        """
        agents = []

        for file_path in self.agents_dir.glob("*.json"):
            try:
                agent = self._load_agent_from_file(file_path)
                agents.append(agent)
            except Exception as e:
                logger.error(f"Failed to load agent from {file_path}: {e}")

        logger.info(f"Loaded {len(agents)} agents from disk")
        return agents

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Get a specific agent definition.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent definition

        Raises:
            NotFoundError: If agent not found
        """
        self._validate_agent_id(agent_id)
        file_path = self.agents_dir / f"{agent_id}.json"

        if not file_path.exists():
            raise NotFoundError("Agent", agent_id)

        agent = self._load_agent_from_file(file_path)
        logger.info(f"Retrieved agent: {agent_id}")
        return agent

    async def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new agent definition.

        Args:
            agent_data: Agent definition data

        Returns:
            Created agent with assigned ID

        Raises:
            ValidationError: If agent data invalid
        """
        # Validate required fields
        if "name" not in agent_data:
            raise ValidationError("Agent name is required", field="name")

        # Generate ID from name if not provided
        agent_id = agent_data.get("id") or self._slugify_agent_id(
            agent_data["name"]
        )

        # Check if agent already exists
        file_path = self.agents_dir / f"{agent_id}.json"
        if file_path.exists():
            # Add number suffix to make unique
            counter = 1
            while (self.agents_dir / f"{agent_id}-{counter}.json").exists():
                counter += 1
            agent_id = f"{agent_id}-{counter}"
            file_path = self.agents_dir / f"{agent_id}.json"

        # Set ID in agent data
        agent_data["id"] = agent_id

        # Save to disk
        self._save_agent_to_file(agent_id, agent_data)

        # Add file metadata
        agent_data["file"] = file_path.name

        logger.info(f"Created agent: {agent_id}")
        return agent_data

    async def update_agent(
        self, agent_id: str, agent_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing agent definition.

        Args:
            agent_id: Agent identifier
            agent_data: Updated agent data

        Returns:
            Updated agent definition

        Raises:
            NotFoundError: If agent not found
        """
        self._validate_agent_id(agent_id)
        file_path = self.agents_dir / f"{agent_id}.json"

        if not file_path.exists():
            raise NotFoundError("Agent", agent_id)

        # Ensure ID stays the same
        agent_data["id"] = agent_id

        # Save to disk
        self._save_agent_to_file(agent_id, agent_data)

        # Add file metadata
        agent_data["file"] = file_path.name

        logger.info(f"Updated agent: {agent_id}")
        return agent_data

    async def delete_agent(self, agent_id: str) -> Dict[str, str]:
        """
        Delete an agent definition.

        Args:
            agent_id: Agent identifier

        Returns:
            Deletion status

        Raises:
            NotFoundError: If agent not found
        """
        self._validate_agent_id(agent_id)
        file_path = self.agents_dir / f"{agent_id}.json"

        if not file_path.exists():
            raise NotFoundError("Agent", agent_id)

        file_path.unlink()

        logger.info(f"Deleted agent: {agent_id}")
        return {"status": "deleted", "id": agent_id}

    async def export_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Export an agent definition (alias for get_agent).

        Args:
            agent_id: Agent identifier

        Returns:
            Agent definition

        Raises:
            NotFoundError: If agent not found
        """
        return await self.get_agent(agent_id)

    # Private helper methods

    def _validate_agent_id(self, agent_id: str) -> None:
        """
        Validate agent ID to prevent path traversal attacks.

        Args:
            agent_id: Agent identifier to validate

        Raises:
            ValidationError: If agent_id contains path separators or is invalid
        """
        if not agent_id:
            raise ValidationError("Agent ID cannot be empty", field="agent_id")

        # Check for path traversal attempts
        if "/" in agent_id or "\\" in agent_id or ".." in agent_id:
            raise ValidationError(
                "Agent ID cannot contain path separators or '..'",
                field="agent_id"
            )

        # Ensure the resolved path is within agents_dir
        file_path = (self.agents_dir / f"{agent_id}.json").resolve()
        try:
            file_path.relative_to(self.agents_dir.resolve())
        except ValueError:
            raise ValidationError(
                "Invalid agent ID: path traversal detected",
                field="agent_id"
            )

    def _load_agent_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load an agent from a JSON file.

        Args:
            file_path: Path to agent JSON file

        Returns:
            Agent definition

        Raises:
            JSONDecodeError: If file is not valid JSON
        """
        agent_data = json.loads(file_path.read_text())

        # Use filename (without .json) as ID if not present
        if "id" not in agent_data:
            agent_data["id"] = file_path.stem

        # Add file metadata
        agent_data["file"] = file_path.name

        return agent_data

    def _save_agent_to_file(
        self, agent_id: str, agent_data: Dict[str, Any]
    ) -> Path:
        """
        Save an agent to a JSON file.

        Args:
            agent_id: Agent identifier
            agent_data: Agent definition data

        Returns:
            Path to saved file
        """
        file_path = self.agents_dir / f"{agent_id}.json"

        # Remove file metadata from saved data
        save_data = {
            k: v for k, v in agent_data.items() if k not in ["file"]
        }

        file_path.write_text(json.dumps(save_data, indent=2))
        return file_path

    def _slugify_agent_id(self, name: str) -> str:
        """
        Generate a slug-style ID from agent name.

        Args:
            name: Agent name

        Returns:
            Slugified ID

        Example:
            >>> service._slugify_agent_id("My Agent Name")
            "my-agent-name"
        """
        # Convert to lowercase and replace spaces/underscores with hyphens
        agent_id = name.lower().replace(" ", "-").replace("_", "-")

        # Remove special characters (keep only alphanumeric and hyphens)
        agent_id = "".join(c for c in agent_id if c.isalnum() or c == "-")

        return agent_id
