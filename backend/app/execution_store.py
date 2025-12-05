# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Execution Store - Persistent storage for workflow execution history
Follows ADCL principle: "Configuration is Code" - all history in text files

Thread-safe with async file locking to prevent race conditions
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import asyncio
import aiofiles
import aiofiles.os
from .config_loader import get_workflow_config


class ExecutionStore:
    """
    Store and query workflow execution history.

    Storage structure:
        workflows/executions/
        └── {YYYY-MM-DD}/
            ├── exec_001.json
            ├── exec_002.json
            └── exec_003.json

    Each execution file contains:
        - execution_id
        - workflow_name
        - status (completed/failed)
        - started_at / completed_at
        - duration
        - trigger_type
        - params
        - results
        - errors
        - node_states
    """

    def __init__(self, base_dir: str = None):
        # Load from config (ADCL: Configuration is Code)
        if base_dir is None:
            config = get_workflow_config()
            base_dir = config["workflows"]["executions_dir"]

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Async locks for thread-safe file operations
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _get_lock(self, file_path: str) -> asyncio.Lock:
        """Get or create lock for a specific file"""
        if file_path not in self._locks:
            self._locks[file_path] = asyncio.Lock()
        return self._locks[file_path]

    async def save(self, execution_id: str, execution_data: Dict[str, Any]):
        """
        Save execution to disk.

        Args:
            execution_id: Unique execution ID
            execution_data: Execution metadata and results

        Returns:
            Path to saved file
        """
        # Extract date from execution_id (format: exec_YYYYMMDD_HHMMSS_hash)
        date_str = execution_id.split("_")[1]  # YYYYMMDD
        date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

        # Create date directory
        date_dir = self.base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)

        # Save execution with file locking
        execution_file = date_dir / f"{execution_id}.json"

        # Get lock for this file
        lock = self._get_lock(str(execution_file))

        async with lock:
            # Use async file operations
            async with aiofiles.open(execution_file, 'w') as f:
                await f.write(json.dumps(execution_data, indent=2))

        return str(execution_file)

    def get(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution by ID.

        Args:
            execution_id: Execution ID to retrieve

        Returns:
            Execution data or None if not found
        """
        # Parse date from execution_id
        try:
            date_str = execution_id.split("_")[1]  # YYYYMMDD
            date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        except (IndexError, ValueError):
            # Try searching all dates
            return self._search_all_dates(execution_id)

        # Try specific date
        execution_file = self.base_dir / date / f"{execution_id}.json"

        if execution_file.exists():
            with open(execution_file, 'r') as f:
                return json.load(f)

        return None

    def _search_all_dates(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Search for execution across all dates"""
        for date_dir in self.base_dir.glob("*"):
            if not date_dir.is_dir():
                continue

            execution_file = date_dir / f"{execution_id}.json"
            if execution_file.exists():
                with open(execution_file, 'r') as f:
                    return json.load(f)

        return None

    def list(
        self,
        date: Optional[str] = None,
        workflow: Optional[str] = None,
        status: Optional[str] = None,
        trigger_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List executions with optional filters.

        Args:
            date: Filter by date (YYYY-MM-DD)
            workflow: Filter by workflow name
            status: Filter by status (completed/failed)
            trigger_type: Filter by trigger (manual/api/cron/webhook)
            limit: Max results to return
            offset: Skip first N results

        Returns:
            List of execution metadata (sorted by date desc)
        """
        executions = []

        # Determine which dates to scan
        if date:
            date_dirs = [self.base_dir / date]
        else:
            # Get all date directories, sorted desc
            date_dirs = sorted(self.base_dir.glob("*"), reverse=True)

        # Scan date directories
        for date_dir in date_dirs:
            if not date_dir.is_dir():
                continue

            # Get all execution files in this date
            for execution_file in sorted(date_dir.glob("exec_*.json"), reverse=True):
                try:
                    with open(execution_file, 'r') as f:
                        execution_data = json.load(f)

                    # Apply filters
                    if workflow and execution_data.get("workflow") != workflow:
                        continue
                    if status and execution_data.get("status") != status:
                        continue
                    if trigger_type and execution_data.get("trigger") != trigger_type:
                        continue

                    executions.append(execution_data)

                    # Stop if we have enough
                    if len(executions) >= limit + offset:
                        break

                except Exception as e:
                    print(f"Warning: Failed to load execution {execution_file}: {e}")

            # Stop if we have enough
            if len(executions) >= limit + offset:
                break

        # Apply offset and limit
        return executions[offset:offset + limit]

    def query(
        self,
        date: Optional[str] = None,
        workflow: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query executions (alias for list with extended filters).

        Args:
            date: Single date (YYYY-MM-DD)
            workflow: Workflow name
            status: Status filter
            start_date: Start of date range (YYYY-MM-DD)
            end_date: End of date range (YYYY-MM-DD)

        Returns:
            List of execution metadata
        """
        # Convert date range to list of dates
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            executions = []
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                executions.extend(self.list(date=date_str, workflow=workflow, status=status, limit=1000))
                current += timedelta(days=1)

            return executions

        return self.list(date=date, workflow=workflow, status=status, limit=1000)

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get execution statistics for last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dict with counts, success rates, etc.
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Collect executions
        executions = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            executions.extend(self.list(date=date_str, limit=10000))
            current += timedelta(days=1)

        # Calculate statistics
        total = len(executions)
        completed = sum(1 for e in executions if e.get("status") == "completed")
        failed = sum(1 for e in executions if e.get("status") == "failed")

        # Average duration (for completed executions)
        durations = [e.get("duration", 0) for e in executions if e.get("status") == "completed" and "duration" in e]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Group by workflow
        by_workflow = {}
        for execution in executions:
            workflow_name = execution.get("workflow", "unknown")
            if workflow_name not in by_workflow:
                by_workflow[workflow_name] = {
                    "total": 0,
                    "completed": 0,
                    "failed": 0
                }

            by_workflow[workflow_name]["total"] += 1
            if execution.get("status") == "completed":
                by_workflow[workflow_name]["completed"] += 1
            else:
                by_workflow[workflow_name]["failed"] += 1

        # Group by trigger type
        by_trigger = {}
        for execution in executions:
            trigger = execution.get("trigger", "unknown")
            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1

        return {
            "period_days": days,
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "avg_duration_seconds": round(avg_duration, 2),
            "by_workflow": by_workflow,
            "by_trigger": by_trigger
        }

    def delete_old_executions(self, days: int = 90):
        """
        Delete executions older than N days (cleanup).

        Args:
            days: Keep executions from last N days

        Returns:
            Number of executions deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        # Scan all date directories
        for date_dir in self.base_dir.glob("*"):
            if not date_dir.is_dir():
                continue

            # Parse directory date
            try:
                dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")

                # Delete if older than cutoff
                if dir_date < cutoff_date:
                    # Delete all execution files
                    for execution_file in date_dir.glob("exec_*.json"):
                        execution_file.unlink()
                        deleted_count += 1

                    # Delete empty directory
                    if not any(date_dir.iterdir()):
                        date_dir.rmdir()

            except ValueError:
                print(f"Warning: Invalid date directory name: {date_dir.name}")

        return deleted_count

    def get_workflow_history(self, workflow_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get execution history for a specific workflow.

        Args:
            workflow_name: Workflow to query
            limit: Max results

        Returns:
            List of executions for this workflow
        """
        return self.list(workflow=workflow_name, limit=limit)

    def get_recent_failures(self, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent failed executions for debugging.

        Args:
            days: Look back N days
            limit: Max results

        Returns:
            List of failed executions
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        failures = []
        current = start_date
        while current <= end_date and len(failures) < limit:
            date_str = current.strftime("%Y-%m-%d")
            day_failures = self.list(date=date_str, status="failed", limit=limit)
            failures.extend(day_failures)
            current += timedelta(days=1)

        return failures[:limit]

    def count_executions(self, date: Optional[str] = None, workflow: Optional[str] = None) -> int:
        """
        Count executions matching filters.

        Args:
            date: Date filter (YYYY-MM-DD)
            workflow: Workflow name filter

        Returns:
            Count of matching executions
        """
        return len(self.list(date=date, workflow=workflow, limit=100000))
