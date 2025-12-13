# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow V2 Executor

Wave-based DAG execution engine.
"""

import asyncio
from typing import List, Set, Dict, Any
from datetime import datetime, timezone
import uuid

from .models import WorkflowV2Definition, WorkflowV2Node
from .context import ExecutionContext
from .validation import validate_workflow_v2, validate_agents_exist
from .exceptions import NodeExecutionException, NodeTimeoutException, WorkflowExecutionError
from .logging import WorkflowLogger


class WorkflowExecutor:
    """
    Wave-based workflow executor.
    
    Executes nodes in waves based on dependency satisfaction.
    """
    
    def __init__(self, agent_runtime, agent_service, history_mcp_url: str):
        self.agent_runtime = agent_runtime
        self.agent_service = agent_service
        self.logger = WorkflowLogger(history_mcp_url)
    
    async def execute(self, workflow_def: WorkflowV2Definition, initial_message: str = None) -> ExecutionContext:
        """
        Execute workflow using wave-based execution.
        
        Returns ExecutionContext with results.
        """
        # Validate workflow
        validate_workflow_v2(workflow_def, self.agent_service)
        await validate_agents_exist(workflow_def, self.agent_service)
        
        # Create execution context
        execution_id = f"exec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(execution_id, workflow_def.workflow_id)
        context.initial_message = initial_message  # Store for start nodes
        
        # Create History MCP session (fails gracefully if unavailable)
        history_session_id = await self.logger.create_session(
            workflow_def.workflow_id,
            workflow_def.name
        )
        context.history_session_id = history_session_id
        
        # Build dependency map
        dependencies = self._build_dependency_map(workflow_def)
        
        try:
            # Execute in waves
            while len(context.completed_nodes) < len(workflow_def.nodes):
                # Get ready nodes (all dependencies satisfied)
                ready_nodes = self._get_ready_nodes(workflow_def, dependencies, context)
                
                if not ready_nodes:
                    # No ready nodes but workflow incomplete - invalid DAG or deadlock
                    incomplete_nodes = [n.node_id for n in workflow_def.nodes if n.node_id not in context.completed_nodes]
                    raise WorkflowExecutionError(
                        f"DAG execution deadlock: No ready nodes but {len(incomplete_nodes)} nodes incomplete. "
                        f"Incomplete nodes: {incomplete_nodes}. This indicates a validation bug or circular dependency."
                    )
                
                # Execute wave in parallel
                await self._execute_wave(ready_nodes, workflow_def, context, history_session_id)
            
            # Log workflow completion
            await self.logger.log_workflow_complete(
                history_session_id,
                workflow_def.workflow_id,
                "completed",
                context.node_results
            )
            
        except Exception as e:
            # Log error
            if isinstance(e, NodeExecutionException):
                await self.logger.log_error(
                    history_session_id,
                    e.node_id,
                    e.agent_id,
                    str(e),
                    e.context
                )
            
            # Log workflow failure
            await self.logger.log_workflow_complete(
                history_session_id,
                workflow_def.workflow_id,
                "failed"
            )
            
            raise
        finally:
            context.finalize()
            await self.logger.close()
        
        return context
    
    def _build_dependency_map(self, workflow_def: WorkflowV2Definition) -> Dict[str, Set[str]]:
        """Build map of node_id -> set of parent node_ids"""
        dependencies: Dict[str, Set[str]] = {node.node_id: set() for node in workflow_def.nodes}
        
        for edge in workflow_def.edges:
            dependencies[edge.to].add(edge.from_)
        
        return dependencies
    
    def _get_ready_nodes(
        self,
        workflow_def: WorkflowV2Definition,
        dependencies: Dict[str, Set[str]],
        context: ExecutionContext
    ) -> List[WorkflowV2Node]:
        """Get nodes ready to execute (all dependencies satisfied)"""
        ready = []
        
        for node in workflow_def.nodes:
            if context.is_completed(node.node_id):
                continue
            
            # Check if all dependencies are satisfied
            deps = dependencies[node.node_id]
            if all(context.is_completed(dep) for dep in deps):
                ready.append(node)
        
        return ready
    
    async def _execute_wave(
        self,
        nodes: List[WorkflowV2Node],
        workflow_def: WorkflowV2Definition,
        context: ExecutionContext,
        history_session_id: str = None
    ) -> None:
        """Execute a wave of nodes in parallel"""
        tasks = [
            self._execute_node(node, workflow_def, context, history_session_id)
            for node in nodes
        ]
        
        # Wait for all nodes in wave to complete, capturing exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for failures and raise the first exception found
        for result in results:
            if isinstance(result, Exception):
                raise result
    
    async def _execute_node(
        self,
        node: WorkflowV2Node,
        workflow_def: WorkflowV2Definition,
        context: ExecutionContext,
        history_session_id: str = None
    ) -> None:
        """Execute a single node"""
        # Log node start
        await self.logger.log_node_start(history_session_id, node.node_id, node.agent_id)
        
        # Get agent definition
        agent_def = await self.agent_service.get_agent(node.agent_id)
        
        # Prepare task and context for agent
        task, agent_context = self._prepare_agent_input(node, workflow_def, context)
        
        # Execute agent with timeout
        try:
            result = await asyncio.wait_for(
                self.agent_runtime.run_agent(
                    agent_definition=agent_def,
                    task=task,
                    context=agent_context
                ),
                timeout=node.timeout
            )
        except asyncio.TimeoutError:
            raise NodeTimeoutException(node.node_id, node.agent_id, node.timeout)
        
        # Check agent status
        if result.get("status") != "completed":
            raise NodeExecutionException(
                node.node_id,
                node.agent_id,
                result.get("error", "Agent execution failed"),
                context=result
            )
        
        # Log node completion
        await self.logger.log_node_complete(
            history_session_id,
            node.node_id,
            node.agent_id,
            result
        )
        
        # Mark node as completed
        context.mark_completed(node.node_id, result)
    
    def _prepare_agent_input(
        self,
        node: WorkflowV2Node,
        workflow_def: WorkflowV2Definition,
        context: ExecutionContext
    ) -> tuple[str, Dict[str, Any]]:
        """
        Prepare task and context for agent execution.
        
        For serial nodes: task = previous node's answer
        For convergence nodes: context = {branch_name: answer, ...}
        """
        # Find parent nodes
        parent_nodes = [
            edge.from_ for edge in workflow_def.edges
            if edge.to == node.node_id
        ]
        
        if not parent_nodes:
            # Start node - use initial message if provided
            task = context.initial_message or ""
            return task, {}
        
        if len(parent_nodes) == 1:
            # Serial execution - pass previous answer as task
            parent_result = context.get_result(parent_nodes[0])
            task = parent_result.get("answer", "")
            return task, {}
        
        # Convergence - multiple parents
        # Build context with branch names
        agent_context = {}
        for parent_id in parent_nodes:
            parent_result = context.get_result(parent_id)
            
            # Get branch name (from parent node definition)
            parent_node = next(n for n in workflow_def.nodes if n.node_id == parent_id)
            branch_name = parent_node.branch_name or parent_node.node_id
            
            agent_context[branch_name] = parent_result.get("answer", "")
        
        # For convergence, task can be empty or workflow-defined
        # Agent uses context to synthesize results
        return "Synthesize the results", agent_context
