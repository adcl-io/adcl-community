# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Team Service - Manages multi-agent team definitions and coordination.

Single responsibility: Team CRUD operations on disk.
Follows ADCL principle: Do one thing well.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_service_logger

logger = get_service_logger("team")


class TeamService:
    """
    Manages multi-agent team definitions stored as JSON files.

    Responsibilities:
    - Load teams from disk
    - Create new teams
    - Update existing teams
    - Delete teams
    - Export team definitions
    - Validate team configurations
    """

    def __init__(self, teams_dir: Path):
        """
        Initialize TeamService.

        Args:
            teams_dir: Directory containing team JSON files
        """
        self.teams_dir = teams_dir
        self.teams_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TeamService initialized with directory: {teams_dir}")

    async def list_teams(self) -> List[Dict[str, Any]]:
        """
        List all team definitions from disk.

        Returns:
            List of team definitions with metadata

        Example:
            >>> service = TeamService(Path("agent-teams"))
            >>> teams = await service.list_teams()
            >>> len(teams)
            3
        """
        teams = []

        for file_path in self.teams_dir.glob("*.json"):
            try:
                team = self._load_team_from_file(file_path)
                teams.append(team)
            except Exception as e:
                logger.error(f"Failed to load team from {file_path}: {e}")

        logger.info(f"Loaded {len(teams)} teams from disk")
        return teams

    async def get_team(self, team_id: str) -> Dict[str, Any]:
        """
        Get a specific team definition.

        Args:
            team_id: Team identifier

        Returns:
            Team definition

        Raises:
            NotFoundError: If team not found
        """
        self._validate_team_id(team_id)
        file_path = self.teams_dir / f"{team_id}.json"

        if not file_path.exists():
            raise NotFoundError("Team", team_id)

        team = self._load_team_from_file(file_path)
        logger.info(f"Retrieved team: {team_id}")
        return team

    async def create_team(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new team definition.

        Args:
            team_data: Team definition data

        Returns:
            Created team with assigned ID

        Raises:
            ValidationError: If team data invalid
        """
        # Validate required fields
        if "name" not in team_data:
            raise ValidationError("Team name is required", field="name")

        if "available_mcps" not in team_data:
            raise ValidationError(
                "Team must specify available MCPs", field="available_mcps"
            )

        if "agents" not in team_data or len(team_data["agents"]) == 0:
            raise ValidationError(
                "Team must have at least one agent", field="agents"
            )

        # Generate ID from name
        team_id = self._slugify_team_id(team_data["name"])

        # Check if team already exists
        file_path = self.teams_dir / f"{team_id}.json"
        if file_path.exists():
            # Add number suffix to make unique
            counter = 1
            while (self.teams_dir / f"{team_id}-{counter}.json").exists():
                counter += 1
            team_id = f"{team_id}-{counter}"
            file_path = self.teams_dir / f"{team_id}.json"

        # Set ID in team data
        team_data["id"] = team_id

        # Save to disk
        self._save_team_to_file(team_id, team_data)

        # Add file metadata
        team_data["file"] = file_path.name

        logger.info(f"Created team: {team_id}")
        return team_data

    async def update_team(
        self, team_id: str, team_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing team definition.

        Args:
            team_id: Team identifier
            team_data: Updated team data

        Returns:
            Updated team definition

        Raises:
            NotFoundError: If team not found
        """
        self._validate_team_id(team_id)
        file_path = self.teams_dir / f"{team_id}.json"

        if not file_path.exists():
            raise NotFoundError("Team", team_id)

        # Ensure ID stays the same
        team_data["id"] = team_id

        # Save to disk
        self._save_team_to_file(team_id, team_data)

        # Add file metadata
        team_data["file"] = file_path.name

        logger.info(f"Updated team: {team_id}")
        return team_data

    async def delete_team(self, team_id: str) -> Dict[str, str]:
        """
        Delete a team definition.

        Args:
            team_id: Team identifier

        Returns:
            Deletion status

        Raises:
            NotFoundError: If team not found
        """
        self._validate_team_id(team_id)
        file_path = self.teams_dir / f"{team_id}.json"

        if not file_path.exists():
            raise NotFoundError("Team", team_id)

        file_path.unlink()

        logger.info(f"Deleted team: {team_id}")
        return {"status": "deleted", "id": team_id}

    async def export_team(self, team_id: str) -> Dict[str, Any]:
        """
        Export a team definition for sharing.

        Args:
            team_id: Team identifier

        Returns:
            Team definition without metadata

        Raises:
            NotFoundError: If team not found
        """
        self._validate_team_id(team_id)
        file_path = self.teams_dir / f"{team_id}.json"

        if not file_path.exists():
            raise NotFoundError("Team", team_id)

        # Load raw data (without id/file metadata)
        team_data = json.loads(file_path.read_text())

        logger.info(f"Exported team: {team_id}")
        return team_data

    # Private helper methods

    def _validate_team_id(self, team_id: str) -> None:
        """
        Validate team ID to prevent path traversal attacks.

        Args:
            team_id: Team identifier to validate

        Raises:
            ValidationError: If team_id contains path separators or is invalid
        """
        if not team_id:
            raise ValidationError("Team ID cannot be empty", field="team_id")

        # Check for path traversal attempts
        if "/" in team_id or "\\" in team_id or ".." in team_id:
            raise ValidationError(
                "Team ID cannot contain path separators or '..'",
                field="team_id"
            )

        # Ensure the resolved path is within teams_dir
        file_path = (self.teams_dir / f"{team_id}.json").resolve()
        try:
            file_path.relative_to(self.teams_dir.resolve())
        except ValueError:
            raise ValidationError(
                "Invalid team ID: path traversal detected",
                field="team_id"
            )

    def _load_team_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a team from a JSON file.

        Args:
            file_path: Path to team JSON file

        Returns:
            Team definition

        Raises:
            JSONDecodeError: If file is not valid JSON
        """
        team_data = json.loads(file_path.read_text())

        # Use filename (without .json) as ID if not present
        if "id" not in team_data:
            team_data["id"] = file_path.stem

        # Add file metadata
        team_data["file"] = file_path.name

        return team_data

    def _save_team_to_file(
        self, team_id: str, team_data: Dict[str, Any]
    ) -> Path:
        """
        Save a team to a JSON file.

        Args:
            team_id: Team identifier
            team_data: Team definition data

        Returns:
            Path to saved file
        """
        file_path = self.teams_dir / f"{team_id}.json"

        # Remove metadata from saved data
        save_data = {
            k: v for k, v in team_data.items() if k not in ["id", "file"]
        }

        file_path.write_text(json.dumps(save_data, indent=2))
        return file_path

    def _slugify_team_id(self, name: str) -> str:
        """
        Generate a slug-style ID from team name.

        Args:
            name: Team name

        Returns:
            Slugified ID

        Example:
            >>> service._slugify_team_id("Security Team")
            "security-team"
        """
        # Convert to lowercase and replace spaces/underscores with hyphens
        team_id = name.lower().replace(" ", "-").replace("_", "-")

        # Remove special characters (keep only alphanumeric and hyphens)
        team_id = "".join(c for c in team_id if c.isalnum() or c == "-")

        return team_id
