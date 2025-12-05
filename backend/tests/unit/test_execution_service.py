# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for ExecutionService

Tests execution persistence and history management.
"""

import pytest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.execution_service import ExecutionService
from app.core.errors import NotFoundError


@pytest.fixture
def temp_executions_dir():
    """Create temporary directory for test executions"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def execution_service(temp_executions_dir):
    """Create ExecutionService instance with temp directory"""
    return ExecutionService(executions_dir=temp_executions_dir)


@pytest.fixture
def sample_metadata():
    """Sample execution metadata"""
    return {
        "agent": "test-agent",
        "task": "Test task",
        "trigger": "manual"
    }


class TestExecutionServiceInit:
    """Test ExecutionService initialization"""

    def test_creates_directory_if_not_exists(self, temp_executions_dir):
        """Should create executions directory if it doesn't exist"""
        new_dir = temp_executions_dir / "new_executions"
        assert not new_dir.exists()
        
        service = ExecutionService(executions_dir=new_dir)
        assert new_dir.exists()


class TestCreateExecution:
    """Test create_execution method"""

    @pytest.mark.asyncio
    async def test_creates_execution_directory(self, execution_service, temp_executions_dir, sample_metadata):
        """Should create directory for execution"""
        exec_path = await execution_service.create_execution("exec_001", sample_metadata)
        
        assert exec_path.exists()
        assert exec_path.is_dir()
        assert exec_path.name == "exec_001"

    @pytest.mark.asyncio
    async def test_saves_metadata_file(self, execution_service, sample_metadata):
        """Should save metadata.json file"""
        exec_path = await execution_service.create_execution("exec_001", sample_metadata)
        
        metadata_file = exec_path / "metadata.json"
        assert metadata_file.exists()
        
        saved_metadata = json.loads(metadata_file.read_text())
        assert saved_metadata["agent"] == "test-agent"
        assert saved_metadata["task"] == "Test task"
        assert "created_at" in saved_metadata
        assert "execution_id" in saved_metadata


class TestLogEvent:
    """Test log_event method"""

    @pytest.mark.asyncio
    async def test_logs_event_to_progress_file(self, execution_service, sample_metadata):
        """Should append event to progress.jsonl"""
        exec_path = await execution_service.create_execution("exec_001", sample_metadata)

        event = {"type": "started", "message": "Execution started"}
        await execution_service.log_event("exec_001", event)
        
        progress_file = exec_path / "progress.jsonl"
        assert progress_file.exists()
        
        lines = progress_file.read_text().strip().split("\n")
        assert len(lines) == 1
        
        logged_event = json.loads(lines[0])
        assert logged_event["type"] == "started"
        assert "timestamp" in logged_event

    @pytest.mark.asyncio
    async def test_logs_multiple_events(self, execution_service, sample_metadata):
        """Should append multiple events"""
        exec_path = await execution_service.create_execution("exec_001", sample_metadata)
        
        await execution_service.log_event("exec_001", {"type": "started"})
        await execution_service.log_event("exec_001", {"type": "processing"})
        await execution_service.log_event("exec_001", {"type": "completed"})
        
        progress_file = exec_path / "progress.jsonl"
        lines = progress_file.read_text().strip().split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_log_event_nonexistent_execution_raises_error(self, execution_service):
        """Should raise NotFoundError for non-existent execution"""
        with pytest.raises(NotFoundError):
            await execution_service.log_event("nonexistent", {"type": "test"})


class TestSaveResult:
    """Test save_result method"""

    @pytest.mark.asyncio
    async def test_saves_result_file(self, execution_service, sample_metadata):
        """Should save result.json file"""
        exec_path = await execution_service.create_execution("exec_001", sample_metadata)
        
        result = {"status": "success", "output": "Task completed"}
        await execution_service.save_result("exec_001", result)
        
        result_file = exec_path / "result.json"
        assert result_file.exists()
        
        saved_result = json.loads(result_file.read_text())
        assert saved_result["status"] == "success"
        assert "completed_at" in saved_result

    @pytest.mark.asyncio
    async def test_save_result_nonexistent_execution_raises_error(self, execution_service):
        """Should raise NotFoundError for non-existent execution"""
        with pytest.raises(NotFoundError):
            await execution_service.save_result("nonexistent", {"status": "success"})


