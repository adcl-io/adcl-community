# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Execution Service - Manages execution persistence and history.

Single responsibility: Execution tracking and disk-based persistence.
Follows ADCL principle: Disk-first, no hidden state. Configuration is Code.
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.errors import NotFoundError
from app.core.logging import get_service_logger

logger = get_service_logger("execution")


class ExecutionService:
    """
    Manages execution state persistence to disk (ADCL compliance).

    Responsibilities:
    - Create execution directories
    - Log execution events to disk (source of truth)
    - Retrieve execution history
    - Manage execution metadata
    - Track execution progress

    All execution state is persisted to disk immediately - no in-memory caching.
    This ensures full auditability and crash recovery.
    """

    def __init__(self, executions_dir: Path):
        """
        Initialize ExecutionService.

        Args:
            executions_dir: Directory for execution persistence (volumes/executions)
        """
        self.executions_dir = executions_dir
        self.executions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ExecutionService initialized with directory: {executions_dir}")

    async def create_execution(
        self, execution_id: str, metadata: Dict[str, Any]
    ) -> Path:
        """
        Create a new execution directory and save metadata.

        Args:
            execution_id: Unique execution identifier
            metadata: Execution metadata (agent, task, trigger, etc.)

        Returns:
            Path to execution directory

        Example:
            >>> service = ExecutionService(Path("volumes/executions"))
            >>> exec_dir = await service.create_execution("exec_001", {"task": "scan"})
            >>> exec_dir.exists()
            True
        """
        execution_dir = self.executions_dir / execution_id

        # Use asyncio.to_thread for mkdir
        await asyncio.to_thread(execution_dir.mkdir, parents=True, exist_ok=True)

        # Save metadata to disk asynchronously
        metadata_file = execution_dir / "metadata.json"
        metadata_with_timestamp = {
            **metadata,
            "execution_id": execution_id,
            "created_at": datetime.now().isoformat(),
        }

        async with aiofiles.open(metadata_file, "w") as f:
            await f.write(json.dumps(metadata_with_timestamp, indent=2))

        logger.info(f"Created execution: {execution_id}")
        return execution_dir

    async def log_event(
        self, execution_id: str, event: Dict[str, Any]
    ) -> None:
        """
        Log an execution event to disk (append-only log).

        Args:
            execution_id: Execution identifier
            event: Event data to log

        Raises:
            NotFoundError: If execution directory doesn't exist
        """
        execution_dir = self.executions_dir / execution_id

        # Check if directory exists asynchronously
        exists = await asyncio.to_thread(execution_dir.exists)
        if not exists:
            raise NotFoundError("Execution", execution_id)

        # Append event to progress.jsonl asynchronously
        progress_file = execution_dir / "progress.jsonl"
        event_with_timestamp = {
            **event,
            "timestamp": datetime.now().isoformat(),
        }

        async with aiofiles.open(progress_file, "a") as f:
            await f.write(json.dumps(event_with_timestamp) + "\n")

        logger.debug(f"Logged event for execution {execution_id}: {event.get('type', 'unknown')}")

    async def save_result(
        self, execution_id: str, result: Dict[str, Any]
    ) -> None:
        """
        Save execution final result to disk.

        Args:
            execution_id: Execution identifier
            result: Final execution result

        Raises:
            NotFoundError: If execution directory doesn't exist
        """
        execution_dir = self.executions_dir / execution_id

        # Check if directory exists asynchronously
        exists = await asyncio.to_thread(execution_dir.exists)
        if not exists:
            raise NotFoundError("Execution", execution_id)

        # Save result asynchronously
        result_file = execution_dir / "result.json"
        result_with_timestamp = {
            **result,
            "completed_at": datetime.now().isoformat(),
        }

        async with aiofiles.open(result_file, "w") as f:
            await f.write(json.dumps(result_with_timestamp, indent=2))

        logger.info(f"Saved result for execution: {execution_id}")

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Retrieve execution state from disk.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict with execution metadata, events, result, and status

        Raises:
            NotFoundError: If execution not found
        """
        execution_dir = self.executions_dir / execution_id

        # Check if directory exists asynchronously
        exists = await asyncio.to_thread(execution_dir.exists)
        if not exists:
            raise NotFoundError("Execution", execution_id)

        # Load metadata asynchronously
        metadata_file = execution_dir / "metadata.json"
        metadata_exists = await asyncio.to_thread(metadata_file.exists)
        if not metadata_exists:
            raise NotFoundError("Execution metadata", execution_id)

        async with aiofiles.open(metadata_file, "r") as f:
            content = await f.read()
            metadata = json.loads(content)

        # Load all events from progress.jsonl asynchronously
        events = []
        progress_file = execution_dir / "progress.jsonl"
        progress_exists = await asyncio.to_thread(progress_file.exists)
        if progress_exists:
            async with aiofiles.open(progress_file, "r") as f:
                content = await f.read()
                for line in content.splitlines():
                    if line.strip():
                        events.append(json.loads(line))

        # Load result if exists asynchronously
        result = None
        result_file = execution_dir / "result.json"
        result_exists = await asyncio.to_thread(result_file.exists)
        if result_exists:
            async with aiofiles.open(result_file, "r") as f:
                content = await f.read()
                result = json.loads(content)

        # Determine status
        if result:
            status = "completed"
        elif events:
            status = "in_progress"
        else:
            status = "started"

        logger.info(f"Retrieved execution: {execution_id} (status: {status})")

        return {
            "execution_id": execution_id,
            "metadata": metadata,
            "events": events,
            "result": result,
            "status": status,
        }

    async def list_executions(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all executions from disk (newest first).

        Args:
            limit: Maximum number of executions to return
            offset: Number of executions to skip

        Returns:
            List of execution summaries

        Example:
            >>> service = ExecutionService(Path("volumes/executions"))
            >>> executions = await service.list_executions(limit=10)
            >>> len(executions) <= 10
            True
        """
        executions = []

        # Get all execution directories, sorted by modification time (newest first)
        # Use asyncio.to_thread for directory iteration
        def get_sorted_dirs():
            return sorted(
                self.executions_dir.iterdir(),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

        execution_dirs = await asyncio.to_thread(get_sorted_dirs)

        # Apply offset and limit
        execution_dirs = execution_dirs[offset:]
        if limit:
            execution_dirs = execution_dirs[:limit]

        for execution_dir in execution_dirs:
            is_dir = await asyncio.to_thread(execution_dir.is_dir)
            if not is_dir:
                continue

            try:
                # Load metadata asynchronously
                metadata_file = execution_dir / "metadata.json"
                metadata_exists = await asyncio.to_thread(metadata_file.exists)
                if not metadata_exists:
                    continue

                async with aiofiles.open(metadata_file, "r") as f:
                    content = await f.read()
                    metadata = json.loads(content)

                # Check for result asynchronously
                result_file = execution_dir / "result.json"
                has_result = await asyncio.to_thread(result_file.exists)

                executions.append({
                    "execution_id": execution_dir.name,
                    "created_at": metadata.get("created_at"),
                    "status": "completed" if has_result else "in_progress",
                    "task": metadata.get("task", ""),
                    "agent": metadata.get("agent", ""),
                })
            except Exception as e:
                logger.error(f"Failed to load execution {execution_dir.name}: {e}")
                continue

        logger.info(f"Listed {len(executions)} executions (offset: {offset}, limit: {limit})")
        return executions

    async def delete_execution(self, execution_id: str) -> Dict[str, str]:
        """
        Delete an execution from disk.

        Args:
            execution_id: Execution identifier

        Returns:
            Deletion status

        Raises:
            NotFoundError: If execution not found
        """
        execution_dir = self.executions_dir / execution_id

        # Check if directory exists asynchronously
        exists = await asyncio.to_thread(execution_dir.exists)
        if not exists:
            raise NotFoundError("Execution", execution_id)

        # Delete all files and directory asynchronously
        def delete_dir():
            # Delete all files in execution directory
            for file in execution_dir.iterdir():
                file.unlink()
            # Delete directory
            execution_dir.rmdir()

        await asyncio.to_thread(delete_dir)

        logger.info(f"Deleted execution: {execution_id}")
        return {"status": "deleted", "execution_id": execution_id}
