# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for TeamService

Tests all CRUD operations and validation for multi-agent team management.
"""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.team_service import TeamService
from app.core.errors import NotFoundError, ValidationError


@pytest.fixture
def temp_teams_dir():
    """Create temporary directory for test teams"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def team_service(temp_teams_dir):
    """Create TeamService instance with temp directory"""
    return TeamService(teams_dir=temp_teams_dir)


@pytest.fixture
def sample_team_data():
    """Sample team definition"""
    return {
        "name": "Security Team",
        "description": "A security testing team",
        "version": "1.0.0",
        "available_mcps": ["nmap", "gobuster"],
        "agents": [
            {
                "agent_id": "scanner",
                "role": "Network Scanner",
                "responsibilities": ["Port scanning", "Service enumeration"]
            }
        ],
        "coordination": {
            "mode": "sequential",
            "share_context": True
        }
    }


class TestTeamServiceInit:
    """Test TeamService initialization"""

    def test_creates_directory_if_not_exists(self, temp_teams_dir):
        """Should create teams directory if it doesn't exist"""
        new_dir = temp_teams_dir / "new_teams"
        assert not new_dir.exists()
        
        service = TeamService(teams_dir=new_dir)
        assert new_dir.exists()


class TestListTeams:
    """Test list_teams method"""

    @pytest.mark.asyncio
    async def test_empty_directory_returns_empty_list(self, team_service):
        """Should return empty list when no teams exist"""
        teams = await team_service.list_teams()
        assert teams == []

    @pytest.mark.asyncio
    async def test_lists_all_teams(self, team_service, temp_teams_dir, sample_team_data):
        """Should list all team files in directory"""
        (temp_teams_dir / "team1.json").write_text(json.dumps({**sample_team_data, "name": "Team 1"}))
        (temp_teams_dir / "team2.json").write_text(json.dumps({**sample_team_data, "name": "Team 2"}))
        
        teams = await team_service.list_teams()
        assert len(teams) == 2

    @pytest.mark.asyncio
    async def test_skips_invalid_json_files(self, team_service, temp_teams_dir):
        """Should skip files with invalid JSON"""
        (temp_teams_dir / "invalid.json").write_text("not valid json")
        (temp_teams_dir / "valid.json").write_text(json.dumps({"name": "Valid"}))
        
        teams = await team_service.list_teams()
        assert len(teams) == 1


class TestGetTeam:
    """Test get_team method"""

    @pytest.mark.asyncio
    async def test_get_existing_team(self, team_service, temp_teams_dir, sample_team_data):
        """Should retrieve existing team by ID"""
        (temp_teams_dir / "security-team.json").write_text(json.dumps(sample_team_data))
        
        team = await team_service.get_team("security-team")
        assert team["name"] == "Security Team"

    @pytest.mark.asyncio
    async def test_get_nonexistent_team_raises_error(self, team_service):
        """Should raise NotFoundError for non-existent team"""
        with pytest.raises(NotFoundError):
            await team_service.get_team("nonexistent")


class TestCreateTeam:
    """Test create_team method"""

    @pytest.mark.asyncio
    async def test_create_team_with_name(self, team_service, sample_team_data):
        """Should create team with slugified ID from name"""
        result = await team_service.create_team(sample_team_data)
        
        assert result["id"] == "security-team"
        assert result["name"] == "Security Team"

    @pytest.mark.asyncio
    async def test_create_team_without_name_raises_error(self, team_service):
        """Should raise ValidationError when name is missing"""
        with pytest.raises(ValidationError) as exc_info:
            await team_service.create_team({})
        assert "name" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_team_without_mcps_raises_error(self, team_service):
        """Should raise ValidationError when available_mcps is missing"""
        with pytest.raises(ValidationError):
            await team_service.create_team({"name": "Test"})

    @pytest.mark.asyncio
    async def test_create_team_without_agents_raises_error(self, team_service):
        """Should raise ValidationError when agents list is empty"""
        with pytest.raises(ValidationError):
            await team_service.create_team({
                "name": "Test",
                "available_mcps": ["nmap"],
                "agents": []
            })

    @pytest.mark.asyncio
    async def test_create_duplicate_team_adds_suffix(self, team_service, sample_team_data):
        """Should add numeric suffix for duplicate team names"""
        await team_service.create_team(sample_team_data)
        result = await team_service.create_team(sample_team_data)
        
        assert result["id"] == "security-team-1"


class TestUpdateTeam:
    """Test update_team method"""

    @pytest.mark.asyncio
    async def test_update_existing_team(self, team_service, temp_teams_dir, sample_team_data):
        """Should update existing team"""
        (temp_teams_dir / "security-team.json").write_text(json.dumps(sample_team_data))
        
        updated_data = {**sample_team_data, "description": "Updated"}
        result = await team_service.update_team("security-team", updated_data)
        
        assert result["description"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_team_raises_error(self, team_service, sample_team_data):
        """Should raise NotFoundError for non-existent team"""
        with pytest.raises(NotFoundError):
            await team_service.update_team("nonexistent", sample_team_data)


class TestDeleteTeam:
    """Test delete_team method"""

    @pytest.mark.asyncio
    async def test_delete_existing_team(self, team_service, temp_teams_dir, sample_team_data):
        """Should delete existing team file"""
        file_path = temp_teams_dir / "security-team.json"
        file_path.write_text(json.dumps(sample_team_data))
        
        result = await team_service.delete_team("security-team")
        
        assert result["status"] == "deleted"
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_team_raises_error(self, team_service):
        """Should raise NotFoundError for non-existent team"""
        with pytest.raises(NotFoundError):
            await team_service.delete_team("nonexistent")


class TestExportTeam:
    """Test export_team method"""

    @pytest.mark.asyncio
    async def test_export_existing_team(self, team_service, temp_teams_dir, sample_team_data):
        """Should export team definition"""
        (temp_teams_dir / "security-team.json").write_text(json.dumps(sample_team_data))
        
        result = await team_service.export_team("security-team")
        assert result["name"] == "Security Team"
        assert "id" not in result  # ID should not be in exported data

    @pytest.mark.asyncio
    async def test_export_nonexistent_team_raises_error(self, team_service):
        """Should raise NotFoundError for non-existent team"""
        with pytest.raises(NotFoundError):
            await team_service.export_team("nonexistent")
