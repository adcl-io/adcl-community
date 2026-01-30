# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Service

Manages V2 workflow definitions and execution.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_service_logger
from app.workflow_v2.models import WorkflowV2Definition, ExecutionV2Result
from app.workflow_v2.executor import WorkflowExecutor

logger = get_service_logger("workflow-v2")


class WorkflowV2Service:
    """
    Manages V2 workflow definitions and execution.

    Responsibilities:
    - CRUD operations for workflow definitions
    - Workflow execution via WorkflowExecutor
    """

    def __init__(self, workflows_dir: Path, executor: WorkflowExecutor, result_processor=None):
        self.workflows_dir = workflows_dir
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.executor = executor
        self.result_processor = result_processor  # Optional - allows workflows without recon integration
        logger.info(f"WorkflowV2Service initialized with directory: {workflows_dir}")

    def _migrate_workflow_to_v2(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate V1 workflow to V2 schema with UI metadata.

        V2 additions:
        - version: "2.0"
        - ui_metadata: {zoom, viewport}
        - nodes[].position: {x, y}
        - nodes[].ui: {width, height}
        - edges[].ui: {animated}
        """
        # Set version
        workflow_data["version"] = "2.0"

        # Add ui_metadata if missing
        if "ui_metadata" not in workflow_data:
            workflow_data["ui_metadata"] = {
                "zoom": 1.0,
                "viewport": {"x": 0, "y": 0}
            }

        # Apply auto-layout if positions missing
        if not any("position" in node for node in workflow_data.get("nodes", [])):
            workflow_data = self._apply_simple_auto_layout(workflow_data)

        # Ensure edges have UI metadata
        for edge in workflow_data.get("edges", []):
            if "ui" not in edge:
                edge["ui"] = {"animated": True}

        return workflow_data

    def _apply_simple_auto_layout(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply simple grid-based auto-layout to nodes without positions.

        Uses 3-column grid with 300px horizontal spacing and 200px vertical spacing.
        """
        nodes_per_row = 3
        x_spacing = 300
        y_spacing = 200
        x_offset = 100
        y_offset = 100

        for i, node in enumerate(workflow_data.get("nodes", [])):
            if "position" not in node:
                row = i // nodes_per_row
                col = i % nodes_per_row
                node["position"] = {
                    "x": x_offset + (col * x_spacing),
                    "y": y_offset + (row * y_spacing)
                }

            # Add default UI metadata
            if "ui" not in node:
                node["ui"] = {
                    "width": 200,
                    "height": 150
                }

        return workflow_data

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all V2 workflow definitions"""
        workflows = []

        for file in self.workflows_dir.glob("*.json"):
            try:
                workflow_data = json.loads(file.read_text())
                workflows.append({
                    "workflow_id": workflow_data.get("workflow_id"),
                    "name": workflow_data.get("name"),
                    "description": workflow_data.get("description"),
                    "node_count": len(workflow_data.get("nodes", [])),
                    "filename": file.name
                })
            except Exception as e:
                logger.warning(f"Skipping invalid workflow file {file.name}: {e}")

        logger.info(f"Listed {len(workflows)} V2 workflows")
        return workflows

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow definition with automatic V1 → V2 migration"""
        file_path = self.workflows_dir / f"{workflow_id}.json"

        if not file_path.exists():
            raise NotFoundError("Workflow", workflow_id)

        workflow_data = json.loads(file_path.read_text())

        # Auto-migrate V1 workflows to V2
        if "version" not in workflow_data or workflow_data.get("version") == "1.0":
            workflow_data = self._migrate_workflow_to_v2(workflow_data)
            # Save migrated version back to disk
            file_path.write_text(json.dumps(workflow_data, indent=2))
            logger.info(f"Auto-migrated workflow '{workflow_id}' to V2.0")

        logger.info(f"Retrieved workflow: {workflow_id}")
        return workflow_data

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow definition"""
        if "workflow_id" not in workflow_data:
            raise ValidationError("workflow_id is required", field="workflow_id")

        workflow_id = workflow_data["workflow_id"]
        file_path = self.workflows_dir / f"{workflow_id}.json"

        if file_path.exists():
            raise ValidationError(f"Workflow '{workflow_id}' already exists", field="workflow_id")

        # Validate workflow structure
        WorkflowV2Definition(**workflow_data)

        # Save to disk
        file_path.write_text(json.dumps(workflow_data, indent=2))

        logger.info(f"Created workflow: {workflow_id}")
        return workflow_data

    async def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing workflow definition"""
        file_path = self.workflows_dir / f"{workflow_id}.json"

        if not file_path.exists():
            raise NotFoundError("Workflow", workflow_id)

        # Ensure workflow_id matches
        workflow_data["workflow_id"] = workflow_id

        # Validate workflow structure
        WorkflowV2Definition(**workflow_data)

        # Save to disk
        file_path.write_text(json.dumps(workflow_data, indent=2))

        logger.info(f"Updated workflow: {workflow_id}")
        return workflow_data

    async def delete_workflow(self, workflow_id: str) -> Dict[str, str]:
        """Delete a workflow definition"""
        file_path = self.workflows_dir / f"{workflow_id}.json"

        if not file_path.exists():
            raise NotFoundError("Workflow", workflow_id)

        file_path.unlink()

        logger.info(f"Deleted workflow: {workflow_id}")
        return {"message": f"Workflow '{workflow_id}' deleted"}

    async def run_workflow(
        self,
        workflow_id: str,
        initial_message: str = None,
        params: Dict[str, Any] = None,
        progress_callback: Any = None,
        session_id: str = None,
        security_context: Any = None
    ) -> ExecutionV2Result:
        """Execute a workflow"""
        # Load workflow definition
        workflow_data = await self.get_workflow(workflow_id)
        workflow_def = WorkflowV2Definition(**workflow_data)

        # Execute workflow with progress callback
        logger.info(f"Executing workflow: {workflow_id}")
        context = await self.executor.execute(
            workflow_def,
            initial_message=initial_message,
            progress_callback=progress_callback,
            attack_playground_session_id=session_id,
            security_context=security_context
        )

        # Process results if workflow completed successfully
        scan_id = None
        if context.completed_at and self.result_processor:
            try:
                scan_id = await self.result_processor.process_workflow_result(
                    workflow_id=workflow_id,
                    execution_id=context.execution_id,
                    initial_message=initial_message or "",
                    final_result=context.node_results
                )
                if scan_id:
                    logger.info(f"Created scan {scan_id} from workflow {context.execution_id}")
            except Exception as e:
                logger.error(f"Failed to process workflow results: {e}", exc_info=True)
                # Don't fail the workflow if scan creation fails

        # Update attack playground session if session_id provided
        logger.info(f"Session update check: session_id={session_id}, completed_at={context.completed_at}")
        if session_id and context.completed_at:
            try:
                from app.services.attack_session_service import attack_session_service

                # Build execution result for session processor
                execution_result = {
                    "execution_id": context.execution_id,
                    "workflow_id": workflow_id,
                    "result": context.node_results
                }

                logger.info(f"Calling on_workflow_complete for session {session_id}, workflow {workflow_id}")
                attack_session_service.on_workflow_complete(
                    session_id=session_id,
                    workflow_id=workflow_id,
                    target=initial_message or "",
                    execution_result=execution_result
                )
                logger.info(f"Updated attack session {session_id} from workflow {context.execution_id}")
            except Exception as e:
                logger.error(f"Failed to update attack session: {e}", exc_info=True)
                # Don't fail the workflow if session update fails

        # Load updated session state to include in response
        updated_session_state = None
        if session_id:
            try:
                from app.services.attack_session_service import attack_session_service
                updated_session = attack_session_service.get_or_create_session(session_id)
                updated_session_state = updated_session
                logger.info(f"Loaded updated session state for {session_id}: {len(updated_session.get('hosts', []))} hosts")
            except Exception as e:
                logger.error(f"Failed to load session state: {e}", exc_info=True)

        # Build result
        result = ExecutionV2Result(
            execution_id=context.execution_id,
            workflow_id=context.workflow_id,
            status="completed",
            history_session_id=context.history_session_id or "",
            started_at=context.started_at,
            completed_at=context.completed_at or "",
            final_result=context.node_results,
            scan_id=scan_id,  # Include scan_id for UI
            cumulative_tokens=context.cumulative_tokens,  # Include token usage and cost
            session_state=updated_session_state  # Include updated session with exploit results
        )

        logger.info(f"Workflow execution completed: {context.execution_id}")
        return result
