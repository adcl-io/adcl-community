# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Docker Manager - CLI-based Container Lifecycle Management
Uses Docker CLI instead of Docker SDK to avoid compatibility issues
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
import os
from datetime import datetime, UTC
from app.config import get_config


class DockerManager:
    """Manages Docker containers using CLI commands"""

    def __init__(self, base_dir: str = "/app", resource_type: str = "mcp"):
        """
        Initialize Docker Manager

        Args:
            base_dir: Base directory for resource installations
            resource_type: Type of resource to manage ("mcp" or "trigger")
        """
        self.config = get_config()
        self.base_dir = Path(base_dir)
        self.resource_type = resource_type
        self.installed_file = self.base_dir / f"installed-{resource_type}s.json"

        # Auto-detect network from environment or current container
        self.network_name = self._detect_network()

        # Build map of container paths to host paths
        self.path_mapping = self._build_path_mapping()

        # Ensure network exists
        self._ensure_network()

        # Load installed resources registry
        self.installed = self._load_installed()

        # Backwards compatibility alias
        if resource_type == "mcp":
            self.installed_mcps = self.installed
            self.installed_mcps_file = self.installed_file

    def _run_docker(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Run docker CLI command

        Args:
            args: Docker command arguments
            check: Raise exception on non-zero exit code

        Returns:
            CompletedProcess result
        """
        cmd = ["docker"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if check and result.returncode != 0:
            raise Exception(f"Docker command failed: {' '.join(cmd)}\n{result.stderr}")

        return result

    def _detect_network(self) -> str:
        """
        Auto-detect the Docker network to use for MCP containers.
        Checks:
        1. MCP_NETWORK environment variable
        2. Current container's network (if running in Docker)
        3. Falls back to default 'mcp-network'

        Returns:
            Network name to use for MCP containers
        """
        # 1. Check environment variable
        env_network = os.getenv("MCP_NETWORK")
        if env_network:
            print(f"📡 Using network from MCP_NETWORK env: {env_network}")
            return env_network

        # 2. Try to detect from current container
        try:
            hostname = os.getenv("HOSTNAME", "")
            if hostname:
                # Get networks this container is connected to
                result = self._run_docker(
                    ["inspect", hostname, "--format", "{{json .NetworkSettings.Networks}}"],
                    check=False
                )

                if result.returncode == 0 and result.stdout.strip():
                    networks = json.loads(result.stdout)
                    # Filter out default networks
                    custom_networks = [
                        net for net in networks.keys()
                        if net not in ['bridge', 'host', 'none']
                    ]

                    if custom_networks:
                        detected_network = custom_networks[0]
                        print(f"📡 Auto-detected network from container: {detected_network}")
                        return detected_network
        except Exception as e:
            print(f"⚠️  Could not auto-detect network: {e}")

        # 3. Fall back to default
        default_network = self.config.get_docker_network_name()
        print(f"📡 Using default network: {default_network}")
        return default_network

    def _ensure_network(self):
        """Ensure mcp-network exists"""
        # Check if network exists (exact match)
        result = self._run_docker(
            ["network", "ls", "--filter", f"name=^{self.network_name}$", "--format", "{{.Name}}"],
            check=False
        )

        # Check for exact match (not substring)
        networks = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        if self.network_name not in networks:
            # Create network
            self._run_docker(["network", "create", self.network_name])
            print(f"Created network: {self.network_name}")

    def _load_installed(self) -> Dict[str, Any]:
        """Load registry of installed resources"""
        if self.installed_file.exists():
            return json.loads(self.installed_file.read_text())
        return {}

    # Backwards compatibility
    def _load_installed_mcps(self) -> Dict[str, Any]:
        """Load registry of installed MCPs (backwards compatibility)"""
        return self._load_installed()

    def _save_installed(self):
        """Save registry of installed resources"""
        self.installed_file.write_text(
            json.dumps(self.installed, indent=2)
        )

    # Backwards compatibility
    def _save_installed_mcps(self):
        """Save registry of installed MCPs (backwards compatibility)"""
        self._save_installed()

    def _resolve_env_vars(self, value: str) -> str:
        """
        Resolve environment variable placeholders

        Examples:
            ${ANTHROPIC_API_KEY} -> actual key from env
            ${AGENT_PORT:-7000} -> env value or 7000
        """
        # Match ${VAR} or ${VAR:-default}
        # Note: ([^}]*) allows zero or more chars for default value (handles ${VAR:-} case)
        pattern = r'\$\{([^:}]+)(?::-([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) or ""
            return os.getenv(var_name, default_value)

        return re.sub(pattern, replacer, str(value))

    def _build_trigger_env_vars(self, trigger_package: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Build environment variables for trigger container

        Platform auto-injects:
        - ORCHESTRATOR_URL
        - ORCHESTRATOR_WS
        - WORKFLOW_ID or TEAM_ID (from user_config)

        Args:
            trigger_package: Trigger package definition
            user_config: User-provided configuration

        Returns:
            Dictionary of environment variables
        """
        deployment = trigger_package["deployment"]
        env_vars = {}

        # User-defined environment variables from package
        for key, value in deployment.get("environment", {}).items():
            env_vars[key] = self._resolve_env_vars(value)

        # Platform auto-injected variables
        env_vars["ORCHESTRATOR_URL"] = "http://orchestrator:8000"
        env_vars["ORCHESTRATOR_WS"] = "ws://orchestrator:8000"

        # User-configured target
        if user_config.get("workflow_id"):
            env_vars["WORKFLOW_ID"] = user_config["workflow_id"]
        if user_config.get("team_id"):
            env_vars["TEAM_ID"] = user_config["team_id"]

        return env_vars

    def _build_path_mapping(self) -> Dict[str, str]:
        """
        Build mapping of container paths to host paths by inspecting this container's mounts.
        This is needed because when we create new containers using Docker socket,
        we need to specify host paths, not paths from within this container.

        Returns:
            Dictionary mapping container paths to host paths
        """
        mapping = {}

        # Get hostname to identify this container
        try:
            hostname = os.getenv("HOSTNAME", "")
            if not hostname:
                return mapping

            # Inspect this container's mounts
            result = self._run_docker(
                ["inspect", hostname, "--format", "{{json .Mounts}}"],
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                mounts = json.loads(result.stdout)
                for mount in mounts:
                    if mount.get("Type") == "bind":
                        container_path = mount.get("Destination", "")
                        host_path = mount.get("Source", "")
                        if container_path and host_path:
                            mapping[container_path] = host_path

            print(f"📂 Path mapping built: {len(mapping)} mounts discovered")

        except Exception as e:
            print(f"⚠️  Warning: Could not build path mapping: {e}")

        return mapping

    def _resolve_to_host_path(self, path: str) -> str:
        """
        Resolve a path to its host equivalent using the path mapping.

        Args:
            path: Path that might be a container path

        Returns:
            Host path if mapping exists, otherwise the original path
        """
        abs_path = str(Path(path).resolve())

        # Check if this path is within any mapped container path
        for container_path, host_path in self.path_mapping.items():
            if abs_path == container_path:
                return host_path
            elif abs_path.startswith(container_path + "/"):
                # Path is within a mapped directory
                relative = abs_path[len(container_path):].lstrip("/")
                return str(Path(host_path) / relative)

        # No mapping found, return original
        return abs_path

    def install(self, mcp_package: Dict[str, Any], user_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Install and deploy an MCP/Trigger from package definition

        Args:
            mcp_package: MCP/Trigger package JSON from registry
            user_config: User-provided configuration (for triggers: workflow_id or team_id)

        Returns:
            Installation result with status and container info
        """
        name = mcp_package["name"]
        version = mcp_package["version"]
        deployment = mcp_package["deployment"]

        # For triggers, validate user_config
        if self.resource_type == "trigger":
            if not user_config:
                return {
                    "status": "error",
                    "name": name,
                    "version": version,
                    "error": "Triggers require user_config (workflow_id or team_id)"
                }
            if not user_config.get("workflow_id") and not user_config.get("team_id"):
                return {
                    "status": "error",
                    "name": name,
                    "version": version,
                    "error": "Must specify workflow_id or team_id"
                }

        # Check if already installed
        if name in self.installed:
            installed_version = self.installed[name]["version"]
            if installed_version == version:
                return {
                    "status": "already_installed",
                    "name": name,
                    "version": version
                }

        try:
            # Build Docker image if build context provided
            if "build" in deployment:
                image = self._build_image(name, version, deployment["build"])
            else:
                image = deployment["image"]

            # Build environment variables for triggers
            env_vars = None
            if self.resource_type == "trigger":
                env_vars = self._build_trigger_env_vars(mcp_package, user_config)

            # Create and start container
            container_name = self._create_container(name, deployment, image, env_vars)

            # Register installation
            install_record = {
                "version": version,
                "package": mcp_package,
                "container_name": container_name,
                "installed_at": self._get_timestamp()
            }

            # Add trigger-specific metadata
            if self.resource_type == "trigger":
                install_record["user_config"] = user_config
                install_record["trigger_type"] = mcp_package.get("trigger", {}).get("type", "unknown")

            self.installed[name] = install_record
            self._save_installed()

            return {
                "status": "installed",
                "name": name,
                "version": version,
                "container_name": container_name
            }

        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "version": version,
                "error": str(e)
            }

    def _build_image(self, name: str, version: str, build_config: Dict[str, Any]) -> str:
        """
        Build Docker image from build context

        Args:
            name: MCP name
            version: MCP version
            build_config: Build configuration (context, dockerfile)

        Returns:
            Image tag
        """
        context_path = Path(build_config["context"])
        dockerfile = build_config["dockerfile"]
        image_tag = f"{self.resource_type}-{name}:{version}"

        print(f"Building image {image_tag} from {context_path}/{dockerfile}")

        # Build image
        self._run_docker([
            "build",
            "-t", image_tag,
            "-f", str(context_path / dockerfile),
            str(context_path)
        ])

        return image_tag

    def _create_container(self, name: str, deployment: Dict[str, Any], image: str, environment: Optional[Dict[str, str]] = None) -> str:
        """
        Create and start Docker container

        Args:
            name: Resource name
            deployment: Deployment configuration
            image: Docker image tag
            environment: Optional environment variables (overrides deployment env vars)

        Returns:
            Container name
        """
        container_name = deployment.get("container_name", f"{self.resource_type}-{name}")

        # Remove existing container if present
        self._remove_container_if_exists(container_name)

        # Build docker run command
        run_args = ["run", "-d", "--name", container_name]

        # Add restart policy
        restart = deployment.get("restart", "unless-stopped")
        run_args.extend(["--restart", restart])

        # Add network or network mode
        if deployment.get("network_mode") == "host":
            run_args.extend(["--network", "host"])
        else:
            run_args.extend(["--network", self.network_name])

            # Add ports if not using host networking
            for port_config in deployment.get("ports", []):
                host_port = self._resolve_env_vars(port_config["host"])
                container_port = self._resolve_env_vars(port_config["container"])
                run_args.extend(["-p", f"{host_port}:{container_port}"])

        # Add volumes
        for volume in deployment.get("volumes", []):
            host_path = self._resolve_env_vars(volume["host"])
            container_path = volume["container"]

            # Ensure host path exists (before resolving to host path)
            Path(host_path).mkdir(parents=True, exist_ok=True)

            # Resolve to actual host path (not container path)
            actual_host_path = self._resolve_to_host_path(host_path)
            run_args.extend(["-v", f"{actual_host_path}:{container_path}"])

        # Add environment variables
        # Use provided environment if available, otherwise use deployment environment
        env_to_use = environment if environment is not None else {}
        if environment is None:
            # For MCPs, use deployment environment variables
            for key, value in deployment.get("environment", {}).items():
                env_to_use[key] = self._resolve_env_vars(value)

        for key, value in env_to_use.items():
            run_args.extend(["-e", f"{key}={value}"])

        # Add capabilities
        for cap in deployment.get("cap_add", []):
            run_args.extend(["--cap-add", cap])

        # Add image
        run_args.append(image)

        # Create and start container
        self._run_docker(run_args)

        return container_name

    def _remove_container_if_exists(self, container_name: str):
        """Remove container if it exists"""
        # Check if container exists
        result = self._run_docker(
            ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
            check=False
        )

        if container_name in result.stdout:
            # Stop container
            self._run_docker(["stop", container_name], check=False)
            # Remove container
            self._run_docker(["rm", container_name], check=False)

    def uninstall(self, name: str) -> Dict[str, Any]:
        """
        Uninstall an MCP (stop and remove container)

        Args:
            name: MCP name

        Returns:
            Uninstallation result
        """
        if name not in self.installed:
            return {
                "status": "not_installed",
                "name": name
            }

        try:
            container_name = self.installed[name]["container_name"]

            # Stop and remove container
            self._run_docker(["stop", container_name], check=False)
            self._run_docker(["rm", container_name], check=False)

            # Remove from registry
            del self.installed[name]
            self._save_installed()

            return {
                "status": "uninstalled",
                "name": name
            }

        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def start(self, name: str) -> Dict[str, Any]:
        """Start an installed MCP container"""
        if name not in self.installed:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed[name]["container_name"]
            self._run_docker(["start", container_name])

            return {
                "status": "started",
                "name": name
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def stop(self, name: str) -> Dict[str, Any]:
        """Stop an installed MCP container"""
        if name not in self.installed:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed[name]["container_name"]
            self._run_docker(["stop", container_name])

            return {
                "status": "stopped",
                "name": name
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def restart(self, name: str) -> Dict[str, Any]:
        """Restart an installed MCP container"""
        if name not in self.installed:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed[name]["container_name"]
            self._run_docker(["restart", container_name])

            return {
                "status": "restarted",
                "name": name
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def get_status(self, name: str) -> Dict[str, Any]:
        """Get status of an installed MCP"""
        if name not in self.installed:
            return {
                "status": "not_installed",
                "name": name
            }

        try:
            mcp_info = self.installed[name]
            container_name = mcp_info["container_name"]

            # Get container status
            result = self._run_docker(
                ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Status}}"],
                check=False
            )

            if not result.stdout.strip():
                status_response = {
                    "name": name,
                    "version": mcp_info["version"],
                    "state": "container_missing",
                    "running": False,
                    "container_name": container_name,
                    "installed_at": mcp_info.get("installed_at", "unknown")
                }
                # Add trigger-specific fields
                if self.resource_type == "trigger":
                    status_response["trigger_type"] = mcp_info.get("trigger_type", "unknown")
                return status_response

            status_text = result.stdout.strip()
            running = status_text.startswith("Up")

            status_response = {
                "name": name,
                "version": mcp_info["version"],
                "container_name": container_name,
                "state": "running" if running else "exited",
                "running": running,
                "installed_at": mcp_info.get("installed_at", "unknown")
            }
            # Add trigger-specific fields
            if self.resource_type == "trigger":
                status_response["trigger_type"] = mcp_info.get("trigger_type", "unknown")
            return status_response

        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def list_installed(self) -> List[Dict[str, Any]]:
        """List all installed MCPs with their status"""
        mcps = []

        for name in self.installed.keys():
            mcps.append(self.get_status(name))

        return mcps

    def update(self, name: str, new_package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an MCP to a new version

        Args:
            name: MCP name
            new_package: New MCP package from registry

        Returns:
            Update result
        """
        if name not in self.installed:
            return {"status": "not_installed", "name": name}

        old_version = self.installed[name]["version"]
        new_version = new_package["version"]

        if old_version == new_version:
            return {
                "status": "already_latest",
                "name": name,
                "version": old_version
            }

        # For triggers, preserve user_config
        user_config = None
        if self.resource_type == "trigger":
            user_config = self.installed[name].get("user_config", {})

        # Uninstall old version
        uninstall_result = self.uninstall(name)
        if uninstall_result["status"] != "uninstalled":
            return uninstall_result

        # Install new version
        install_result = self.install(new_package, user_config)

        if install_result["status"] == "installed":
            install_result["old_version"] = old_version
            install_result["new_version"] = new_version
            install_result["status"] = "updated"

        return install_result

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now(UTC).isoformat()
