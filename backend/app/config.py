# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Configuration loader for ADCL services.
Follows Unix philosophy: Configuration is code, all in plain text.

Environment variables take precedence over YAML config.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional, Dict, List


class Config:
    """
    Centralized configuration loader.

    Priority (highest to lowest):
    1. Environment variables
    2. YAML config file
    3. Default values
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to YAML config file. If None, uses ORCHESTRATOR_CONFIG_PATH env var
                        or defaults to /app/configs/orchestrator.yaml
        """
        self.config_path = config_path or os.getenv(
            "ORCHESTRATOR_CONFIG_PATH",
            "/app/configs/orchestrator.yaml"
        )
        self._config_data: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file if it exists."""
        config_file = Path(self.config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                self._config_data = yaml.safe_load(f) or {}
        else:
            print(f"Warning: Config file not found at {self.config_path}, using env vars and defaults")

    def get(self, key_path: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Get configuration value with priority: env var > yaml > default.

        Args:
            key_path: Dot-separated path in YAML (e.g., "services.orchestrator.port")
            default: Default value if not found
            env_var: Environment variable name to check first

        Returns:
            Configuration value
        """
        # Check environment variable first
        if env_var:
            env_value = os.getenv(env_var)
            if env_value is not None:
                return self._convert_type(env_value, default)

        # Navigate YAML structure
        keys = key_path.split('.')
        value = self._config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value if value is not None else default

    def _convert_type(self, value: str, reference: Any) -> Any:
        """Convert string environment variable to appropriate type based on reference value."""
        if reference is None:
            return value

        ref_type = type(reference)

        try:
            if ref_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif ref_type == int:
                return int(value)
            elif ref_type == float:
                return float(value)
            elif ref_type == list:
                # Handle comma-separated lists
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                return value
        except (ValueError, AttributeError):
            return value

    # Service Ports
    def get_orchestrator_port(self) -> int:
        return self.get("orchestrator.port", 8000, "ORCHESTRATOR_PORT")

    def get_frontend_port(self) -> int:
        # Frontend is not in orchestrator config, use env var only
        return int(os.getenv("FRONTEND_PORT", "3000"))

    def get_registry_port(self) -> int:
        # Registry is separate service, use env var only
        return int(os.getenv("REGISTRY_PORT", "9000"))

    def get_agent_port(self) -> int:
        # MCP ports from env vars (MCPs have their own configs)
        return int(os.getenv("AGENT_PORT", "7000"))

    def get_file_tools_port(self) -> int:
        return int(os.getenv("FILE_TOOLS_PORT", "7002"))

    def get_nmap_port(self) -> int:
        return int(os.getenv("NMAP_PORT", "7003"))

    def get_history_port(self) -> int:
        return int(os.getenv("HISTORY_PORT", "7004"))

    def get_service_host(self) -> str:
        return self.get("orchestrator.host", "0.0.0.0", "SERVICE_HOST")

    # Paths
    def get_agent_definitions_path(self) -> str:
        return self.get("paths.agent_definitions", "/app/agent-definitions", "CONTAINER_AGENT_DEFINITIONS_PATH")

    def get_agent_teams_path(self) -> str:
        return self.get("paths.agent_teams", "/app/agent-teams", "CONTAINER_AGENT_TEAMS_PATH")

    def get_workflows_path(self) -> str:
        return self.get("paths.workflows", "/app/workflows", "CONTAINER_WORKFLOWS_PATH")

    def get_registries_conf_path(self) -> str:
        return self.get("paths.registries_conf", "/app/registries.conf", "CONTAINER_REGISTRIES_CONF_PATH")

    def get_logs_path(self) -> str:
        return self.get("paths.logs", "/app/logs", "CONTAINER_LOGS_PATH")

    def get_mcp_servers_path(self) -> str:
        return self.get("paths.mcp_servers", "/app/mcp_servers", "CONTAINER_MCP_SERVERS_PATH")

    def get_workspace_shared_path(self) -> str:
        return self.get("paths.workspace_shared", "/app/workspace_shared", "CONTAINER_WORKSPACE_SHARED_PATH")

    def get_history_storage_path(self) -> str:
        return self.get("paths.history_storage", "/app/volumes/conversations", "CONTAINER_HISTORY_STORAGE_PATH")

    def get_file_workspace_path(self) -> str:
        return self.get("paths.file_workspace", "/workspace", "CONTAINER_FILE_WORKSPACE_PATH")

    def get_registry_data_path(self) -> str:
        return self.get("paths.registry_data", "/app/registries", "CONTAINER_REGISTRY_DATA_PATH")

    # Docker Configuration
    def get_docker_socket_path(self) -> str:
        return self.get("docker.socket_path", "unix:///var/run/docker.sock", "DOCKER_SOCKET_PATH")

    def get_docker_network_name(self) -> str:
        return self.get("docker.network_name", "mcp-network", "DOCKER_NETWORK_NAME")

    def get_docker_network_driver(self) -> str:
        return self.get("docker.network_driver", "bridge", "DOCKER_NETWORK_DRIVER")

    def get_docker_host_internal(self) -> str:
        return self.get("docker.host_internal", "host.docker.internal", "DOCKER_HOST_INTERNAL")

    def get_docker_stop_timeout(self) -> int:
        return self.get("docker.stop_timeout", 10, "DOCKER_STOP_TIMEOUT")

    # HTTP Configuration
    def get_http_timeout_default(self) -> float:
        return self.get("http.timeouts.default", 10.0, "HTTP_TIMEOUT_DEFAULT")

    def get_http_timeout_health_check(self) -> float:
        return self.get("http.timeouts.health_check", 5.0, "HTTP_TIMEOUT_HEALTH_CHECK")

    def get_http_timeout_long_running(self) -> float:
        return self.get("http.timeouts.long_running", 600.0, "HTTP_TIMEOUT_LONG_RUNNING")

    def get_docker_host_url_pattern(self) -> str:
        """Returns pattern with {port} placeholder"""
        pattern = self.get("http.url_patterns.docker_host",
                          "http://{host_internal}:{port}")
        host_internal = self.get_docker_host_internal()
        return pattern.replace("{host_internal}", host_internal)

    def get_docker_container_url_pattern(self) -> str:
        """Returns pattern with {container_name} and {port} placeholders"""
        return self.get("http.url_patterns.docker_container",
                       "http://{container_name}:{port}")

    # Nmap Configuration
    def get_nmap_timeout_quick_scan(self) -> int:
        return self.get("nmap.timeouts.quick_scan", 300, "NMAP_TIMEOUT_QUICK_SCAN")

    def get_nmap_timeout_full_scan(self) -> int:
        return self.get("nmap.timeouts.full_scan", 600, "NMAP_TIMEOUT_FULL_SCAN")

    def get_nmap_timeout_vulnerability_scan(self) -> int:
        # Nmap config is in its own file, use env var
        return int(os.getenv("NMAP_TIMEOUT_VULNERABILITY_SCAN", "600"))

    def get_default_scan_network(self) -> str:
        return os.getenv("DEFAULT_SCAN_NETWORK", "192.168.50.0/24")

    def get_default_scan_target(self) -> str:
        return os.getenv("DEFAULT_SCAN_TARGET", "192.168.50.1")

    def get_allowed_scan_networks(self) -> List[str]:
        env_value = os.getenv("ALLOWED_SCAN_NETWORKS")
        if env_value:
            return [net.strip() for net in env_value.split(',') if net.strip()]
        return ["192.168.50.0/24", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

    # LLM Configuration
    def get_llm_max_tokens(self) -> int:
        return self.get("llm.max_tokens", 4096, "LLM_MAX_TOKENS")

    # Auto-install Configuration
    def get_auto_install_mcps(self) -> List[str]:
        env_value = os.getenv("AUTO_INSTALL_MCPS")
        if env_value:
            return [mcp.strip() for mcp in env_value.split(',') if mcp.strip()]
        return self.get("auto_install.mcps", [
            "agent",
            "file_tools",
            "nmap_recon",
            "history"
        ])

    # Polling Configuration
    def get_polling_interval(self) -> float:
        return self.get("polling.interval", 2.0, "POLLING_INTERVAL")

    def get_polling_short_interval(self) -> float:
        return self.get("polling.short_interval", 0.1, "POLLING_SHORT_INTERVAL")

    def get_polling_supervisor_interval(self) -> float:
        return self.get("polling.supervisor_interval", 10.0, "POLLING_SUPERVISOR_INTERVAL")

    # API Configuration
    def get_api_protocol(self) -> str:
        return os.getenv("API_PROTOCOL", "http")

    def get_api_host(self) -> str:
        return os.getenv("API_HOST", "localhost")

    # API Keys
    def get_anthropic_api_key(self) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY")

    def get_openai_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config():
    """Reload configuration (useful for hot-reload scenarios)."""
    global _config
    _config = Config()
    return _config
