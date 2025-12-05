# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Supervisor - Agent lifecycle management

Responsible for:
- Spawning agents based on campaign configuration
- Monitoring agent health (heartbeats)
- Restarting failed agents
- Stopping agents gracefully
- Load balancing across agent pool
"""

import asyncio
from typing import Dict, List, Optional, Any
from uuid import uuid4
from datetime import datetime

from agents.base import BaseAgent
from agents.memory import AgentMemory
from api.models import PersonaConfig, TeamMember
from api.redis_queue import redis_queue


class Supervisor:
    """
    Supervisor process for managing agent lifecycle

    Uses actor model supervision tree pattern:
    - Each agent is a child process
    - Supervisor monitors children via heartbeats
    - Failed children are restarted
    - Graceful shutdown of all children
    """

    def __init__(self):
        # Active agents: campaign_id -> [agent_ids]
        self.campaign_agents: Dict[str, List[str]] = {}

        # Agent tasks (asyncio tasks)
        self.agent_tasks: Dict[str, asyncio.Task] = {}

        # Agent instances
        self.agents: Dict[str, BaseAgent] = {}

        # Monitoring task
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False

    async def spawn_agents(
        self,
        campaign_id: str,
        team_config: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Spawn agents for a campaign based on team configuration

        Args:
            campaign_id: Campaign ID
            team_config: List of TeamMember configurations

        Returns:
            List of spawned agent IDs
        """
        spawned_ids = []

        for member_config in team_config:
            persona = member_config["persona"]
            count = member_config.get("count", 1)
            config_data = member_config["config"]

            # Create PersonaConfig from dict
            persona_config = PersonaConfig(**config_data)

            # Spawn multiple instances if count > 1
            for i in range(count):
                agent_id = str(uuid4())

                # Create agent
                agent = BaseAgent(
                    agent_id=agent_id,
                    persona=persona,
                    config=persona_config,
                    campaign_id=campaign_id
                )

                # Initialize agent
                await agent.initialize()

                # Store agent
                self.agents[agent_id] = agent

                # Start agent task
                task = asyncio.create_task(agent.run())
                self.agent_tasks[agent_id] = task

                # Track by campaign
                if campaign_id not in self.campaign_agents:
                    self.campaign_agents[campaign_id] = []
                self.campaign_agents[campaign_id].append(agent_id)

                spawned_ids.append(agent_id)

                print(f"[Supervisor] Spawned agent {agent_id} (persona: {persona}, instance {i+1}/{count})")

        return spawned_ids

    async def stop_agent(self, agent_id: str):
        """Stop a specific agent"""
        agent = self.agents.get(agent_id)
        if agent:
            await agent.stop()

        task = self.agent_tasks.get(agent_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Cleanup
        self.agents.pop(agent_id, None)
        self.agent_tasks.pop(agent_id, None)

        # Remove from campaign tracking
        for campaign_id, agent_ids in self.campaign_agents.items():
            if agent_id in agent_ids:
                agent_ids.remove(agent_id)

        print(f"[Supervisor] Stopped agent {agent_id}")

    async def stop_campaign_agents(self, campaign_id: str):
        """Stop all agents for a campaign"""
        agent_ids = self.campaign_agents.get(campaign_id, [])

        for agent_id in list(agent_ids):
            await self.stop_agent(agent_id)

        self.campaign_agents.pop(campaign_id, None)
        print(f"[Supervisor] Stopped all agents for campaign {campaign_id}")

    async def stop_all_agents(self, campaign_id: Optional[str] = None):
        """Stop all agents (optionally filtered by campaign)"""
        if campaign_id:
            await self.stop_campaign_agents(campaign_id)
        else:
            # Stop all agents across all campaigns
            for cid in list(self.campaign_agents.keys()):
                await self.stop_campaign_agents(cid)

    def get_campaign_agents(self, campaign_id: str) -> List[str]:
        """Get all agent IDs for a campaign"""
        return self.campaign_agents.get(campaign_id, [])

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent instance by ID"""
        return self.agents.get(agent_id)

    async def start_monitoring(self):
        """Start health monitoring of all agents"""
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        print("[Supervisor] Started health monitoring")

    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        print("[Supervisor] Stopped health monitoring")

    async def _monitor_loop(self):
        """
        Monitor agent health via heartbeats

        - Check heartbeats every 10 seconds
        - Restart agents that haven't sent heartbeat in 60 seconds
        - Cleanup completed agents
        """
        try:
            while self.running:
                await asyncio.sleep(10)  # Check every 10 seconds

                for agent_id, agent in list(self.agents.items()):
                    # Check if agent is alive (heartbeat check)
                    is_alive = await redis_queue.check_agent_alive(agent_id)

                    if not is_alive:
                        print(f"[Supervisor] Agent {agent_id} heartbeat timeout - restarting")
                        await self._restart_agent(agent_id)

                    # Check if task completed
                    task = self.agent_tasks.get(agent_id)
                    if task and task.done():
                        print(f"[Supervisor] Agent {agent_id} task completed")
                        # Optionally restart or remove

        except asyncio.CancelledError:
            print("[Supervisor] Monitor loop cancelled")
        except Exception as e:
            print(f"[Supervisor] Monitor loop error: {e}")

    async def _restart_agent(self, agent_id: str):
        """Restart a failed agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            return

        # Stop existing agent
        await self.stop_agent(agent_id)

        # Create new agent with same configuration
        new_agent = BaseAgent(
            agent_id=agent_id,
            persona=agent.persona,
            config=agent.config,
            campaign_id=agent.campaign_id
        )

        await new_agent.initialize()

        # Store and start
        self.agents[agent_id] = new_agent
        task = asyncio.create_task(new_agent.run())
        self.agent_tasks[agent_id] = task

        print(f"[Supervisor] Restarted agent {agent_id}")

    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status"""
        return {
            "running": self.running,
            "total_agents": len(self.agents),
            "campaigns": len(self.campaign_agents),
            "agents_by_campaign": {
                campaign_id: len(agent_ids)
                for campaign_id, agent_ids in self.campaign_agents.items()
            }
        }


# Global supervisor instance
supervisor = Supervisor()
