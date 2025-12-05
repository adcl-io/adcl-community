# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
BaseAgent - Actor model worker with persona-based behavior

This is the core agent class that combines:
- Actor model infrastructure (isolated process, message passing)
- Persona-based configuration (prompts, tools, parameters)
- MCP client integration
- LLM reasoning loop
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from uuid import uuid4
from datetime import datetime

from api.models import PersonaConfig, AgentTask, TaskType, WSMessage, WSMessageType
from api.redis_queue import redis_queue


class BaseAgent:
    """
    Actor-like worker process with persona configuration.

    Each agent instance:
    - Runs independently (actor model)
    - Receives tasks via Redis queue (message passing)
    - Uses persona config for behavior (system prompt, tools, params)
    - Calls MCP servers for actual operations
    - Reports progress via Redis pub/sub
    """

    def __init__(
        self,
        agent_id: str,
        persona: str,
        config: PersonaConfig,
        campaign_id: Optional[str] = None
    ):
        self.id = agent_id
        self.persona = persona
        self.config = config
        self.campaign_id = campaign_id

        # LLM client (will be initialized based on config.llm_model)
        self.llm = None

        # MCP clients (will be initialized based on config.mcp_servers)
        self.mcp_clients: Dict[str, Any] = {}

        # Agent state
        self.running = False
        self.tasks_completed = 0
        self.current_task: Optional[AgentTask] = None

        # Memory store
        self.memory: Dict[str, Any] = {
            "findings": [],
            "scan_results": [],
            "context": []
        }

    async def initialize(self):
        """Initialize LLM and MCP connections"""
        # Initialize LLM client
        self.llm = await self._init_llm()

        # Initialize MCP clients
        for mcp_server in self.config.mcp_servers:
            self.mcp_clients[mcp_server] = await self._init_mcp_client(mcp_server)

        print(f"[Agent {self.id}] Initialized with persona '{self.persona}'")
        print(f"[Agent {self.id}] MCP servers: {list(self.mcp_clients.keys())}")

    async def _init_llm(self):
        """Initialize LLM client based on config"""
        model = self.config.llm_model.lower()

        if "claude" in model:
            # Initialize Anthropic client
            try:
                from anthropic import AsyncAnthropic
                import os

                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key or api_key == "sk-ant-test":
                    print(f"[Agent {self.id}] Warning: No valid Anthropic API key, using mock LLM")
                    return MockLLM()

                return AsyncAnthropic(api_key=api_key)
            except ImportError:
                print(f"[Agent {self.id}] Warning: anthropic package not installed, using mock LLM")
                return MockLLM()

        elif "gpt" in model:
            # Initialize OpenAI client
            try:
                from openai import AsyncOpenAI
                import os

                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key or api_key == "sk-test":
                    print(f"[Agent {self.id}] Warning: No valid OpenAI API key, using mock LLM")
                    return MockLLM()

                return AsyncOpenAI(api_key=api_key)
            except ImportError:
                print(f"[Agent {self.id}] Warning: openai package not installed, using mock LLM")
                return MockLLM()

        else:
            print(f"[Agent {self.id}] Unknown model: {model}, using mock LLM")
            return MockLLM()

    async def _init_mcp_client(self, server_name: str):
        """Initialize MCP client for a server"""
        # For now, return a mock MCP client
        # In production, this would connect to the actual MCP server
        return MockMCPClient(server_name)

    async def run(self):
        """
        Main agent loop - actor model worker

        1. Pull tasks from Redis queue (message passing)
        2. Execute task using LLM reasoning + MCP tools
        3. Report results via pub/sub
        4. Send heartbeat
        """
        self.running = True
        print(f"[Agent {self.id}] Starting main loop")

        idle_count = 0
        max_idle = 3  # Stop after 3 consecutive empty queue checks (15 seconds)

        try:
            while self.running and self.tasks_completed < self.config.max_tasks:
                # Send heartbeat
                await redis_queue.agent_heartbeat(self.id, ttl=30)

                # Get next task from queue (blocking with timeout)
                task = await redis_queue.pop_task(self.id, timeout=5)

                if task is None:
                    # No task available
                    idle_count += 1
                    if idle_count >= max_idle:
                        print(f"[Agent {self.id}] No tasks for {max_idle * 5}s, stopping")
                        break
                    await asyncio.sleep(1)
                    continue

                # Reset idle counter when we get a task
                idle_count = 0

                # Execute task
                self.current_task = task
                await self._execute_task(task)
                self.tasks_completed += 1
                self.current_task = None

                # Update state in Redis
                await redis_queue.set_agent_state(self.id, {
                    "status": "running",
                    "tasks_completed": self.tasks_completed,
                    "persona": self.persona
                })

        except Exception as e:
            print(f"[Agent {self.id}] Error in main loop: {e}")
            await self._publish_error(str(e))
        finally:
            self.running = False
            print(f"[Agent {self.id}] Stopped (completed {self.tasks_completed} tasks)")

    async def _execute_task(self, task: AgentTask):
        """
        Execute a task using LLM reasoning + MCP tools

        This is the core reasoning loop:
        1. Analyze task with LLM
        2. Call appropriate MCP tools
        3. Process results
        4. Store findings
        5. Report progress
        """
        print(f"[Agent {self.id}] Executing task: {task.task_type} on {task.target}")

        # Publish task start
        await self._publish_update({
            "event": "task_start",
            "task_type": task.task_type,
            "target": task.target
        })

        try:
            # Build context for LLM
            context = self._build_context(task)

            # Get LLM decision on what to do
            action = await self._llm_reasoning(context, task)

            # Execute action via MCP
            result = await self._execute_mcp_action(action, task)

            # Process and store results
            await self._process_results(result, task)

            # Publish completion
            await self._publish_update({
                "event": "task_complete",
                "task_type": task.task_type,
                "target": task.target,
                "result": "success"
            })

        except Exception as e:
            print(f"[Agent {self.id}] Task execution failed: {e}")
            await self._publish_update({
                "event": "task_failed",
                "task_type": task.task_type,
                "target": task.target,
                "error": str(e)
            })

    def _build_context(self, task: AgentTask) -> str:
        """Build context for LLM based on task and memory"""
        context = f"""
You are a {self.persona} agent.

Your role: {self.config.system_prompt}

Current task:
- Type: {task.task_type}
- Target: {task.target}
- Parameters: {json.dumps(task.parameters, indent=2)}

Available MCP tools:
{', '.join(self.mcp_clients.keys())}

Previous findings:
{json.dumps(self.memory.get('findings', [])[-5:], indent=2)}

What action should you take?
"""
        return context

    async def _llm_reasoning(self, context: str, task: AgentTask) -> Dict[str, Any]:
        """
        Use LLM to decide what action to take

        Returns action plan with tool calls
        """
        # For now, return a simple action based on task type
        # In production, this would call the actual LLM

        if task.task_type == TaskType.RECON:
            return {
                "tool": "nmap",
                "action": "port_scan",
                "parameters": {
                    "target": task.target,
                    "scan_type": task.parameters.get("scan_type", "quick")
                }
            }

        elif task.task_type == TaskType.EXPLOIT:
            return {
                "tool": "web_tools",
                "action": "vulnerability_scan",
                "parameters": {
                    "target": task.target
                }
            }

        else:
            return {
                "tool": "generic",
                "action": "analyze",
                "parameters": task.parameters
            }

    async def _execute_mcp_action(self, action: Dict[str, Any], task: AgentTask) -> Dict[str, Any]:
        """Execute action via MCP client"""
        tool_name = action.get("tool")
        mcp_client = self.mcp_clients.get(tool_name)

        if not mcp_client:
            raise Exception(f"MCP client '{tool_name}' not available")

        # Call MCP tool
        result = await mcp_client.call_tool(
            action.get("action"),
            action.get("parameters", {})
        )

        return result

    async def _process_results(self, result: Dict[str, Any], task: AgentTask):
        """Process MCP results and store findings"""
        # Store in memory
        self.memory["scan_results"].append({
            "task_id": str(task.id),
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        })

        # Extract findings (mock for now)
        if result.get("findings"):
            for finding in result["findings"]:
                self.memory["findings"].append(finding)

                # Publish finding
                await self._publish_finding(finding)

    async def _publish_update(self, data: Dict[str, Any]):
        """Publish update via Redis pub/sub"""
        if not self.campaign_id:
            return

        message = WSMessage(
            type=WSMessageType.AGENT_STATUS,
            campaign_id=self.campaign_id,
            data={
                "agent_id": self.id,
                "persona": self.persona,
                **data
            }
        )

        await redis_queue.publish_update(self.campaign_id, message)

    async def _publish_finding(self, finding: Dict[str, Any]):
        """Publish finding via Redis pub/sub"""
        if not self.campaign_id:
            return

        message = WSMessage(
            type=WSMessageType.FINDING,
            campaign_id=self.campaign_id,
            data={
                "agent_id": self.id,
                "finding": finding
            }
        )

        await redis_queue.publish_update(self.campaign_id, message)

    async def _publish_error(self, error: str):
        """Publish error via Redis pub/sub"""
        if not self.campaign_id:
            return

        message = WSMessage(
            type=WSMessageType.ERROR,
            campaign_id=self.campaign_id,
            data={
                "agent_id": self.id,
                "persona": self.persona,
                "error": error
            }
        )

        await redis_queue.publish_update(self.campaign_id, message)

    async def stop(self):
        """Stop agent gracefully"""
        print(f"[Agent {self.id}] Stopping...")
        self.running = False


