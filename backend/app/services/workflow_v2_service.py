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
    
    def __init__(self, workflows_dir: Path, executor: WorkflowExecutor):
        self.workflows_dir = workflows_dir
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.executor = executor
        logger.info(f"WorkflowV2Service initialized with directory: {workflows_dir}")
    
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
        """Get a specific workflow definition"""
        file_path = self.workflows_dir / f"{workflow_id}.json"
        
        if not file_path.exists():
            raise NotFoundError("Workflow", workflow_id)
        
        workflow_data = json.loads(file_path.read_text())
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
    
    async def run_workflow(self, workflow_id: str, initial_message: str = None, params: Dict[str, Any] = None) -> ExecutionV2Result:
        """Execute a workflow"""
        # Load workflow definition
        workflow_data = await self.get_workflow(workflow_id)
        workflow_def = WorkflowV2Definition(**workflow_data)
        
        # Execute workflow
        logger.info(f"Executing workflow: {workflow_id}")
        context = await self.executor.execute(workflow_def, initial_message=initial_message)
        
        # Build result
        result = ExecutionV2Result(
            execution_id=context.execution_id,
            workflow_id=context.workflow_id,
            status="completed",
            history_session_id=context.history_session_id or "",
            started_at=context.started_at,
            completed_at=context.completed_at or "",
            final_result=context.node_results
        )
        
        logger.info(f"Workflow execution completed: {context.execution_id}")
        return result
