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
import docker
from datetime import datetime
from uuid import uuid4
from app.docker_manager import DockerManager
from app.agent_runtime import AgentRuntime
from app.team_runtime import TeamRuntime
from app.core.config import get_config
from app.core.errors import sanitize_error_for_user
from app.services.feature_service import init_feature_service, get_feature_service
from app.services.config_version_service import init_config_version_service
from anthropic import Anthropic
from openai import OpenAI

# Import data models
from app.models import (
    MCPServerInfo,
    WorkflowNode,
    WorkflowEdge,
    WorkflowDefinition,
    ExecutionRequest,
    ExecutionLog,
    NodeState,
    ExecutionResult,
    TeamAgent,
    Coordination,
    Team,
    TeamUpdate,
    ChatMessage,
    Model,
    ModelUpdate,
    ModelConfigSchema,
    ModelsConfigFile,
    UserSettingsUpdate,
)
from app.models.settings import ALLOWED_SETTINGS

# Import API routers (PRD-99 refactoring)
from app.api import agents, workflows, teams, models, mcps, executions, recon, system, license
from app.api import dashboard, scanner, vulnerabilities  # Red Team Dashboard
from app.api import vulhub  # Vulhub container management
from app.api import attack_playground  # Attack Playground state management
from app.api import registry as registry_api  # YUM-style package management
from app.api import triggers  # Trigger management (Phase 4 refactoring)
from app.api.v2 import workflows as workflows_v2
from app.api import migration  # Migration API endpoints
from app.api import edition_capabilities  # Edition capability awareness for agents
from app.api import settings  # User settings (Phase 3.4 refactoring)


def serialize_anthropic_objects(obj: Any) -> Any:
    """
    Recursively serialize Anthropic SDK objects (TextBlock, etc.) to JSON-safe dicts.

    The Anthropic SDK returns TextBlock objects which are not JSON serializable.
    This function converts them to plain dicts/strings for WebSocket transmission.
    """
    # Handle None
    if obj is None:
        return None

    # Handle Anthropic TextBlock and similar objects
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
        return {"type": "text", "text": getattr(obj, 'text', str(obj))}

    # Handle objects with model_dump (Pydantic models)
    if hasattr(obj, 'model_dump'):
        try:
            return serialize_anthropic_objects(obj.model_dump(mode='json'))
        except Exception:
            pass

    # Handle dicts recursively
    if isinstance(obj, dict):
        return {k: serialize_anthropic_objects(v) for k, v in obj.items()}

    # Handle lists recursively
    if isinstance(obj, list):
        return [serialize_anthropic_objects(item) for item in obj]

    # Handle tuples as lists
    if isinstance(obj, tuple):
        return [serialize_anthropic_objects(item) for item in obj]

    # Return primitives as-is
    return obj


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
# Models moved to app/models/ (Phase 1.1 refactoring)


# MCP Server Registry (class moved to app/services/mcp_registry.py - Phase 1.2 refactoring)
from app.services.mcp_registry import MCPRegistry

# Global registry
registry = MCPRegistry()


# WebSocket Connection Manager (class moved to app/services/connection_manager.py - Phase 2.1 refactoring)
from app.services.connection_manager import ConnectionManager

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
ollama_api_key = os.getenv("OLLAMA_API_KEY")  # Optional for remote Ollama
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Ollama dummy key - local instances don't require authentication
OLLAMA_DUMMY_API_KEY = "ollama-local-no-auth-required"

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

# Ollama client (optional, uses OpenAI-compatible API)
# For local Ollama, no API key needed. For remote, use OLLAMA_API_KEY env var
try:
    import httpx
    ollama_client = OpenAI(
        base_url=f"{ollama_base_url}/v1",
        api_key=ollama_api_key or OLLAMA_DUMMY_API_KEY,
        timeout=httpx.Timeout(5.0, connect=2.0)  # Fast timeout for health check
    )

    # Health check: verify Ollama is actually running (with timeout)
    try:
        ollama_client.models.list()
        print(f"✓ Ollama client initialized and verified (base_url: {ollama_base_url})")
    except Exception as health_error:
        print(f"⚠️  Warning: Ollama client created but health check failed: {health_error}")
        print(f"   Ollama may not be running at {ollama_base_url}")
        print(f"   Models will fail at runtime if Ollama is not available")
        # Keep client - will fail at runtime with clear error

