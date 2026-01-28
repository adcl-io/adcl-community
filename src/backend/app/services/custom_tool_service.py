# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Custom Tool Installation Service

Manages installation, validation, and lifecycle of custom tools for ADCL editions.
Supports MCP servers, binary wrappers, and script-based tools.
"""

import os
import json
import asyncio
import tempfile
import shutil
import tarfile
import zipfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
import yaml
import logging
from datetime import datetime

from app.core.logging import get_service_logger

logger = get_service_logger("custom_tool_service")

class CustomToolService:
    """Service for managing custom tool installations"""
    
    def __init__(self):
        self.tools_dir = Path(os.getenv('ADCL_CUSTOM_TOOLS_DIR', '/workspace/custom_tools'))
        self.manifests_dir = self.tools_dir / "manifests"
        self.installed_tools_file = self.tools_dir / "installed.json"
        
        # Ensure directories exist
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        
        # Load installed tools registry
        self._installed_tools = self._load_installed_tools()

    def _load_installed_tools(self) -> Dict[str, Dict[str, Any]]:
        """Load installed tools registry"""
        if not self.installed_tools_file.exists():
            return {}
        
        try:
            with open(self.installed_tools_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load installed tools registry: {e}")
            return {}

    def _save_installed_tools(self):
        """Save installed tools registry"""
        try:
            with open(self.installed_tools_file, 'w') as f:
                json.dump(self._installed_tools, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save installed tools registry: {e}")
            raise

    async def validate_tool(self, request) -> Dict[str, Any]:
        """Validate a tool before installation"""
        result = {
            "valid": False,
            "tool_info": {},
            "errors": [],
            "warnings": []
        }

        try:
            # Download/extract tool to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                tool_path = await self._fetch_tool_source(request.source, temp_dir)
                
                # Load and validate manifest
                manifest_path = Path(tool_path) / "manifest.json"
                if not manifest_path.exists():
                    result["errors"].append("Tool manifest (manifest.json) not found")
                    return result
                
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Validate manifest structure
                validation_result = self._validate_manifest(manifest, request)
                result["errors"].extend(validation_result["errors"])
                result["warnings"].extend(validation_result["warnings"])
                
                if validation_result["errors"]:
                    return result
                
                # Tool-type specific validation
                if manifest.get("type") == "mcp":
                    mcp_validation = self._validate_mcp_tool(tool_path, manifest)
                    result["errors"].extend(mcp_validation["errors"])
                    result["warnings"].extend(mcp_validation["warnings"])
                
                result["valid"] = len(result["errors"]) == 0
                result["tool_info"] = {
                    "name": manifest.get("name"),
                    "version": manifest.get("version"),
                    "description": manifest.get("description"),
                    "type": manifest.get("type"),
                    "tools": manifest.get("tools", []),
                    "dependencies": manifest.get("dependencies", {})
                }

        except Exception as e:
            result["errors"].append(f"Validation failed: {str(e)}")

        return result

    async def install_custom_tool(self, request) -> Dict[str, Any]:
        """Install a custom tool"""
        result = {
            "success": False,
            "message": "",
            "tool_info": {},
            "installation_path": "",
            "requires_restart": False
        }

        try:
            # Check if tool already exists
            if request.name in self._installed_tools:
                result["message"] = f"Tool '{request.name}' already installed. Use force=true to override."
                return result

            # Validate tool first
            validation_result = await self.validate_tool(request)
            if not validation_result["valid"]:
                result["message"] = f"Tool validation failed: {validation_result['errors']}"
                return result

            # Create installation directory
            install_dir = self.tools_dir / request.name
            if install_dir.exists():
                shutil.rmtree(install_dir)
            install_dir.mkdir(parents=True)

            # Download and extract tool
            tool_path = await self._fetch_tool_source(request.source, str(install_dir))
            
            # Load manifest
            manifest_path = Path(tool_path) / "manifest.json"
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Install dependencies if needed
            if manifest.get("dependencies"):
                await self._install_dependencies(manifest["dependencies"])

            # Tool-type specific installation
            if manifest.get("type") == "mcp":
                await self._install_mcp_tool(install_dir, manifest)
            elif manifest.get("type") == "binary":
                await self._install_binary_tool(install_dir, manifest)
            elif manifest.get("type") == "script":
                await self._install_script_tool(install_dir, manifest)

            # Register installed tool
            self._installed_tools[request.name] = {
                "name": request.name,
                "version": manifest.get("version"),
                "type": manifest.get("type"),
                "source": request.source,
                "install_path": str(install_dir),
                "installed_at": datetime.now().isoformat(),
                "manifest": manifest
            }
            
            self._save_installed_tools()

            result["success"] = True
            result["message"] = f"Tool '{request.name}' installed successfully"
            result["tool_info"] = validation_result["tool_info"]
            result["installation_path"] = str(install_dir)
            result["requires_restart"] = manifest.get("type") == "mcp"

        except Exception as e:
            logger.error(f"Tool installation failed: {e}")
            result["message"] = f"Installation failed: {str(e)}"

        return result

    async def list_custom_tools(self) -> List[Dict[str, Any]]:
        """List all installed custom tools"""
        tools = []
        for name, info in self._installed_tools.items():
            # Check if tool is still valid
            tool_path = Path(info["install_path"])
            status = "installed" if tool_path.exists() else "missing"
            
            tools.append({
                "name": name,
                "version": info.get("version"),
                "type": info.get("type"),
                "description": info.get("manifest", {}).get("description", ""),
                "status": status,
                "installed_at": info.get("installed_at"),
                "tools": info.get("manifest", {}).get("tools", [])
            })
        
        return sorted(tools, key=lambda x: x["name"])

    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a custom tool"""
        if tool_name not in self._installed_tools:
            return None
        
        tool_info = self._installed_tools[tool_name].copy()
        tool_path = Path(tool_info["install_path"])
        
        # Add runtime status
        tool_info["status"] = "installed" if tool_path.exists() else "missing"
        
        # Add manifest details
        manifest = tool_info.get("manifest", {})
        tool_info.update({
            "description": manifest.get("description", ""),
            "author": manifest.get("author"),
            "license": manifest.get("license"),
            "homepage": manifest.get("homepage"),
            "repository": manifest.get("repository"),
            "tools": manifest.get("tools", []),
            "dependencies": manifest.get("dependencies", {}),
            "capabilities": manifest.get("capabilities", [])
        })
        
        return tool_info

    async def uninstall_tool(self, tool_name: str, force: bool = False) -> Dict[str, Any]:
        """Uninstall a custom tool"""
        result = {
            "success": False,
            "message": "",
            "requires_restart": False
        }

        if tool_name not in self._installed_tools:
            result["message"] = f"Tool '{tool_name}' not found"
            return result

        try:
            tool_info = self._installed_tools[tool_name]
            tool_path = Path(tool_info["install_path"])

            # Check for dependencies (other tools depending on this one)
            if not force:
                dependent_tools = self._find_dependent_tools(tool_name)
                if dependent_tools:
                    result["message"] = f"Cannot remove tool. Dependencies exist: {dependent_tools}. Use force=true to override."
                    return result

            # Remove tool directory
            if tool_path.exists():
                shutil.rmtree(tool_path)

            # Tool-type specific cleanup
            if tool_info.get("type") == "mcp":
                await self._cleanup_mcp_tool(tool_name, tool_info)

            # Remove from registry
            del self._installed_tools[tool_name]
            self._save_installed_tools()

            result["success"] = True
            result["message"] = f"Tool '{tool_name}' uninstalled successfully"
            result["requires_restart"] = tool_info.get("type") == "mcp"

        except Exception as e:
            logger.error(f"Tool uninstallation failed: {e}")
            result["message"] = f"Uninstallation failed: {str(e)}"

        return result

    async def validate_installed_tool(self, tool_name: str) -> Dict[str, Any]:
        """Validate an installed tool"""
        result = {
            "valid": False,
            "issues": [],
            "warnings": [],
            "capabilities": []
        }

        if tool_name not in self._installed_tools:
            result["issues"].append("Tool not found in registry")
            return result

        try:
            tool_info = self._installed_tools[tool_name]
            tool_path = Path(tool_info["install_path"])
            
            # Check installation path exists
            if not tool_path.exists():
                result["issues"].append("Installation directory missing")
                return result

            # Validate manifest
            manifest_path = tool_path / "manifest.json"
            if not manifest_path.exists():
                result["issues"].append("Manifest file missing")
                return result

            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Tool-type specific validation
            if manifest.get("type") == "mcp":
                mcp_validation = self._validate_mcp_tool(str(tool_path), manifest)
                result["issues"].extend(mcp_validation["errors"])
                result["warnings"].extend(mcp_validation["warnings"])

            result["valid"] = len(result["issues"]) == 0
            result["capabilities"] = manifest.get("tools", [])

        except Exception as e:
            result["issues"].append(f"Validation error: {str(e)}")

        return result

    def create_tool_manifest(self, manifest_data) -> Dict[str, Any]:
        """Create a tool manifest file"""
        manifest = {
            "name": manifest_data.name,
            "version": manifest_data.version,
            "description": manifest_data.description,
            "type": manifest_data.type,
            "category": manifest_data.category,
            "created_at": datetime.now().isoformat()
        }

        # Add optional fields
        for field in ["author", "license", "homepage", "repository", "dependencies", "tools", "deployment"]:
            value = getattr(manifest_data, field, None)
            if value:
                manifest[field] = value

        # Add type-specific defaults
        if manifest_data.type == "mcp":
            manifest.setdefault("deployment", {
                "type": "docker",
                "image": f"{manifest_data.name}:latest",
                "ports": ["8000"],
                "protocol": "stdio"
            })

        # Validate manifest
        validation = self._validate_manifest_structure(manifest)

        return {
            "manifest": manifest,
            "validation": validation
        }

    def get_tool_templates(self) -> Dict[str, Any]:
        """Get tool templates for different types"""
        return {
            "mcp_server": {
                "name": "my-custom-tool",
                "version": "1.0.0",
                "description": "Custom MCP server tool",
                "type": "mcp",
                "category": "custom",
                "tools": ["custom_action"],
                "deployment": {
                    "type": "docker",
                    "image": "my-custom-tool:latest",
                    "ports": ["8000"],
                    "protocol": "stdio",
                    "environment": {
                        "TOOL_CONFIG": "/config/tool.json"
                    }
                },
                "files": {
                    "server.py": "# MCP Server Implementation\n...",
                    "requirements.txt": "# Python dependencies\n...",
                    "Dockerfile": "# Container definition\n..."
                }
            },
            "binary_wrapper": {
                "name": "my-binary-tool",
                "version": "1.0.0", 
                "description": "Binary tool wrapper",
                "type": "binary",
                "category": "custom",
                "tools": ["execute_binary"],
                "deployment": {
                    "type": "binary",
                    "executable": "./bin/my-tool",
                    "wrapper": "./wrapper.py"
                },
                "files": {
                    "wrapper.py": "# MCP wrapper for binary tool\n...",
                    "bin/my-tool": "# Binary executable\n..."
                }
            },
            "script_tool": {
                "name": "my-script-tool",
                "version": "1.0.0",
                "description": "Script-based tool",
                "type": "script", 
                "category": "custom",
                "tools": ["run_script"],
                "deployment": {
                    "type": "script",
                    "interpreter": "python3",
                    "entry_point": "main.py"
                },
                "files": {
                    "main.py": "# Script entry point\n...",
                    "config.yaml": "# Tool configuration\n..."
                }
            }
        }

    async def _fetch_tool_source(self, source: str, destination: str) -> str:
        """Download and extract tool from source"""
        source_path = Path(destination) / "source"
        source_path.mkdir(parents=True, exist_ok=True)

        if source.startswith(("http://", "https://")):
            # Download from URL
            await self._download_from_url(source, str(source_path))
        elif source.startswith("file://"):
            # Copy from local file
            local_path = source[7:]  # Remove file:// prefix
            await self._copy_from_local(local_path, str(source_path))
        else:
            # Assume it's a registry reference or local path
            if os.path.exists(source):
                await self._copy_from_local(source, str(source_path))
            else:
                raise ValueError(f"Invalid tool source: {source}")

        return str(source_path)

    async def _download_from_url(self, url: str, destination: str):
        """Download tool from URL"""
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Determine file type from URL or content-type
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path) or "tool_package"
        
        temp_file = Path(destination) / filename
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract if it's an archive
        if filename.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(destination)
        elif filename.endswith('.tar'):
            with tarfile.open(temp_file, 'r') as tar:
                tar.extractall(destination)
        elif filename.endswith('.zip'):
            with zipfile.ZipFile(temp_file, 'r') as zip_file:
                zip_file.extractall(destination)

        # Remove temp file
        temp_file.unlink()

    async def _copy_from_local(self, source: str, destination: str):
        """Copy tool from local path"""
        source_path = Path(source)
        if source_path.is_file():
            # Copy single file or extract archive
            if source.endswith(('.tar.gz', '.tgz', '.zip')):
                # Extract archive
                if source.endswith('.zip'):
                    with zipfile.ZipFile(source_path, 'r') as zip_file:
                        zip_file.extractall(destination)
                else:
                    with tarfile.open(source_path, 'r:*') as tar:
                        tar.extractall(destination)
            else:
                shutil.copy2(source_path, destination)
        else:
            # Copy directory
            shutil.copytree(source_path, destination, dirs_exist_ok=True)

    def _validate_manifest(self, manifest: Dict[str, Any], request) -> Dict[str, Any]:
        """Validate tool manifest"""
        result = {"errors": [], "warnings": []}

        # Required fields
        required_fields = ["name", "version", "type", "description"]
        for field in required_fields:
            if field not in manifest:
                result["errors"].append(f"Missing required field: {field}")

        # Validate tool name matches request
        if manifest.get("name") != request.name:
            result["warnings"].append("Manifest name doesn't match request name")

        # Validate type
        valid_types = ["mcp", "binary", "script"]
        if manifest.get("type") not in valid_types:
            result["errors"].append(f"Invalid tool type. Must be one of: {valid_types}")

        return result

    def _validate_manifest_structure(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Validate manifest structure"""
        result = {"valid": True, "errors": [], "warnings": []}

        # Required fields
        required_fields = ["name", "version", "type", "description"]
        for field in required_fields:
            if field not in manifest:
                result["errors"].append(f"Missing required field: {field}")
                result["valid"] = False

        return result

    def _validate_mcp_tool(self, tool_path: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Validate MCP-specific tool requirements"""
        result = {"errors": [], "warnings": []}
        
        tool_dir = Path(tool_path)

        # Check for required MCP files
        required_files = ["server.py"]
        for file in required_files:
            if not (tool_dir / file).exists():
                result["errors"].append(f"Missing required MCP file: {file}")

        # Check for Dockerfile if deployment type is docker
        deployment = manifest.get("deployment", {})
        if deployment.get("type") == "docker":
            if not (tool_dir / "Dockerfile").exists():
                result["errors"].append("Docker deployment requires Dockerfile")

        return result

    async def _install_dependencies(self, dependencies: Dict[str, str]):
        """Install tool dependencies"""
        # This could integrate with the existing registry system
        logger.info(f"Installing dependencies: {dependencies}")

    async def _install_mcp_tool(self, install_dir: Path, manifest: Dict[str, Any]):
        """Install MCP tool specific setup"""
        # Build Docker image if needed
        deployment = manifest.get("deployment", {})
        if deployment.get("type") == "docker":
            await self._build_docker_image(install_dir, manifest)

    async def _install_binary_tool(self, install_dir: Path, manifest: Dict[str, Any]):
        """Install binary tool specific setup"""
        # Make binary executable
        binary_path = install_dir / "bin"
        if binary_path.exists():
            for file in binary_path.iterdir():
                if file.is_file():
                    file.chmod(0o755)

    async def _install_script_tool(self, install_dir: Path, manifest: Dict[str, Any]):
        """Install script tool specific setup"""
        # Make scripts executable
        for file in install_dir.iterdir():
            if file.suffix in ['.py', '.sh', '.pl']:
                file.chmod(0o755)

    async def _build_docker_image(self, install_dir: Path, manifest: Dict[str, Any]):
        """Build Docker image for MCP tool"""
        deployment = manifest.get("deployment", {})
        image_name = deployment.get("image", f"{manifest['name']}:latest")
        
        # Build using Docker API or subprocess
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "build", "-t", image_name, str(install_dir)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Built Docker image: {image_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker build failed: {e.stderr}")
            raise

    def _find_dependent_tools(self, tool_name: str) -> List[str]:
        """Find tools that depend on the given tool"""
        dependents = []
        for name, info in self._installed_tools.items():
            if name == tool_name:
                continue
            dependencies = info.get("manifest", {}).get("dependencies", {})
            if tool_name in dependencies:
                dependents.append(name)
        return dependents

    async def _cleanup_mcp_tool(self, tool_name: str, tool_info: Dict[str, Any]):
        """Cleanup MCP tool specific resources"""
        manifest = tool_info.get("manifest", {})
        deployment = manifest.get("deployment", {})
        
        # Remove Docker image if exists
        if deployment.get("type") == "docker":
            image_name = deployment.get("image", f"{tool_name}:latest")
            import subprocess
            try:
                subprocess.run(
                    ["docker", "rmi", image_name],
                    capture_output=True,
                    check=False  # Don't fail if image doesn't exist
                )
                logger.info(f"Removed Docker image: {image_name}")
            except Exception as e:
                logger.warning(f"Failed to remove Docker image: {e}")


# Service instance management
_custom_tool_service: Optional[CustomToolService] = None

def get_custom_tool_service() -> CustomToolService:
    """Get or create custom tool service instance"""
    global _custom_tool_service
    
    if _custom_tool_service is None:
        _custom_tool_service = CustomToolService()
    
    return _custom_tool_service