# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

import redis.asyncio as redis
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from api.models import WSMessage, AgentTask

load_dotenv()

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))


class RedisQueue:
    """Redis-based queue for agent task distribution and pub/sub for live updates"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None

    async def connect(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            encoding="utf-8",
            decode_responses=True
        )
        print(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            print("✓ Disconnected from Redis")

    # Task Queue Methods (for agent work distribution)

    async def push_task(self, agent_id: str, task: AgentTask):
        """Push a task to an agent's queue"""
        queue_key = f"agent:{agent_id}:tasks"
        task_data = task.model_dump_json()
        await self.redis_client.rpush(queue_key, task_data)

    async def pop_task(self, agent_id: str, timeout: int = 0) -> Optional[AgentTask]:
        """Pop a task from an agent's queue (blocking)"""
        queue_key = f"agent:{agent_id}:tasks"
        result = await self.redis_client.blpop(queue_key, timeout=timeout)
        if result:
            _, task_data = result
            return AgentTask.model_validate_json(task_data)
        return None

    async def get_queue_length(self, agent_id: str) -> int:
        """Get the number of pending tasks for an agent"""
        queue_key = f"agent:{agent_id}:tasks"
        return await self.redis_client.llen(queue_key)

    async def clear_queue(self, agent_id: str):
        """Clear all tasks for an agent"""
        queue_key = f"agent:{agent_id}:tasks"
        await self.redis_client.delete(queue_key)

    # Pub/Sub Methods (for live updates via WebSocket)

    async def publish_update(self, campaign_id: str, message: WSMessage):
        """Publish update to campaign channel"""
        channel = f"campaign:{campaign_id}:updates"
        message_data = message.model_dump_json()
        await self.redis_client.publish(channel, message_data)

    async def subscribe_to_campaign(self, campaign_id: str):
        """Subscribe to campaign updates"""
        channel = f"campaign:{campaign_id}:updates"
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def unsubscribe_from_campaign(self, pubsub, campaign_id: str):
        """Unsubscribe from campaign updates"""
        channel = f"campaign:{campaign_id}:updates"
        await pubsub.unsubscribe(channel)
        await pubsub.close()

    # Agent State Management

    async def set_agent_state(self, agent_id: str, state: Dict[str, Any], ttl: int = 3600):
        """Store agent state with TTL (1 hour default)"""
        key = f"agent:{agent_id}:state"
        await self.redis_client.setex(key, ttl, json.dumps(state))

    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state"""
        key = f"agent:{agent_id}:state"
        state_data = await self.redis_client.get(key)
        if state_data:
            return json.loads(state_data)
        return None

    async def delete_agent_state(self, agent_id: str):
        """Delete agent state"""
        key = f"agent:{agent_id}:state"
        await self.redis_client.delete(key)

    # Campaign State Management

    async def set_campaign_state(self, campaign_id: str, state: Dict[str, Any]):
        """Store campaign state"""
        key = f"campaign:{campaign_id}:state"
        await self.redis_client.set(key, json.dumps(state))

    async def get_campaign_state(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve campaign state"""
        key = f"campaign:{campaign_id}:state"
        state_data = await self.redis_client.get(key)
        if state_data:
            return json.loads(state_data)
        return None

    # Agent Heartbeat (for supervision)

    async def agent_heartbeat(self, agent_id: str, ttl: int = 30):
        """Update agent heartbeat with TTL (30 seconds default)"""
        key = f"agent:{agent_id}:heartbeat"
        await self.redis_client.setex(key, ttl, "alive")

    async def check_agent_alive(self, agent_id: str) -> bool:
        """Check if agent is alive based on heartbeat"""
        key = f"agent:{agent_id}:heartbeat"
        return await self.redis_client.exists(key) > 0


# Global Redis queue instance
redis_queue = RedisQueue()


async def get_redis() -> RedisQueue:
    """Dependency to get Redis queue"""
    return redis_queue