except Exception as e:
    ollama_client = None
    import traceback
    traceback.print_exc()
    print(f"⚠️  Warning: Could not initialize Ollama client: {e}")

# Initialize agent runtime for autonomous agents with all clients
agent_runtime = AgentRuntime(registry, anthropic_client, openai_client, ollama_client, config=config)

# Initialize team runtime for multi-agent teams
team_runtime = TeamRuntime(
    agent_runtime=agent_runtime,
    agents_dir=Path(config.get_agent_definitions_path()),
    teams_dir=Path(config.get_agent_teams_path()),
)

# Initialize WebSocket chat router with dependencies (Phase 2.2 refactoring)
from app.api.ws.chat import create_chat_websocket_router
ws_chat_router = create_chat_websocket_router(manager, agent_runtime)

# Initialize Workflow V2 Service
from app.services.workflow_v2_service import WorkflowV2Service
from app.services.agent_service import AgentService
from app.services.recon_service import ReconService
from app.services.attack_service import AttackService
from app.services.workflow_result_processor import WorkflowResultProcessor
from app.workflow_v2.executor import WorkflowExecutor
from app.api.v2.workflows import set_workflow_v2_service

# Initialize ReconService and AttackService
recon_service = ReconService(base_dir=str(Path(config.volumes_path) / "recon"))
attack_service = AttackService(base_dir=str(Path(config.volumes_path) / "recon"))

# Create WorkflowResultProcessor to integrate workflows with recon/attack services
workflow_result_processor = WorkflowResultProcessor(
    recon_service=recon_service,
    attack_service=attack_service
)

agent_service = AgentService(agents_dir=Path(config.get_agent_definitions_path()))
workflow_v2_executor = WorkflowExecutor(
    agent_runtime=agent_runtime,
    agent_service=agent_service,
    history_mcp_url=config.history_mcp_url
)
workflow_v2_service = WorkflowV2Service(
    workflows_dir=Path("workflows/v2"),
    executor=workflow_v2_executor,
    result_processor=workflow_result_processor
)

# Initialize workflow V2 service for dependency injection
set_workflow_v2_service(workflow_v2_service)


# Initialize FeatureService early (before router mounting)
# This must happen before routers are included since decorators will call get_feature_service()
feature_service = init_feature_service("/configs/auto-install.json")
print(f"✅ FeatureService initialized: {feature_service}")

# Initialize LicenseService early (before router mounting)
# License validation decorators will call get_license_service()
from app.services.license_service import init_license_service
license_service = init_license_service("/configs/license.json")
print(f"✅ LicenseService initialized: {license_service}")

config_version_service = init_config_version_service("/configs")
print(f"✅ ConfigVersionService initialized: {config_version_service}")

# Mount API routers (PRD-99 refactoring)
# Note: All routers either have prefixes defined or include full paths in their routes,
# so we don't add prefixes here to avoid double-prefixing (e.g., /agents/agents).

# Core platform routers (always enabled)
app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(workflows_v2.router)  # V2 workflows at /v2/workflows/*
app.include_router(teams.router)
app.include_router(models.router)
app.include_router(mcps.router)  # Routes already include /mcp and /mcps paths
app.include_router(executions.router)
app.include_router(system.router)  # System health, version, security policy
app.include_router(license.router)  # License management at /api/license/*
app.include_router(migration.router)  # Migration at /api/migration/*
app.include_router(edition_capabilities.router)  # Edition capability awareness at /api/edition/*
app.include_router(registry_api.router)  # Registry at /api/v1/registry/*
app.include_router(triggers.router)  # Trigger management at /triggers (Phase 4 refactoring)
app.include_router(ws_chat_router)  # WebSocket chat endpoints (Phase 2.2 refactoring)
app.include_router(settings.router)  # User settings at /api/settings (Phase 3.4 refactoring)

