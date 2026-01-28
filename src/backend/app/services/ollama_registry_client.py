# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Ollama Registry Client - Fetches model catalog from Ollama registry.

Provides functionality to:
- Fetch model catalog from Ollama registry
- Search and filter models
- Get model manifests with all tags/versions
- Parse model metadata (size, parameters, quantization)
- Cache registry responses for performance
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from app.core.logging import get_service_logger
from app.core.errors import ValidationError, NotFoundError

logger = get_service_logger("ollama_registry")


class RegistryModel:
    """Represents a model from the Ollama registry"""

    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.tags = data.get("tags", [])
        self.downloads = data.get("downloads", 0)
        self.stars = data.get("stars", 0)
        self.capabilities = data.get("capabilities", [])
        self.readme_url = data.get("readme_url", "")
        self.updated_at = data.get("updated_at", "")
        # Estimate model size based on common patterns (default 4GB)
        self.size = data.get("size", 4 * 1024 * 1024 * 1024)  # 4GB default

    def to_dict(self) -> Dict[str, Any]:
        # Convert stars (0-10000+) to rating (0-5)
        rating = min(5.0, (self.stars / 2000.0))  # 10000 stars = 5.0 rating

        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "downloads": self.downloads,
            "stars": self.stars,
            "rating": round(rating, 1),  # Add rating field for frontend
            "size": self.size,  # Add size field for frontend
            "capabilities": self.capabilities,
            "readme_url": self.readme_url,
            "updated_at": self.updated_at,
            # Add default version for models without explicit versions
            "versions": [
                {
                    "tag": "latest",
                    "size": self.size
                }
            ]
        }


