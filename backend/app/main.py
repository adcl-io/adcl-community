# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
FastAPI Orchestrator - Main Platform API
Manages MCP server registry and executes workflows
"""
# Load environment variables from .env file (local development)
# Docker Compose loads .env automatically, but this helps with local dev
from dotenv import load_dotenv
from pathlib import Path as _PathForEnv
_env_path = _PathForEnv(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    print(f"✅ Loaded environment variables from {_env_path}")

from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Dict, List, Any, Optional, Callable
import httpx
import json
import yaml
from pathlib import Path
import asyncio
import os
from datetime import datetime
from uuid import uuid4
from app.docker_manager import DockerManager
from app.agent_runtime import AgentRuntime
from app.team_runtime import TeamRuntime
from app.config import get_config
from app.core.errors import sanitize_error_for_user
from anthropic import Anthropic
from openai import OpenAI

# Import API routers (PRD-99 refactoring)
from app.api import agents, workflows, teams, models, mcps, executions


app = FastAPI(
    title="MCP Agent Platform",
    description="Orchestrator for MCP-based agent teams",
    version="0.1.0",
)

# Initialize configuration
config = get_config()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class MCPServerInfo(BaseModel):
    name: str
    endpoint: str
    description: Optional[str] = ""
    version: str = "1.0.0"


class WorkflowNode(BaseModel):
    id: str
    type: str  # "mcp_call"
    mcp_server: str
    tool: str
    params: Dict[str, Any]


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowDefinition(BaseModel):
    name: str
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class ExecutionRequest(BaseModel):
    workflow: WorkflowDefinition


class ExecutionLog(BaseModel):
    timestamp: str
    node_id: Optional[str] = None
    level: str  # "info", "success", "error"
    message: str


class NodeState(BaseModel):
    node_id: str
    status: str  # "pending", "running", "completed", "error"
    result: Optional[Any] = None
    error: Optional[str] = None


class ExecutionResult(BaseModel):
    status: str
    results: Dict[str, Any]
    errors: List[str] = []
    logs: List[ExecutionLog] = []
    node_states: Dict[str, str] = {}  # node_id -> status


# MCP Server Registry
class MCPRegistry:
    """Registry of available MCP servers"""

    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}

    def register(self, server: MCPServerInfo):
        """Register an MCP server"""
        self.servers[server.name] = server
        print(f"Registered MCP server: {server.name} at {server.endpoint}")

    def get(self, name: str) -> Optional[MCPServerInfo]:
        """Get MCP server info"""
        return self.servers.get(name)

    def list_all(self) -> List[MCPServerInfo]:
        """List all registered servers"""
        return list(self.servers.values())


# Global registry
registry = MCPRegistry()


# WebSocket Connection Manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.cancellation_flags: Dict[str, bool] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect a new WebSocket client"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.cancellation_flags[session_id] = False
        print(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.cancellation_flags:
            del self.cancellation_flags[session_id]
        print(f"WebSocket disconnected: {session_id}")

    def cancel_execution(self, session_id: str):
        """Mark execution as cancelled"""
        self.cancellation_flags[session_id] = True
        print(f"Execution cancelled for session: {session_id}")

    def is_cancelled(self, session_id: str) -> bool:
        """Check if execution is cancelled"""
        return self.cancellation_flags.get(session_id, False)

    async def send_update(self, session_id: str, message: dict):
        """Send update to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error sending to {session_id}: {e}")
                self.disconnect(session_id)


manager = ConnectionManager()

# MCP Manager for Docker lifecycle (lazy initialization)
mcp_manager = None


def get_mcp_manager():
    """Get or initialize MCP manager (lazy loading)"""
    global mcp_manager
    if mcp_manager is None:
        try:
            mcp_manager = DockerManager()
            print("✅ Docker Manager initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Docker Manager: {e}")
            print("   MCP installation features will be disabled.")

            # Return a dummy object that raises errors on use
            class DummyMCPManager:
                def __getattr__(self, name):
                    raise HTTPException(
                        status_code=503,
                        detail="Docker Manager not available. Docker CLI may not be accessible.",
                    )

            mcp_manager = DummyMCPManager()
    return mcp_manager


# Trigger Manager for Docker lifecycle (lazy initialization)
trigger_manager = None


def get_trigger_manager():
    """Get or initialize Trigger manager (lazy loading)"""
    global trigger_manager
    if trigger_manager is None:
        try:
            trigger_manager = DockerManager(resource_type="trigger")
            print("✅ Trigger Manager initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Trigger Manager: {e}")
            print("   Trigger installation features will be disabled.")

            # Return a dummy object that raises errors on use
            class DummyTriggerManager:
                def __getattr__(self, name):
                    raise HTTPException(
                        status_code=503,
                        detail="Trigger Manager not available. Docker CLI may not be accessible.",
                    )

            trigger_manager = DummyTriggerManager()
    return trigger_manager

# Import enhanced workflow engine
from app.workflow_engine import WorkflowEngine
from app.workflow_loader import WorkflowLoader

# Initialize workflow loader and engine
workflow_loader = WorkflowLoader()
engine = WorkflowEngine(registry, workflow_loader)

# Initialize AI clients (allow None for optional providers)
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Anthropic client (required for most features)
if anthropic_api_key:
    anthropic_client = Anthropic(api_key=anthropic_api_key)
else:
    anthropic_client = None
    print("⚠️  Warning: ANTHROPIC_API_KEY not set. Agent features will be limited.")

# OpenAI client (optional)
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)
else:
    openai_client = None
    print("⚠️  Warning: OPENAI_API_KEY not set. OpenAI models will not be available.")

# Initialize agent runtime for autonomous agents with both clients
agent_runtime = AgentRuntime(registry, anthropic_client, openai_client)

# Initialize team runtime for multi-agent teams
team_runtime = TeamRuntime(
    agent_runtime=agent_runtime,
    agents_dir=Path(config.get_agent_definitions_path()),
    teams_dir=Path(config.get_agent_teams_path()),
)


# Mount API routers (PRD-99 refactoring)
# Note: All routers either have prefixes defined or include full paths in their routes,
# so we don't add prefixes here to avoid double-prefixing (e.g., /agents/agents).
app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(teams.router)
app.include_router(models.router)
app.include_router(mcps.router)  # Routes already include /mcp and /mcps paths
app.include_router(executions.router)


