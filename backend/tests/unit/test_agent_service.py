# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for AgentService

Tests all CRUD operations and edge cases for agent management.
"""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.agent_service import AgentService
from app.core.errors import NotFoundError, ValidationError


@pytest.fixture
def temp_agents_dir():
    """Create temporary directory for test agents"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent_service(temp_agents_dir):
    """Create AgentService instance with temp directory"""
    return AgentService(agents_dir=temp_agents_dir)


@pytest.fixture
def sample_agent_data():
    """Sample agent definition"""
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "version": "1.0.0",
        "available_mcps": ["nmap", "gobuster"],
        "system_prompt": "You are a test agent",
    }


class TestAgentServiceInit:
    """Test AgentService initialization"""

    def test_creates_directory_if_not_exists(self, temp_agents_dir):
        """Should create agents directory if it doesn't exist"""
        new_dir = temp_agents_dir / "new_agents"
        assert not new_dir.exists()
        
        service = AgentService(agents_dir=new_dir)
        assert new_dir.exists()

    def test_uses_existing_directory(self, temp_agents_dir):
        """Should use existing directory without error"""
        service = AgentService(agents_dir=temp_agents_dir)
        assert service.agents_dir == temp_agents_dir


class TestListAgents:
    """Test list_agents method"""

    @pytest.mark.asyncio
    async def test_empty_directory_returns_empty_list(self, agent_service):
        """Should return empty list when no agents exist"""
        agents = await agent_service.list_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_lists_all_agents(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should list all agent files in directory"""
        # Create test agents
        (temp_agents_dir / "agent1.json").write_text(json.dumps({**sample_agent_data, "name": "Agent 1"}))
        (temp_agents_dir / "agent2.json").write_text(json.dumps({**sample_agent_data, "name": "Agent 2"}))
        
        agents = await agent_service.list_agents()
        assert len(agents) == 2
        assert any(a["name"] == "Agent 1" for a in agents)
        assert any(a["name"] == "Agent 2" for a in agents)

    @pytest.mark.asyncio
    async def test_adds_id_from_filename(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should add 'id' field from filename if not present"""
        (temp_agents_dir / "test-agent.json").write_text(json.dumps(sample_agent_data))
        
        agents = await agent_service.list_agents()
        assert agents[0]["id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_skips_invalid_json_files(self, agent_service, temp_agents_dir):
        """Should skip files with invalid JSON"""
        (temp_agents_dir / "invalid.json").write_text("not valid json {")
        (temp_agents_dir / "valid.json").write_text(json.dumps({"name": "Valid"}))
        
        agents = await agent_service.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "Valid"


class TestGetAgent:
    """Test get_agent method"""

    @pytest.mark.asyncio
    async def test_get_existing_agent(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should retrieve existing agent by ID"""
        (temp_agents_dir / "test-agent.json").write_text(json.dumps(sample_agent_data))
        
        agent = await agent_service.get_agent("test-agent")
        assert agent["name"] == "Test Agent"
        assert agent["id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent_raises_error(self, agent_service):
        """Should raise NotFoundError for non-existent agent"""
        with pytest.raises(NotFoundError) as exc_info:
            await agent_service.get_agent("nonexistent")
        
        assert "Agent" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)


class TestCreateAgent:
    """Test create_agent method"""

    @pytest.mark.asyncio
    async def test_create_agent_with_name(self, agent_service, sample_agent_data):
        """Should create agent with slugified ID from name"""
        result = await agent_service.create_agent(sample_agent_data)
        
        assert result["id"] == "test-agent"
        assert result["name"] == "Test Agent"
        assert "file" in result

    @pytest.mark.asyncio
    async def test_create_agent_without_name_raises_error(self, agent_service):
        """Should raise ValidationError when name is missing"""
        with pytest.raises(ValidationError) as exc_info:
            await agent_service.create_agent({})
        
        assert "name" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_duplicate_agent_adds_suffix(self, agent_service, sample_agent_data):
        """Should add numeric suffix for duplicate agent names"""
        # Create first agent
        await agent_service.create_agent(sample_agent_data)
        
        # Create duplicate
        result = await agent_service.create_agent(sample_agent_data)
        assert result["id"] == "test-agent-1"

    @pytest.mark.asyncio
    async def test_create_multiple_duplicates(self, agent_service, sample_agent_data):
        """Should handle multiple duplicates with incrementing suffixes"""
        await agent_service.create_agent(sample_agent_data)
        await agent_service.create_agent(sample_agent_data)
        result = await agent_service.create_agent(sample_agent_data)
        
        assert result["id"] == "test-agent-2"

    @pytest.mark.asyncio
    async def test_slugifies_special_characters(self, agent_service):
        """Should remove special characters from ID"""
        agent_data = {
            "name": "Test@Agent#123!",
            "available_mcps": []
        }
        result = await agent_service.create_agent(agent_data)
        assert result["id"] == "testagent123"

    @pytest.mark.asyncio
    async def test_persists_to_disk(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should persist agent data to JSON file"""
        result = await agent_service.create_agent(sample_agent_data)
        
        file_path = temp_agents_dir / f"{result['id']}.json"
        assert file_path.exists()
        
        saved_data = json.loads(file_path.read_text())
        assert saved_data["name"] == "Test Agent"


class TestUpdateAgent:
    """Test update_agent method"""

    @pytest.mark.asyncio
    async def test_update_existing_agent(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should update existing agent"""
        (temp_agents_dir / "test-agent.json").write_text(json.dumps(sample_agent_data))
        
        updated_data = {**sample_agent_data, "description": "Updated description"}
        result = await agent_service.update_agent("test-agent", updated_data)
        
        assert result["description"] == "Updated description"
        assert result["id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_update_nonexistent_agent_raises_error(self, agent_service, sample_agent_data):
        """Should raise NotFoundError for non-existent agent"""
        with pytest.raises(NotFoundError):
            await agent_service.update_agent("nonexistent", sample_agent_data)

    @pytest.mark.asyncio
    async def test_update_preserves_id(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should preserve agent ID even if changed in data"""
        (temp_agents_dir / "test-agent.json").write_text(json.dumps(sample_agent_data))
        
        updated_data = {**sample_agent_data, "id": "different-id"}
        result = await agent_service.update_agent("test-agent", updated_data)
        
        assert result["id"] == "test-agent"


class TestDeleteAgent:
    """Test delete_agent method"""

    @pytest.mark.asyncio
    async def test_delete_existing_agent(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should delete existing agent file"""
        file_path = temp_agents_dir / "test-agent.json"
        file_path.write_text(json.dumps(sample_agent_data))
        assert file_path.exists()
        
        result = await agent_service.delete_agent("test-agent")
        
        assert result["status"] == "deleted"
        assert result["id"] == "test-agent"
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_agent_raises_error(self, agent_service):
        """Should raise NotFoundError for non-existent agent"""
        with pytest.raises(NotFoundError):
            await agent_service.delete_agent("nonexistent")


class TestExportAgent:
    """Test export_agent method"""

    @pytest.mark.asyncio
    async def test_export_existing_agent(self, agent_service, temp_agents_dir, sample_agent_data):
        """Should export agent definition"""
        (temp_agents_dir / "test-agent.json").write_text(json.dumps(sample_agent_data))
        
        result = await agent_service.export_agent("test-agent")
        assert result["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_export_nonexistent_agent_raises_error(self, agent_service):
        """Should raise NotFoundError for non-existent agent"""
        with pytest.raises(NotFoundError):
            await agent_service.export_agent("nonexistent")


class TestSlugifyAgentId:
    """Test _slugify_agent_id method"""

    def test_lowercase_conversion(self, agent_service):
        """Should convert to lowercase"""
        assert agent_service._slugify_agent_id("UPPERCASE") == "uppercase"

    def test_space_replacement(self, agent_service):
        """Should replace spaces with hyphens"""
        assert agent_service._slugify_agent_id("Test Agent Name") == "test-agent-name"

    def test_underscore_replacement(self, agent_service):
        """Should replace underscores with hyphens"""
        assert agent_service._slugify_agent_id("test_agent_name") == "test-agent-name"

    def test_special_character_removal(self, agent_service):
        """Should remove special characters"""
        assert agent_service._slugify_agent_id("test@agent#123!") == "testagent123"

    def test_mixed_transformations(self, agent_service):
        """Should handle multiple transformations"""
        assert agent_service._slugify_agent_id("My_Test Agent@2024!") == "my-test-agent2024"
