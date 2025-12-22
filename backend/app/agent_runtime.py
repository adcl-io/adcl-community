# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Autonomous Agent Runtime
Enables agents to autonomously chain MCP tool calls using ReAct pattern
"""

from typing import Dict, List, Any, Optional
import json
import asyncio
import aiohttp
import logging
from datetime import datetime
from app.token_tracker import get_token_tracker
from app.utils.token_counter import get_token_counter
from app.mcp_session_manager import MCPSessionManager

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime for autonomous agents that can use MCPs as tools.
    Implements ReAct pattern: Reason → Act → Observe loop
    """

    def __init__(self, mcp_registry, anthropic_client, openai_client=None):
        """
        Initialize Agent Runtime

        Args:
            mcp_registry: MCPRegistry instance with registered MCP servers
            anthropic_client: Anthropic API client
            openai_client: OpenAI API client (optional)
        """
        self.mcp_registry = mcp_registry
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client
        self.mcp_session_manager = MCPSessionManager()

    def _get_client_for_model(self, model_name: str):
        """Determine which client to use based on model name"""
        if model_name.startswith("gpt-") or model_name.startswith("o1-"):
            if not self.openai_client:
                raise ValueError(f"OpenAI client not configured but model {model_name} requires it")
            return "openai", self.openai_client
        elif model_name.startswith("claude-"):
            return "anthropic", self.anthropic_client
        else:
            # Default to Anthropic for unknown models
            return "anthropic", self.anthropic_client

    async def run_agent(
        self,
        agent_definition: Dict[str, Any],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run an autonomous agent on a task

        Args:
            agent_definition: Agent configuration with persona, tools, etc.
            task: The task/goal for the agent
            context: Additional context (files, data, etc.)
            progress_callback: Optional callback for progress updates (ADCL: dual logging)

        Returns:
            Result with agent's final answer, tools used, thinking process
        """
        print(
            f"\n🚀 run_agent() called for agent: {agent_definition.get('name', 'unknown')}"
        )
        print(f"📋 Requested MCPs: {agent_definition.get('available_mcps', [])}")
        print(f"📚 Registry has: {list(self.mcp_registry.servers.keys())}")

        # Build tool definitions from available MCPs
        tools = await self._build_tools_from_mcps(agent_definition["available_mcps"])

        if not tools:
            registry_servers = list(self.mcp_registry.servers.keys())
            requested_mcps = agent_definition['available_mcps']
            return {
                "status": "error",
                "error": (
                    f"No tools available for this agent. "
                    f"Registry has: {registry_servers}, Agent requested: {requested_mcps}"
                ),
                "agent_id": agent_definition.get("id"),
                "debug": {
                    "registry_servers": list(self.mcp_registry.servers.keys()),
                    "requested_mcps": agent_definition.get("available_mcps", []),
                },
            }

        # Initialize conversation with system prompt and task
        messages = [
            {
                "role": "user",
                "content": self._build_initial_prompt(agent_definition, task, context),
            }
        ]

        # Agent loop tracking
        iteration = 0
        max_iterations = agent_definition.get("capabilities", {}).get(
            "max_iterations", 10
        )
        tool_uses = []
        reasoning_steps = []

        # Track which provider we're using for proper message formatting
        model_name = agent_definition["model_config"]["model"]
        provider_type, _ = self._get_client_for_model(model_name)

        print(f"\n🤖 Starting autonomous agent: {agent_definition['name']}")
        print(f"📋 Task: {task}")
        print(f"🔧 Available tools: {', '.join(agent_definition['available_mcps'])}")
        print(f"🔄 Max iterations: {max_iterations}\n")

        while iteration < max_iterations:
            iteration += 1

            # Check if execution has been cancelled
            if session_id and manager and manager.is_cancelled(session_id):
                print(f"🛑 Agent execution cancelled for session {session_id}")
                return {
                    "status": "cancelled",
                    "message": "Execution cancelled by user",
                    "iterations": iteration - 1,  # Don't count the cancelled iteration
                    "tools_used": tool_uses,
                    "reasoning_steps": reasoning_steps,
                    "agent_id": agent_definition.get("id"),
                    "agent_name": agent_definition.get("name"),
                }

            # Dual logging (ADCL principle: print for Docker logs AND callback for SSE)
            print(f"  Iteration {iteration}/{max_iterations}...")

            # Send iteration start event
            if progress_callback:
                await progress_callback(
                    {
                        "type": "iteration_start",
                        "agent": agent_definition.get("id", agent_definition.get("name")),
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                    }
                )

            try:
                # Determine which AI provider to use
                model_name = agent_definition["model_config"]["model"]
                provider, client = self._get_client_for_model(model_name)

                # Validate request size BEFORE sending to API (fail fast)
                token_counter = get_token_counter()
                validation = token_counter.validate_request_size(messages, model_name)

                if not validation["valid"]:
                    # Pre-emptive failure - don't waste API call
                    error_msg = (
                        f"Request too large for model {model_name}:\n"
                        f"- Tokens in request: {validation['token_count']}\n"
                        f"- Model limit (with safety margin): {validation['limit']}\n\n"
                        f"Suggestions:\n"
                        f"- Reduce agent max_iterations (currently {max_iterations})\n"
                        f"- Use fewer agents in the team\n"
                        f"- Switch to a model with higher limits (e.g., gpt-4-turbo: 120K tokens)\n"
                        f"- Summarize previous outputs before passing to next agent\n"
                    )
                    print(f"❌ {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "iterations": iteration - 1,  # Don't count this iteration
                        "tools_used": tool_uses,
                        "reasoning_steps": reasoning_steps,
                        "token_count": validation['token_count'],
                        "token_limit": validation['limit'],
                    }

                # Agent reasons and decides next action
                if provider == "anthropic":
                    response = client.messages.create(
                        model=model_name,
                        max_tokens=agent_definition["model_config"]["max_tokens"],
                        temperature=agent_definition["model_config"].get(
                            "temperature", 0.7
                        ),
                        system=agent_definition["persona"]["system_prompt"],
                        messages=messages,
                        tools=tools,
                    )
                elif provider == "openai":
                    # OpenAI uses different format - convert tools and make API call
                    openai_tools = self._convert_tools_to_openai_format(tools)

                    # Convert messages to OpenAI format
                    openai_messages = self._convert_messages_to_openai_format(
                        messages,
                        agent_definition["persona"]["system_prompt"]
                    )

                    response = client.chat.completions.create(
                        model=model_name,
                        messages=openai_messages,
                        tools=openai_tools if openai_tools else None,
                        max_tokens=agent_definition["model_config"]["max_tokens"],
                        temperature=agent_definition["model_config"].get("temperature", 0.7),
                    )

                    # Convert OpenAI response to Anthropic-like format for unified handling
                    response = self._convert_openai_response_to_anthropic_format(response)
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                # Extract token usage from response
                token_usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

                # Track tokens in backend (single source of truth)
                cumulative_tokens = None
                if session_id:
                    tracker = get_token_tracker()
                    model = agent_definition["model_config"]["model"]
                    state = tracker.add_tokens(
                        session_id=session_id,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        model=model
                    )
                    cumulative_tokens = {
                        "total_input_tokens": state["total_input_tokens"],
                        "total_output_tokens": state["total_output_tokens"],
                        "total_cost": state["total_cost"]
                    }

                # Extract reasoning (text blocks before tool use)
                reasoning = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        reasoning += block.text

                if reasoning.strip():
                    reasoning_steps.append(
                        {"iteration": iteration, "thinking": reasoning.strip()}
                    )
                    print(f"    💭 Thinking: {reasoning.strip()[:100]}...")

                    # Send reasoning as separate event for better visibility
                    if progress_callback:
                        await progress_callback(
                            {
                                "type": "agent_reasoning",
                                "agent": agent_definition.get("id", agent_definition.get("name")),
                                "reasoning": reasoning.strip(),
                                "iteration": iteration,
                            }
                        )

                # Extract tool calls info for display
                tool_calls_info = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_info = {
                            "name": block.name,
                            "id": block.id,
                            "input": block.input
                        }
                        tool_calls_info.append(tool_info)

                # Send iteration details via callback
                if progress_callback:
                    callback_data = {
                        "type": "agent_iteration",
                        "agent": agent_definition.get("id", agent_definition.get("name")),
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "token_usage": token_usage,
                        "model": agent_definition["model_config"]["model"],
                        "thinking_preview": (
                            reasoning.strip()[:500] if reasoning.strip() else None
                        ),  # Short preview
                            "thinking": (
                                reasoning.strip() if reasoning.strip() else None
                            ),  # Full reasoning
                            "tools_used": tool_calls_info,
                            "stop_reason": response.stop_reason,
                        }

                    # Add cumulative totals (backend is source of truth)
                    if cumulative_tokens:
                        callback_data["cumulative_tokens"] = cumulative_tokens

                    await progress_callback(callback_data)

                # Check if agent wants to use tools
                if response.stop_reason == "tool_use":
                    # Extract tool calls
                    tool_calls = [
                        block for block in response.content if block.type == "tool_use"
                    ]

                    print(f"    🔧 Using {len(tool_calls)} tool(s)...")

                    # Execute each tool call via MCP
                    tool_results = []
                    for tool_call in tool_calls:
                        print(f"      → {tool_call.name}")

                        # Send real-time update for this specific tool call
                        if progress_callback:
                            await progress_callback(
                                {
                                    "type": "tool_execution",
                                    "agent": agent_definition.get("id", agent_definition.get("name")),
                                    "tool_name": tool_call.name,
                                    "tool_input": tool_call.input,
                                    "iteration": iteration,
                                }
                            )

                        result = await self._execute_mcp_tool(
                            tool_call.name,
                            tool_call.input,
                            agent_definition["available_mcps"],
                        )

                        # Send tool result update immediately after execution
                        if progress_callback:
                            await progress_callback(
                                {
                                    "type": "tool_result",
                                    "agent": agent_definition.get("id", agent_definition.get("name")),
                                    "tool_name": tool_call.name,
                                    "tool_input": tool_call.input,
                                    "result": result,
                                    "iteration": iteration,
                                    "success": "error" not in result,
                                }
                            )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": json.dumps(result),
                            }
                        )

                        tool_uses.append(
                            {
                                "iteration": iteration,
                                "tool": tool_call.name,
                                "input": tool_call.input,
                                "result": result,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                    # Add assistant response and tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                elif response.stop_reason == "end_turn":
                    # Agent is done - extract final answer
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text

                    print(f"\n✅ Agent completed task in {iteration} iterations\n")

                    # Send final answer update before returning
                    if progress_callback:
                        await progress_callback(
                            {
                                "type": "agent_answer",
                                "agent": agent_definition.get("id", agent_definition.get("name")),
                                "answer": final_text,
                                "iteration": iteration,
                                "total_iterations": iteration,
                                "status": "completed",
                            }
                        )

                    result = {
                        "status": "completed",
                        "answer": final_text,
                        "iterations": iteration,
                        "tools_used": tool_uses,
                        "reasoning_steps": reasoning_steps,
                        "conversation_history": messages,
                        "agent_id": agent_definition.get("id"),
                        "agent_name": agent_definition.get("name"),
                        "token_usage": token_usage,  # Token usage for this agent
                    }

                    # Add cumulative tokens if tracking is enabled
                    if cumulative_tokens:
                        result["cumulative_tokens"] = cumulative_tokens

                    return result
                else:
                    # Unexpected stop reason
                    print(f"⚠️  Unexpected stop reason: {response.stop_reason}")
                    break

            except Exception as e:
                import traceback
                error_details = str(e)
                print(f"❌ Error in iteration {iteration}: {error_details}")
                print(f"   Full traceback: {traceback.format_exc()}")

                # Provide user-friendly error messages for common issues
                if "credit balance is too low" in error_details.lower():
                    model_provider = agent_definition['model_config']['model'].split('-')[0].upper()
                    error_details = (
                        f"Insufficient API credits. Please add credits to your {model_provider} account.\n\n"
                        f"Original error: {error_details}"
                    )
                elif "api key" in error_details.lower():
                    model_name = agent_definition['model_config']['model']
                    error_details = (
                        f"API key issue for model {model_name}.\n\n"
                        f"Original error: {error_details}"
                    )
                elif "rate_limit" in error_details.lower() or "429" in error_details:
                    # OpenAI/Anthropic rate limit error
                    model_name = agent_definition['model_config']['model']
                    error_details = (
                        f"Rate limit exceeded for model {model_name}. "
                        f"This often happens when the input context is too large for your tier.\n\n"
                        f"Suggestions:\n"
                        f"- Reduce the number of agents in the team\n"
                        f"- Limit agent max_iterations to reduce message history\n"
                        f"- Use a model with higher token limits (e.g., gpt-4-turbo)\n"
                        f"- Upgrade your API tier for higher rate limits\n\n"
                        f"Original error: {error_details}"
                    )

                return {
                    "status": "error",
                    "error": error_details,
                    "iterations": iteration,
                    "tools_used": tool_uses,
                    "reasoning_steps": reasoning_steps,
                }

        # Max iterations reached
        print(f"\n⚠️  Agent reached max iterations ({max_iterations})\n")

        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "tools_used": tool_uses,
            "reasoning_steps": reasoning_steps,
            "partial_result": messages[-1] if messages else None,
        }

    async def _build_tools_from_mcps(self, mcp_names: List[str]) -> List[Dict]:
        """Convert MCP tool definitions to Claude tool format"""
        tools = []

        print(f"🔍 Building tools from MCPs: {mcp_names}")
        print(f"📚 Registry has: {list(self.mcp_registry.servers.keys())}")

        for mcp_name in mcp_names:
            print(f"  🔎 Looking up MCP: {mcp_name}")
            mcp_info = self.mcp_registry.get(mcp_name)
            if not mcp_info:
                print(f"  ⚠️  MCP '{mcp_name}' not found in registry")
                print(f"  📚 Available MCPs: {list(self.mcp_registry.servers.keys())}")
                continue

            print(f"  ✅ Found MCP '{mcp_name}' at {mcp_info.endpoint}")

            # Get MCP's tool definitions
            mcp_tools = await self._fetch_mcp_tools(mcp_info.endpoint)
            print(f"  📥 Fetched {len(mcp_tools)} tools from {mcp_name}")

            for mcp_tool in mcp_tools:
                # Validate required MCP tool fields (fail fast)
                if "name" not in mcp_tool:
                    logger.warning(
                        f"Tool from {mcp_name} missing required 'name' field, skipping",
                        extra={"mcp": mcp_name, "tool_keys": list(mcp_tool.keys())}
                    )
                    continue

                tool_name_mcp = mcp_tool["name"]

                if "inputSchema" not in mcp_tool:
                    logger.error(
                        f"Tool '{tool_name_mcp}' from {mcp_name} missing required 'inputSchema' field - SKIPPING",
                        extra={
                            "mcp": mcp_name,
                            "tool": tool_name_mcp,
                            "available_keys": list(mcp_tool.keys()),
                            "note": "MCP server not compliant with protocol - tool will not be available to agent"
                        }
                    )
                    # Skip this tool entirely - cannot be called without schema
                    continue

                # Use double underscore as separator (periods not allowed by Anthropic)
                tool_name = f"{mcp_name}__{tool_name_mcp}"

                # Protocol boundary translation: MCP camelCase → Anthropic snake_case
                # MCP spec uses camelCase, Anthropic API requires snake_case
                tools.append(
                    {
                        "name": tool_name,
                        "description": f"[{mcp_name}] {mcp_tool.get('description', '')}",
                        "input_schema": mcp_tool["inputSchema"],
                    }
                )

        return tools

    def _convert_messages_to_openai_format(self, messages: List[Dict], system_prompt: str) -> List[Dict]:
        """Convert message history to OpenAI format"""
        openai_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                # Check if this is tool results (list format)
                if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                    # This is tool results - convert to OpenAI format
                    for tool_result in content:
                        if tool_result.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_result.get("tool_use_id"),
                                "content": tool_result.get("content", "")
                            })
                else:
                    # Regular user message
                    openai_messages.append({"role": "user", "content": content})

            elif role == "assistant":
                # Convert assistant message with possible tool calls
                if isinstance(content, list):
                    # Extract text and tool calls from content blocks
                    text_parts = []
                    tool_calls = []

                    for block in content:
                        # Handle both object and dict formats
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                            elif block.get('type') == 'tool_use':
                                # Convert double underscore to hyphen for OpenAI compatibility
                                openai_name = block['name'].replace("__", "-")

                                tool_calls.append({
                                    "id": block['id'],
                                    "type": "function",
                                    "function": {
                                        "name": openai_name,
                                        "arguments": json.dumps(block['input'])
                                    }
                                })
                        elif hasattr(block, 'text'):
                            text_parts.append(block.text)
                        elif hasattr(block, 'type') and block.type == 'tool_use':
                            # Convert double underscore to hyphen for OpenAI compatibility
                            openai_name = block.name.replace("__", "-")

                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": openai_name,
                                    "arguments": json.dumps(block.input)
                                }
                            })

                    # Build OpenAI assistant message
                    assistant_msg = {
                        "role": "assistant",
                        "content": "\n".join(text_parts) if text_parts else None
                    }
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls

                    openai_messages.append(assistant_msg)
                else:
                    # Simple text response
                    openai_messages.append({"role": "assistant", "content": content})

        return openai_messages

    def _convert_tools_to_openai_format(self, claude_tools: List[Dict]) -> List[Dict]:
        """Convert Claude tool format to OpenAI tool format

        Note: OpenAI has strict naming requirements. We replace double underscores
        with single hyphens to ensure compatibility while maintaining uniqueness.
        """
        openai_tools = []
        for tool in claude_tools:
            # Convert double underscore separator to hyphen for OpenAI compatibility
            openai_name = tool["name"].replace("__", "-")

            openai_tool = {
                "type": "function",
                "function": {
                    "name": openai_name,
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def _convert_openai_response_to_anthropic_format(self, openai_response):
        """Convert OpenAI response to Anthropic-like format for unified handling"""

        # Create a mock Anthropic-like response object
        class MockAnthropicResponse:
            def __init__(self, openai_resp):
                self.usage = type('obj', (object,), {
                    'input_tokens': openai_resp.usage.prompt_tokens,
                    'output_tokens': openai_resp.usage.completion_tokens,
                })()

                # Convert message content to Anthropic format
                self.content = []
                message = openai_resp.choices[0].message

                # Add text content if present
                if message.content:
                    text_block = type('obj', (object,), {
                        'type': 'text',
                        'text': message.content
                    })()
                    self.content.append(text_block)

                # Add tool calls if present
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        # Convert hyphenated OpenAI names back to double underscore format
                        claude_name = tool_call.function.name.replace("-", "__")

                        tool_use_block = type('obj', (object,), {
                            'type': 'tool_use',
                            'id': tool_call.id,
                            'name': claude_name,  # Use original double underscore format
                            'input': json.loads(tool_call.function.arguments)
                        })()
                        self.content.append(tool_use_block)

                # Determine stop reason
                finish_reason = openai_resp.choices[0].finish_reason
                if finish_reason == "tool_calls":
                    self.stop_reason = "tool_use"
                elif finish_reason == "stop":
                    self.stop_reason = "end_turn"
                else:
                    self.stop_reason = finish_reason

        return MockAnthropicResponse(openai_response)

    def _build_initial_prompt(
        self, agent_def: Dict, task: str, context: Optional[Dict]
    ) -> str:
        """Build the initial prompt for the agent"""

        tool_list = "\n".join([f"  - {mcp}" for mcp in agent_def["available_mcps"]])

        prompt = f"""Your task: {task}

You have access to the following MCP tool servers:
{tool_list}

Each MCP provides multiple tools. Use them strategically to complete the task.

Think step by step and use tools as needed. When you have completed the task, provide a
comprehensive summary of your findings and work.
"""

        # Add non-agent context only (avoid duplication with task description)
        # Agent outputs are already summarized in the task string from team_runtime
        if context:
            # Filter out agent outputs to avoid duplication
            non_agent_context = {
                k: v for k, v in context.items()
                if not k.startswith("agent_") and not k.startswith("round")
            }
            if non_agent_context:
                # Use token-based truncation (not character-based)
                token_counter = get_token_counter()
                max_context_tokens = token_counter.get_config_limits()["additional_context_max_tokens"]
                model_name = agent_def["model_config"]["model"]

                context_str = json.dumps(non_agent_context, indent=2)
                context_str = token_counter.truncate_to_token_limit(
                    context_str,
                    max_context_tokens,
                    model_name
                )
                prompt += f"\n\nAdditional context:\n{context_str}\n"

        return prompt

    async def _execute_mcp_tool(
        self, tool_name: str, params: Dict, available_mcps: List[str]
    ) -> Dict[str, Any]:
        """Execute an MCP tool call"""

        # Parse tool name: "mcp_name__tool_name" (double underscore separator)
        parts = tool_name.split("__", 1)
        if len(parts) != 2:
            return {
                "error": f"Invalid tool name format: {tool_name}. Expected 'mcp_name__tool_name'"
            }

        mcp_name, mcp_tool = parts

        if mcp_name not in available_mcps:
            return {"error": f"MCP '{mcp_name}' not available to this agent"}

        # Get MCP endpoint from registry
        mcp_info = self.mcp_registry.get(mcp_name)
        if not mcp_info:
            return {"error": f"MCP '{mcp_name}' not found in registry"}

        # Call MCP via HTTP
        result = await self._call_mcp(mcp_info.endpoint, mcp_tool, params)

        return result

    async def _call_mcp(self, endpoint: str, tool: str, params: Dict) -> Dict:
        """Make HTTP call to MCP server using MCPSessionManager"""
        try:
            result = await self.mcp_session_manager.call_tool(endpoint, tool, params)
            return result
        except Exception as e:
            return {"error": f"MCP call failed: {str(e)}"}

    async def _fetch_mcp_tools(self, endpoint: str) -> List[Dict]:
        """Fetch tool definitions from MCP server using MCPSessionManager"""
        try:
            tools = await self.mcp_session_manager.list_tools(endpoint)
            return tools
        except Exception as e:
            print(f"⚠️  Could not fetch tools from {endpoint}: {e}")
            return []
