# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
ADCL Configuration - Single source of truth.
YAML is king. Env vars ONLY for secrets.

Follows ADCL Core Principle:
- ALL configuration in plain text (JSON/YAML/TOML)
- NO hidden state - everything inspectable via `cat`, `grep`, `jq`
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


# =============================================================================
# CONFIGURATION DATACLASS
# =============================================================================

@dataclass(frozen=True)
class Config:
    """
    Immutable application configuration.
    All values from YAML. No hidden state.
    """

    # -- Ports --
    orchestrator_port: int = 8000
    frontend_port: int = 3000
    registry_port: int = 9000
    agent_port: int = 7000
    file_tools_port: int = 7002
    nmap_port: int = 7003
    history_port: int = 7004

    # -- Paths --
    agent_definitions_path: str = "/app/agent-definitions"
    agent_teams_path: str = "/app/agent-teams"
    workflows_path: str = "/app/workflows"
    registries_conf_path: str = "/app/registries.conf"
    logs_path: str = "/app/logs"
    mcp_servers_path: str = "/app/mcp_servers"
    workspace_shared_path: str = "/app/workspace_shared"
    history_storage_path: str = "/app/volumes/conversations"
    file_workspace_path: str = "/workspace"
    registry_data_path: str = "/app/registries"
    volumes_path: str = "/app/volumes"
    configs_path: str = "/configs"
    models_config_path: str = "/configs/models.yaml"
    pricing_config_path: str = "/configs/pricing.json"

    # -- Docker --
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_network: str = "mcp-network"
    docker_network_driver: str = "bridge"
    docker_host_internal: str = "host.docker.internal"
    docker_stop_timeout: int = 10

    # -- HTTP --
    http_timeout: float = 10.0
    http_timeout_health: float = 5.0
    http_timeout_long: float = 600.0
    service_host: str = "0.0.0.0"

    # -- Nmap --
    nmap_timeout_quick: int = 300
    nmap_timeout_full: int = 600
    nmap_timeout_vulnerability: int = 600
    default_scan_network: str = "192.168.50.0/24"
    default_scan_target: str = "192.168.50.1"
    allowed_scan_networks: List[str] = field(default_factory=lambda: [
        "192.168.50.0/24", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
    ])

    # -- Runtime --
    llm_max_tokens: int = 4096
    polling_interval: float = 2.0
    polling_short: float = 0.1
    polling_supervisor: float = 10.0
    auto_install_mcps: List[str] = field(default_factory=lambda: [
        "agent", "file_tools", "nmap_recon", "history"
    ])
    api_protocol: str = "http"
    api_host: str = "localhost"
    log_level: str = "INFO"
    log_format: str = "json"

    # -- Derived URLs (computed from ports) --
    @property
    def history_mcp_url(self) -> str:
        return f"http://localhost:{self.history_port}"

    @property
    def docker_host_url_pattern(self) -> str:
        """Returns pattern with {port} placeholder"""
        return f"http://{self.docker_host_internal}:{{port}}"

    @property
    def docker_container_url_pattern(self) -> str:
        """Returns pattern with {container_name} and {port} placeholders"""
        return "http://{container_name}:{port}"

    # -- Compatibility methods for legacy code --
    def get_orchestrator_port(self) -> int:
        return self.orchestrator_port

    def get_agent_definitions_path(self) -> str:
        return self.agent_definitions_path

    def get_agent_teams_path(self) -> str:
        return self.agent_teams_path

    def get_registries_conf_path(self) -> str:
        return self.registries_conf_path

    def get_docker_socket_path(self) -> str:
        return self.docker_socket

    def get_docker_network_name(self) -> str:
        return self.docker_network

    def get_docker_network_driver(self) -> str:
        return self.docker_network_driver

    def get_docker_stop_timeout(self) -> int:
        return self.docker_stop_timeout

    def get_polling_interval(self) -> float:
        return self.polling_interval

    def get_http_timeout_default(self) -> float:
        return self.http_timeout

    def get_http_timeout_health_check(self) -> float:
        return self.http_timeout_health

    def get_nmap_port(self) -> int:
        return self.nmap_port

    def get_agent_port(self) -> int:
        return self.agent_port

    def get_llm_max_tokens(self) -> int:
        return self.llm_max_tokens

    def get_service_host(self) -> str:
        return self.service_host

    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from environment"""
        return get_anthropic_api_key()

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment"""
        return get_openai_api_key()

    def get_docker_host_url_pattern(self) -> str:
        """Get Docker host URL pattern"""
        return self.docker_host_url_pattern

    def get_docker_container_url_pattern(self) -> str:
        """Get Docker container URL pattern"""
        return self.docker_container_url_pattern


# =============================================================================
# SECRETS - The ONLY thing from environment variables
# =============================================================================

