# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Service - Manages workflow definitions and execution.

Single responsibility: Workflow CRUD operations and execution orchestration.
Follows ADCL principle: Do one thing well.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_service_logger
from app.workflow_engine import WorkflowEngine
from app.workflow_models import WorkflowDefinition, ExecutionResult

logger = get_service_logger("workflow")


class WorkflowService:
    """
    Manages workflow definitions stored as JSON files and execution.

    Responsibilities:
    - Load workflows from disk
    - Save new workflows
    - Delete workflows
    - Execute workflows via WorkflowEngine
    - List available workflows
    """

    def __init__(self, workflows_dir: Path, workflow_engine: WorkflowEngine):
        """
        Initialize WorkflowService.

        Args:
            workflows_dir: Directory containing workflow JSON files
            workflow_engine: WorkflowEngine instance for execution
        """
        self.workflows_dir = workflows_dir
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.engine = workflow_engine
        logger.info(f"WorkflowService initialized with directory: {workflows_dir}")

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflow definitions from disk.

        Returns:
            List of workflow summaries (name, filename, description)

        Example:
            >>> service = WorkflowService(Path("workflows"), engine)
            >>> workflows = await service.list_workflows()
            >>> len(workflows)
            3
        """
        workflows = []

        for file in self.workflows_dir.glob("*.json"):
            try:
                workflow_data = json.loads(file.read_text())
                workflows.append({
                    "name": workflow_data.get("name", file.stem),
                    "filename": file.name,
                    "description": workflow_data.get("description", "")
                })
            except (json.JSONDecodeError, IOError, OSError) as e:
                # Skip malformed workflow files
                logger.warning(f"Skipping invalid workflow file {file.name}: {e}")
                continue

        logger.info(f"Listed {len(workflows)} workflows from disk")
        return workflows

    async def list_example_workflows(self) -> List[Dict[str, str]]:
        """
        List example workflows (alias for list_workflows for backwards compatibility).

        Returns:
            List of workflow examples
        """
        examples = []

        for file in self.workflows_dir.glob("*.json"):
            try:
                workflow_data = json.loads(file.read_text())
                examples.append({
                    "name": workflow_data.get("name", file.stem),
                    "file": file.name
                })
            except (json.JSONDecodeError, IOError, OSError) as e:
                logger.warning(f"Skipping invalid workflow file {file.name}: {e}")
                continue

        logger.info(f"Listed {len(examples)} example workflows")
        return examples

    async def get_workflow(self, filename: str) -> Dict[str, Any]:
        """
        Get a specific workflow definition by filename.

        Args:
            filename: Workflow filename (e.g., "my_workflow.json")

        Returns:
            Workflow definition as dict

        Raises:
            NotFoundError: If workflow file not found
        """
        self._validate_filename(filename)
        file_path = self.workflows_dir / filename

        if not file_path.exists():
            raise NotFoundError("Workflow", filename)

        workflow_data = json.loads(file_path.read_text())
        logger.info(f"Retrieved workflow: {filename}")
        return workflow_data

    async def save_workflow(self, workflow: WorkflowDefinition) -> Dict[str, str]:
        """
        Save a workflow definition to disk.

        Args:
            workflow: Workflow definition

        Returns:
            Dict with message and filename

        Raises:
            ValidationError: If workflow data is invalid or too large
        """
        # Sanitize filename from workflow name
        filename = workflow.name.lower().replace(" ", "_").replace("/", "_")
        filename = "".join(c for c in filename if c.isalnum() or c in "_-")
        file_path = self.workflows_dir / f"{filename}.json"

        # Convert to dict and validate size (1MB limit)
        workflow_json = json.dumps(workflow.dict(), indent=2)
        if len(workflow_json) > 1_000_000:
            raise ValidationError(
                "Workflow too large (max 1MB)",
                field="workflow",
                details={"size": len(workflow_json)}
            )

        # Write workflow to disk
        file_path.write_text(workflow_json)

        logger.info(f"Saved workflow: {file_path.name}")
        return {"message": "Workflow saved", "filename": file_path.name}

    async def delete_workflow(self, filename: str) -> Dict[str, str]:
        """
        Delete a workflow definition from disk.

        Args:
            filename: Workflow filename to delete

        Returns:
            Deletion status message

        Raises:
            NotFoundError: If workflow file not found
        """
        self._validate_filename(filename)
        file_path = self.workflows_dir / filename

        if not file_path.exists():
            raise NotFoundError("Workflow", filename)

        file_path.unlink()

        logger.info(f"Deleted workflow: {filename}")
        return {"message": "Workflow deleted"}

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        params: Optional[Dict[str, Any]] = None,
        trigger_type: str = "manual",
        update_callback: Optional[Callable] = None
    ) -> ExecutionResult:
        """
        Execute a workflow using the WorkflowEngine.

        Args:
            workflow: Workflow definition to execute
            params: Input parameters for workflow execution
            trigger_type: Type of trigger ("manual", "api", "cron", "webhook")
            update_callback: Optional callback for real-time updates

        Returns:
            Execution result with status, logs, and node states

        Example:
            >>> workflow = WorkflowDefinition(name="test", nodes=[], edges=[])
            >>> result = await service.execute_workflow(workflow)
            >>> result.status
            "completed"
        """
        logger.info(f"Executing workflow: {workflow.name} (trigger: {trigger_type})")

        result = await self.engine.execute(
            workflow=workflow,
            params=params or {},
            trigger_type=trigger_type,
            update_callback=update_callback
        )

        logger.info(
            f"Workflow execution {result.status}: {workflow.name} "
            f"(errors: {len(result.errors)})"
        )

        return result

    # Private helper methods

    def _validate_filename(self, filename: str) -> None:
        """
        Validate filename to prevent path traversal attacks.

        Args:
            filename: Filename to validate

        Raises:
            ValidationError: If filename contains path separators or is invalid
        """
        if not filename:
            raise ValidationError("Filename cannot be empty", field="filename")

        # Check for path traversal attempts
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValidationError(
                "Filename cannot contain path separators or '..'",
                field="filename"
            )

        # Ensure the resolved path is within workflows_dir
        file_path = (self.workflows_dir / filename).resolve()
        try:
            file_path.relative_to(self.workflows_dir.resolve())
        except ValueError:
            raise ValidationError(
                "Invalid filename: path traversal detected",
                field="filename"
            )
