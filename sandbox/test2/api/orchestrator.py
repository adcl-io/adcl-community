# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Campaign Orchestrator - Campaign workflow management

Responsible for:
- Starting and stopping campaigns
- Managing workflow (sequential vs parallel)
- Agent handoff between phases (recon → exploit → post-exploit)
- Result aggregation
- Campaign state management
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    CampaignStatus, CampaignMode, TaskType, AgentTask,
    WSMessage, WSMessageType, AgentStatus
)
from api.database import async_session_maker, CampaignDB, AgentDB, FindingDB
from api.redis_queue import redis_queue
from api.supervisor import supervisor


class Orchestrator:
    """
    Campaign orchestrator - manages entire campaign lifecycle

    Workflows:
    - Sequential: Recon → Analyze → Exploit → Report
    - Parallel: All phases run concurrently as targets are discovered
    """

    def __init__(self):
        self.active_campaigns: Dict[str, asyncio.Task] = {}

    async def start_campaign(self, campaign_id: str):
        """
        Start a campaign

        1. Load campaign from DB
        2. Update status to RUNNING
        3. Start workflow based on mode (sequential/parallel)
        4. Monitor progress
        """
        print(f"[Orchestrator] Starting campaign {campaign_id}")

        # Load campaign from database
        async with async_session_maker() as db:
            result = await db.execute(
                select(CampaignDB).where(CampaignDB.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()

            if not campaign:
                raise Exception(f"Campaign {campaign_id} not found")

            # Update status
            campaign.status = CampaignStatus.RUNNING
            campaign.started_at = datetime.utcnow()
            await db.commit()

        # Publish campaign start
        await redis_queue.publish_update(campaign_id, WSMessage(
            type=WSMessageType.CAMPAIGN_STATUS,
            campaign_id=UUID(campaign_id),
            data={
                "status": CampaignStatus.RUNNING,
                "message": f"Campaign '{campaign.name}' started"
            }
        ))

        # Start workflow based on mode
        if campaign.mode == CampaignMode.SEQUENTIAL:
            task = asyncio.create_task(
                self._sequential_workflow(campaign_id, campaign)
            )
        else:
            task = asyncio.create_task(
                self._parallel_workflow(campaign_id, campaign)
            )

        self.active_campaigns[campaign_id] = task

        # Wait for completion (non-blocking in background)
        asyncio.create_task(self._monitor_campaign(campaign_id, task))

        return campaign_id

    async def stop_campaign(self, campaign_id: str):
        """Stop a running campaign"""
        print(f"[Orchestrator] Stopping campaign {campaign_id}")

        # Stop all agents for this campaign
        await supervisor.stop_campaign_agents(campaign_id)

        # Cancel campaign task
        task = self.active_campaigns.get(campaign_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Update status in database
        async with async_session_maker() as db:
            result = await db.execute(
                select(CampaignDB).where(CampaignDB.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()

            if campaign:
                campaign.status = CampaignStatus.CANCELLED
                campaign.completed_at = datetime.utcnow()
                await db.commit()

        # Publish campaign stopped
        await redis_queue.publish_update(campaign_id, WSMessage(
            type=WSMessageType.CAMPAIGN_STATUS,
            campaign_id=UUID(campaign_id),
            data={
                "status": CampaignStatus.CANCELLED,
                "message": "Campaign stopped"
            }
        ))

        self.active_campaigns.pop(campaign_id, None)

    async def _sequential_workflow(self, campaign_id: str, campaign: CampaignDB):
        """
        Sequential workflow (MVP1)

        Phase 1: Reconnaissance
        - Spawn recon agents
        - Wait for completion
        - Analyze attack surface

        Phase 2: Exploitation
        - Spawn exploit agents based on findings
        - Wait for completion

        Phase 3: Reporting
        - Spawn report agent
        - Generate final report
        """
        try:
            print(f"[Orchestrator] Running sequential workflow for {campaign_id}")

            # Phase 1: Reconnaissance
            await self._publish_log(campaign_id, "Starting reconnaissance phase...")

            recon_agents = await self._spawn_recon_agents(campaign_id, campaign)
            await self._distribute_recon_tasks(campaign_id, campaign.target, recon_agents)
            await self._wait_for_agents(recon_agents)

            await self._publish_log(campaign_id, "Reconnaissance complete")

            # Phase 2: Exploitation (if configured)
            exploit_team = [m for m in campaign.team_config if "exploit" in m.get("persona", "").lower()]

            if exploit_team:
                await self._publish_log(campaign_id, "Starting exploitation phase...")

                exploit_agents = await supervisor.spawn_agents(campaign_id, exploit_team)
                await self._distribute_exploit_tasks(campaign_id, exploit_agents)
                await self._wait_for_agents(exploit_agents)

                await self._publish_log(campaign_id, "Exploitation complete")

            # Phase 3: Reporting
            await self._publish_log(campaign_id, "Generating report...")
            await self._generate_report(campaign_id)

            # Mark campaign as completed
            await self._complete_campaign(campaign_id, CampaignStatus.COMPLETED)

        except Exception as e:
            print(f"[Orchestrator] Campaign {campaign_id} failed: {e}")
            await self._complete_campaign(campaign_id, CampaignStatus.FAILED, str(e))

    async def _parallel_workflow(self, campaign_id: str, campaign: CampaignDB):
        """
        Parallel workflow (post-MVP1)

        - Spawn all agents at once
        - Recon agents discover targets → immediately queue exploit tasks
        - Continuous feedback loop
        """
        try:
            print(f"[Orchestrator] Running parallel workflow for {campaign_id}")

            # Spawn all agents
            all_agents = await supervisor.spawn_agents(campaign_id, campaign.team_config)

            # Distribute initial tasks
            recon_agents = [
                aid for aid in all_agents
                if "recon" in supervisor.get_agent(aid).persona.lower()
            ]
            await self._distribute_recon_tasks(campaign_id, campaign.target, recon_agents)

            # Wait for all agents to complete
            await self._wait_for_agents(all_agents)

            # Generate report
            await self._generate_report(campaign_id)

            # Mark complete
            await self._complete_campaign(campaign_id, CampaignStatus.COMPLETED)

        except Exception as e:
            print(f"[Orchestrator] Campaign {campaign_id} failed: {e}")
            await self._complete_campaign(campaign_id, CampaignStatus.FAILED, str(e))

    async def _spawn_recon_agents(self, campaign_id: str, campaign: CampaignDB) -> List[str]:
        """Spawn reconnaissance agents"""
        recon_team = [m for m in campaign.team_config if "recon" in m.get("persona", "").lower()]
        if recon_team:
            return await supervisor.spawn_agents(campaign_id, recon_team)
        return []

    async def _distribute_recon_tasks(self, campaign_id: str, target: str, agent_ids: List[str]):
        """Distribute reconnaissance tasks to agents"""
        for agent_id in agent_ids:
            task = AgentTask(
                agent_id=UUID(agent_id),
                campaign_id=UUID(campaign_id),
                task_type=TaskType.RECON,
                target=target,
                parameters={"scan_type": "comprehensive"}
            )
            await redis_queue.push_task(agent_id, task)

            print(f"[Orchestrator] Queued recon task for agent {agent_id}")

    async def _distribute_exploit_tasks(self, campaign_id: str, agent_ids: List[str]):
        """Distribute exploitation tasks based on recon findings"""
        # Get findings from database
        async with async_session_maker() as db:
            result = await db.execute(
                select(FindingDB).where(FindingDB.campaign_id == campaign_id)
            )
            findings = result.scalars().all()

        # Create exploit tasks based on findings
        for agent_id in agent_ids:
            for finding in findings[:5]:  # Limit to first 5 findings
                task = AgentTask(
                    agent_id=UUID(agent_id),
                    campaign_id=UUID(campaign_id),
                    task_type=TaskType.EXPLOIT,
                    target=finding.target_host,
                    parameters={
                        "finding_id": finding.id,
                        "port": finding.target_port
                    }
                )
                await redis_queue.push_task(agent_id, task)

            print(f"[Orchestrator] Queued exploit tasks for agent {agent_id}")

    async def _wait_for_agents(self, agent_ids: List[str], timeout: int = 300):
        """Wait for agents to complete their tasks"""
        print(f"[Orchestrator] Waiting for {len(agent_ids)} agents...")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if all agents completed
            all_done = True
            for agent_id in agent_ids:
                agent = supervisor.get_agent(agent_id)
                if agent and agent.running:
                    all_done = False
                    break

            if all_done:
                print(f"[Orchestrator] All agents completed")
                break

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"[Orchestrator] Agent timeout reached")
                break

            await asyncio.sleep(2)

    async def _generate_report(self, campaign_id: str):
        """Generate campaign report"""
        # For MVP1, just log report generation
        # In production, spawn report_writer agent
        await self._publish_log(campaign_id, "Report generation complete")

    async def _complete_campaign(self, campaign_id: str, status: CampaignStatus, error: Optional[str] = None):
        """Mark campaign as completed"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(CampaignDB).where(CampaignDB.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()

            if campaign:
                campaign.status = status
                campaign.completed_at = datetime.utcnow()
                if error:
                    campaign.error_message = error
                await db.commit()

        # Publish completion
        await redis_queue.publish_update(campaign_id, WSMessage(
            type=WSMessageType.CAMPAIGN_STATUS,
            campaign_id=UUID(campaign_id),
            data={
                "status": status,
                "message": f"Campaign {status.value}"
            }
        ))

        print(f"[Orchestrator] Campaign {campaign_id} {status.value}")

    async def _publish_log(self, campaign_id: str, message: str):
        """Publish log message"""
        await redis_queue.publish_update(campaign_id, WSMessage(
            type=WSMessageType.LOG,
            campaign_id=UUID(campaign_id),
            data={"message": message}
        ))

    async def _monitor_campaign(self, campaign_id: str, task: asyncio.Task):
        """Monitor campaign completion"""
        try:
            await task
        except Exception as e:
            print(f"[Orchestrator] Campaign {campaign_id} error: {e}")
        finally:
            self.active_campaigns.pop(campaign_id, None)


# Global orchestrator instance
orchestrator = Orchestrator()