def get_anthropic_api_key() -> Optional[str]:
    """API keys cannot be in version control."""
    return os.getenv("ANTHROPIC_API_KEY")


def get_openai_api_key() -> Optional[str]:
    """API keys cannot be in version control."""
    return os.getenv("OPENAI_API_KEY")


# =============================================================================
# LOADER
# =============================================================================

def load_config(path: str = "/app/configs/orchestrator.yaml") -> Config:
    """
    Load configuration from YAML.
    Returns defaults if file doesn't exist.
    """
    if not Path(path).exists():
        print(f"Config not found at {path}, using defaults")
        return Config()

    with open(path) as f:
        y = yaml.safe_load(f) or {}

    # Helper to safely navigate nested dicts
    def get(d: dict, *keys, default=None):
        for k in keys:
            if not isinstance(d, dict):
                return default
            d = d.get(k, {})
        return d if d != {} else default

    return Config(
        # Ports
        orchestrator_port=get(y, "orchestrator", "port") or 8000,
        frontend_port=int(os.getenv("FRONTEND_PORT", "3000")),
        registry_port=int(os.getenv("REGISTRY_PORT", "9000")),
        agent_port=int(os.getenv("AGENT_PORT", "7000")),
        file_tools_port=int(os.getenv("FILE_TOOLS_PORT", "7002")),
        nmap_port=int(os.getenv("NMAP_PORT", "7003")),
        history_port=get(y, "ports", "history") or 7004,

        # Paths
        agent_definitions_path=get(y, "paths", "agent_definitions") or "/app/agent-definitions",
        agent_teams_path=get(y, "paths", "agent_teams") or "/app/agent-teams",
        workflows_path=get(y, "paths", "workflows") or "/app/workflows",
        registries_conf_path=get(y, "paths", "registries_conf") or "/app/registries.conf",
        logs_path=get(y, "paths", "logs") or "/app/logs",
        mcp_servers_path=get(y, "paths", "mcp_servers") or "/app/mcp_servers",
        workspace_shared_path=get(y, "paths", "workspace_shared") or "/app/workspace_shared",
        history_storage_path=get(y, "paths", "history_storage") or "/app/volumes/conversations",
        file_workspace_path=get(y, "paths", "file_workspace") or "/workspace",
        registry_data_path=get(y, "paths", "registry_data") or "/app/registries",

        # Docker
        docker_socket=get(y, "docker", "socket_path") or "unix:///var/run/docker.sock",
        docker_network=get(y, "docker", "network_name") or "mcp-network",
        docker_network_driver=get(y, "docker", "network_driver") or "bridge",
        docker_host_internal=get(y, "docker", "host_internal") or "host.docker.internal",
        docker_stop_timeout=get(y, "docker", "stop_timeout") or 10,

        # HTTP
        http_timeout=get(y, "http", "timeouts", "default") or 10.0,
        http_timeout_health=get(y, "http", "timeouts", "health_check") or 5.0,
        http_timeout_long=get(y, "http", "timeouts", "long_running") or 600.0,
        service_host=get(y, "orchestrator", "host") or "0.0.0.0",

        # Nmap
        nmap_timeout_quick=get(y, "nmap", "timeouts", "quick_scan") or 300,
        nmap_timeout_full=get(y, "nmap", "timeouts", "full_scan") or 600,
        nmap_timeout_vulnerability=int(os.getenv("NMAP_TIMEOUT_VULNERABILITY_SCAN", "600")),
        default_scan_network=os.getenv("DEFAULT_SCAN_NETWORK", "192.168.50.0/24"),
        default_scan_target=os.getenv("DEFAULT_SCAN_TARGET", "192.168.50.1"),
        allowed_scan_networks=[
            net.strip() for net in os.getenv("ALLOWED_SCAN_NETWORKS", "").split(',') if net.strip()
        ] or ["192.168.50.0/24", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],

        # Runtime
        llm_max_tokens=get(y, "llm", "max_tokens") or 4096,
        polling_interval=get(y, "polling", "interval") or 2.0,
        polling_short=get(y, "polling", "short_interval") or 0.1,
        polling_supervisor=get(y, "polling", "supervisor_interval") or 10.0,
        auto_install_mcps=get(y, "auto_install", "mcps") or [
            "agent", "file_tools", "nmap_recon", "history"
        ],
        api_protocol=os.getenv("API_PROTOCOL", "http"),
        api_host=os.getenv("API_HOST", "localhost"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=get(y, "logging", "format") or "json",
    )


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        config_path = os.getenv("ORCHESTRATOR_CONFIG_PATH", "/app/configs/orchestrator.yaml")
        _config = load_config(config_path)
    return _config


def reload_config() -> Config:
    """Force reload configuration."""
    global _config
    _config = None
    return get_config()