# API Routes
@app.on_event("startup")
async def startup():
    """
    Startup tasks:
    1. Store runtime objects in app.state for dependency injection
    2. Discover and register dynamically installed MCPs
    3. Auto-install default MCPs from registry if configured
    """
    print("🚀 Starting orchestrator...")

    # Store runtime objects in app.state for proper dependency injection
    app.state.workflow_engine = engine
    app.state.agent_runtime = agent_runtime
    app.state.team_runtime = team_runtime
    app.state.mcp_registry = registry  # Global MCP registry with registered servers
    app.state.mcp_manager = None  # Will be set after MCP manager initializes
    print("✅ Runtime objects stored in app.state")

    # Wait for registry to be ready
    print("⏳ Waiting for registry server...")
    await asyncio.sleep(config.get_polling_interval())

    # 1. Discover already installed MCPs
    print("🔍 Discovering installed MCPs...")
    try:
        mcp_mgr = get_mcp_manager()
        app.state.mcp_manager = mcp_mgr  # Store in app.state for dependency injection
        installed_mcps = mcp_mgr.list_installed()
        installed_names = {mcp["name"] for mcp in installed_mcps}
    except Exception as e:
        print(f"⚠️  Could not discover installed MCPs: {e}")
        installed_mcps = []
        installed_names = set()

    # 2. Auto-install default MCPs from registry if not already installed
    auto_install = os.getenv("AUTO_INSTALL_MCPS", "")
    if auto_install:
        mcps_to_install = [
            name.strip() for name in auto_install.split(",") if name.strip()
        ]
        print(f"📦 Auto-installing default MCPs: {', '.join(mcps_to_install)}")

        for mcp_name in mcps_to_install:
            if mcp_name in installed_names:
                print(f"  ⏭️  Skipping {mcp_name} - already installed")
                continue

            try:
                # Fetch from registry
                registries = parse_registries_conf()
                enabled_registries = [r for r in registries if r.get("enabled", True)]

                for reg in enabled_registries:
                    try:
                        async with httpx.AsyncClient(
                            timeout=config.get_http_timeout_default()
                        ) as client:
                            # Try to find MCP by name
                            response = await client.get(f"{reg['url']}/catalog")
                            response.raise_for_status()
                            catalog = response.json()

                            # Find MCP in catalog
                            mcp_id = None
                            for mcp in catalog.get("mcps", []):
                                if mcp.get("name") == mcp_name:
                                    mcp_id = mcp.get("id")
                                    break

                            if mcp_id:
                                # Fetch full package
                                response = await client.get(
                                    f"{reg['url']}/mcps/{mcp_id}"
                                )
                                response.raise_for_status()
                                mcp_package = response.json()

                                # Install
                                print(
                                    f"  📥 Installing {mcp_name} from {reg['name']}..."
                                )
                                result = get_mcp_manager().install(mcp_package)

                                if result["status"] in [
                                    "installed",
                                    "already_installed",
                                ]:
                                    print(f"  ✅ Installed {mcp_name} successfully")
                                    installed_mcps.append(result)
                                    break
                                else:
                                    print(
                                        f"  ❌ Failed to install {mcp_name}: {result.get('error', 'Unknown error')}"
                                    )
                    except Exception as e:
                        print(
                            f"  ⚠️  Error fetching {mcp_name} from {reg.get('name', 'registry')}: {e}"
                        )
                        continue
            except Exception as e:
                print(f"  ⚠️  Failed to auto-install {mcp_name}: {e}")

    # 3. Register all installed MCPs with orchestrator
    print("🔧 Registering installed MCPs...")
    installed_mcps = get_mcp_manager().list_installed()

    for mcp in installed_mcps:
        # Only register if running
        if mcp.get("running"):
            try:
                # Get full package info to register
                # Use backwards-compatible property access (works for both MCPManager and DockerManager)
                mcp_manager = get_mcp_manager()
                installed_registry = getattr(
                    mcp_manager, "installed", mcp_manager.installed_mcps
                )
                mcp_info = installed_registry.get(mcp["name"])
                if mcp_info and "package" in mcp_info:
                    mcp_package = mcp_info["package"]
                    deployment = mcp_package.get("deployment", {})

                    # Determine endpoint based on network mode
                    if deployment.get("network_mode") == "host":
                        # Host mode: use host.docker.internal
                        port_env_var = f"{mcp['name'].upper()}_PORT"
                        port = os.getenv(port_env_var, str(config.get_nmap_port()))
                        endpoint = config.get_docker_host_url_pattern().format(
                            port=port
                        )
                    else:
                        # Bridge mode: use container name
                        container_name = deployment.get(
                            "container_name", f"mcp-{mcp['name']}"
                        )
                        port_config = deployment.get("ports", [{}])[0]
                        port = port_config.get(
                            "container", str(config.get_agent_port())
                        )
                        # Resolve environment variables in port
                        port = (
                            port.replace("${", "").split(":-")[1].replace("}", "")
                            if "${" in str(port)
                            else port
                        )
                        endpoint = config.get_docker_container_url_pattern().format(
                            container_name=container_name, port=port
                        )

                    # Register with orchestrator
                    registry.register(
                        MCPServerInfo(
                            name=mcp["name"],
                            endpoint=endpoint,
                            description=mcp_package.get("description", ""),
                            version=mcp_package.get("version", "1.0.0"),
                        )
                    )
                    print(
                        f"  ✅ Registered {mcp['name']} v{mcp['version']} at {endpoint}"
                    )
            except Exception as e:
                print(f"  ⚠️  Failed to register {mcp['name']}: {e}")

    print(f"✅ Orchestrator ready! {len(registry.servers)} MCP servers registered.")

    # 4. Load model configurations from configs/models.yaml
    print("🤖 Loading model configurations from configs/models.yaml...")
    global models_db
    models_db = load_models_from_config()
    print(f"✅ Loaded {len(models_db)} models")


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/debug/mcps")
async def debug_mcps():
    """Debug endpoint to test MCP detection"""
    import subprocess

    debug_info = {
        "registry_servers": list(registry.servers.keys()),
        "docker_containers": [],
        "matches": [],
    }

    # Get all containers
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"],
        capture_output=True,
        text=True,
        check=False,
    )

    for line in result.stdout.strip().split("\n"):
        if line:
            debug_info["docker_containers"].append(line)

    # Test matching
    for server_name in registry.servers.keys():
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) == 2:
                container_name, status_text = parts
                if server_name in container_name and not container_name.startswith(
                    "mcp-"
                ):
                    if (
                        container_name == server_name
                        or f"_{server_name}_" in container_name
                        or container_name.endswith(f"_{server_name}_1")
                    ):
                        debug_info["matches"].append(
                            {
                                "server": server_name,
                                "container": container_name,
                                "status": status_text,
                            }
                        )

    return debug_info


# MCP Server Management API (Endpoints moved to app/api/mcps.py)