# Red Team feature routers (conditionally enabled based on edition)
if feature_service.is_enabled("red_team"):
    print("✅ Red Team features enabled - mounting red team routers")
    app.include_router(recon.router)  # Recon/Attack playground at /api/recon/*
    app.include_router(attack_playground.router)  # Attack playground sessions at /api/playground/*
    app.include_router(dashboard.router)  # Dashboard KPIs at /api/dashboard/*
    app.include_router(scanner.router)  # Scanner at /api/scans/*
    app.include_router(vulnerabilities.router)  # Vulnerabilities at /api/vulnerabilities/*
    app.include_router(vulhub.router)  # Vulhub at /api/vulhub/*
else:
    print("⚠️  Red Team features disabled - routers not mounted")


# API Routes
@app.on_event("startup")
async def startup():
    """Startup tasks - Extracted to app/startup.py (Phase 5 refactoring)"""
    from app.startup import run_startup
    await run_startup(
        app=app,
        config=config,
        engine=engine,
        agent_runtime=agent_runtime,
        team_runtime=team_runtime,
        registry=registry,
        get_mcp_manager=get_mcp_manager,
        get_trigger_manager=get_trigger_manager,
        parse_registries_conf=parse_registries_conf,
    )


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
# Team models moved to app/models/team.py (Phase 1.1 refactoring)


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
# ChatMessage model moved to app/models/chat.py (Phase 1.1 refactoring)


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

    # Handle model-only selection (no team or agent specified)
    if msg.model_id and not team and not msg.agent_id:
        print(f"🎯 HTTP Model-only mode: Direct chat with model {msg.model_id}")
        try:
            # Get provider and client for the model
            from app.agent_runtime import AgentRuntime
            temp_runtime = AgentRuntime(
                mcp_registry=registry,
                anthropic_client=anthropic_client,
                openai_client=openai_client,
                ollama_client=ollama_client
            )
            provider, client = temp_runtime._get_client_for_model(msg.model_id)

            # Build messages from history
            messages = []
            for item in msg.history:
                messages.append({"role": item["role"], "content": item["content"]})
            messages.append({"role": "user", "content": msg.message})

            # Load full model config to get actual model_id and max_tokens
            import yaml
            from pathlib import Path
            models_file = Path("/configs/models.yaml")
            with open(models_file) as f:
                models_data = yaml.safe_load(f)

            # Find model config by ID
            model_config = next((m for m in models_data["models"] if m["id"] == msg.model_id), None)
            if not model_config:
                raise ValueError(f"Model {msg.model_id} not found in config")

            max_tokens = model_config.get("max_tokens", 2048)
            actual_model_id = model_config.get("model_id", msg.model_id)

            print(f"📤 Calling {provider} with model: {actual_model_id}, max_tokens: {max_tokens}")

            # Call model API directly
            if provider == "anthropic":
                response = client.messages.create(
                    model=actual_model_id,
                    max_tokens=max_tokens,
                    messages=messages
                )
                response_text = response.content[0].text
            elif provider in ["openai", "ollama"]:
                response = client.chat.completions.create(
                    model=actual_model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Return formatted response
            return {
                "response": response_text,
                "agent": f"Direct chat with {msg.model_id}",
                "model_used": msg.model_id,
                "provider": provider,
            }

        except Exception as e:
            import traceback
            print(f"Model-only chat error (HTTP): {traceback.format_exc()}")
            return {
                "response": f"❌ Chat failed: {str(e)}",
                "agent": f"Model {msg.model_id}",
            }

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
        agent_id = data.get("agent_id")
        model_id = data.get("model_id")
        message = data.get("message")

        print(f"\n💬 WebSocket chat for session {session_id}")
        print(f"   team: {team_id}, agent: {agent_id}, model: {model_id}")

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

        # Handle model-only selection (no team or agent specified)
        if model_id and not team and not agent_id:
            print(f"🎯 Model-only mode: Creating simple chat agent with model {model_id}")
            try:
                # Initialize SessionContextService for conversation memory
                from app.services.session_context_service import SessionContextService
                context_service = SessionContextService(
                    conversations_dir=Path(config.volumes_path) / "conversations",
                    max_context_items=5,
                    max_context_tokens=4000
                )

                # Load previous conversation context
                session_context = await context_service.get_context(session_id)
                context_text = context_service.format_context_for_agent(session_context)

                # Build context with model override
                context = {"model_override": model_id}
                if context_text:
                    context["conversation_history"] = context_text
                    print(f"📚 Loaded {session_context.get('total_items', 0)} previous execution(s)")

                # Create a minimal agent definition for direct chat
                from app.agent_runtime import AgentRuntime
                agent_runtime = AgentRuntime(
                    mcp_registry=registry,
                    anthropic_client=anthropic_client,
                    openai_client=openai_client,
                    ollama_client=ollama_client
                )

                # Minimal agent definition - just the model
                simple_agent = {
                    "id": f"simple-chat-{model_id}",
                    "name": f"Chat with {model_id}",
                    "role": "assistant",
                    "available_mcps": [],  # No tools, just chat
                    "model_config": {
                        "model": model_id,  # This will be overridden anyway
                        "max_tokens": 8192,
                        "temperature": 0.7
                    }
                }

                await send_update({
                    "type": "status",
                    "status": "starting",
                    "message": f"💬 Starting chat with {model_id}...",
                })

                # Run agent directly
                result = await agent_runtime.run_agent(
                    agent_definition=simple_agent,
                    task=message,
                    context=context,
                    progress_callback=send_update,
                    session_id=session_id,
                    manager=manager,
                )

                # Save to context
                try:
                    await context_service.update_context(
                        session_id=session_id,
                        execution_result=result,
                        user_message=message
                    )
                except Exception as ctx_error:
                    print(f"⚠️  Failed to save context: {ctx_error}")

                # Send result
                if result.get("status") == "cancelled":
                    await send_update({"type": "cancelled", "message": "Execution cancelled"})
                elif result.get("status") == "error":
                    await send_update({"type": "error", "error": result.get("error", "Unknown error")})
                else:
                    await send_update({"type": "complete", "result": result})

            except Exception as e:
                import traceback
                print(f"Model-only chat error: {traceback.format_exc()}")
                await send_update({"type": "error", "error": sanitize_error_for_user(e, include_type=False)})

            return  # Exit after handling model-only mode

        # Check if team uses new schema (has available_mcps)
        if team and "available_mcps" in team:
            # New team format: use team runtime with streaming
            try:
                # Initialize SessionContextService for conversation memory
                from app.services.session_context_service import SessionContextService
                context_service = SessionContextService(
                    conversations_dir=Path(config.volumes_path) / "conversations",
                    max_context_items=5,
                    max_context_tokens=4000
                )

                # Load previous conversation context from disk
                session_context = await context_service.get_context(session_id)

                # Format context for agent consumption
                context_text = context_service.format_context_for_agent(session_context)

                # Build context dict for team runtime
                context = {}
                if context_text:
                    context["conversation_history"] = context_text
                    print(f"📚 Loaded {session_context.get('total_items', 0)} previous execution(s) from session context")
                else:
                    print(f"📭 No previous context for session {session_id}")

                # Send initial status
                await send_update(
                    {
                        "type": "status",
                        "status": "starting",
                        "message": f"🚀 Starting {team['name']}...",
                    }
                )

                # Pass model_id override if specified
                if model_id:
                    context["model_override"] = model_id
                    print(f"🔧 Using model override: {model_id}")

                result = await team_runtime.run_team(
                    team_definition=team,
                    task=message,
                    context=context,  # Now includes conversation history and model override!
                    progress_callback=send_update,
                    session_id=session_id,
                    manager=manager,
                )

                # Save execution result to session context for future turns
                # This happens regardless of success/failure so agent has full history
                try:
                    await context_service.update_context(
                        session_id=session_id,
                        execution_result=result,
                        user_message=message
                    )
                    print(f"💾 Saved execution to session context")
                except Exception as ctx_error:
                    # Don't fail the whole execution if context save fails
                    print(f"⚠️  Failed to save context: {ctx_error}")

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


# WebSocket Recon/Attack API for real-time updates
@app.websocket("/ws/recon/{session_id}")
async def websocket_recon(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time recon/attack progress streaming.
    Follows ADCL pattern: Backend pushes events, UI renders.
    """
    from app.services.recon_service import ReconService
    from app.services.attack_service import AttackService

    await manager.connect(session_id, websocket)

    try:
        # Wait for command
        data = await websocket.receive_json()
        command_type = data.get("type")

        # Create callback to send updates
        async def send_update(update: dict):
            await manager.send_update(session_id, update)

        if command_type == "start_scan":
            # Start reconnaissance scan
            recon_service = ReconService()
            target = data.get("target")
            scan_type = data.get("scan_type", "network_discovery")
            options = data.get("options", {})

            await send_update({
                "type": "status",
                "message": f"Creating scan for {target}..."
            })

            # Create scan
            scan_id = await recon_service.create_scan(
                target=target,
                scan_type=scan_type,
                options=options
            )

            await send_update({
                "type": "scan_created",
                "scan_id": scan_id,
                "target": target
            })

            # TODO: Start actual scan using agent_runtime
            # For now, just mark as pending
            await send_update({
                "type": "scan_complete",
                "scan_id": scan_id,
                "message": "Scan infrastructure ready. Use AI agents to execute reconnaissance."
            })

        elif command_type == "start_attack":
            # Start attack operation
            attack_service = AttackService()
            scan_id = data.get("scan_id")
            target_host = data.get("target_host")
            attack_type = data.get("attack_type")
            options = data.get("options", {})

            await send_update({
                "type": "status",
                "message": f"Creating attack against {target_host}..."
            })

            # Create attack
            attack_id = await attack_service.create_attack(
                scan_id=scan_id,
                target_host=target_host,
                attack_type=attack_type,
                options=options
            )

            await send_update({
                "type": "attack_created",
                "attack_id": attack_id,
                "scan_id": scan_id,
                "target_host": target_host
            })

            # TODO: Start actual attack using agent_runtime
            # For now, just mark as pending
            await send_update({
                "type": "attack_complete",
                "attack_id": attack_id,
                "message": "Attack infrastructure ready. Use AI agents to execute attack."
            })

        else:
            await send_update({
                "type": "error",
                "error": f"Unknown command type: {command_type}"
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_update(session_id, {"type": "error", "error": str(e)})
        manager.disconnect(session_id)


@app.websocket("/ws/workflow/{session_id}")
async def websocket_workflow_execution(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time workflow execution progress.
    Streams node start/complete events as workflow executes.
    """
    await manager.connect(session_id, websocket)

    try:
        # Wait for workflow execution request
        data = await websocket.receive_json()
        workflow_id = data.get("workflow_id")
        initial_message = data.get("initial_message", "")
        params = data.get("params", {})
        attack_playground_session_id = data.get("attack_playground_session_id")

        if not workflow_id:
            await manager.send_update(session_id, {
                "type": "error",
                "error": "workflow_id is required"
            })
            return

        # Create callback to send progress updates (serialize to avoid TextBlock errors)
        async def send_progress(event_type: str, event_data: Dict[str, Any]):
            # Serialize Anthropic objects (TextBlock, etc.) before sending
            serialized_data = serialize_anthropic_objects(event_data)
            await manager.send_update(session_id, {
                "type": event_type,
                **serialized_data
            })

        # Send initial status
        await send_progress("workflow_accepted", {
            "workflow_id": workflow_id,
            "message": "Workflow execution starting..."
        })

        # Get security context for the current user
        # For attack playground, create a permissive context
        from app.core.security import SecurityContext, UserRole, DangerLevel
        try:
            from app.core.dependencies import get_current_user_context
            security_context = get_current_user_context()
        except Exception:
            # WebSocket context - create appropriate security context for attack playground
            # Use PRO role to allow scanning and testing tools
            security_context = SecurityContext(
                user_id="attack_playground",
                role=UserRole.PRO,
                license_type="pro",
                edition="pro",
                features={"core_platform", "red_team", "vulnerability_scanning"},
                max_danger_level=DangerLevel.CRITICAL,
                allowed_tools=set(),
                denied_tools=set()
            )

        # Execute workflow - pass callback directly (thread-safe, no race condition)
        result = await workflow_v2_service.run_workflow(
            workflow_id=workflow_id,
            initial_message=initial_message,
            params=params,
            progress_callback=send_progress,
            session_id=attack_playground_session_id,  # Pass session_id for automatic state updates
            security_context=security_context
        )

        # Send completion (serialize result properly to avoid TextBlock errors)
        # Use serialize_anthropic_objects to handle nested TextBlock objects
        result_dict = result.model_dump(mode='json')
        final_result_serialized = serialize_anthropic_objects(result_dict.get("final_result"))

        # Load attack session state if session_id provided (eliminates race condition)
        session_state = None
        if attack_playground_session_id:
            try:
                from pathlib import Path
                import json
                session_file = Path("/app/volumes/data/attack_sessions") / f"{attack_playground_session_id}.json"
                if session_file.exists():
                    with open(session_file) as f:
                        session_state = json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load session state: {e}")

        await manager.send_update(session_id, {
            "type": "workflow_complete",
            "execution_id": result.execution_id,
            "status": result.status,
            "final_result": final_result_serialized,
            "scan_id": result.scan_id,  # Tell UI which scan was created
            "cumulative_tokens": result.cumulative_tokens,  # Include token usage and cost
            "session_state": session_state  # Include session state in response (no race condition)
        })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        error_msg = sanitize_error_for_user(str(e))
        await manager.send_update(session_id, {
            "type": "workflow_error",
            "error": error_msg
        })
        manager.disconnect(session_id)


# ============================================================================
# Red Team Dashboard WebSocket Endpoints
# ============================================================================
# WebSocket chat handlers deduplicated and moved to app/api/ws/chat.py (Phase 2.2 refactoring)
# Previously: 3 identical copy-paste handlers for scanner, vulnerabilities, attack-console (122 lines)
# Now: Single parametrized handler at /ws/chat/{context_type}/{session_id}
# Mount via: app.include_router(ws_chat_router)


# Models API - Following ADCL principle: Configuration is Code
# Model config logic moved to app/services/model_config_service.py (Phase 3.2 refactoring)
from app.services.model_config_service import (
    models_db,
    models_lock,
    MODELS_CONFIG_PATH,
    load_models_from_config,
    save_models_to_config,
)


# Model configuration models moved to app/models/model.py (Phase 1.1 refactoring)


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
            # Handle file:// registries by scanning local directory
            if registry['url'].startswith('file://'):
                from pathlib import Path
                import json

                local_path = registry['url'].replace('file://', '')
                if local_path.startswith('./') or local_path.startswith('../'):
                    # Relative paths are resolved from application base directory
                    base_dir = os.getenv('APP_BASE_DIR', '/app')
                    directory = (Path(base_dir) / local_path).resolve()
                else:
                    directory = Path(local_path)

                combined_catalog["registries"].append({
                    "id": registry["id"],
                    "name": registry["name"],
                    "url": registry["url"],
                    "available": True,
                    "type": "local"
                })

                # Scan directory for mcp.json files
                if directory.exists() and directory.is_dir():
                    for item in directory.iterdir():
                        if not item.is_dir():
                            continue
                        mcp_json = item / "mcp.json"
                        if mcp_json.exists():
                            try:
                                with open(mcp_json) as f:
                                    mcp_data = json.load(f)
                                mcp_data["registry"] = registry["id"]
                                mcp_data["registry_name"] = registry["name"]
                                mcp_data["id"] = mcp_data.get("name")  # Use name as ID for local packages
                                combined_catalog["mcps"].append(mcp_data)
                            except Exception as e:
                                print(f"Failed to load {mcp_json}: {e}")
                continue

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

    # Also scan local agent-teams and triggers directories
    from pathlib import Path
    import json

    # Scan agent-teams directory
    teams_dir = Path("/app/agent-teams")
    if teams_dir.exists() and teams_dir.is_dir():
        for team_file in teams_dir.glob("*.json"):
            try:
                with open(team_file) as f:
                    team_data = json.load(f)

                # Return simplified structure for catalog listing to avoid React rendering errors
                # Frontend can fetch full details separately if needed
                team_summary = {
                    "id": team_file.stem,
                    "name": team_data.get("name", team_file.stem),
                    "description": team_data.get("description", ""),
                    "version": team_data.get("version", "1.0.0"),
                    "tags": team_data.get("tags", []),
                    "author": team_data.get("author", ""),
                    "agent_count": len(team_data.get("agents", [])),
                    "coordination_mode": team_data.get("coordination", {}).get("mode", "sequential"),
                    "registry": "local",
                    "registry_name": "Local Teams"
                }
                combined_catalog["teams"].append(team_summary)
            except Exception as e:
                print(f"Failed to load team {team_file}: {e}")

    # Scan triggers directory
    triggers_dir = Path("/app/triggers")
    if triggers_dir.exists() and triggers_dir.is_dir():
        for trigger_type_dir in triggers_dir.iterdir():
            if not trigger_type_dir.is_dir():
                continue
            for trigger_file in trigger_type_dir.glob("*.json"):
                try:
                    with open(trigger_file) as f:
                        trigger_data = json.load(f)
                    trigger_data["id"] = trigger_file.stem
                    trigger_data["type"] = trigger_type_dir.name
                    trigger_data["registry"] = "local"
                    trigger_data["registry_name"] = "Local Triggers"
                    combined_catalog["triggers"].append(trigger_data)
                except Exception as e:
                    print(f"Failed to load trigger {trigger_file}: {e}")

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
            # Handle file:// registries (local directory)
            if registry['url'].startswith('file://'):
                from pathlib import Path
                import json

                local_path = registry['url'].replace('file://', '')
                if local_path.startswith('./') or local_path.startswith('../'):
                    # Relative paths are resolved from application base directory
                    base_dir = os.getenv('APP_BASE_DIR', '/app')
                    directory = (Path(base_dir) / local_path).resolve()
                else:
                    directory = Path(local_path)

                # Scan all subdirectories to find mcp.json with matching name
                # (directory name might not match package name)
                mcp_package = None
                if directory.exists() and directory.is_dir():
                    for item in directory.iterdir():
                        if not item.is_dir():
                            continue
                        mcp_json_path = item / "mcp.json"
                        if mcp_json_path.exists():
                            try:
                                with open(mcp_json_path) as f:
                                    pkg = json.load(f)
                                # Match by package name from mcp.json, not directory name
                                if pkg.get("name") == mcp_id:
                                    mcp_package = pkg
                                    break
                            except Exception as e:
                                print(f"Failed to read {mcp_json_path}: {e}")
                                continue

                if not mcp_package:
                    print(f"MCP {mcp_id} not found in local registry {registry['name']}")
                    continue

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

            # Handle HTTP/HTTPS registries
            else:
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
# Trigger Management API - Moved to app/api/triggers.py (Phase 4 refactoring)
# ============================================================================


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

# User Settings API
# Moved to app/api/settings.py (Phase 3.4 refactoring)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=config.get_service_host(), port=config.get_orchestrator_port()
    )