class ModelTag:
    """Represents a specific version/tag of a model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.size = data.get("size", 0)
        self.digest = data.get("digest", "")
        self.updated_at = data.get("updated_at", "")
        # Parse metadata from tag name if available
        self.parameters = self._extract_parameters(self.name)
        self.quantization = self._extract_quantization(self.name)
        
    def _extract_parameters(self, tag_name: str) -> str:
        """Extract parameter count from tag name (e.g., '7b' -> '7B')"""
        tag_lower = tag_name.lower()
        # Check in descending order to match longer patterns first (e.g., 13b before 3b)
        for size in ['70b', '34b', '13b', '8b', '7b', '3.8b', '3b', '2b', '1b', '6.7b', '9b', '14b']:
            if size in tag_lower:
                return size.upper()
        return "Unknown"
    
    def _extract_quantization(self, tag_name: str) -> str:
        """Extract quantization level from tag name"""
        tag_lower = tag_name.lower()
        if 'q4' in tag_lower:
            return 'Q4'
        elif 'q5' in tag_lower:
            return 'Q5'
        elif 'q8' in tag_lower:
            return 'Q8'
        elif 'fp16' in tag_lower:
            return 'FP16'
        return "Default"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
            "digest": self.digest,
            "updated_at": self.updated_at,
            "parameters": self.parameters,
            "quantization": self.quantization
        }


class ModelManifest:
    """Represents a complete model manifest with all versions"""
    
    def __init__(self, model_name: str, tags: List[ModelTag], metadata: Dict[str, Any]):
        self.model_name = model_name
        self.tags = tags
        self.metadata = metadata
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "tags": [tag.to_dict() for tag in self.tags],
            "metadata": self.metadata
        }


class OllamaRegistryClient:
    """
    Client for Ollama model registry API.
    
    Responsibilities:
    - Fetch model catalog from registry
    - Search and filter models
    - Get model manifests with all tags
    - Parse model metadata
    - Cache responses for performance
    """
    
    # Note: Ollama doesn't have a public registry API yet, so we'll use a curated list
    # In the future, this would connect to https://registry.ollama.ai/v2
    REGISTRY_URL = "https://registry.ollama.ai/v2"
    CACHE_TTL_SECONDS = 3600  # 1 hour cache
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize Ollama Registry Client.
        
        Args:
            cache_dir: Directory for caching registry responses
        """
        self.cache_dir = cache_dir or Path("/tmp/ollama_registry_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        
        # Request deduplication: track in-flight requests
        self._pending_catalog_request: Optional[asyncio.Task] = None
        self._pending_manifest_requests: Dict[str, asyncio.Task] = {}
        
        logger.info(f"OllamaRegistryClient initialized with cache_dir: {self.cache_dir}")
    
    async def search_models(self, query: str = "") -> List[RegistryModel]:
        """
        Search models in the registry with request deduplication.
        
        Args:
            query: Optional search term to filter models
            
        Returns:
            List of models matching the search query
            
        Raises:
            ValidationError: If unable to fetch models
        """
        try:
            # Check cache first
            cached_models = await self._get_cached_catalog()
            if cached_models is not None:
                models = cached_models
            else:
                # Request deduplication: if a catalog request is already in flight, wait for it
                if self._pending_catalog_request is not None and not self._pending_catalog_request.done():
                    logger.debug("Catalog request already in flight, waiting for it to complete")
                    models = await self._pending_catalog_request
                else:
                    # Create new request task
                    self._pending_catalog_request = asyncio.create_task(self._fetch_and_cache_catalog())
                    models = await self._pending_catalog_request
            
            # Apply search filter if provided
            if query:
                query_lower = query.lower()
                models = [
                    model for model in models
                    if (query_lower in model.name.lower() or 
                        query_lower in model.description.lower() or
                        any(query_lower in tag.lower() for tag in model.tags) or
                        any(query_lower in cap.lower() for cap in model.capabilities))
                ]
            
            logger.info(f"Found {len(models)} models matching query: '{query}'")
            return models
            
        except Exception as e:
            logger.error(f"Failed to search models: {e}")
            raise ValidationError(
                f"Failed to search models: {str(e)}",
                field="model_search"
            )
    
    async def _fetch_and_cache_catalog(self) -> List[RegistryModel]:
        """Fetch catalog and cache it. Helper for request deduplication."""
        models = await self._fetch_model_catalog()
        await self._cache_catalog(models)
        return models
    
    async def get_model_manifest(self, model_name: str) -> ModelManifest:
        """
        Get model manifest with all versions, with request deduplication.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model manifest with all tags/versions
            
        Raises:
            NotFoundError: If model not found
            ValidationError: If unable to fetch manifest
        """
        try:
            # Check cache first
            cached_manifest = await self._get_cached_manifest(model_name)
            if cached_manifest is not None:
                return cached_manifest
            
            # Request deduplication: if a manifest request for this model is already in flight, wait for it
            if model_name in self._pending_manifest_requests:
                pending_task = self._pending_manifest_requests[model_name]
                if not pending_task.done():
                    logger.debug(f"Manifest request for {model_name} already in flight, waiting for it to complete")
                    return await pending_task
            
            # Create new request task
            async def fetch_and_cache():
                try:
                    manifest = await self._fetch_model_manifest(model_name)
                    await self._cache_manifest(model_name, manifest)
                    return manifest
                finally:
                    # Clean up the pending request
                    if model_name in self._pending_manifest_requests:
                        del self._pending_manifest_requests[model_name]
            
            self._pending_manifest_requests[model_name] = asyncio.create_task(fetch_and_cache())
            manifest = await self._pending_manifest_requests[model_name]
            
            logger.info(f"Retrieved manifest for model: {model_name} with {len(manifest.tags)} tags")
            return manifest
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get model manifest for {model_name}: {e}")
            raise ValidationError(
                f"Failed to get model manifest: {str(e)}",
                field="model_manifest"
            )
    
    async def get_model_metadata(self, model_name: str, tag: str) -> Dict[str, Any]:
        """
        Get metadata for specific model version.
        
        Args:
            model_name: Name of the model
            tag: Specific tag/version
            
        Returns:
            Model metadata including size, parameters, quantization
            
        Raises:
            NotFoundError: If model or tag not found
            ValidationError: If unable to fetch metadata
        """
        try:
            # Get the full manifest
            manifest = await self.get_model_manifest(model_name)
            
            # Find the specific tag
            for model_tag in manifest.tags:
                if model_tag.name == tag:
                    return {
                        "model_name": model_name,
                        "tag": tag,
                        "size": model_tag.size,
                        "digest": model_tag.digest,
                        "updated_at": model_tag.updated_at,
                        "parameters": model_tag.parameters,
                        "quantization": model_tag.quantization
                    }
            
            # Tag not found
            raise NotFoundError("Model tag", f"{model_name}:{tag}")
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata for {model_name}:{tag}: {e}")
            raise ValidationError(
                f"Failed to get model metadata: {str(e)}",
                field="model_metadata"
            )
    
    # Private helper methods
    
    async def _fetch_model_catalog(self) -> List[RegistryModel]:
        """
        Fetch model catalog from registry.
        
        Since Ollama doesn't have a public registry API yet, we use a curated list.
        In the future, this would make an HTTP request to the registry.
        """
        # Curated list of popular Ollama models
        catalog_data = [
            {
                "name": "llama3.2",
                "description": "Meta's Llama 3.2 model family - efficient and capable",
                "tags": ["llama", "meta", "general", "latest"],
                "downloads": 2500000,
                "stars": 8500,
                "size": 2000000000,  # 2GB (3B model)
                "capabilities": ["text-generation", "conversation", "reasoning"],
                "readme_url": "https://ollama.ai/library/llama3.2",
                "updated_at": "2024-12-01T00:00:00Z"
            },
            {
                "name": "codellama",
                "description": "Code Llama - specialized for code generation and understanding",
                "tags": ["codellama", "meta", "coding", "programming"],
                "downloads": 1800000,
                "stars": 7200,
                "size": 3800000000,  # 3.8GB (7B model)
                "capabilities": ["code-generation", "text-generation", "code-completion"],
                "readme_url": "https://ollama.ai/library/codellama",
                "updated_at": "2024-11-15T00:00:00Z"
            },
            {
                "name": "mistral",
                "description": "Mistral 7B - high-quality general purpose model",
                "tags": ["mistral", "general", "efficient"],
                "downloads": 2200000,
                "stars": 9100,
                "size": 4100000000,  # 4.1GB (7B model)
                "capabilities": ["text-generation", "conversation", "reasoning", "multilingual"],
                "readme_url": "https://ollama.ai/library/mistral",
                "updated_at": "2024-11-20T00:00:00Z"
            },
            {
                "name": "hermes3",
                "description": "Nous Hermes 3 - excellent for function calling and structured output",
                "tags": ["hermes", "nous", "function-calling", "structured"],
                "downloads": 950000,
                "stars": 4800,
                "size": 4700000000,  # 4.7GB (8B model)
                "capabilities": ["text-generation", "function-calling", "reasoning", "structured-output"],
                "readme_url": "https://ollama.ai/library/hermes3",
                "updated_at": "2024-12-10T00:00:00Z"
            },
            {
                "name": "gemma2",
                "description": "Google's Gemma 2 - efficient and capable open model",
                "tags": ["gemma", "google", "efficient", "open"],
                "downloads": 1400000,
                "stars": 6300,
                "size": 5400000000,  # 5.4GB (9B model)
                "capabilities": ["text-generation", "conversation", "reasoning"],
                "readme_url": "https://ollama.ai/library/gemma2",
                "updated_at": "2024-11-25T00:00:00Z"
            },
            {
                "name": "phi3",
                "description": "Microsoft's Phi-3 - small but powerful model",
                "tags": ["phi", "microsoft", "small", "efficient"],
                "downloads": 1100000,
                "stars": 5400,
                "size": 2300000000,  # 2.3GB (3.8B model)
                "capabilities": ["text-generation", "conversation", "reasoning"],
                "readme_url": "https://ollama.ai/library/phi3",
                "updated_at": "2024-12-05T00:00:00Z"
            },
            {
                "name": "qwen2.5",
                "description": "Alibaba's Qwen 2.5 - multilingual and capable",
                "tags": ["qwen", "alibaba", "multilingual", "general"],
                "downloads": 850000,
                "stars": 4200,
                "size": 4300000000,  # 4.3GB (7B model)
                "capabilities": ["text-generation", "conversation", "multilingual", "reasoning"],
                "readme_url": "https://ollama.ai/library/qwen2.5",
                "updated_at": "2024-12-08T00:00:00Z"
            },
            {
                "name": "deepseek-coder",
                "description": "DeepSeek Coder - specialized for code generation",
                "tags": ["deepseek", "coding", "programming"],
                "downloads": 720000,
                "stars": 3900,
                "size": 3800000000,  # 3.8GB (6.7B model)
                "capabilities": ["code-generation", "text-generation", "code-completion"],
                "readme_url": "https://ollama.ai/library/deepseek-coder",
                "updated_at": "2024-11-28T00:00:00Z"
            }
        ]
        
        return [RegistryModel(data) for data in catalog_data]
    
    async def _fetch_model_manifest(self, model_name: str) -> ModelManifest:
        """
        Fetch model manifest with all tags.
        
        Since Ollama doesn't have a public registry API yet, we use curated data.
        """
        # Curated manifest data for popular models
        manifests = {
            "llama3.2": {
                "tags": [
                    {"name": "latest", "size": 2000000000, "digest": "sha256:llama32-latest", "updated_at": "2024-12-01T00:00:00Z"},
                    {"name": "3b", "size": 2000000000, "digest": "sha256:llama32-3b", "updated_at": "2024-12-01T00:00:00Z"},
                    {"name": "1b", "size": 1300000000, "digest": "sha256:llama32-1b", "updated_at": "2024-12-01T00:00:00Z"},
                ],
                "metadata": {
                    "family": "llama",
                    "provider": "meta",
                    "license": "llama3"
                }
            },
            "codellama": {
                "tags": [
                    {"name": "latest", "size": 3800000000, "digest": "sha256:codellama-latest", "updated_at": "2024-11-15T00:00:00Z"},
                    {"name": "7b", "size": 3800000000, "digest": "sha256:codellama-7b", "updated_at": "2024-11-15T00:00:00Z"},
                    {"name": "13b", "size": 7300000000, "digest": "sha256:codellama-13b", "updated_at": "2024-11-15T00:00:00Z"},
                    {"name": "34b", "size": 19000000000, "digest": "sha256:codellama-34b", "updated_at": "2024-11-15T00:00:00Z"},
                ],
                "metadata": {
                    "family": "llama",
                    "provider": "meta",
                    "license": "llama2"
                }
            },
            "mistral": {
                "tags": [
                    {"name": "latest", "size": 4100000000, "digest": "sha256:mistral-latest", "updated_at": "2024-11-20T00:00:00Z"},
                    {"name": "7b", "size": 4100000000, "digest": "sha256:mistral-7b", "updated_at": "2024-11-20T00:00:00Z"},
                    {"name": "7b-q4", "size": 2300000000, "digest": "sha256:mistral-7b-q4", "updated_at": "2024-11-20T00:00:00Z"},
                ],
                "metadata": {
                    "family": "mistral",
                    "provider": "mistral-ai",
                    "license": "apache-2.0"
                }
            },
            "hermes3": {
                "tags": [
                    {"name": "latest", "size": 4600000000, "digest": "sha256:hermes3-latest", "updated_at": "2024-12-10T00:00:00Z"},
                    {"name": "8b", "size": 4600000000, "digest": "sha256:hermes3-8b", "updated_at": "2024-12-10T00:00:00Z"},
                ],
                "metadata": {
                    "family": "llama",
                    "provider": "nous-research",
                    "license": "llama3"
                }
            },
            "gemma2": {
                "tags": [
                    {"name": "latest", "size": 1600000000, "digest": "sha256:gemma2-latest", "updated_at": "2024-11-25T00:00:00Z"},
                    {"name": "2b", "size": 1600000000, "digest": "sha256:gemma2-2b", "updated_at": "2024-11-25T00:00:00Z"},
                    {"name": "9b", "size": 5400000000, "digest": "sha256:gemma2-9b", "updated_at": "2024-11-25T00:00:00Z"},
                ],
                "metadata": {
                    "family": "gemma",
                    "provider": "google",
                    "license": "gemma"
                }
            },
            "phi3": {
                "tags": [
                    {"name": "latest", "size": 2300000000, "digest": "sha256:phi3-latest", "updated_at": "2024-12-05T00:00:00Z"},
                    {"name": "3.8b", "size": 2300000000, "digest": "sha256:phi3-3.8b", "updated_at": "2024-12-05T00:00:00Z"},
                ],
                "metadata": {
                    "family": "phi",
                    "provider": "microsoft",
                    "license": "mit"
                }
            },
            "qwen2.5": {
                "tags": [
                    {"name": "latest", "size": 4400000000, "digest": "sha256:qwen25-latest", "updated_at": "2024-12-08T00:00:00Z"},
                    {"name": "7b", "size": 4400000000, "digest": "sha256:qwen25-7b", "updated_at": "2024-12-08T00:00:00Z"},
                    {"name": "14b", "size": 8200000000, "digest": "sha256:qwen25-14b", "updated_at": "2024-12-08T00:00:00Z"},
                ],
                "metadata": {
                    "family": "qwen",
                    "provider": "alibaba",
                    "license": "apache-2.0"
                }
            },
            "deepseek-coder": {
                "tags": [
                    {"name": "latest", "size": 3700000000, "digest": "sha256:deepseek-latest", "updated_at": "2024-11-28T00:00:00Z"},
                    {"name": "6.7b", "size": 3700000000, "digest": "sha256:deepseek-6.7b", "updated_at": "2024-11-28T00:00:00Z"},
                ],
                "metadata": {
                    "family": "deepseek",
                    "provider": "deepseek",
                    "license": "deepseek"
                }
            }
        }
        
        if model_name not in manifests:
            raise NotFoundError("Model", model_name)
        
        manifest_data = manifests[model_name]
        tags = [ModelTag(tag_data) for tag_data in manifest_data["tags"]]
        
        return ModelManifest(
            model_name=model_name,
            tags=tags,
            metadata=manifest_data["metadata"]
        )
    
    async def _get_cached_catalog(self) -> Optional[List[RegistryModel]]:
        """Get cached catalog if available and not expired."""
        cache_file = self.cache_dir / "catalog.json"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is expired
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() > self.CACHE_TTL_SECONDS:
                logger.debug("Catalog cache expired")
                return None
            
            # Load from cache
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            logger.debug(f"Loaded {len(data)} models from cache")
            return [RegistryModel(model_data) for model_data in data]
            
        except Exception as e:
            logger.warning(f"Failed to load catalog from cache: {e}")
            return None
    
    async def _cache_catalog(self, models: List[RegistryModel]) -> None:
        """Cache the catalog to disk."""
        cache_file = self.cache_dir / "catalog.json"
        
        try:
            data = [model.to_dict() for model in models]
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached {len(models)} models to disk")
            
        except Exception as e:
            logger.warning(f"Failed to cache catalog: {e}")
    
    async def _get_cached_manifest(self, model_name: str) -> Optional[ModelManifest]:
        """Get cached manifest if available and not expired."""
        cache_file = self.cache_dir / f"manifest_{model_name}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is expired
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() > self.CACHE_TTL_SECONDS:
                logger.debug(f"Manifest cache for {model_name} expired")
                return None
            
            # Load from cache
            with open(cache_file, "r") as f:
                data = json.load(f)
            
            tags = [ModelTag(tag_data) for tag_data in data["tags"]]
            manifest = ModelManifest(
                model_name=data["model_name"],
                tags=tags,
                metadata=data["metadata"]
            )
            
            logger.debug(f"Loaded manifest for {model_name} from cache")
            return manifest
            
        except Exception as e:
            logger.warning(f"Failed to load manifest from cache: {e}")
            return None
    
    async def _cache_manifest(self, model_name: str, manifest: ModelManifest) -> None:
        """Cache the manifest to disk."""
        cache_file = self.cache_dir / f"manifest_{model_name}.json"
        
        try:
            with open(cache_file, "w") as f:
                json.dump(manifest.to_dict(), f, indent=2)
            
            logger.debug(f"Cached manifest for {model_name} to disk")
            
        except Exception as e:
            logger.warning(f"Failed to cache manifest: {e}")