class TestGetExecution:
    """Test get_execution method"""

    @pytest.mark.asyncio
    async def test_get_existing_execution(self, execution_service, sample_metadata):
        """Should retrieve execution with metadata, events, and result"""
        # Create execution
        await execution_service.create_execution("exec_001", sample_metadata)
        await execution_service.log_event("exec_001", {"type": "started"})
        await execution_service.log_event("exec_001", {"type": "completed"})
        await execution_service.save_result("exec_001", {"status": "success"})
        
        # Retrieve execution
        execution = await execution_service.get_execution("exec_001")
        
        assert execution["execution_id"] == "exec_001"
        assert execution["metadata"]["agent"] == "test-agent"
        assert len(execution["events"]) == 2
        assert execution["result"]["status"] == "success"
        assert execution["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_execution_without_result(self, execution_service, sample_metadata):
        """Should return status 'in_progress' without result"""
        await execution_service.create_execution("exec_001", sample_metadata)
        await execution_service.log_event("exec_001", {"type": "started"})
        
        execution = await execution_service.get_execution("exec_001")
        assert execution["status"] == "in_progress"
        assert execution["result"] is None

    @pytest.mark.asyncio
    async def test_get_execution_without_events(self, execution_service, sample_metadata):
        """Should return status 'started' without events"""
        await execution_service.create_execution("exec_001", sample_metadata)
        
        execution = await execution_service.get_execution("exec_001")
        assert execution["status"] == "started"
        assert len(execution["events"]) == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_execution_raises_error(self, execution_service):
        """Should raise NotFoundError for non-existent execution"""
        with pytest.raises(NotFoundError):
            await execution_service.get_execution("nonexistent")


class TestListExecutions:
    """Test list_executions method"""

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, execution_service):
        """Should return empty list when no executions exist"""
        executions = await execution_service.list_executions()
        assert executions == []

    @pytest.mark.asyncio
    async def test_list_all_executions(self, execution_service, sample_metadata):
        """Should list all executions"""
        await execution_service.create_execution("exec_001", {**sample_metadata, "task": "Task 1"})
        await execution_service.create_execution("exec_002", {**sample_metadata, "task": "Task 2"})
        
        executions = await execution_service.list_executions()
        assert len(executions) == 2

    @pytest.mark.asyncio
    async def test_list_with_limit(self, execution_service, sample_metadata):
        """Should respect limit parameter"""
        for i in range(5):
            await execution_service.create_execution(f"exec_{i:03d}", sample_metadata)
        
        executions = await execution_service.list_executions(limit=3)
        assert len(executions) == 3

    @pytest.mark.asyncio
    async def test_list_with_offset(self, execution_service, sample_metadata):
        """Should respect offset parameter"""
        for i in range(5):
            await execution_service.create_execution(f"exec_{i:03d}", sample_metadata)
        
        executions = await execution_service.list_executions(offset=2, limit=2)
        assert len(executions) == 2

    @pytest.mark.asyncio
    async def test_list_includes_status(self, execution_service, sample_metadata):
        """Should include status for each execution"""
        await execution_service.create_execution("exec_001", sample_metadata)
        await execution_service.save_result("exec_001", {"status": "success"})
        
        executions = await execution_service.list_executions()
        assert executions[0]["status"] == "completed"


class TestDeleteExecution:
    """Test delete_execution method"""

    @pytest.mark.asyncio
    async def test_delete_existing_execution(self, execution_service, sample_metadata, temp_executions_dir):
        """Should delete execution directory and all files"""
        await execution_service.create_execution("exec_001", sample_metadata)
        await execution_service.log_event("exec_001", {"type": "test"})
        
        exec_path = temp_executions_dir / "exec_001"
        assert exec_path.exists()
        
        result = await execution_service.delete_execution("exec_001")
        
        assert result["status"] == "deleted"
        assert not exec_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_execution_raises_error(self, execution_service):
        """Should raise NotFoundError for non-existent execution"""
        with pytest.raises(NotFoundError):
            await execution_service.delete_execution("nonexistent")
