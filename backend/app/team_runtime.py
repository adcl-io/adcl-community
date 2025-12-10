# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Multi-Agent Team Runtime
Enables teams of autonomous agents to collaborate on complex tasks
"""

from typing import Dict, List, Any, Optional
import json
import asyncio
import logging
from datetime import datetime
from app.utils.token_counter import get_token_counter

logger = logging.getLogger(__name__)


class TeamRuntime:
    """
    Runtime for multi-agent teams.
    Coordinates multiple autonomous agents working together on a task.
    """

    def __init__(self, agent_runtime, agents_dir, teams_dir):
        """
        Initialize Team Runtime

        Args:
            agent_runtime: AgentRuntime instance for running individual agents
            agents_dir: Path to agent definitions directory
            teams_dir: Path to team definitions directory
        """
        self.agent_runtime = agent_runtime
        self.agents_dir = agents_dir
        self.teams_dir = teams_dir

        # Add locks for thread-safe operations in parallel mode
        self._results_lock = asyncio.Lock()
        self._log_lock = asyncio.Lock()

    async def run_team(
        self,
        team_definition: Dict[str, Any],
        task: str,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run a multi-agent team on a task

        Args:
            team_definition: Team configuration with agents, MCPs, coordination
            task: The task/goal for the team
            context: Additional context (files, data, etc.)

        Returns:
            Result with team's final answer, individual agent results, coordination log
        """
        print(f"\n👥 Starting multi-agent team: {team_definition['name']}")
        print(f"📋 Task: {task}")
        print(f"🤖 Team size: {len(team_definition['agents'])} agents")
        print(
            f"🔧 Available MCPs: {', '.join(team_definition.get('available_mcps', []))}"
        )
        print(
            f"🔄 Coordination mode: {team_definition.get('coordination', {}).get('mode', 'sequential')}\n"
        )

        # Validate team has agents
        if not team_definition.get("agents"):
            return {
                "status": "error",
                "error": "Team has no agents configured",
                "team_id": team_definition.get("id"),
            }

        # Validate team has MCPs
        if not team_definition.get("available_mcps"):
            return {
                "status": "error",
                "error": "Team has no MCPs configured. Add 'available_mcps' to team definition.",
                "team_id": team_definition.get("id"),
            }

        coordination_mode = team_definition.get("coordination", {}).get(
            "mode", "sequential"
        )

        agent_results = []
        shared_context = context or {}
        team_log = []

        # Execute based on coordination mode
        if coordination_mode == "sequential":
            result = await self._run_sequential(
                team_definition,
                task,
                shared_context,
                agent_results,
                team_log,
                progress_callback,
                session_id,
                manager,
            )
        elif coordination_mode == "parallel":
            result = await self._run_parallel(
                team_definition, task, shared_context, agent_results, team_log, session_id, manager
            )
        elif coordination_mode == "collaborative":
            result = await self._run_collaborative(
                team_definition, task, shared_context, agent_results, team_log, session_id, manager
            )
        else:
            return {
                "status": "error",
                "error": f"Unknown coordination mode: {coordination_mode}",
            }

        print(f"\n✅ Team execution completed: {team_definition['name']}\n")

        return result

    async def _run_sequential(
        self,
        team_def: Dict,
        task: str,
        shared_context: Dict,
        agent_results: List,
        team_log: List,
        progress_callback: Optional[Any] = None,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run agents sequentially, each building on previous results"""

        for idx, agent_config in enumerate(team_def["agents"], 1):
            # Check if execution has been cancelled
            if session_id and manager and manager.is_cancelled(session_id):
                print(f"🛑 Team execution cancelled for session {session_id}")
                return {
                    "status": "cancelled",
                    "team_id": team_def.get("id"),
                    "team_name": team_def.get("name"),
                    "message": "Execution cancelled by user",
                    "agent_results": agent_results,  # Return partial results
                    "team_log": team_log,
                }
            agent_id = agent_config["agent_id"]
            role = agent_config.get("role", "Agent")

            print(f"  🤖 Agent {idx}/{len(team_def['agents'])}: {agent_id} ({role})")

            # Send progress update
            if progress_callback:
                await progress_callback(
                    {
                        "type": "agent_start",
                        "agent_id": agent_id,
                        "role": role,
                        "progress": f"{idx}/{len(team_def['agents'])}",
                        "message": f"🤖 Starting {role} ({agent_id})...",
                    }
                )

            # Load agent definition
            agent_def = self._load_agent_definition(agent_id)
            if not agent_def:
                error_msg = f"Agent '{agent_id}' not found"
                agent_results.append(
                    {
                        "agent_id": agent_id,
                        "role": role,
                        "status": "error",
                        "error": error_msg,
                    }
                )
                team_log.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "agent_id": agent_id,
                        "event": "error",
                        "message": error_msg,
                    }
                )
                continue

            # Override agent's MCPs with team's MCP pool
            agent_def = self._apply_mcp_restrictions(
                agent_def,
                team_def.get("available_mcps", []),
                agent_config.get("mcp_access"),
            )

            # Build agent-specific task with context from previous agents
            agent_task = self._build_agent_task(
                task, role, agent_config.get("responsibilities", []), shared_context, agent_def
            )

            team_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": agent_id,
                    "event": "started",
                    "message": f"Starting {role}",
                }
            )

            # Execute agent with error handling
            try:
                result = await self.agent_runtime.run_agent(
                    agent_definition=agent_def,
                    task=agent_task,
                    context=shared_context,
                    progress_callback=progress_callback,
                    session_id=session_id,
                    manager=manager,
                )

                # Check if agent reported error status
                if result.get("status") == "error":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(
                        f"Agent {agent_id} failed with error: {error_msg}",
                        extra={
                            "agent_id": agent_id,
                            "role": role,
                            "team_id": team_def.get("id"),
                        }
                    )

            except Exception as e:
                # Agent runtime threw exception
                import traceback
                error_detail = traceback.format_exc()

                logger.error(
                    f"Agent {agent_id} crashed with exception: {str(e)}",
                    extra={
                        "agent_id": agent_id,
                        "role": role,
                        "team_id": team_def.get("id"),
                        "traceback": error_detail,
                    }
                )

                # Create error result
                result = {
                    "status": "error",
                    "error": str(e),
                    "traceback": error_detail,
                    "answer": None,
                    "tools_used": [],
                    "iterations": 0,
                    "reasoning_steps": [],
                }

            # Store result (success or error)
            agent_result = {
                "agent_id": agent_id,
                "role": role,
                "status": result.get("status"),
                "answer": result.get("answer"),
                "error": result.get("error"),
                "traceback": result.get("traceback"),
                "iterations": result.get("iterations"),
                "tools_used": result.get("tools_used", []),
                "reasoning_steps": result.get("reasoning_steps", []),
                "token_usage": result.get("token_usage"),  # Include token usage for KPI tracking
                "cumulative_tokens": result.get("cumulative_tokens"),  # Session totals if available
            }
            agent_results.append(agent_result)

            team_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": agent_id,
                    "event": "completed",
                    "message": f"Completed with status: {result.get('status')}",
                }
            )

            # Send progress update
            if progress_callback:
                await progress_callback(
                    {
                        "type": "agent_complete",
                        "agent_id": agent_id,
                        "role": role,
                        "status": result.get("status"),
                        "progress": f"{idx}/{len(team_def['agents'])}",
                        "message": f"✅ {role} completed",
                        "answer_preview": (
                            result.get("answer", "")[:200] + "..."
                            if result.get("answer")
                            and len(result.get("answer", "")) > 200
                            else result.get("answer", "")
                        ),
                        "answer": result.get("answer", ""),  # Full answer for detailed view
                        "tools_used": result.get("tools_used", []),
                    }
                )

            # Update shared context with agent's results
            if result.get("status") == "completed":
                shared_context[f"agent_{agent_id}_output"] = result.get("answer")
                shared_context[f"agent_{agent_id}_tools"] = result.get("tools_used", [])

        # Synthesize final answer
        final_answer = self._synthesize_team_answer(agent_results, task)

        return {
            "status": "completed",
            "team_id": team_def.get("id"),
            "team_name": team_def.get("name"),
            "coordination_mode": "sequential",
            "answer": final_answer,
            "agent_results": agent_results,
            "team_log": team_log,
            "shared_context": shared_context,
        }

    async def _run_parallel(
        self,
        team_def: Dict,
        task: str,
        shared_context: Dict,
        agent_results: List,
        team_log: List,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run all agents in parallel on the same task"""

        # Check if execution has been cancelled before starting
        if session_id and manager and manager.is_cancelled(session_id):
            print(f"🛑 Team execution cancelled for session {session_id}")
            return {
                "status": "cancelled",
                "team_id": team_def.get("id"),
                "team_name": team_def.get("name"),
                "message": "Execution cancelled by user",
                "agent_results": [],
                "team_log": team_log,
            }

        print("  🚀 Running agents in parallel...")

        tasks = []
        for agent_config in team_def["agents"]:
            agent_id = agent_config["agent_id"]

            # Load and configure agent
            agent_def = self._load_agent_definition(agent_id)
            if not agent_def:
                continue

            agent_def = self._apply_mcp_restrictions(
                agent_def,
                team_def.get("available_mcps", []),
                agent_config.get("mcp_access"),
            )

            # Build agent-specific task
            agent_task = self._build_agent_task(
                task,
                agent_config.get("role", "Agent"),
                agent_config.get("responsibilities", []),
                shared_context,
                agent_def,
            )

            # Create async task
            tasks.append(
                self._run_agent_with_logging(
                    agent_def,
                    agent_task,
                    shared_context,
                    agent_id,
                    agent_config.get("role", "Agent"),
                    agent_results,
                    team_log,
                    session_id,
                    manager,
                )
            )

        # Execute all agents in parallel
        await asyncio.gather(*tasks)

        # Synthesize final answer from parallel results
        final_answer = self._synthesize_team_answer(agent_results, task)

        return {
            "status": "completed",
            "team_id": team_def.get("id"),
            "team_name": team_def.get("name"),
            "coordination_mode": "parallel",
            "answer": final_answer,
            "agent_results": agent_results,
            "team_log": team_log,
        }

    async def _run_collaborative(
        self,
        team_def: Dict,
        task: str,
        shared_context: Dict,
        agent_results: List,
        team_log: List,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run agents collaboratively with iterative feedback"""

        print("  🤝 Running agents collaboratively...")

        max_rounds = 3  # Maximum collaboration rounds

        for round_num in range(1, max_rounds + 1):
            # Check if execution has been cancelled
            if session_id and manager and manager.is_cancelled(session_id):
                print(f"🛑 Team execution cancelled for session {session_id}")
                return {
                    "status": "cancelled",
                    "team_id": team_def.get("id"),
                    "team_name": team_def.get("name"),
                    "message": "Execution cancelled by user",
                    "agent_results": agent_results,  # Return partial results
                    "team_log": team_log,
                }
            print(f"\n  📍 Collaboration Round {round_num}/{max_rounds}")

            round_results = []

            # Each agent contributes in this round
            for agent_config in team_def["agents"]:
                agent_id = agent_config["agent_id"]
                role = agent_config.get("role", "Agent")

                # Load and configure agent
                agent_def = self._load_agent_definition(agent_id)
                if not agent_def:
                    continue

                agent_def = self._apply_mcp_restrictions(
                    agent_def,
                    team_def.get("available_mcps", []),
                    agent_config.get("mcp_access"),
                )

                # Build collaborative task with feedback from previous rounds
                agent_task = self._build_collaborative_task(
                    task, role, round_num, agent_results, shared_context
                )

                # Execute agent with error handling
                try:
                    result = await self.agent_runtime.run_agent(
                        agent_definition=agent_def,
                        task=agent_task,
                        context=shared_context,
                        session_id=session_id,
                        manager=manager,
                    )

                    # Check if agent reported error status
                    if result.get("status") == "error":
                        error_msg = result.get("error", "Unknown error")
                        logger.error(
                            f"Agent {agent_id} (collaborative round {round_num}) failed with error: {error_msg}",
                            extra={
                                "agent_id": agent_id,
                                "role": role,
                                "round": round_num,
                            }
                        )

                except Exception as e:
                    # Agent runtime threw exception
                    import traceback
                    error_detail = traceback.format_exc()

                    logger.error(
                        f"Agent {agent_id} (collaborative round {round_num}) crashed with exception: {str(e)}",
                        extra={
                            "agent_id": agent_id,
                            "role": role,
                            "round": round_num,
                            "traceback": error_detail,
                        }
                    )

                    # Create error result
                    result = {
                        "status": "error",
                        "error": str(e),
                        "traceback": error_detail,
                        "answer": None,
                        "iterations": 0,
                    }

                round_result = {
                    "round": round_num,
                    "agent_id": agent_id,
                    "role": role,
                    "status": result.get("status"),
                    "answer": result.get("answer"),
                    "error": result.get("error"),
                    "traceback": result.get("traceback"),
                    "iterations": result.get("iterations"),
                    "token_usage": result.get("token_usage"),  # Include token usage for KPI tracking
                    "cumulative_tokens": result.get("cumulative_tokens"),  # Session totals if available
                }
                round_results.append(round_result)
                agent_results.append(round_result)

                # Update shared context
                if result.get("status") == "completed":
                    shared_context[f"round{round_num}_{agent_id}"] = result.get(
                        "answer"
                    )

        # Synthesize final collaborative answer
        final_answer = self._synthesize_collaborative_answer(agent_results, task)

        return {
            "status": "completed",
            "team_id": team_def.get("id"),
            "team_name": team_def.get("name"),
            "coordination_mode": "collaborative",
            "answer": final_answer,
            "agent_results": agent_results,
            "collaboration_rounds": max_rounds,
            "team_log": team_log,
        }

    async def _run_agent_with_logging(
        self,
        agent_def: Dict,
        task: str,
        context: Dict,
        agent_id: str,
        role: str,
        agent_results: List,
        team_log: List,
        session_id: Optional[str] = None,
        manager: Optional[Any] = None,
    ):
        """Run agent with logging for parallel execution"""

        # Log start (use lock for thread-safety)
        async with self._log_lock:
            team_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": agent_id,
                    "event": "started",
                    "message": f"Starting {role}",
                }
            )

        # Run agent with error handling (no lock needed - independent execution)
        try:
            result = await self.agent_runtime.run_agent(
                agent_definition=agent_def,
                task=task,
                context=context,
                session_id=session_id,
                manager=manager,
            )

            # Check if agent reported error status
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                logger.error(
                    f"Agent {agent_id} (parallel mode) failed with error: {error_msg}",
                    extra={
                        "agent_id": agent_id,
                        "role": role,
                    }
                )

        except Exception as e:
            # Agent runtime threw exception
            import traceback
            error_detail = traceback.format_exc()

            logger.error(
                f"Agent {agent_id} (parallel mode) crashed with exception: {str(e)}",
                extra={
                    "agent_id": agent_id,
                    "role": role,
                    "traceback": error_detail,
                }
            )

            # Create error result
            result = {
                "status": "error",
                "error": str(e),
                "traceback": error_detail,
                "answer": None,
                "tools_used": [],
                "iterations": 0,
            }

        # Store result (use lock for thread-safety)
        agent_result = {
            "agent_id": agent_id,
            "role": role,
            "status": result.get("status"),
            "answer": result.get("answer"),
            "error": result.get("error"),
            "traceback": result.get("traceback"),
            "iterations": result.get("iterations"),
            "tools_used": result.get("tools_used", []),
            "token_usage": result.get("token_usage"),  # Include token usage for KPI tracking
            "cumulative_tokens": result.get("cumulative_tokens"),  # Session totals if available
        }

        async with self._results_lock:
            agent_results.append(agent_result)

        # Log completion (use lock for thread-safety)
        async with self._log_lock:
            team_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": agent_id,
                    "event": "completed",
                    "message": f"Completed with status: {result.get('status')}",
                }
            )

    def _load_agent_definition(self, agent_id: str) -> Optional[Dict]:
        """Load agent definition from file"""
        file_path = self.agents_dir / f"{agent_id}.json"
        if not file_path.exists():
            print(f"  ⚠️  Agent definition not found: {agent_id}")
            return None

        try:
            return json.loads(file_path.read_text())
        except Exception as e:
            print(f"  ⚠️  Error loading agent {agent_id}: {e}")
            return None

    def _apply_mcp_restrictions(
        self,
        agent_def: Dict,
        team_mcps: List[str],
        agent_mcp_access: Optional[List[str]] = None,
    ) -> Dict:
        """Override agent's MCPs with team's pool and optional restrictions"""

        # Start with team's MCP pool
        if agent_mcp_access:
            # Agent has specific MCP restrictions
            available_mcps = [mcp for mcp in agent_mcp_access if mcp in team_mcps]
        else:
            # Agent gets full team MCP pool
            available_mcps = team_mcps

        agent_def["available_mcps"] = available_mcps
        return agent_def

    def _build_agent_task(
        self, original_task: str, role: str, responsibilities: List[str], context: Dict, agent_def: Dict
    ) -> str:
        """Build agent-specific task based on role and previous context"""

        task_parts = [f"Task: {original_task}\n"]
        task_parts.append(f"Your role: {role}")

        if responsibilities:
            task_parts.append(f"Your responsibilities: {', '.join(responsibilities)}")

        # Add SUMMARY of context from previous agents (not full outputs)
        # Use token-based truncation to prevent API rate limits
        if context:
            relevant_context = {
                k: v for k, v in context.items() if k.startswith("agent_")
            }
            if relevant_context:
                token_counter = get_token_counter()
                max_preview_tokens = token_counter.get_config_limits()["agent_output_preview_tokens"]
                model_name = agent_def["model_config"]["model"]

                task_parts.append("\nPrevious agent outputs (summaries):")
                for key, value in relevant_context.items():
                    if isinstance(value, str):
                        # Use token-based truncation
                        preview = token_counter.truncate_to_token_limit(
                            value,
                            max_preview_tokens,
                            model_name
                        )
                        task_parts.append(f"- {key}: {preview}")
                    elif isinstance(value, list):
                        # Handle tool lists with count
                        task_parts.append(f"- {key}: {len(value)} tools used")

        return "\n".join(task_parts)

    def _build_collaborative_task(
        self,
        original_task: str,
        role: str,
        round_num: int,
        previous_results: List[Dict],
        context: Dict,
    ) -> str:
        """Build collaborative task with feedback from previous rounds"""

        task_parts = [
            f"Collaborative Task (Round {round_num}): {original_task}\n",
            f"Your role: {role}",
        ]

        # Add feedback from previous rounds
        if round_num > 1 and previous_results:
            task_parts.append("\nFeedback from previous rounds:")
            for result in previous_results[-3:]:  # Last 3 results
                if result.get("round", 0) < round_num:
                    task_parts.append(
                        f"- {result.get('role')}: {result.get('answer', '')[:200]}..."
                    )

        return "\n".join(task_parts)

    def _synthesize_team_answer(self, agent_results: List[Dict], task: str) -> str:
        """Synthesize final answer from all agent results"""

        if not agent_results:
            return "No results from agents"

        answer_parts = [f"# Team Execution Results\n\nTask: {task}\n"]

        for result in agent_results:
            agent_id = result.get("agent_id", "unknown")
            role = result.get("role", "Agent")
            status = result.get("status", "unknown")
            answer = result.get("answer", "No answer provided")

            answer_parts.append(f"\n## {role} ({agent_id})")
            answer_parts.append(f"Status: {status}")
            if status == "completed":
                answer_parts.append(f"\n{answer}")
            else:
                # Get detailed error information
                error_msg = result.get('error', 'Unknown error')

                # If error is empty string, provide more context
                if not error_msg or error_msg.strip() == '':
                    error_msg = 'Agent failed without error message'
                    # Add debug info if available
                    if result.get('debug'):
                        error_msg += f"\n\nDebug info: {result['debug']}"

                answer_parts.append(f"\nError: {error_msg}")

        return "\n".join(answer_parts)

    def _synthesize_collaborative_answer(
        self, agent_results: List[Dict], task: str
    ) -> str:
        """Synthesize answer from collaborative rounds"""

        answer_parts = [f"# Collaborative Team Results\n\nTask: {task}\n"]

        # Group by rounds
        rounds = {}
        for result in agent_results:
            round_num = result.get("round", 1)
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(result)

        # Present results by round
        for round_num in sorted(rounds.keys()):
            answer_parts.append(f"\n## Round {round_num}")
            for result in rounds[round_num]:
                role = result.get("role", "Agent")
                answer = result.get("answer", "")[:300]
                answer_parts.append(f"\n**{role}**: {answer}...")

        return "\n".join(answer_parts)
