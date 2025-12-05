# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
MCP Manager - Docker Container Lifecycle Management
Handles installation, deployment, and management of MCP servers
"""
import docker
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from docker.models.containers import Container
from docker.models.networks import Network
from app.config import get_config


class MCPManager:
    """Manages MCP server lifecycle using Docker API"""

    def __init__(self, base_dir: str = "/app"):
        """
        Initialize MCP Manager

        Args:
            base_dir: Base directory for MCP installations
        """
        self.config = get_config()
        # Connect to Docker using Unix socket (three slashes for absolute path)
        self.client = docker.DockerClient(base_url=self.config.get_docker_socket_path())
        self.base_dir = Path(base_dir)
        self.installed_mcps_file = self.base_dir / "installed-mcps.json"
        self.network_name = self.config.get_docker_network_name()

        # Ensure network exists
        self._ensure_network()

        # Load installed MCPs registry
        self.installed_mcps = self._load_installed_mcps()

    def _ensure_network(self):
        """Ensure mcp-network exists"""
        try:
            self.client.networks.get(self.network_name)
        except docker.errors.NotFound:
            self.client.networks.create(
                self.network_name,
                driver=self.config.get_docker_network_driver()
            )

    def _load_installed_mcps(self) -> Dict[str, Any]:
        """Load registry of installed MCPs"""
        if self.installed_mcps_file.exists():
            return json.loads(self.installed_mcps_file.read_text())
        return {}

    def _save_installed_mcps(self):
        """Save registry of installed MCPs"""
        self.installed_mcps_file.write_text(
            json.dumps(self.installed_mcps, indent=2)
        )

    def _resolve_env_vars(self, value: str) -> str:
        """
        Resolve environment variable placeholders

        Examples:
            ${ANTHROPIC_API_KEY} -> actual key from env
            ${AGENT_PORT:-7000} -> env value or 7000
        """
        # Match ${VAR} or ${VAR:-default}
        pattern = r'\$\{([^:}]+)(?::-([^}]+))?\}'

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) or ""
            return os.getenv(var_name, default_value)

        return re.sub(pattern, replacer, str(value))

    def install(self, mcp_package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install and deploy an MCP from package definition

        Args:
            mcp_package: MCP package JSON from registry

        Returns:
            Installation result with status and container info
        """
        name = mcp_package["name"]
        version = mcp_package["version"]
        deployment = mcp_package["deployment"]

        # Check if already installed
        if name in self.installed_mcps:
            installed_version = self.installed_mcps[name]["version"]
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

            # Create and start container
            container = self._create_container(name, deployment, image)

            # Register installation
            self.installed_mcps[name] = {
                "version": version,
                "package": mcp_package,
                "container_id": container.id,
                "container_name": deployment.get("container_name", f"mcp-{name}"),
                "installed_at": self._get_timestamp()
            }
            self._save_installed_mcps()

            return {
                "status": "installed",
                "name": name,
                "version": version,
                "container_id": container.id,
                "container_name": container.name
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
        image_tag = f"mcp-{name}:{version}"

        print(f"Building image {image_tag} from {context_path}/{dockerfile}")

        # Build image
        image, build_logs = self.client.images.build(
            path=str(context_path),
            dockerfile=dockerfile,
            tag=image_tag,
            rm=True
        )

        return image_tag

    def _create_container(self, name: str, deployment: Dict[str, Any], image: str) -> Container:
        """
        Create and start Docker container

        Args:
            name: MCP name
            deployment: Deployment configuration
            image: Docker image tag

        Returns:
            Started container
        """
        container_name = deployment.get("container_name", f"mcp-{name}")

        # Prepare environment variables (resolve placeholders)
        environment = {}
        for key, value in deployment.get("environment", {}).items():
            environment[key] = self._resolve_env_vars(value)

        # Prepare volumes
        volumes = {}
        for volume in deployment.get("volumes", []):
            host_path = self._resolve_env_vars(volume["host"])
            container_path = volume["container"]

            # Ensure host path exists
            Path(host_path).mkdir(parents=True, exist_ok=True)

            volumes[str(Path(host_path).absolute())] = {
                "bind": container_path,
                "mode": "rw"
            }

        # Prepare port bindings
        ports = {}
        if "ports" in deployment:
            for port_config in deployment["ports"]:
                host_port = self._resolve_env_vars(port_config["host"])
                container_port = self._resolve_env_vars(port_config["container"])
                ports[f"{container_port}/tcp"] = host_port

        # Create container config
        container_config = {
            "image": image,
            "name": container_name,
            "environment": environment,
            "volumes": volumes,
            "detach": True,
            "restart_policy": {"Name": deployment.get("restart", "unless-stopped")},
        }

        # Add ports if not using host networking
        if deployment.get("network_mode") != "host":
            container_config["ports"] = ports
            container_config["network"] = self.network_name
        else:
            container_config["network_mode"] = "host"

        # Add capabilities if specified
        if "cap_add" in deployment:
            container_config["cap_add"] = deployment["cap_add"]

        # Remove existing container if present
        self._remove_container_if_exists(container_name)

        # Create and start container
        container = self.client.containers.run(**container_config)

        return container

    def _remove_container_if_exists(self, container_name: str):
        """Remove container if it exists"""
        try:
            existing = self.client.containers.get(container_name)
            existing.stop()
            existing.remove()
        except docker.errors.NotFound:
            pass

    def uninstall(self, name: str) -> Dict[str, Any]:
        """
        Uninstall an MCP (stop and remove container)

        Args:
            name: MCP name

        Returns:
            Uninstallation result
        """
        if name not in self.installed_mcps:
            return {
                "status": "not_installed",
                "name": name
            }

        try:
            container_name = self.installed_mcps[name]["container_name"]

            # Stop and remove container
            try:
                container = self.client.containers.get(container_name)
                container.stop(timeout=self.config.get_docker_stop_timeout())
                container.remove()
            except docker.errors.NotFound:
                pass

            # Remove from registry
            del self.installed_mcps[name]
            self._save_installed_mcps()

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
        if name not in self.installed_mcps:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed_mcps[name]["container_name"]
            container = self.client.containers.get(container_name)
            container.start()

            return {
                "status": "started",
                "name": name,
                "container_id": container.id
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def stop(self, name: str) -> Dict[str, Any]:
        """Stop an installed MCP container"""
        if name not in self.installed_mcps:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed_mcps[name]["container_name"]
            container = self.client.containers.get(container_name)
            container.stop(timeout=self.config.get_docker_stop_timeout())

            return {
                "status": "stopped",
                "name": name,
                "container_id": container.id
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def restart(self, name: str) -> Dict[str, Any]:
        """Restart an installed MCP container"""
        if name not in self.installed_mcps:
            return {"status": "not_installed", "name": name}

        try:
            container_name = self.installed_mcps[name]["container_name"]
            container = self.client.containers.get(container_name)
            container.restart(timeout=self.config.get_docker_stop_timeout())

            return {
                "status": "restarted",
                "name": name,
                "container_id": container.id
            }
        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def get_status(self, name: str) -> Dict[str, Any]:
        """Get status of an installed MCP"""
        if name not in self.installed_mcps:
            return {
                "status": "not_installed",
                "name": name
            }

        try:
            mcp_info = self.installed_mcps[name]
            container_name = mcp_info["container_name"]

            try:
                container = self.client.containers.get(container_name)
                container.reload()

                return {
                    "name": name,
                    "version": mcp_info["version"],
                    "container_id": container.id,
                    "container_name": container.name,
                    "state": container.status,
                    "running": container.status == "running",
                    "installed_at": mcp_info.get("installed_at", "unknown")
                }
            except docker.errors.NotFound:
                return {
                    "name": name,
                    "version": mcp_info["version"],
                    "state": "container_missing",
                    "running": False,
                    "installed_at": mcp_info.get("installed_at", "unknown")
                }

        except Exception as e:
            return {
                "status": "error",
                "name": name,
                "error": str(e)
            }

    def list_installed(self) -> List[Dict[str, Any]]:
        """List all installed MCPs with their status"""
        mcps = []

        for name in self.installed_mcps.keys():
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
        if name not in self.installed_mcps:
            return {"status": "not_installed", "name": name}

        old_version = self.installed_mcps[name]["version"]
        new_version = new_package["version"]

        if old_version == new_version:
            return {
                "status": "already_latest",
                "name": name,
                "version": old_version
            }

        # Uninstall old version
        uninstall_result = self.uninstall(name)
        if uninstall_result["status"] != "uninstalled":
            return uninstall_result

        # Install new version
        install_result = self.install(new_package)

        if install_result["status"] == "installed":
            install_result["old_version"] = old_version
            install_result["new_version"] = new_version
            install_result["status"] = "updated"

        return install_result

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