# ============================================================================
# Mock implementations for testing without API keys
# ============================================================================

class MockLLM:
    """Mock LLM for testing"""

    async def messages_create(self, **kwargs):
        """Mock Anthropic API"""
        return type('obj', (object,), {
            'content': [type('obj', (object,), {
                'text': 'Mock LLM response: Execute port scan on target'
            })()]
        })()

    async def chat_completions_create(self, **kwargs):
        """Mock OpenAI API"""
        return type('obj', (object,), {
            'choices': [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': 'Mock LLM response: Execute port scan on target'
                })()
            })()]
        })()


class MockMCPClient:
    """Mock MCP client for testing"""

    def __init__(self, server_name: str):
        self.server_name = server_name

    async def call_tool(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mock MCP tool call"""
        print(f"[MockMCP:{self.server_name}] Calling {action} with {parameters}")

        # Return mock results based on server type
        if self.server_name == "nmap":
            return {
                "status": "success",
                "target": parameters.get("target"),
                "ports": [
                    {"port": 80, "state": "open", "service": "http"},
                    {"port": 443, "state": "open", "service": "https"},
                    {"port": 22, "state": "open", "service": "ssh"}
                ],
                "findings": [
                    {
                        "title": "Open HTTP port",
                        "severity": "info",
                        "description": "Port 80 is open and running HTTP service"
                    }
                ]
            }

        return {
            "status": "success",
            "message": f"Mock {action} completed",
            "findings": []
        }