@app.websocket("/ws/execute/{session_id}")
async def websocket_execute(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time workflow execution"""
    await manager.connect(session_id, websocket)

    try:
        # Wait for workflow data
        data = await websocket.receive_json()
        workflow = WorkflowDefinition(**data["workflow"])

        # Create callback to send updates
        async def send_update(message: dict):
            await manager.send_update(session_id, message)

        # Execute workflow with real-time updates
        result = await engine.execute(workflow, update_callback=send_update)

        # Send final result
        await manager.send_update(
            session_id, {"type": "complete", "result": result.dict()}
        )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_update(session_id, {"type": "error", "error": str(e)})
        manager.disconnect(session_id)


# Workflow Execution API (All endpoints moved to app/api/workflows.py)

# Teams API - File-based storage with MCP pools
class TeamAgent(BaseModel):
    """Agent reference in a team - references autonomous agent by ID"""

    agent_id: str
    role: str
    responsibilities: Optional[List[str]] = []
    mcp_access: Optional[List[str]] = []  # Optional MCP restrictions


class Coordination(BaseModel):
    """Team coordination configuration"""

    mode: str = "sequential"  # sequential, parallel, collaborative
    share_context: bool = True
    task_distribution: str = "automatic"


class Team(BaseModel):
    """Multi-agent team with shared MCP pool"""

    name: str
    description: Optional[str] = ""
    version: str = "1.0.0"
    available_mcps: List[str]  # Team MCP pool
    agents: List[TeamAgent]
    coordination: Optional[Coordination] = None
    tags: Optional[List[str]] = []
    author: Optional[str] = ""


class TeamUpdate(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    version: str = "1.0.0"
    available_mcps: List[str]
    agents: List[TeamAgent]
    coordination: Optional[Coordination] = None
    tags: Optional[List[str]] = []
    author: Optional[str] = ""


def get_teams_dir():
    """Get the teams directory path"""
    teams_dir = Path(config.get_agent_teams_path())
    teams_dir.mkdir(exist_ok=True)
    return teams_dir


def load_team_from_file(file_path: Path) -> dict:
    """Load a team from a JSON file"""
    team_data = json.loads(file_path.read_text())
    # Use filename (without .json) as ID
    team_data["id"] = file_path.stem
    team_data["file"] = file_path.name
    return team_data


def save_team_to_file(team_id: str, team_data: dict):
    """Save a team to a JSON file"""
    teams_dir = get_teams_dir()
    file_path = teams_dir / f"{team_id}.json"

    # Remove id and file from saved data (metadata only)
    save_data = {k: v for k, v in team_data.items() if k not in ["id", "file"]}

    file_path.write_text(json.dumps(save_data, indent=2))
    return file_path


# Execution persistence helpers (ADCL compliance - disk-first, no hidden state)
def get_executions_dir():
    """Get the executions directory path"""
    executions_dir = Path("volumes/executions")
    executions_dir.mkdir(parents=True, exist_ok=True)
    return executions_dir


def create_execution_dir(execution_id: str):
    """Create execution directory and return path"""
    execution_dir = get_executions_dir() / execution_id
    execution_dir.mkdir(parents=True, exist_ok=True)
    return execution_dir


def log_execution_event(execution_dir: Path, event: dict):
    """Log event to disk (REQUIRED - source of truth)"""
    progress_file = execution_dir / "progress.jsonl"
    event_with_timestamp = {**event, "timestamp": datetime.now().isoformat()}
    with open(progress_file, "a") as f:
        f.write(json.dumps(event_with_timestamp) + "\n")


# Teams API (CRUD endpoints moved to app/api/teams.py)


# Chat API
class ChatMessage(BaseModel):
    team_id: str
    message: str
    history: List[Dict[str, str]] = []


@app.post("/chat")
async def chat(msg: ChatMessage):
    """Chat with an agent team - can execute workflows based on intent"""
    import re

    # Find team from disk
    team = None
    try:
        teams_dir = get_teams_dir()
        for file in teams_dir.glob("*.json"):
            team_data = load_team_from_file(file)
            if team_data["id"] == msg.team_id:
                team = team_data
                break
    except Exception as e:
        print(f"Error loading teams: {e}")

    # Check if team uses new schema (has available_mcps)
    if team and "available_mcps" in team:
        # New team format: use team runtime for execution
        try:
            result = await team_runtime.run_team(
                team_definition=team, task=msg.message, context={}
            )

            # Format result for chat response
            return {
                "response": result.get("answer", "Team completed the task."),
                "agent": team["name"],
                "team_result": result,
            }
        except Exception as e:
            import traceback

            print(f"Team execution error: {traceback.format_exc()}")
            return {
                "response": f"❌ Team execution failed: {str(e)}",
                "agent": team["name"] if team else "Agent",
            }

    # Check if this is a network scanning request
    scan_keywords = [
        "scan",
        "discover",
        "find hosts",
        "network discovery",
        "identify hosts",
        "reconnaissance",
    ]
    is_scan_request = any(keyword in msg.message.lower() for keyword in scan_keywords)

    # Extract IP/network from message
    network_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b"
    network_match = re.search(network_pattern, msg.message)

    import logging

    logging.info(
        f"Chat debug: is_scan_request={is_scan_request}, network_match={network_match}"
    )
    logging.info(f"Chat debug: team={team}, message='{msg.message}'")

    if is_scan_request and network_match:
        target_network = network_match.group(0)

        # Check if team has nmap_recon agent
        has_scanner = False
        if team and len(team.get("agents", [])) > 0:
            has_scanner = any(
                agent.get("mcp_server") == "nmap_recon" for agent in team["agents"]
            )

        if has_scanner or not team:
            # Execute network discovery workflow
            try:
                # Generate timestamp for filename
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = (
                    f"network_scan_{target_network.replace('/', '_')}_{timestamp}.md"
                )

                workflow = WorkflowDefinition(
                    name="Chat-triggered Network Scan",
                    nodes=[
                        WorkflowNode(
                            id="discover-hosts",
                            type="mcp_call",
                            mcp_server="nmap_recon",
                            tool="network_discovery",
                            params={"network": target_network},
                        ),
                        WorkflowNode(
                            id="analyze-results",
                            type="mcp_call",
                            mcp_server="agent",
                            tool="think",
                            params={
                                "prompt": f"Analyze these network discovery results and create a detailed report:\n\n${{discover-hosts}}\n\nProvide: 1) Executive summary, 2) Number of active hosts, 3) Key findings, 4) Security recommendations\n\nFormat the output as a professional security report in Markdown."
                            },
                        ),
                        WorkflowNode(
                            id="write-report",
                            type="mcp_call",
                            mcp_server="file_tools",
                            tool="write_file",
                            params={
                                "path": f"/workspace/{report_filename}",
                                "content": "${analyze-results.reasoning}",
                            },
                        ),
                    ],
                    edges=[
                        WorkflowEdge(source="discover-hosts", target="analyze-results"),
                        WorkflowEdge(source="analyze-results", target="write-report"),
                    ],
                )

                # Execute the workflow
                result = await engine.execute(workflow)

                if result.status == "completed":
                    # Get the analysis
                    analysis = result.results.get("analyze-results", {})
                    if isinstance(analysis, dict):
                        response_text = analysis.get("reasoning", str(analysis))
                    else:
                        response_text = str(analysis)

                    # Check if report was written
                    report_written = result.results.get("write-report", {})

                    # Also include scan summary
                    scan_data = result.results.get("discover-hosts", {})
                    scan_summary = f"\n\n**Scan Results:**\n"
                    if isinstance(scan_data, dict):
                        scan_summary += (
                            f"- Network: {scan_data.get('network', target_network)}\n"
                        )
                        scan_summary += f"- Total Hosts Scanned: {scan_data.get('total_hosts', 'N/A')}\n"
                        if "hosts_discovered" in scan_data and isinstance(
                            scan_data["hosts_discovered"], list
                        ):
                            scan_summary += f"- Active Hosts: {len(scan_data['hosts_discovered'])}\n"

                            # Add report file info
                            if report_written:
                                scan_summary += f"- 📄 **Detailed Report Saved:** `workspace/{report_filename}`\n"
                                scan_summary += (
                                    f"  (Accessible from project directory)\n\n"
                                )

                            if len(scan_data["hosts_discovered"]) > 0:
                                scan_summary += f"\n**Discovered Hosts (first 10):**\n"
                                for host in scan_data["hosts_discovered"][
                                    :10
                                ]:  # Limit to first 10
                                    ip = host.get("ip", "unknown")
                                    hostname = host.get("hostname", "")
                                    mac = host.get("mac", "")
                                    scan_summary += f"- {ip}"
                                    if hostname:
                                        scan_summary += f" ({hostname})"
                                    if mac:
                                        scan_summary += f" [MAC: {mac}]"
                                    scan_summary += "\n"
                            else:
                                scan_summary += "\nNo active hosts found."
                        else:
                            scan_summary += f"\nNo hosts discovered."

                    team_name = team["name"] if team else "Security Team"
                    return {
                        "response": f"✅ Network scan completed and report generated!\n\n{scan_summary}",
                        "agent": team_name,
                        "workflow_result": result.dict(),
                        "report_file": report_filename,
                    }
                else:
                    return {
                        "response": f"❌ Scan failed: {', '.join(result.errors)}",
                        "agent": team["name"] if team else "Agent",
                    }

            except Exception as e:
                import traceback

                print(f"Workflow execution error: {traceback.format_exc()}")
                return {
                    "response": f"❌ Failed to execute scan: {str(e)}",
                    "agent": team["name"] if team else "Agent",
                }

    # Default: use agent for thinking/reasoning with multi-agent collaboration

    # Build conversation history
    conversation_history = ""
    if msg.history and len(msg.history) > 0:
        conversation_history = "\n\nPrevious conversation:\n"
        for hist in msg.history[-10:]:  # Last 10 messages
            role = hist.get("role", "unknown")
            content = hist.get("content", "")
            conversation_history += f"{role}: {content}\n"
        conversation_history += "\n"

    # If team has multiple agents, get input from each
    if team and len(team.get("agents", [])) > 1:
        team_responses = []

        # Get response from each agent in the team
        for agent in team["agents"]:
            server = registry.get(agent["mcp_server"])
            if not server:
                team_responses.append(
                    {
                        "agent": agent["name"],
                        "role": agent["role"],
                        "response": f"⚠️ MCP server '{agent['mcp_server']}' not available",
                    }
                )
                continue

            # Build agent-specific prompt
            agent_context = f"You are {agent['name']}, the {agent['role']} on the '{team['name']}' team.\n"
            agent_context += f"Team description: {team['description']}\n"
            agent_context += f"Your MCP server capabilities: {agent['mcp_server']}\n\n"

            # Only agent MCP has think tool, others should describe their capabilities
            if agent["mcp_server"] == "agent":
                tool = "think"
                prompt = f"{conversation_history}{agent_context}User message: {msg.message}\n\nProvide your analysis and recommendations."
            else:
                # For non-agent MCP servers, use agent to explain what this team member would do
                server = registry.get("agent")
                if not server:
                    continue
                tool = "think"
                prompt = f"{conversation_history}{agent_context}User message: {msg.message}\n\nAs {agent['name']}, explain what you would do with your {agent['mcp_server']} capabilities to help with this request. Be specific about the tools/actions you would use."

            try:
                response = await engine.client.post(
                    f"{server.endpoint}/mcp/call_tool",
                    json={"tool": tool, "arguments": {"prompt": prompt}},
                )
                response.raise_for_status()
                data = response.json()

                if data.get("isError"):
                    team_responses.append(
                        {
                            "agent": agent["name"],
                            "role": agent["role"],
                            "response": f"⚠️ Error: {data['content'][0]['text']}",
                        }
                    )
                else:
                    result = data["content"][0]["text"]
                    try:
                        result_json = json.loads(result)
                        team_responses.append(
                            {
                                "agent": agent["name"],
                                "role": agent["role"],
                                "response": result_json.get("reasoning", result),
                            }
                        )
                    except (json.JSONDecodeError, TypeError, KeyError):
                        # Use raw response if JSON parsing fails
                        team_responses.append(
                            {
                                "agent": agent["name"],
                                "role": agent["role"],
                                "response": result,
                            }
                        )
            except Exception as e:
                team_responses.append(
                    {
                        "agent": agent["name"],
                        "role": agent["role"],
                        "response": f"⚠️ Error: {str(e)}",
                    }
                )

        # Combine all team responses
        combined_response = f"**{team['name']} Team Response:**\n\n"
        for resp in team_responses:
            combined_response += (
                f"**{resp['agent']}** ({resp['role']}):\n{resp['response']}\n\n---\n\n"
            )

        return {
            "response": combined_response,
            "agent": team["name"],
            "team_responses": team_responses,
        }

    # Single agent or default
    server = registry.get("agent")
    if not server:
        raise HTTPException(status_code=404, detail="Agent server not found")

    # Build context
    team_context = ""
    if team and len(team.get("agents", [])) > 0:
        agent = team["agents"][0]
        team_context = f"\n\nYou are {agent['name']}, the {agent['role']} on the '{team['name']}' team: {team['description']}\n"
        team_context += "\nNote: For network scanning requests, just ask me to 'scan [network]' and I will execute the scan for you.\n"

    # Combine message with history and context
    full_prompt = f"{conversation_history}{team_context}User message: {msg.message}"

    try:
        response = await engine.client.post(
            f"{server.endpoint}/mcp/call_tool",
            json={"tool": "think", "arguments": {"prompt": full_prompt}},
        )
        response.raise_for_status()
        data = response.json()

        if data.get("isError"):
            raise ValueError(data["content"][0]["text"])

        result = data["content"][0]["text"]
        try:
            result_json = json.loads(result)
            agent_name = team["name"] if team else "Agent"
            return {
                "response": result_json.get("reasoning", result),
                "agent": agent_name,
                "reasoning": result_json if isinstance(result_json, dict) else None,
            }
        except (json.JSONDecodeError, TypeError, KeyError):
            # Use raw response if JSON parsing fails
            agent_name = team["name"] if team else "Agent"
            return {"response": result, "agent": agent_name}
    except Exception as e:
        import traceback

        # Log full traceback for debugging
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Chat error: {error_detail}")

        # Send sanitized error to user
        raise HTTPException(status_code=500, detail=sanitize_error_for_user(e))


# Token Tracking API
@app.get("/sessions/{session_id}/tokens")
async def get_session_tokens(session_id: str):
    """
    Get token usage and cost for a session.
    Backend is source of truth for billing data.
    """
    from app.token_tracker import get_token_tracker

    tracker = get_token_tracker()
    return tracker.get_session_tokens(session_id)


# WebSocket Chat API for streaming
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat with streaming agent updates"""
    await manager.connect(session_id, websocket)

    try:
        # Wait for chat message
        data = await websocket.receive_json()

        # Check if this is a cancellation request
        if data.get("type") == "cancel_execution":
            manager.cancel_execution(session_id)
            await manager.send_update(session_id, {
                "type": "cancelled",
                "message": "Execution cancelled by user"
            })
            return

        team_id = data.get("team_id")
        message = data.get("message")

        print(f"\n💬 WebSocket chat for session {session_id}, team: {team_id}")

        # Find team from disk
        team = None
        try:
            teams_dir = get_teams_dir()
            for file in teams_dir.glob("*.json"):
                team_data = load_team_from_file(file)
                if team_data["id"] == team_id:
                    team = team_data
                    break
        except Exception as e:
            print(f"Error loading teams: {e}")

        # Create callback to send updates
        async def send_update(update: dict):
            await manager.send_update(session_id, update)

        # Check if team uses new schema (has available_mcps)
        if team and "available_mcps" in team:
            # New team format: use team runtime with streaming
            try:
                # Send initial status
                await send_update(
                    {
                        "type": "status",
                        "status": "starting",
                        "message": f"🚀 Starting {team['name']}...",
                    }
                )

                result = await team_runtime.run_team(
                    team_definition=team,
                    task=message,
                    context={},
                    progress_callback=send_update,
                    session_id=session_id,
                    manager=manager,
                )

                # Check if execution was cancelled
                if result.get("status") == "cancelled":
                    print(f"\n🛑 Execution was cancelled")
                    await manager.send_update(
                        session_id, {
                            "type": "cancelled",
                            "message": result.get("message", "Execution cancelled by user"),
                            "result": result
                        }
                    )
                    return

                # Check if any agent had an error
                agent_errors = []
                if result.get("agent_results"):
                    print(f"\n🔍 Checking {len(result['agent_results'])} agent results for errors...")
                    for agent_result in result["agent_results"]:
                        status = agent_result.get("status")
                        agent_id = agent_result.get("agent_id", "unknown")
                        print(f"   Agent {agent_id}: status = {status}")
                        if status == "error":
                            error_msg = agent_result.get("error", "Unknown error")
                            role = agent_result.get("role", "Agent")
                            agent_errors.append(f"{role} ({agent_id}): {error_msg}")
                            print(f"   ❌ Error found: {error_msg[:100]}...")

                # If any agent had an error, send as error type
                if agent_errors:
                    error_summary = "\n".join(agent_errors)
                    print(f"\n⚠️  Sending error message to frontend: {error_summary[:200]}...")
                    await manager.send_update(
                        session_id, {
                            "type": "error",
                            "error": f"Team execution failed:\n\n{error_summary}",
                            "result": result  # Include full result for debugging
                        }
                    )
                else:
                    # Send final result (all agents succeeded)
                    print(f"\n✅ All agents succeeded, sending complete message")
                    await manager.send_update(
                        session_id, {"type": "complete", "result": result}
                    )

            except Exception as e:
                import traceback

                # Log full traceback for debugging
                print(f"Team execution error: {traceback.format_exc()}")

                # Send sanitized error to user
                await manager.send_update(
                    session_id, {"type": "error", "error": sanitize_error_for_user(e, include_type=False)}
                )
        else:
            # Old format or no team - simple response
            await manager.send_update(
                session_id,
                {"type": "error", "error": "Team not found or using old format"},
            )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_update(session_id, {"type": "error", "error": str(e)})
        manager.disconnect(session_id)


# Models API - Following ADCL principle: Configuration is Code
# Models are stored in configs/models.yaml and loaded at startup
# API keys are stored in environment variables for security
models_db = []  # Loaded from configs/models.yaml
models_lock = asyncio.Lock()  # Prevent race conditions
MODELS_CONFIG_PATH = Path("/configs/models.yaml")


def load_models_from_config() -> List[Dict[str, Any]]:
    """
    Load model configurations from configs/models.yaml
    Following ADCL principle: All config in text files
    """
    try:
        if not MODELS_CONFIG_PATH.exists():
            print(f"  ⚠️  Models config not found at {MODELS_CONFIG_PATH}")
            return []

        with open(MODELS_CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data or "models" not in config_data:
            print("  ⚠️  No models section in config file")
            return []

        # Validate config structure with Pydantic
        try:
            validated_config = ModelsConfigFile(**config_data)
        except Exception as validation_error:
            print(f"  ❌ Config validation error in {MODELS_CONFIG_PATH}:")
            print(f"     {validation_error}")
            return []

        # Check for duplicate model IDs
        model_ids = [m.id for m in validated_config.models]
        if len(model_ids) != len(set(model_ids)):
            duplicates = [id for id in model_ids if model_ids.count(id) > 1]
            print(f"  ❌ Duplicate model IDs found in config: {set(duplicates)}")
            return []

        # Check for multiple default models
        default_count = sum(1 for m in validated_config.models if m.is_default)
        if default_count > 1:
            print(f"  ❌ Multiple default models found in config ({default_count}). Only one allowed.")
            return []

        models = []
        anthropic_key = config.get_anthropic_api_key()
        openai_key = config.get_openai_api_key()

        for model_config in validated_config.models:
            # Determine if model is configured based on environment variables
            api_key_env = model_config.api_key_env
            if api_key_env == "ANTHROPIC_API_KEY":
                configured = bool(anthropic_key)
            elif api_key_env == "OPENAI_API_KEY":
                configured = bool(openai_key)
            else:
                configured = False

            model_data = {
                "id": model_config.id,
                "name": model_config.name,
                "provider": model_config.provider,
                "model_id": model_config.model_id,
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_tokens,
                "description": model_config.description,
                "is_default": model_config.is_default,
                "configured": configured,
                "api_key": "***configured***" if configured else None,
            }
            models.append(model_data)

        print(f"  ✅ Loaded {len(models)} models from {MODELS_CONFIG_PATH}")

        # Ensure exactly one default model
        default_models = [m for m in models if m.get("is_default")]
        if len(default_models) == 0 and len(models) > 0:
            print("  ⚠️  No default model set, setting first configured model as default")
            for m in models:
                if m.get("configured"):
                    m["is_default"] = True
                    break
        elif len(default_models) > 1:
            print(f"  ⚠️  Multiple default models found, keeping only first one")
            for i, m in enumerate(models):
                if m.get("is_default") and i > 0:
                    m["is_default"] = False

        return models

    except yaml.YAMLError as e:
        print(f"  ❌ YAML parsing error in {MODELS_CONFIG_PATH}: {e}")
        return []
    except FileNotFoundError:
        print(f"  ❌ Config file not found: {MODELS_CONFIG_PATH}")
        return []
    except Exception as e:
        print(f"  ❌ Unexpected error loading models: {e}")
        return []


async def save_models_to_config(models: List[Dict[str, Any]]) -> bool:
    """
    Save model configurations to configs/models.yaml
    Following ADCL principle: All config persisted in text files
    """
    try:
        # Load existing config to preserve other sections
        existing_config = {}
        if MODELS_CONFIG_PATH.exists():
            with open(MODELS_CONFIG_PATH, "r") as f:
                existing_config = yaml.safe_load(f) or {}

        # Update models section
        config_models = []
        for model in models:
            # Determine api_key_env based on provider
            if model["provider"] == "anthropic":
                api_key_env = "ANTHROPIC_API_KEY"
            elif model["provider"] == "openai":
                api_key_env = "OPENAI_API_KEY"
            else:
                api_key_env = f"{model['provider'].upper()}_API_KEY"

            config_model = {
                "id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
                "model_id": model["model_id"],
                "temperature": model.get("temperature", 0.7),
                "max_tokens": model.get("max_tokens", 4096),
                "description": model.get("description", ""),
                "is_default": model.get("is_default", False),
                "api_key_env": api_key_env,
            }
            config_models.append(config_model)

        existing_config["models"] = config_models

        # Write back to file
        with open(MODELS_CONFIG_PATH, "w") as f:
            yaml.safe_dump(existing_config, f, default_flow_style=False, sort_keys=False)

        print(f"  💾 Saved {len(models)} models to {MODELS_CONFIG_PATH}")
        return True

    except Exception as e:
        print(f"  ❌ Failed to save models to config: {e}")
        return False


class Model(BaseModel):
    name: str
    provider: str
    model_id: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = config.get_llm_max_tokens()
    description: Optional[str] = ""
    is_default: bool = False


class ModelUpdate(BaseModel):
    name: str
    provider: str
    model_id: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = config.get_llm_max_tokens()
    description: Optional[str] = ""
    is_default: bool = False


# Validation models for models.yaml config file
class ModelConfigSchema(BaseModel):
    """Schema for validating individual model configs in models.yaml"""
    id: str
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    description: str = ""
    is_default: bool = False
    api_key_env: str = ""

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('temperature must be between 0.0 and 2.0')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1 or v > 1000000:
            raise ValueError('max_tokens must be between 1 and 1000000')
        return v

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        allowed = ['anthropic', 'openai', 'google', 'cohere', 'mistral']
        if v not in allowed:
            raise ValueError(f'provider must be one of: {", ".join(allowed)}')
        return v


class ModelsConfigFile(BaseModel):
    """Schema for validating the entire models.yaml file"""
    models: List[ModelConfigSchema]


# Models API (All endpoints moved to app/api/models.py)


# Registry API - Package management (yum-like)
def parse_registries_conf() -> List[Dict[str, Any]]:
    """Parse registries.conf file (similar to /etc/yum.repos.d/)"""
    config_path = Path(config.get_registries_conf_path())
    if not config_path.exists():
        return []

    registries = []
    current_registry = {}

    for line in config_path.read_text().splitlines():
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # New registry section
        if line.startswith("[") and line.endswith("]"):
            if current_registry:
                registries.append(current_registry)
            current_registry = {"id": line[1:-1]}
        # Key-value pairs
        elif "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Convert boolean strings
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            # Convert numeric strings
            elif value.isdigit():
                value = int(value)

            current_registry[key] = value

    if current_registry:
        registries.append(current_registry)

    return registries


@app.get("/registries")
async def list_registries():
    """List configured package registries"""
    return parse_registries_conf()


@app.get("/registries/catalog")
async def get_all_catalogs():
    """Get combined catalog from all enabled registries"""
    registries = parse_registries_conf()
    enabled_registries = [r for r in registries if r.get("enabled", True)]

    combined_catalog = {"registries": [], "mcps": [], "teams": [], "triggers": []}

    for registry in enabled_registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_health_check()
            ) as client:
                response = await client.get(f"{registry['url']}/catalog")
                response.raise_for_status()
                catalog = response.json()

                # Add registry info
                combined_catalog["registries"].append(
                    {
                        "id": registry["id"],
                        "name": registry["name"],
                        "url": registry["url"],
                        "available": True,
                    }
                )

                # Add packages with registry source
                for mcp in catalog.get("mcps", []):
                    mcp["registry"] = registry["id"]
                    mcp["registry_name"] = registry["name"]
                    combined_catalog["mcps"].append(mcp)

                for team in catalog.get("teams", []):
                    team["registry"] = registry["id"]
                    team["registry_name"] = registry["name"]
                    combined_catalog["teams"].append(team)

                for trigger in catalog.get("triggers", []):
                    trigger["registry"] = registry["id"]
                    trigger["registry_name"] = registry["name"]
                    combined_catalog["triggers"].append(trigger)

        except Exception as e:
            print(
                f"Failed to fetch catalog from {registry.get('name', 'unknown')}: {e}"
            )
            combined_catalog["registries"].append(
                {
                    "id": registry["id"],
                    "name": registry.get("name", "Unknown"),
                    "url": registry["url"],
                    "available": False,
                    "error": str(e),
                }
            )

    return combined_catalog


@app.post("/registries/install/team/{team_id}")
async def install_team_from_registry(team_id: str, registry_id: Optional[str] = None):
    """Install a team from a registry (yum install equivalent)"""
    registries = parse_registries_conf()

    # If no registry specified, try all enabled registries by priority
    if not registry_id:
        registries = [r for r in registries if r.get("enabled", True)]
        registries.sort(key=lambda r: r.get("priority", 99))
    else:
        registries = [
            r for r in registries if r["id"] == registry_id and r.get("enabled", True)
        ]

    if not registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    # Try to fetch team from registries
    for registry in registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                response = await client.get(f"{registry['url']}/teams/{team_id}")
                response.raise_for_status()
                team_data = response.json()

                # Save to local teams directory
                teams_dir = get_teams_dir()
                team_id_normalized = team_id.replace(
                    f"-{team_data.get('version', '')}", ""
                )
                file_path = teams_dir / f"{team_id_normalized}.json"

                save_data = {
                    k: v
                    for k, v in team_data.items()
                    if k not in ["id", "file", "registry", "registry_name"]
                }
                file_path.write_text(json.dumps(save_data, indent=2))

                return {
                    "status": "installed",
                    "team": team_data["name"],
                    "version": team_data.get("version", "unknown"),
                    "registry": registry.get("name", "Unknown"),
                    "file": file_path.name,
                }
        except Exception as e:
            print(f"Failed to install from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404, detail=f"Team '{team_id}' not found in any registry"
    )


# MCP Management API - Docker-based package management
@app.post("/registries/install/mcp/{mcp_id}")
async def install_mcp_from_registry(mcp_id: str, registry_id: Optional[str] = None):
    """
    Install an MCP from a registry (yum install equivalent for MCPs)
    Downloads package definition and deploys Docker container
    """
    registries = parse_registries_conf()

    # If no registry specified, try all enabled registries by priority
    if not registry_id:
        registries = [r for r in registries if r.get("enabled", True)]
        registries.sort(key=lambda r: r.get("priority", 99))
    else:
        registries = [
            r for r in registries if r["id"] == registry_id and r.get("enabled", True)
        ]

    if not registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    # Try to fetch MCP from registries
    for registry in registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                response = await client.get(f"{registry['url']}/mcps/{mcp_id}")
                response.raise_for_status()
                mcp_package = response.json()

                # Install using MCP manager (builds and deploys Docker container)
                result = get_mcp_manager().install(mcp_package)

                if result["status"] in ["installed", "already_installed"]:
                    # Register with orchestrator if newly installed
                    if result["status"] == "installed":
                        await register_installed_mcp(mcp_package)

                    result["registry"] = registry.get("name", "Unknown")
                    return result
                else:
                    raise Exception(result.get("error", "Installation failed"))

        except Exception as e:
            print(f"Failed to install from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404, detail=f"MCP '{mcp_id}' not found in any registry"
    )


async def register_installed_mcp(mcp_package: Dict[str, Any]):
    """Register a newly installed MCP with the orchestrator"""
    name = mcp_package["name"]
    deployment = mcp_package.get("deployment", {})

    # Determine endpoint based on network mode
    if deployment.get("network_mode") == "host":
        # Host mode: use host.docker.internal
        # Find port env var (e.g., KALI_PORT, NMAP_PORT)
        env_vars = mcp_package.get("deployment", {}).get("environment", {})
        port_var = next((k for k in env_vars.keys() if k.endswith("_PORT")), None)
        
        if port_var:
            port = env_vars[port_var]
            # Extract default value from ${VAR:-default} format
            port = port.replace(f"${{{port_var}:-", "").replace("}", "")
        else:
            port = str(config.get_nmap_port())  # Fallback
        
        endpoint = config.get_docker_host_url_pattern().format(port=port)
    else:
        # Bridge mode: use container name
        container_name = deployment.get("container_name", f"mcp-{name}")
        port_config = deployment.get("ports", [{}])[0]
        port = port_config.get("container", str(config.get_agent_port()))
        port = (
            port.replace("${", "").split(":-")[1].replace("}", "")
            if "${" in str(port)
            else port
        )
        endpoint = config.get_docker_container_url_pattern().format(
            container_name=container_name, port=port
        )

    # Register with orchestrator
    registry.register(
        MCPServerInfo(
            name=name,
            endpoint=endpoint,
            description=mcp_package.get("description", ""),
            version=mcp_package.get("version", "1.0.0"),
        )
    )


# MCP Lifecycle Management (Most endpoints moved to app/api/mcps.py)

@app.post("/mcps/{mcp_name}/update")
async def update_mcp(mcp_name: str, registry_id: Optional[str] = None):
    """
    Update an MCP to the latest version from registry
    """
    registries = parse_registries_conf()

    # If no registry specified, try all enabled registries by priority
    if not registry_id:
        registries = [r for r in registries if r.get("enabled", True)]
        registries.sort(key=lambda r: r.get("priority", 99))
    else:
        registries = [
            r for r in registries if r["id"] == registry_id and r.get("enabled", True)
        ]

    if not registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    # Get current version
    status = get_mcp_manager().get_status(mcp_name)
    if status.get("status") == "not_installed":
        raise HTTPException(
            status_code=404, detail=f"MCP '{mcp_name}' is not installed"
        )

    # Try to fetch latest version from registries
    for registry in registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                # List all MCPs and find latest version
                response = await client.get(f"{registry['url']}/mcps")
                response.raise_for_status()
                mcps = response.json()

                # Find MCP by name
                mcp_id = None
                for mcp in mcps:
                    if mcp.get("name") == mcp_name or mcp.get("id", "").startswith(
                        f"{mcp_name}-"
                    ):
                        mcp_id = mcp.get("id")
                        break

                if not mcp_id:
                    continue

                # Get full package
                response = await client.get(f"{registry['url']}/mcps/{mcp_id}")
                response.raise_for_status()
                mcp_package = response.json()

                # Update using MCP manager
                result = get_mcp_manager().update(mcp_name, mcp_package)

                if result["status"] == "updated":
                    # Re-register with orchestrator
                    await register_installed_mcp(mcp_package)
                    result["registry"] = registry.get("name", "Unknown")

                return result

        except Exception as e:
            print(f"Failed to update from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404, detail=f"No updates found for MCP '{mcp_name}'"
    )


# ============================================================================
# Trigger Management API
# ============================================================================


@app.post("/registries/install/trigger/{trigger_id}")
async def install_trigger_from_registry(trigger_id: str, user_config: Dict[str, Any]):
    """
    Install trigger from registry with user-specified target

    Args:
        trigger_id: Trigger package ID (format: {name}-{version})
        user_config: User configuration {"workflow_id": "..." OR "team_id": "..."}

    Returns:
        Installation result
    """
    registries = parse_registries_conf()

    # Try each enabled registry by priority
    enabled_registries = [r for r in registries if r.get("enabled", True)]
    enabled_registries.sort(key=lambda r: r.get("priority", 99))

    if not enabled_registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    for registry in enabled_registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                # Try to get trigger package
                # Support both versioned paths (registry/triggers/{name}/{version}/)
                # and flat paths (triggers/{id})
                response = await client.get(f"{registry['url']}/triggers/{trigger_id}")
                response.raise_for_status()
                trigger_package = response.json()

                # Install using Trigger Manager
                result = get_trigger_manager().install(trigger_package, user_config)

                if result["status"] in ["installed", "already_installed"]:
                    result["registry"] = registry.get("name", "Unknown")
                    return result
                elif result["status"] == "error":
                    raise HTTPException(
                        status_code=500,
                        detail=result.get("error", "Installation failed"),
                    )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            print(f"Failed to install from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404,
        detail=f"Trigger '{trigger_id}' not found in any enabled registry",
    )


@app.delete("/triggers/{trigger_name}")
async def uninstall_trigger(trigger_name: str):
    """Uninstall a trigger"""
    result = get_trigger_manager().uninstall(trigger_name)

    if result["status"] == "not_installed":
        raise HTTPException(
            status_code=404, detail=f"Trigger '{trigger_name}' is not installed"
        )

    return result


@app.post("/triggers/{trigger_name}/start")
async def start_trigger(trigger_name: str):
    """Start a stopped trigger"""
    return get_trigger_manager().start(trigger_name)


@app.post("/triggers/{trigger_name}/stop")
async def stop_trigger(trigger_name: str):
    """Stop a running trigger"""
    return get_trigger_manager().stop(trigger_name)


@app.post("/triggers/{trigger_name}/restart")
async def restart_trigger(trigger_name: str):
    """Restart a trigger"""
    return get_trigger_manager().restart(trigger_name)


@app.get("/triggers")
async def list_triggers():
    """List all installed triggers (alias for /triggers/installed)"""
    return get_trigger_manager().list_installed()


@app.get("/triggers/installed")
async def list_installed_triggers():
    """List all installed triggers with their status"""
    return get_trigger_manager().list_installed()


@app.get("/triggers/{trigger_name}/status")
async def get_trigger_status(trigger_name: str):
    """Get detailed status of an installed trigger"""
    return get_trigger_manager().get_status(trigger_name)


@app.post("/triggers/{trigger_name}/update")
async def update_trigger(trigger_name: str, registry_id: Optional[str] = None):
    """
    Update a trigger to the latest version from registry
    """
    registries = parse_registries_conf()

    # If no registry specified, try all enabled registries by priority
    if not registry_id:
        registries = [r for r in registries if r.get("enabled", True)]
        registries.sort(key=lambda r: r.get("priority", 99))
    else:
        registries = [
            r for r in registries if r["id"] == registry_id and r.get("enabled", True)
        ]

    if not registries:
        raise HTTPException(status_code=404, detail="No enabled registries found")

    # Get current version
    status = get_trigger_manager().get_status(trigger_name)
    if status.get("status") == "not_installed":
        raise HTTPException(
            status_code=404, detail=f"Trigger '{trigger_name}' is not installed"
        )

    # Try to fetch latest version from registries
    for registry in registries:
        try:
            async with httpx.AsyncClient(
                timeout=config.get_http_timeout_default()
            ) as client:
                # List all triggers and find latest version
                response = await client.get(f"{registry['url']}/triggers")
                response.raise_for_status()
                triggers = response.json()

                # Find trigger by name
                trigger_id = None
                for trigger in triggers:
                    if trigger.get("name") == trigger_name or trigger.get(
                        "id", ""
                    ).startswith(f"{trigger_name}-"):
                        trigger_id = trigger.get("id")
                        break

                if not trigger_id:
                    continue

                # Get full package
                response = await client.get(f"{registry['url']}/triggers/{trigger_id}")
                response.raise_for_status()
                trigger_package = response.json()

                # Update using Trigger manager
                result = get_trigger_manager().update(trigger_name, trigger_package)

                if result["status"] == "updated":
                    result["registry"] = registry.get("name", "Unknown")

                return result

        except Exception as e:
            print(f"Failed to update from {registry.get('name', 'unknown')}: {e}")
            continue

    raise HTTPException(
        status_code=404, detail=f"No updates found for trigger '{trigger_name}'"
    )


# ============================================================================
# Autonomous Agents API - File-based storage like teams
# ============================================================================
def get_agents_dir():
    """Get the agent-definitions directory path"""
    agents_dir = Path(config.get_agent_definitions_path())
    agents_dir.mkdir(exist_ok=True)
    return agents_dir


def load_agent_from_file(file_path: Path) -> dict:
    """Load an agent from a JSON file"""
    agent_data = json.loads(file_path.read_text())
    # Use filename (without .json) as ID if not present
    if "id" not in agent_data:
        agent_data["id"] = file_path.stem
    agent_data["file"] = file_path.name
    return agent_data


def save_agent_to_file(agent_id: str, agent_data: dict):
    """Save an agent to a JSON file"""
    agents_dir = get_agents_dir()
    file_path = agents_dir / f"{agent_id}.json"

    # Remove file metadata from saved data
    save_data = {k: v for k, v in agent_data.items() if k not in ["file"]}

    file_path.write_text(json.dumps(save_data, indent=2))
    return file_path


# Agent Execution API (All endpoints moved to app/api/agents.py)

# Multi-Agent Team Execution API (All endpoints moved to app/api/teams.py)

# Execution History API (All endpoints moved to app/api/executions.py)


# ============================================================================
# User Settings API (ADCL: Configuration is Code)
# ============================================================================

import tomllib  # Python 3.11+ built-in for reading TOML
import tomli_w  # For writing TOML
import fcntl  # For file locking

# Allowed settings with type validation
ALLOWED_SETTINGS = {
    "theme": str,
    "log_level": str,
    "mcp_timeout": str,
    "auto_save": bool
}

class UserSettingsUpdate(BaseModel):
    key: str
    value: Any

    @field_validator('key')
    @classmethod
    def validate_key(cls, v):
        if v not in ALLOWED_SETTINGS:
            raise ValueError(f"Invalid setting key. Allowed: {list(ALLOWED_SETTINGS.keys())}")
        return v


def get_settings_path() -> Path:
    """Get validated settings file path"""
    # Use container-friendly path, fallback to home
    config_dir = Path(os.getenv("ADCL_CONFIG_DIR", str(Path.home() / ".config" / "adcl")))
    config_path = config_dir / "user.conf"

    # Validate path is within expected directory
    try:
        config_path.resolve().relative_to(config_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid config path")

    return config_path


@app.get("/api/settings")
async def get_user_settings():
    """Get user settings from user.conf"""
    config_path = get_settings_path()

    # Default settings
    defaults = {
        "theme": "system",
        "log_level": "info",
        "mcp_timeout": "60",
        "auto_save": True
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path, 'rb') as f:
            settings = tomllib.load(f)
        return {**defaults, **settings}
    except Exception as e:
        print(f"Failed to load settings: {e}")
        return defaults


@app.post("/api/settings")
async def update_user_setting(update: UserSettingsUpdate):
    """Update a single user setting with file locking"""
    config_path = get_settings_path()

    # Validate value type
    expected_type = ALLOWED_SETTINGS[update.key]
    if not isinstance(update.value, expected_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type for {update.key}. Expected {expected_type.__name__}"
        )

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Use file locking to prevent corruption from concurrent writes
        lock_path = config_path.with_suffix('.lock')
        with open(lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            try:
                # Load existing settings
                if config_path.exists():
                    with open(config_path, 'rb') as f:
                        settings = tomllib.load(f)
                else:
                    settings = {}

                # Update the setting
                settings[update.key] = update.value

                # Atomic write: write to temp file, then rename
                temp_path = config_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as f:
                    tomli_w.dump(settings, f)

                temp_path.replace(config_path)

                return {"status": "ok", "key": update.key, "value": update.value}
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=config.get_service_host(), port=config.get_orchestrator_port()
    )
