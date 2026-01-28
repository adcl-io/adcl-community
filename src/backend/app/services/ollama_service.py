# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Ollama Service - Manages Ollama model discovery and installation.

Provides functionality to:
- Browse available Ollama models
- Install models from Ollama registry
- Check Ollama service health
- Manage local Ollama models
"""

import asyncio
import httpx
import json
import re
from typing import List, Dict, Any, Optional, AsyncIterator
from pathlib import Path
from datetime import datetime

from app.core.logging import get_service_logger
from app.core.errors import ValidationError, NotFoundError
from app.core.config import get_ollama_base_url
from app.services.ollama_registry_client import (
    OllamaRegistryClient,
    RegistryModel,
    ModelManifest,
    ModelTag
)

logger = get_service_logger("ollama")


class OllamaModel:
    """Represents an Ollama model from the registry"""
    
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.size = data.get("size", "Unknown")
        self.tags = data.get("tags", [])
        self.capabilities = data.get("capabilities", [])
        self.download_size = data.get("download_size", 0)
        self.compatibility_score = data.get("compatibility_score", 3.0)
        self.modified_at = data.get("modified_at", "")
        self.digest = data.get("digest", "")
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "size": self.size,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "download_size": self.download_size,
            "compatibility_score": self.compatibility_score,
            "modified_at": self.modified_at,
            "digest": self.digest
        }


class OllamaService:
    """
    Service for managing Ollama model discovery and installation.
    
    Responsibilities:
    - Connect to Ollama API
    - Browse available models
    - Install/pull models
    - Check service health
    - Manage local model inventory
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Ollama service.
        
        Args:
            base_url: Ollama API base URL (defaults to config value)
        """
        self.base_url = base_url or get_ollama_base_url()
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.registry_client = OllamaRegistryClient()
        logger.info(f"OllamaService initialized with base_url: {self.base_url}")
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check if Ollama service is running and accessible.
        
        This method performs a comprehensive health check including:
        - Service availability
        - Version detection
        - Model count
        - Helpful error messages when unavailable
        
        Returns:
            Health status information including:
            - status: "healthy" or "unavailable"
            - version: Ollama version if available
            - models_count: Number of installed models
            - base_url: The Ollama API URL
            - timestamp: When the check was performed
            - error_message: Helpful message if unavailable
            - troubleshooting: Steps to resolve issues
            
        Raises:
            ValidationError: If service is not accessible (with helpful guidance)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try to get version information first
                version_info = None
                try:
                    version_response = await client.get(f"{self.base_url}/api/version")
                    if version_response.status_code == 200:
                        version_data = version_response.json()
                        version_info = version_data.get("version", "unknown")
                except Exception:
                    # Version endpoint might not be available in all Ollama versions
                    pass
                
                # Check if we can list models (main health check)
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    return {
                        "status": "healthy",
                        "available": True,
                        "version": version_info or "available",
                        "models_count": len(models),
                        "base_url": self.base_url,
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": "Ollama service is running and accessible"
                    }
                else:
                    raise ValidationError(
                        f"Ollama service returned status {response.status_code}",
                        field="service_health"
                    )
                    
        except httpx.ConnectError:
            error_message = (
                f"Cannot connect to Ollama service at {self.base_url}. "
                "The Ollama service does not appear to be running."
            )
            
            troubleshooting = [
                "1. Check if Ollama is installed: Run 'ollama --version' in your terminal",
                "2. Start Ollama service: Run 'ollama serve' or start the Ollama application",
                "3. Verify the service URL is correct in your configuration",
                "4. Check if another process is using port 11434",
                "5. Visit https://ollama.ai for installation instructions"
            ]
            
            raise ValidationError(
                error_message,
                field="service_connection",
                details={
                    "status": "unavailable",
                    "available": False,
                    "base_url": self.base_url,
                    "error_message": error_message,
                    "troubleshooting": troubleshooting,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except httpx.TimeoutException:
            error_message = f"Timeout connecting to Ollama service at {self.base_url}"
            
            troubleshooting = [
                "1. Check if Ollama service is responding slowly",
                "2. Verify network connectivity to the Ollama service",
                "3. Try restarting the Ollama service",
                "4. Check system resources (CPU, memory) on the Ollama host"
            ]
            
            raise ValidationError(
                error_message,
                field="service_timeout",
                details={
                    "status": "unavailable",
                    "available": False,
                    "base_url": self.base_url,
                    "error_message": error_message,
                    "troubleshooting": troubleshooting,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            
            error_message = f"Ollama health check failed: {str(e)}"
            
            troubleshooting = [
                "1. Check Ollama service logs for errors",
                "2. Verify Ollama is properly installed and configured",
                "3. Try restarting the Ollama service",
                "4. Check for any firewall or network issues"
            ]
            
            raise ValidationError(
                error_message,
                field="service_health",
                details={
                    "status": "unavailable",
                    "available": False,
                    "base_url": self.base_url,
                    "error_message": error_message,
                    "troubleshooting": troubleshooting,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def is_service_available(self) -> bool:
        """
        Check if Ollama service is available without raising exceptions.
        
        This is a convenience method that returns a simple boolean indicating
        whether the Ollama service is accessible.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            health = await self.check_health()
            return health.get("available", False)
        except ValidationError:
            return False
        except Exception:
            return False
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status information.
        
        This method returns detailed status information without raising exceptions,
        making it suitable for UI display.
        
        Returns:
            Status information including availability, version, error messages, etc.
        """
        try:
            return await self.check_health()
        except ValidationError as e:
            # Return error details from the exception
            if hasattr(e, 'details') and e.details:
                return e.details
            else:
                return {
                    "status": "unavailable",
                    "available": False,
                    "base_url": self.base_url,
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                "status": "unavailable",
                "available": False,
                "base_url": self.base_url,
                "error_message": f"Unexpected error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def list_available_models(self, search: Optional[str] = None) -> List[OllamaModel]:
        """
        List available models from Ollama registry.
        
        Args:
            search: Optional search term to filter models
            
        Returns:
            List of available Ollama models
            
        Raises:
            ValidationError: If unable to fetch models
        """
        try:
            # First check if service is healthy
            await self.check_health()
            
            # For now, we'll return a curated list of popular models
            # In a real implementation, this would fetch from Ollama's model registry
            popular_models = [
                {
                    "name": "llama3.2:3b",
                    "description": "Meta's Llama 3.2 3B parameter model - fast and efficient",
                    "size": "2.0GB",
                    "tags": ["llama", "meta", "general"],
                    "capabilities": ["text-generation", "conversation"],
                    "download_size": 2147483648,  # 2GB in bytes
                    "compatibility_score": 4.2,
                    "modified_at": "2024-12-01T00:00:00Z"
                },
                {
                    "name": "llama3.2:1b",
                    "description": "Meta's Llama 3.2 1B parameter model - ultra-fast",
                    "size": "1.3GB",
                    "tags": ["llama", "meta", "lightweight"],
                    "capabilities": ["text-generation", "conversation"],
                    "download_size": 1395864371,  # 1.3GB in bytes
                    "compatibility_score": 3.8,
                    "modified_at": "2024-12-01T00:00:00Z"
                },
                {
                    "name": "codellama:7b",
                    "description": "Code Llama 7B - specialized for code generation",
                    "size": "3.8GB",
                    "tags": ["codellama", "meta", "coding"],
                    "capabilities": ["code-generation", "text-generation"],
                    "download_size": 4080218931,  # 3.8GB in bytes
                    "compatibility_score": 4.5,
                    "modified_at": "2024-11-15T00:00:00Z"
                },
                {
                    "name": "mistral:7b",
                    "description": "Mistral 7B - high-quality general purpose model",
                    "size": "4.1GB",
                    "tags": ["mistral", "general"],
                    "capabilities": ["text-generation", "conversation", "reasoning"],
                    "download_size": 4402341478,  # 4.1GB in bytes
                    "compatibility_score": 4.3,
                    "modified_at": "2024-11-20T00:00:00Z"
                },
                {
                    "name": "hermes3:8b",
                    "description": "Nous Hermes 3 8B - excellent for function calling",
                    "size": "4.6GB",
                    "tags": ["hermes", "nous", "function-calling"],
                    "capabilities": ["text-generation", "function-calling", "reasoning"],
                    "download_size": 4939212390,  # 4.6GB in bytes
                    "compatibility_score": 4.7,
                    "modified_at": "2024-12-10T00:00:00Z"
                },
                {
                    "name": "gemma2:2b",
                    "description": "Google's Gemma 2 2B - efficient and capable",
                    "size": "1.6GB",
                    "tags": ["gemma", "google", "efficient"],
                    "capabilities": ["text-generation", "conversation"],
                    "download_size": 1717986918,  # 1.6GB in bytes
                    "compatibility_score": 4.0,
                    "modified_at": "2024-11-25T00:00:00Z"
                }
            ]
            
            models = [OllamaModel(model_data) for model_data in popular_models]
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                models = [
                    model for model in models
                    if (search_lower in model.name.lower() or 
                        search_lower in model.description.lower() or
                        any(search_lower in tag.lower() for tag in model.tags))
                ]
            
            logger.info(f"Retrieved {len(models)} available Ollama models")
            return models
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to list available models: {e}")
            raise ValidationError(
                f"Failed to fetch available models: {str(e)}",
                field="model_listing"
            )
    
    async def list_installed_models(self) -> List[Dict[str, Any]]:
        """
        List models currently installed in Ollama.
        
        Returns:
            List of installed model information
            
        Raises:
            ValidationError: If unable to fetch installed models
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Format model information
                    formatted_models = []
                    for model in models:
                        formatted_models.append({
                            "name": model.get("name", ""),
                            "size": model.get("size", 0),
                            "digest": model.get("digest", ""),
                            "modified_at": model.get("modified_at", ""),
                            "details": model.get("details", {})
                        })
                    
                    logger.info(f"Found {len(formatted_models)} installed Ollama models")
                    return formatted_models
                else:
                    raise ValidationError(
                        f"Failed to list installed models: HTTP {response.status_code}",
                        field="installed_models"
                    )
                    
        except httpx.ConnectError:
            raise ValidationError(
                f"Cannot connect to Ollama service at {self.base_url}",
                field="service_connection"
            )
        except Exception as e:
            logger.error(f"Failed to list installed models: {e}")
            raise ValidationError(
                f"Failed to list installed models: {str(e)}",
                field="installed_models"
            )
    
    async def install_model(self, model_name: str) -> Dict[str, Any]:
        """
        Install/pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to install (e.g., "llama3.2:3b")
            
        Returns:
            Installation status and progress information
            
        Raises:
            ValidationError: If installation fails
            NotFoundError: If model not found
        """
        try:
            # Validate model name format
            if not model_name or ":" not in model_name:
                raise ValidationError(
                    "Model name must be in format 'model:tag' (e.g., 'llama3.2:3b')",
                    field="model_name"
                )
            
            # Check if model is already installed
            installed_models = await self.list_installed_models()
            if any(model["name"] == model_name for model in installed_models):
                return {
                    "status": "already_installed",
                    "model_name": model_name,
                    "message": f"Model {model_name} is already installed"
                }
            
            # Start model pull/installation
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=5.0)) as client:
                pull_data = {"name": model_name}
                
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json=pull_data
                )
                
                if response.status_code == 200:
                    # For now, we'll return success immediately
                    # In a real implementation, this would stream progress updates
                    return {
                        "status": "installing",
                        "model_name": model_name,
                        "message": f"Started installation of {model_name}",
                        "progress": 0
                    }
                elif response.status_code == 404:
                    raise NotFoundError("Model", model_name)
                else:
                    error_text = response.text
                    raise ValidationError(
                        f"Failed to install model {model_name}: {error_text}",
                        field="model_installation"
                    )
                    
        except (ValidationError, NotFoundError):
            raise
        except httpx.ConnectError:
            raise ValidationError(
                f"Cannot connect to Ollama service at {self.base_url}",
                field="service_connection"
            )
        except Exception as e:
            logger.error(f"Failed to install model {model_name}: {e}")
            raise ValidationError(
                f"Failed to install model {model_name}: {str(e)}",
                field="model_installation"
            )
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Detailed model information
            
        Raises:
            NotFoundError: If model not found
            ValidationError: If unable to fetch model info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model_name}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "name": model_name,
                        "modelfile": data.get("modelfile", ""),
                        "parameters": data.get("parameters", ""),
                        "template": data.get("template", ""),
                        "details": data.get("details", {}),
                        "model_info": data.get("model_info", {})
                    }
                elif response.status_code == 404:
                    raise NotFoundError("Model", model_name)
                else:
                    raise ValidationError(
                        f"Failed to get model info: HTTP {response.status_code}",
                        field="model_info"
                    )
                    
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            raise ValidationError(
                f"Failed to get model info: {str(e)}",
                field="model_info"
            )
    
    async def fetch_model_catalog(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch available models from Ollama registry.
        
        This method integrates with OllamaRegistryClient to provide a comprehensive
        catalog of available Ollama models with rich metadata.
        
        Args:
            search: Optional search term to filter models
            
        Returns:
            List of models from the registry with full metadata
            
        Raises:
            ValidationError: If unable to fetch catalog
        """
        try:
            # Use registry client to fetch catalog
            registry_models = await self.registry_client.search_models(search or "")
            
            # Convert to dictionary format for API response
            catalog = []
            for model in registry_models:
                catalog.append(model.to_dict())
            
            logger.info(f"Fetched {len(catalog)} models from registry (search: '{search}')")
            return catalog
            
        except Exception as e:
            logger.error(f"Failed to fetch model catalog: {e}")
            raise ValidationError(
                f"Failed to fetch model catalog: {str(e)}",
                field="model_catalog"
            )
    
    async def get_model_details(self, model_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific model from the registry.
        
        This includes all available tags/versions, metadata, and capabilities.
        
        Args:
            model_name: Name of the model (e.g., "llama3.2", "mistral")
            
        Returns:
            Detailed model information including all tags and metadata
            
        Raises:
            NotFoundError: If model not found in registry
            ValidationError: If unable to fetch model details
        """
        try:
            # Get the model manifest from registry
            manifest = await self.registry_client.get_model_manifest(model_name)
            
            # Convert to dictionary format
            details = manifest.to_dict()
            
            # Add additional information from catalog if available
            catalog_models = await self.registry_client.search_models(model_name)
            for catalog_model in catalog_models:
                if catalog_model.name == model_name:
                    details["description"] = catalog_model.description
                    details["downloads"] = catalog_model.downloads
                    details["stars"] = catalog_model.stars
                    details["capabilities"] = catalog_model.capabilities
                    details["readme_url"] = catalog_model.readme_url
                    details["updated_at"] = catalog_model.updated_at
                    break
            
            logger.info(f"Retrieved details for model: {model_name}")
            return details
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get model details for {model_name}: {e}")
            raise ValidationError(
                f"Failed to get model details: {str(e)}",
                field="model_details"
            )
    
    async def list_available_tags(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List all available tags/versions for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of available tags with metadata (size, parameters, quantization)
            
        Raises:
            NotFoundError: If model not found
            ValidationError: If unable to fetch tags
        """
        try:
            # Get the model manifest
            manifest = await self.registry_client.get_model_manifest(model_name)
            
            # Convert tags to dictionary format
            tags = []
            for tag in manifest.tags:
                tags.append(tag.to_dict())
            
            logger.info(f"Retrieved {len(tags)} tags for model: {model_name}")
            return tags
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to list tags for {model_name}: {e}")
            raise ValidationError(
                f"Failed to list available tags: {str(e)}",
                field="model_tags"
            )
    
    async def pull_model_with_progress(
        self, 
        model_name: str, 
        tag: str = "latest",
        websocket_manager = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Pull a model from Ollama registry and stream progress updates.
        
        This method initiates a model download and yields progress updates that can
        be streamed via WebSocket to provide real-time feedback to the user.
        
        Args:
            model_name: Name of the model to pull (e.g., "llama3.2")
            tag: Specific tag/version to pull (default: "latest")
            websocket_manager: Optional WebSocket manager for streaming updates
            session_id: Optional session ID for WebSocket updates
            
        Yields:
            Progress updates as dictionaries with status, progress, speed, etc.
            
        Raises:
            ValidationError: If pull fails
            NotFoundError: If model not found
        """
        full_model_name = f"{model_name}:{tag}"
        
        try:
            logger.info(f"Starting pull for model: {full_model_name}")
            
            # Initial progress update
            initial_progress = {
                "model_name": full_model_name,
                "status": "starting",
                "progress": 0,
                "message": f"Initiating download of {full_model_name}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send via WebSocket if available
            if websocket_manager and session_id:
                await websocket_manager.send_update(session_id, {
                    "type": "model_pull_progress",
                    "data": initial_progress
                })
            
            yield initial_progress
            
            # Start the pull request with streaming
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=5.0)) as client:
                pull_data = {"name": full_model_name, "stream": True}
                
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json=pull_data
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = error_text.decode('utf-8') if error_text else "Unknown error"
                        
                        error_progress = {
                            "model_name": full_model_name,
                            "status": "error",
                            "progress": 0,
                            "message": f"Failed to pull model: {error_msg}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        if websocket_manager and session_id:
                            await websocket_manager.send_update(session_id, {
                                "type": "model_pull_progress",
                                "data": error_progress
                            })
                        
                        yield error_progress
                        
                        if response.status_code == 404:
                            raise NotFoundError("Model", full_model_name)
                        else:
                            raise ValidationError(
                                f"Failed to pull model: {error_msg}",
                                field="model_pull"
                            )
                    
                    # Parse streaming response
                    total_size = 0
                    downloaded_size = 0
                    last_progress_percent = 0
                    
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                            
                            # Extract progress information from Ollama's response
                            status = data.get("status", "")
                            total = data.get("total", 0)
                            completed = data.get("completed", 0)
                            
                            # Update total size if available
                            if total > 0:
                                total_size = total
                            
                            # Update downloaded size
                            if completed > 0:
                                downloaded_size = completed
                            
                            # Calculate progress percentage
                            progress_percent = 0
                            if total_size > 0:
                                progress_percent = (downloaded_size / total_size) * 100
                            
                            # Only send updates if progress changed significantly (every 5%)
                            if abs(progress_percent - last_progress_percent) >= 5 or status in ["success", "error"]:
                                last_progress_percent = progress_percent
                                
                                # Calculate download speed (simplified)
                                download_speed = "calculating..."
                                if downloaded_size > 0 and total_size > 0:
                                    # Rough estimate based on progress
                                    download_speed = f"{downloaded_size / (1024 * 1024):.1f} MB"
                                
                                # Calculate ETA (simplified)
                                eta = "calculating..."
                                if progress_percent > 0 and progress_percent < 100:
                                    # Rough estimate
                                    eta = f"{int((100 - progress_percent) / progress_percent * 10)} seconds"
                                
                                progress_update = {
                                    "model_name": full_model_name,
                                    "status": "downloading" if status != "success" else "complete",
                                    "progress": round(progress_percent, 2),
                                    "downloaded_bytes": downloaded_size,
                                    "total_bytes": total_size,
                                    "download_speed": download_speed,
                                    "eta": eta,
                                    "current_layer": status,
                                    "message": status,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                
                                # Send via WebSocket if available
                                if websocket_manager and session_id:
                                    await websocket_manager.send_update(session_id, {
                                        "type": "model_pull_progress",
                                        "data": progress_update
                                    })
                                
                                yield progress_update
                            
                            # Check if download is complete
                            if status == "success":
                                completion_progress = {
                                    "model_name": full_model_name,
                                    "status": "complete",
                                    "progress": 100,
                                    "message": f"Successfully downloaded {full_model_name}",
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                
                                if websocket_manager and session_id:
                                    await websocket_manager.send_update(session_id, {
                                        "type": "model_pull_progress",
                                        "data": completion_progress
                                    })
                                
                                yield completion_progress
                                logger.info(f"Successfully pulled model: {full_model_name}")
                                return
                        
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                        except Exception as e:
                            logger.warning(f"Error parsing progress line: {e}")
                            continue
            
        except (ValidationError, NotFoundError):
            raise
        except httpx.ConnectError:
            error_msg = f"Cannot connect to Ollama service at {self.base_url}"
            error_progress = {
                "model_name": full_model_name,
                "status": "error",
                "progress": 0,
                "message": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if websocket_manager and session_id:
                await websocket_manager.send_update(session_id, {
                    "type": "model_pull_progress",
                    "data": error_progress
                })
            
            yield error_progress
            
            raise ValidationError(error_msg, field="service_connection")
        except Exception as e:
            logger.error(f"Failed to pull model {full_model_name}: {e}")
            error_progress = {
                "model_name": full_model_name,
                "status": "error",
                "progress": 0,
                "message": f"Failed to pull model: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if websocket_manager and session_id:
                await websocket_manager.send_update(session_id, {
                    "type": "model_pull_progress",
                    "data": error_progress
                })
            
            yield error_progress
            
            raise ValidationError(
                f"Failed to pull model: {str(e)}",
                field="model_pull"
            )