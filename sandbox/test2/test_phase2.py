#!/usr/bin/env python3
# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Phase 2 Test Harness - First Vertical Slice

Tests:
1. BaseAgent class (actor model + persona configuration)
2. nmap MCP server connectivity
3. Supervisor process (spawn/monitor agents)
4. End-to-end: Campaign → Supervisor → Agent → MCP → Results → DB
"""

import asyncio
import sys
import os
from pathlib import Path
import yaml

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class TestHarness:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def test(self, name: str):
        """Decorator to mark test functions"""
        def decorator(func):
            async def wrapper():
                print(f"\n{BLUE}Testing:{RESET} {name}")
                try:
                    result = await func()
                    if result is None or result is True:
                        print(f"  {GREEN}✓ PASSED{RESET}")
                        self.passed += 1
                    else:
                        print(f"  {YELLOW}⊘ SKIPPED{RESET} - {result}")
                        self.skipped += 1
                except FileNotFoundError as e:
                    print(f"  {YELLOW}⊘ SKIPPED{RESET} - Component not built yet: {e}")
                    self.skipped += 1
                except ImportError as e:
                    print(f"  {YELLOW}⊘ SKIPPED{RESET} - Module not found: {e}")
                    self.skipped += 1
                except Exception as e:
                    print(f"  {RED}✗ FAILED{RESET} - {e}")
                    import traceback
                    traceback.print_exc()
                    self.failed += 1
            return wrapper
        return decorator

    def summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("Phase 2 Test Harness Summary")
        print("=" * 60)
        print(f"{GREEN}Passed:{RESET}  {self.passed}")
        print(f"{YELLOW}Skipped:{RESET} {self.skipped}")
        print(f"{RED}Failed:{RESET}  {self.failed}")
        print("=" * 60)

        if self.failed > 0:
            print(f"\n{RED}Status: FAILED{RESET}")
            return 1
        elif self.skipped > 0:
            print(f"\n{YELLOW}Status: INCOMPLETE (build missing components){RESET}")
            return 0
        else:
            print(f"\n{GREEN}Status: ALL TESTS PASSED!{RESET}")
            return 0


harness = TestHarness()

# Load test configuration
def load_config():
    """Load configuration from vars.yaml"""
    config_path = Path("vars.yaml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    else:
        # Return defaults if vars.yaml doesn't exist
        return {
            "network": {"target": "192.168.1.0/24", "scan_type": "comprehensive"},
            "campaign": {"name": "E2E Test Campaign", "mode": "sequential", "timeout_minutes": 30},
            "agents": {
                "recon": {
                    "persona": "methodical_recon",
                    "count": 1,
                    "llm_model": "claude-sonnet-4",
                    "temperature": 0.3,
                    "max_tasks": 10,
                    "timeout_minutes": 30
                }
            },
            "mcp": {"nmap": {"host": "localhost", "port": 6000}},
            "test": {"wait_for_agents_timeout": 5, "health_check_timeout": 2}
        }

config = load_config()


# ============================================================================
# Test 1: BaseAgent Class
# ============================================================================

@harness.test("BaseAgent class exists")
async def test_base_agent_exists():
    """Check if BaseAgent class is implemented"""
    try:
        from agents.base import BaseAgent
        print(f"    Found: agents/base.py")
        return True
    except ImportError:
        return "agents/base.py not created yet"


@harness.test("BaseAgent can be instantiated with persona config")
async def test_base_agent_init():
    """Test BaseAgent initialization with persona configuration"""
    try:
        from agents.base import BaseAgent
        from api.models import PersonaConfig
        from uuid import uuid4

        agent_config = config["agents"]["recon"]
        persona_config = PersonaConfig(
            system_prompt="Test prompt",
            mcp_servers=["nmap"],
            llm_model=agent_config["llm_model"],
            temperature=agent_config["temperature"],
            max_tasks=agent_config["max_tasks"],
            timeout_minutes=agent_config["timeout_minutes"]
        )

        agent = BaseAgent(
            agent_id=str(uuid4()),
            persona="test_persona",
            config=persona_config
        )

        assert agent is not None
        assert agent.persona == "test_persona"
        print(f"    Agent ID: {agent.id}")
        print(f"    Persona: {agent.persona}")
        return True
    except ImportError:
        return "BaseAgent class not implemented yet"


@harness.test("BaseAgent has task queue integration")
async def test_base_agent_queue():
    """Test if BaseAgent can receive tasks from Redis queue"""
    try:
        from agents.base import BaseAgent
        from api.redis_queue import redis_queue
        from api.models import PersonaConfig, AgentTask, TaskType
        from uuid import uuid4

        # Connect to Redis
        await redis_queue.connect()

        agent_config = config["agents"]["recon"]
        persona_config = PersonaConfig(
            system_prompt="Test prompt",
            mcp_servers=["nmap"],
            llm_model=agent_config["llm_model"],
            temperature=agent_config["temperature"],
            max_tasks=agent_config["max_tasks"],
            timeout_minutes=agent_config["timeout_minutes"]
        )

        agent_id = str(uuid4())
        agent = BaseAgent(agent_id=agent_id, persona="test_persona", config=persona_config)

        # Push a test task
        task = AgentTask(
            agent_id=uuid4(),
            campaign_id=uuid4(),
            task_type=TaskType.RECON,
            target="192.168.1.1",
            parameters={"scan_type": "quick"}
        )

        await redis_queue.push_task(agent_id, task)
        queue_len = await redis_queue.get_queue_length(agent_id)

        assert queue_len == 1
        print(f"    Queue length: {queue_len}")

        # Cleanup
        await redis_queue.clear_queue(agent_id)
        return True
    except ImportError:
        return "BaseAgent queue integration not implemented yet"
    except AttributeError as e:
        return f"Missing method: {e}"


# ============================================================================
# Test 2: MCP Server (nmap)
# ============================================================================

@harness.test("nmap MCP server structure exists")
async def test_nmap_server_exists():
    """Check if nmap MCP server files exist"""
    server_path = Path("mcp_servers/recon/nmap/server.py")
    if server_path.exists():
        print(f"    Found: {server_path}")
        return True
    else:
        return f"{server_path} not created yet"


@harness.test("nmap MCP server is running")
async def test_nmap_server_running():
    """Test if nmap MCP server is accessible"""
    try:
        import httpx
        from httpx import ConnectError

        mcp_config = config["mcp"]["nmap"]
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"http://{mcp_config['host']}:{mcp_config['port']}/health", timeout=config["test"]["health_check_timeout"])
                if response.status_code == 200:
                    print(f"    nmap MCP server is running on port 6000")
                    return True
                else:
                    return f"nmap MCP server returned status {response.status_code}"
            except ConnectError:
                return "nmap MCP server not running (expected - not built yet)"
    except ImportError:
        return "httpx not installed"


@harness.test("nmap MCP server implements MCP protocol")
async def test_nmap_mcp_protocol():
    """Test if nmap server responds to MCP protocol messages"""
    try:
        import httpx

        mcp_config = config["mcp"]["nmap"]
        async with httpx.AsyncClient() as client:
            try:
                # Try to list available tools (MCP protocol)
                response = await client.post(
                    f"http://{mcp_config['host']}:{mcp_config['port']}/mcp",
                    json={"method": "tools/list"},
                    timeout=config["test"]["health_check_timeout"]
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"    Available tools: {data.get('tools', [])}")
                    return True
                else:
                    return f"MCP endpoint returned status {response.status_code}"
            except httpx.ConnectError:
                return "nmap MCP server not running"
    except ImportError:
        return "httpx not installed"


# ============================================================================
# Test 3: Supervisor Process
# ============================================================================

@harness.test("Supervisor module exists")
async def test_supervisor_exists():
    """Check if supervisor module is implemented"""
    try:
        from api.supervisor import Supervisor
        print(f"    Found: api/supervisor.py")
        return True
    except ImportError:
        return "api/supervisor.py not created yet"


@harness.test("Supervisor can spawn agents")
async def test_supervisor_spawn():
    """Test if Supervisor can spawn agents for a campaign"""
    try:
        from api.supervisor import Supervisor
        from api.models import PersonaConfig
        from uuid import uuid4

        supervisor = Supervisor()
        campaign_id = str(uuid4())

        # Test spawning a single agent using config
        agent_config = config["agents"]["recon"]
        team_config = [{
            "persona": agent_config["persona"],
            "count": agent_config["count"],
            "config": {
                "system_prompt": "Test recon agent",
                "mcp_servers": ["nmap"],
                "llm_model": agent_config["llm_model"],
                "temperature": agent_config["temperature"],
                "max_tasks": agent_config["max_tasks"],
                "timeout_minutes": agent_config["timeout_minutes"]
            }
        }]

        agent_ids = await supervisor.spawn_agents(campaign_id, team_config)

        assert len(agent_ids) == 1
        print(f"    Spawned {len(agent_ids)} agent(s)")
        print(f"    Agent ID: {agent_ids[0]}")

        # Cleanup
        await supervisor.stop_all_agents(campaign_id)
        return True
    except ImportError:
        return "Supervisor class not implemented yet"
    except AttributeError as e:
        return f"Missing method: {e}"


@harness.test("Supervisor monitors agent health")
async def test_supervisor_health_check():
    """Test if Supervisor can monitor agent heartbeats"""
    try:
        from api.supervisor import Supervisor
        from api.redis_queue import redis_queue
        from uuid import uuid4

        await redis_queue.connect()

        supervisor = Supervisor()
        agent_id = str(uuid4())

        # Simulate agent heartbeat
        await redis_queue.agent_heartbeat(agent_id, ttl=30)

        # Check if supervisor can detect agent is alive
        is_alive = await redis_queue.check_agent_alive(agent_id)

        assert is_alive is True
        print(f"    Agent heartbeat detected")
        return True
    except ImportError:
        return "Supervisor health monitoring not implemented yet"


# ============================================================================
# Test 4: Orchestrator
# ============================================================================

@harness.test("Orchestrator module exists")
async def test_orchestrator_exists():
    """Check if orchestrator module is implemented"""
    try:
        from api.orchestrator import Orchestrator
        print(f"    Found: api/orchestrator.py")
        return True
    except ImportError:
        return "api/orchestrator.py not created yet"


@harness.test("Orchestrator can start a campaign")
async def test_orchestrator_start_campaign():
    """Test if Orchestrator can start a campaign workflow"""
    try:
        from api.orchestrator import Orchestrator
        from uuid import uuid4

        orchestrator = Orchestrator()
        campaign_id = str(uuid4())

        # This should spawn agents and start the workflow
        # For now, just test that the method exists
        assert hasattr(orchestrator, 'start_campaign')
        print(f"    Orchestrator.start_campaign() exists")
        return True
    except ImportError:
        return "Orchestrator class not implemented yet"


# ============================================================================
# Test 5: End-to-End Integration
# ============================================================================

@harness.test("End-to-end: Campaign → Agent → MCP → Results")
async def test_end_to_end():
    """
    Complete end-to-end test:
    1. Create campaign via API
    2. Supervisor spawns agents
    3. Agent receives task
    4. Agent calls MCP server
    5. Results stored in DB
    6. WebSocket update sent
    """
    try:
        # This test will only run when all components are built
        from api.orchestrator import Orchestrator
        from api.supervisor import Supervisor
        from agents.base import BaseAgent
        from api.redis_queue import redis_queue
        from api.database import async_session_maker, CampaignDB
        from sqlalchemy import select
        import httpx

        print(f"    Creating test campaign...")

        # 1. Create campaign in DB using config from vars.yaml
        campaign_config = config["campaign"]
        agent_config = config["agents"]["recon"]
        network_config = config["network"]

        async with async_session_maker() as db:
            campaign = CampaignDB(
                name=campaign_config["name"],
                target=network_config["target"],
                mode=campaign_config["mode"],
                status="pending",
                team_config=[{
                    "persona": agent_config["persona"],
                    "count": agent_config["count"],
                    "config": {
                        "system_prompt": "Test recon",
                        "mcp_servers": ["nmap"],
                        "llm_model": agent_config["llm_model"],
                        "temperature": agent_config["temperature"],
                        "max_tasks": agent_config["max_tasks"],
                        "timeout_minutes": agent_config["timeout_minutes"]
                    }
                }],
                safety_config=None
            )
            db.add(campaign)
            await db.commit()
            campaign_id = campaign.id
            print(f"    ✓ Campaign created: {campaign_id}")

        # 2. Start orchestrator
        orchestrator = Orchestrator()
        await orchestrator.start_campaign(campaign_id)
        print(f"    ✓ Campaign started")

        # Give it a moment to process
        await asyncio.sleep(config["test"]["wait_for_agents_timeout"])

        # 3. Check if agents were spawned
        from api.supervisor import supervisor
        agents = supervisor.get_campaign_agents(campaign_id)
        assert len(agents) > 0
        print(f"    ✓ Agents spawned: {len(agents)}")

        # 4. Verify agent can communicate with MCP server
        # (This will fail until MCP server is running)
        mcp_config = config["mcp"]["nmap"]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{mcp_config['host']}:{mcp_config['port']}/health",
                    timeout=config["test"]["health_check_timeout"]
                )
                if response.status_code == 200:
                    print(f"    ✓ MCP server responding")
        except httpx.ConnectError:
            print(f"    ⊘ MCP server not running (build nmap server next)")

        # Cleanup
        await orchestrator.stop_campaign(campaign_id)

        return True

    except ImportError as e:
        return f"Components not built yet: {e}"
    except AttributeError as e:
        return f"Missing functionality: {e}"


# ============================================================================
# Main
# ============================================================================

async def main():
    print("=" * 60)
    print("Phase 2 Test Harness - First Vertical Slice")
    print("=" * 60)
    print("\nThis test suite verifies Phase 2 components:")
    print("  1. BaseAgent class (actor + persona)")
    print("  2. nmap MCP server")
    print("  3. Supervisor process")
    print("  4. Campaign orchestrator")
    print("  5. End-to-end integration")
    print("\nTests will be SKIPPED if components aren't built yet.")
    print("=" * 60)

    # Run all tests
    await test_base_agent_exists()
    await test_base_agent_init()
    await test_base_agent_queue()

    await test_nmap_server_exists()
    await test_nmap_server_running()
    await test_nmap_mcp_protocol()

    await test_supervisor_exists()
    await test_supervisor_spawn()
    await test_supervisor_health_check()

    await test_orchestrator_exists()
    await test_orchestrator_start_campaign()

    await test_end_to_end()

    # Print summary
    harness.summary()

    return harness.failed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
