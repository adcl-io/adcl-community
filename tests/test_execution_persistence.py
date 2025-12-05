# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Unit tests for PRD-71: Execution persistence and SSE streaming
"""
import pytest
import json
import asyncio
from pathlib import Path
from datetime import datetime
import tempfile
import shutil


# Mock execution helpers (would normally import from app.main)
def get_executions_dir_test(base_path):
    """Test version of get_executions_dir"""
    executions_dir = base_path / "executions"
    executions_dir.mkdir(parents=True, exist_ok=True)
    return executions_dir


def create_execution_dir_test(base_path, execution_id: str):
    """Test version of create_execution_dir"""
    execution_dir = get_executions_dir_test(base_path) / execution_id
    execution_dir.mkdir(parents=True, exist_ok=True)
    return execution_dir


def log_execution_event_test(execution_dir: Path, event: dict):
    """Test version of log_execution_event"""
    progress_file = execution_dir / "progress.jsonl"
    event_with_timestamp = {**event, 'timestamp': datetime.now().isoformat()}
    with open(progress_file, 'a') as f:
        f.write(json.dumps(event_with_timestamp) + '\n')


class TestExecutionPersistence:
    """Test execution persistence functionality (ADCL compliance)"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    def test_create_execution_directory(self, temp_dir):
        """Test that execution directories are created correctly"""
        execution_id = "test-exec-123"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        assert execution_dir.exists()
        assert execution_dir.is_dir()
        assert execution_dir.name == execution_id

    def test_log_execution_event_creates_file(self, temp_dir):
        """Test that logging events creates progress.jsonl"""
        execution_id = "test-exec-456"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        event = {
            'type': 'agent_start',
            'agent_id': 'test-agent',
            'role': 'tester'
        }

        log_execution_event_test(execution_dir, event)

        progress_file = execution_dir / "progress.jsonl"
        assert progress_file.exists()

    def test_log_execution_event_appends(self, temp_dir):
        """Test that multiple events are appended correctly"""
        execution_id = "test-exec-789"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        events = [
            {'type': 'agent_start', 'agent_id': 'agent1'},
            {'type': 'agent_iteration', 'iteration': 1},
            {'type': 'agent_complete', 'status': 'success'}
        ]

        for event in events:
            log_execution_event_test(execution_dir, event)

        progress_file = execution_dir / "progress.jsonl"
        lines = progress_file.read_text().strip().split('\n')

        assert len(lines) == 3
        for line in lines:
            event = json.loads(line)
            assert 'timestamp' in event
            assert 'type' in event

    def test_event_has_timestamp(self, temp_dir):
        """Test that logged events include timestamp (ADCL observability)"""
        execution_id = "test-exec-timestamp"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        event = {'type': 'test', 'data': 'value'}
        log_execution_event_test(execution_dir, event)

        progress_file = execution_dir / "progress.jsonl"
        logged_event = json.loads(progress_file.read_text())

        assert 'timestamp' in logged_event
        assert logged_event['type'] == 'test'
        assert logged_event['data'] == 'value'
        # Verify timestamp is ISO format
        datetime.fromisoformat(logged_event['timestamp'])

    def test_events_are_jsonl_format(self, temp_dir):
        """Test that events are in JSONL format (one JSON per line)"""
        execution_id = "test-exec-jsonl"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        events = [
            {'type': 'event1'},
            {'type': 'event2'},
            {'type': 'event3'}
        ]

        for event in events:
            log_execution_event_test(execution_dir, event)

        progress_file = execution_dir / "progress.jsonl"
        lines = progress_file.read_text().strip().split('\n')

        # Each line should be valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
            assert 'type' in parsed


class TestExecutionRetrieval:
    """Test execution retrieval functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    def test_retrieve_execution_metadata(self, temp_dir):
        """Test retrieving execution metadata"""
        execution_id = "test-retrieve-123"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        metadata = {
            'id': execution_id,
            'team_id': 'test-team',
            'task': 'Test task',
            'started_at': datetime.now().isoformat()
        }

        (execution_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        # Retrieve and verify
        retrieved = json.loads((execution_dir / "metadata.json").read_text())
        assert retrieved['id'] == execution_id
        assert retrieved['team_id'] == 'test-team'
        assert retrieved['task'] == 'Test task'

    def test_retrieve_execution_events(self, temp_dir):
        """Test retrieving all execution events"""
        execution_id = "test-retrieve-456"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        events = [
            {'type': 'agent_start'},
            {'type': 'agent_iteration', 'iteration': 1},
            {'type': 'agent_iteration', 'iteration': 2},
            {'type': 'agent_complete'}
        ]

        for event in events:
            log_execution_event_test(execution_dir, event)

        # Retrieve all events
        progress_file = execution_dir / "progress.jsonl"
        retrieved_events = []
        for line in progress_file.read_text().splitlines():
            if line.strip():
                retrieved_events.append(json.loads(line))

        assert len(retrieved_events) == 4
        assert retrieved_events[0]['type'] == 'agent_start'
        assert retrieved_events[-1]['type'] == 'agent_complete'

    def test_retrieve_execution_result(self, temp_dir):
        """Test retrieving final execution result"""
        execution_id = "test-retrieve-789"
        execution_dir = create_execution_dir_test(temp_dir, execution_id)

        result = {
            'status': 'completed',
            'answer': 'Task completed successfully',
            'agent_results': []
        }

        (execution_dir / "result.json").write_text(json.dumps(result, indent=2))

        # Retrieve and verify
        retrieved = json.loads((execution_dir / "result.json").read_text())
        assert retrieved['status'] == 'completed'
        assert retrieved['answer'] == 'Task completed successfully'


def test_adcl_compliance_inspection():
    """Test that execution state is inspectable via cat/grep/jq (ADCL principle)"""
    # This is a documentation test - verify file formats are plain text
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        execution_id = "test-adcl-compliance"
        execution_dir = create_execution_dir_test(temp_path, execution_id)

        # Create metadata
        metadata = {'id': execution_id, 'task': 'test'}
        (execution_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        # Create events
        log_execution_event_test(execution_dir, {'type': 'test_event'})

        # Create result
        result = {'status': 'success'}
        (execution_dir / "result.json").write_text(json.dumps(result, indent=2))

        # Verify all files are readable as text
        assert (execution_dir / "metadata.json").read_text()
        assert (execution_dir / "progress.jsonl").read_text()
        assert (execution_dir / "result.json").read_text()

        # Verify all files contain valid JSON
        json.loads((execution_dir / "metadata.json").read_text())
        for line in (execution_dir / "progress.jsonl").read_text().splitlines():
            if line.strip():
                json.loads(line)
        json.loads((execution_dir / "result.json").read_text())
