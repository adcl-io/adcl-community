# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Model Service - Manages AI model configurations.

Single responsibility: Model configuration management (CRUD + persistence).
Follows ADCL principle: All config in text files (configs/models.yaml).
Enhanced with ratings, performance tracking, and MCP compatibility.
"""

import asyncio
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.logging import get_service_logger
from app.core.model_schema import validate_model_config, validate_single_model
from app.services.audit_service import AuditService
from app.services.metadata_tracker_service import MetadataTrackerService
from app.models.enhanced_models import (
    EnhancedModelConfig, ModelWithMetrics, PerformanceMetrics, ModelRatings,
    MCPCompatibilityMatrix, MCPToolCompatibility, ModelCapabilities, 
    SafetyLevel, FunctionCallingSupport, BenchmarkData, Alert, ModelRecommendation
)

logger = get_service_logger("model")


class ModelService:
    """
    Manages AI model configurations stored in YAML config file.

    Responsibilities:
    - Load models from configs/models.yaml
    - Save models to config file
    - CRUD operations on models
    - Validate model configurations
    - Manage default model
    - Thread-safe access to models

    Note: API keys are never stored in config file (security).
    API keys come from environment variables only.
    """

    def __init__(self, models_config_path: Path, config):
        """
        Initialize ModelService.

        Args:
            models_config_path: Path to models.yaml config file
            config: Application configuration for API key checking
        """
        self.models_config_path = models_config_path
        self.config = config
        self.models = []  # In-memory cache
        self.lock = asyncio.Lock()  # Thread safety
        
        # Enhanced features data storage
        self.performance_data_path = models_config_path.parent / "model_performance.json"
        self.ratings_data_path = models_config_path.parent / "model_ratings.json"
        self.mcp_compatibility_path = models_config_path.parent / "mcp_compatibility.json"
        
        # Initialize audit service
        audit_log_path = models_config_path.parent / "audit_trail.jsonl"
        self.audit_service = AuditService(audit_log_path)
        
        # Initialize metadata tracker service
        self.metadata_tracker = MetadataTrackerService()
        
        logger.info(f"ModelService initialized with config: {models_config_path}")

    async def load_from_config(self) -> List[Dict[str, Any]]:
        """
        Load model configurations from YAML config file.

        Returns:
            List of model configurations

        Raises:
            ValidationError: If config file is invalid
        """
        async with self.lock:
            try:
                if not self.models_config_path.exists():
                    logger.warning(f"Models config not found at {self.models_config_path}")
                    self.models = []
                    return []

                with open(self.models_config_path, "r") as f:
                    config_data = yaml.safe_load(f)

                if not config_data or "models" not in config_data:
                    logger.warning("No models section in config file")
                    self.models = []
                    return []

                # Validate configuration against schema
                try:
                    validate_model_config(config_data)
                except ValidationError as e:
                    logger.error(f"Configuration validation failed: {e}")
                    raise

                # Parse and validate models
                models = []
                model_ids = []

                for model_config in config_data["models"]:
                    # Check for duplicate IDs
                    if model_config["id"] in model_ids:
                        raise ValidationError(
                            f"Duplicate model ID: {model_config['id']}",
                            field="id"
                        )
                    model_ids.append(model_config["id"])

                    # Determine if model is configured based on environment
                    api_key_env = model_config.get("api_key_env", "")
                    if api_key_env == "ANTHROPIC_API_KEY":
                        from app.core.config import get_anthropic_api_key
                        configured = bool(get_anthropic_api_key())
                    elif api_key_env == "OPENAI_API_KEY":
                        from app.core.config import get_openai_api_key
                        configured = bool(get_openai_api_key())
                    elif api_key_env == "OLLAMA_API_KEY":
                        # Ollama: No API key required for local instances
                        # We mark as configured, but actual availability checked at runtime
                        configured = True
                    else:
                        configured = False

                    model_data = {
                        "id": model_config["id"],
                        "name": model_config["name"],
                        "provider": model_config["provider"],
                        "model_id": model_config["model_id"],
                        "temperature": model_config.get("temperature", 0.7),
                        "max_tokens": model_config.get("max_tokens", 4096),
                        "description": model_config.get("description", ""),
                        "is_default": model_config.get("is_default", False),
                        "configured": configured,
                        "api_key": "***configured***" if configured else None,
                        # Enhanced fields
                        "capabilities": model_config.get("capabilities", {}),
                        "safety_level": model_config.get("safety_level", "moderate"),
                        "mcp_compatibility": model_config.get("mcp_compatibility", {}),
                        "ratings": model_config.get("ratings", {}),
                        "benchmarks": model_config.get("benchmarks", {}),
                        # Timestamp fields - migrate existing models without timestamps
                        "created_at": model_config.get("created_at"),
                        "last_updated": model_config.get("last_updated"),
                    }
                    models.append(model_data)

                # Validate exactly one default model
                default_models = [m for m in models if m.get("is_default")]
                if len(default_models) == 0 and len(models) > 0:
                    # Set first configured model as default
                    for m in models:
                        if m.get("configured"):
                            m["is_default"] = True
                            break
                elif len(default_models) > 1:
                    raise ValidationError(
                        f"Multiple default models found ({len(default_models)}). Only one allowed.",
                        field="is_default"
                    )

                self.models = models
                logger.info(f"Loaded {len(models)} models from config")
                return models

            except yaml.YAMLError as e:
                raise ValidationError(f"Invalid YAML in config file: {e}", field="config")
            except Exception as e:
                logger.error(f"Failed to load models from config: {e}")
                raise

    async def save_to_config(self, models: List[Dict[str, Any]]) -> bool:
        """
        Save model configurations to YAML config file.

        NOTE: This method does NOT acquire the lock. Caller must hold the lock.

        Args:
            models: List of model configurations

        Returns:
            True if saved successfully

        Raises:
            ValidationError: If save fails
        """
        try:
            # Load existing config to preserve other sections
            existing_config = {}
            if self.models_config_path.exists():
                with open(self.models_config_path, "r") as f:
                    existing_config = yaml.safe_load(f) or {}

            # Update models section
            config_models = []
            for model in models:
                # Determine api_key_env based on provider
                if model["provider"] == "anthropic":
                    api_key_env = "ANTHROPIC_API_KEY"
                elif model["provider"] == "openai":
                    api_key_env = "OPENAI_API_KEY"
                elif model["provider"] == "ollama":
                    api_key_env = "OLLAMA_API_KEY"
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
                
                # Add enhanced fields if present
                if model.get("capabilities"):
                    config_model["capabilities"] = model["capabilities"]
                if model.get("safety_level"):
                    config_model["safety_level"] = model["safety_level"]
                if model.get("mcp_compatibility"):
                    config_model["mcp_compatibility"] = model["mcp_compatibility"]
                if model.get("ratings"):
                    config_model["ratings"] = model["ratings"]
                if model.get("benchmarks"):
                    config_model["benchmarks"] = model["benchmarks"]
                # Add timestamp fields if present
                if model.get("created_at"):
                    config_model["created_at"] = model["created_at"]
                if model.get("last_updated"):
                    config_model["last_updated"] = model["last_updated"]
                config_models.append(config_model)

            existing_config["models"] = config_models

            # Write back to file
            with open(self.models_config_path, "w") as f:
                yaml.safe_dump(existing_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved {len(models)} models to config")
            return True

        except Exception as e:
            logger.error(f"Failed to save models to config: {e}")
            raise ValidationError(f"Failed to save models: {e}", field="config")

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all configured models.

        Returns:
            List of model configurations
        """
        # Lazy load models from config if not already loaded
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            return self.models.copy()

    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """
        Get a specific model configuration.

        Args:
            model_id: Model identifier

        Returns:
            Model configuration

        Raises:
            NotFoundError: If model not found
        """
        # Lazy load - use list_models which handles locking
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            for model in self.models:
                if model["id"] == model_id:
                    return model.copy()

            raise NotFoundError("Model", model_id)

    async def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new model configuration.

        Args:
            model_data: Model configuration data

        Returns:
            Created model configuration

        Raises:
            ValidationError: If model data invalid
            ConflictError: If model ID already exists
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Generate slug from provider and model_id
            slug = f"{model_data['provider']}-{model_data['model_id']}".replace("/", "-").replace("_", "-").replace(":", "-").lower()
            # Remove double dashes
            while "--" in slug:
                slug = slug.replace("--", "-")

            # Check for duplicate IDs
            if any(m["id"] == slug for m in self.models):
                raise ConflictError(
                    "Model",
                    slug,
                    details={"message": "Model with this ID already exists"}
                )

            model_data["id"] = slug

            # API keys stored in environment only, not in config file
            if model_data.get("api_key"):
                model_data["api_key"] = "***configured***"

            # Validate model data against schema (after id and api_key_env are set)
            try:
                validate_single_model(model_data)
            except ValidationError as e:
                logger.error(f"Model validation failed: {e}")
                raise
            
            # Set creation timestamps
            timestamps = self.metadata_tracker.record_model_creation(slug)
            model_data["created_at"] = timestamps.created_at.isoformat()
            model_data["last_updated"] = timestamps.last_updated.isoformat()

            self.models.append(model_data)

            # Persist to config file
            await self.save_to_config(self.models)

            # Record audit trail
            await self.audit_service.record_model_creation(
                model_id=slug,
                model_data=model_data,
                reason="Model created via API"
            )

            logger.info(f"Created model: {slug}")
            return model_data.copy()

    async def update_model(self, model_id: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing model configuration.

        Args:
            model_id: Model identifier
            model_data: Updated model data

        Returns:
            Updated model configuration

        Raises:
            NotFoundError: If model not found
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            for i, m in enumerate(self.models):
                if m["id"] == model_id:
                    old_model_data = m.copy()
                    
                    model_data["id"] = model_id
                    model_data["configured"] = bool(model_data.get("api_key")) or m.get("configured", False)

                    # Handle API key updates
                    if model_data.get("api_key"):
                        model_data["api_key"] = "***configured***"
                    else:
                        # Keep existing configuration status
                        model_data["api_key"] = m.get("api_key")
                    
                    # Preserve created_at, update last_updated
                    model_data["created_at"] = m.get("created_at")
                    updated_timestamp = self.metadata_tracker.record_model_update(model_id, "configuration")
                    model_data["last_updated"] = updated_timestamp.isoformat()

                    self.models[i] = model_data

                    # Persist to config file
                    await self.save_to_config(self.models)

                    # Record audit trail
                    await self.audit_service.record_model_update(
                        model_id=model_id,
                        old_data=old_model_data,
                        new_data=model_data,
                        reason="Model updated via API"
                    )

                    logger.info(f"Updated model: {model_id}")
                    return model_data.copy()

            raise NotFoundError("Model", model_id)

    async def delete_model(self, model_id: str) -> Dict[str, str]:
        """
        Delete a model configuration.

        Args:
            model_id: Model identifier

        Returns:
            Deletion status

        Raises:
            NotFoundError: If model not found
            ValidationError: If trying to delete last model or default model
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Don't allow deleting the last model
            if len(self.models) == 1:
                raise ValidationError(
                    "Cannot delete the last model",
                    field="model_id"
                )

            for i, m in enumerate(self.models):
                if m["id"] == model_id:
                    deleted_model_data = m.copy()
                    
                    # Don't allow deleting the default model
                    if m.get("is_default"):
                        raise ValidationError(
                            "Cannot delete default model. Set another model as default first.",
                            field="is_default"
                        )

                    self.models.pop(i)

                    # Persist to config file
                    await self.save_to_config(self.models)

                    # Record audit trail
                    await self.audit_service.record_model_deletion(
                        model_id=model_id,
                        model_data=deleted_model_data,
                        reason="Model deleted via API"
                    )

                    logger.info(f"Deleted model: {model_id}")
                    return {"status": "deleted", "id": model_id}

            raise NotFoundError("Model", model_id)

    async def set_default_model(self, model_id: str) -> Dict[str, Any]:
        """
        Set a model as the default.

        Args:
            model_id: Model identifier to set as default

        Returns:
            Updated default model configuration

        Raises:
            NotFoundError: If model not found
            ValidationError: If model is not configured
        """
        # Lazy load models before acquiring lock
        if not self.models:
            await self.load_from_config()

        async with self.lock:
            # Find target model
            target_model = None
            old_default_id = None
            
            for m in self.models:
                if m["id"] == model_id:
                    target_model = m
                if m.get("is_default"):
                    old_default_id = m["id"]

            if not target_model:
                raise NotFoundError("Model", model_id)

            if not target_model.get("configured"):
                raise ValidationError(
                    "Cannot set unconfigured model as default",
                    field="configured"
                )

            # Remove default from all models
            for m in self.models:
                m["is_default"] = False

            # Set new default
            target_model["is_default"] = True

            # Persist to config file
            await self.save_to_config(self.models)

            # Record audit trail
            await self.audit_service.record_default_change(
                old_default_id=old_default_id,
                new_default_id=model_id,
                reason="Default model changed via API"
            )

            logger.info(f"Set default model: {model_id}")
            return {"status": "success", "default_model": target_model.copy()}

    # Enhanced functionality methods

    async def get_model_with_metrics(self, model_id: str) -> ModelWithMetrics:
        """
        Get model configuration with performance metrics and alerts.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelWithMetrics with current performance data
            
        Raises:
            NotFoundError: If model not found
        """
        # Get base model configuration
        model_config = await self.get_model(model_id)
        
        # Convert to enhanced model config
        enhanced_model = self._convert_to_enhanced_config(model_config)
        
        # Load performance metrics
        metrics = await self._load_performance_metrics(model_id)
        
        # Load current alerts
        alerts = await self._get_model_alerts(model_id)
        
        return ModelWithMetrics(
            model=enhanced_model,
            metrics=metrics,
            alerts=alerts
        )

    async def update_model_ratings(self, model_id: str, ratings: ModelRatings) -> ModelRatings:
        """
        Update model ratings and persist to storage.
        
        Args:
            model_id: Model identifier
            ratings: New ratings data
            
        Returns:
            Updated ratings
            
        Raises:
            NotFoundError: If model not found
        """
        # Verify model exists
        await self.get_model(model_id)
        
        # Load existing ratings data
        ratings_data = await self._load_ratings_data()
        
        # Update ratings with timestamp
        ratings.last_updated = datetime.utcnow()
        ratings_data[model_id] = ratings.to_dict()
        
        # Persist to storage
        await self._save_ratings_data(ratings_data)
        
        logger.info(f"Updated ratings for model: {model_id}")
        return ratings

    async def get_compatibility_matrix(self) -> Dict[str, MCPCompatibilityMatrix]:
        """
        Get MCP tool compatibility data for all models.
        
        Returns:
            Dictionary mapping model_id to compatibility matrix
        """
        compatibility_data = await self._load_mcp_compatibility_data()
        
        result = {}
        for model_id, data in compatibility_data.items():
            success_rates = {}
            for category, compat_data in data.get("success_rates", {}).items():
                success_rates[category] = MCPToolCompatibility(
                    success_rate=compat_data["success_rate"],
                    avg_response_time=compat_data["avg_response_time"],
                    last_tested=datetime.fromisoformat(compat_data["last_tested"]) if compat_data.get("last_tested") else None
                )
            
            result[model_id] = MCPCompatibilityMatrix(
                reliability_score=data["reliability_score"],
                tested_categories=data["tested_categories"],
                success_rates=success_rates
            )
        
        return result

    async def update_mcp_compatibility(self, model_id: str, compatibility: MCPCompatibilityMatrix) -> MCPCompatibilityMatrix:
        """
        Update MCP compatibility data for a model.
        
        Args:
            model_id: Model identifier
            compatibility: New compatibility data
            
        Returns:
            Updated compatibility matrix
            
        Raises:
            NotFoundError: If model not found
        """
        # Verify model exists
        await self.get_model(model_id)
        
        # Load existing compatibility data
        compatibility_data = await self._load_mcp_compatibility_data()
        
        # Update compatibility data
        compatibility_data[model_id] = compatibility.to_dict()
        
        # Persist to storage
        await self._save_mcp_compatibility_data(compatibility_data)
        
        logger.info(f"Updated MCP compatibility for model: {model_id}")
        return compatibility

    async def suggest_models_for_task(self, task_type: str, requirements: Optional[Dict[str, Any]] = None) -> List[ModelRecommendation]:
        """
        Recommend models based on task requirements.
        
        Args:
            task_type: Type of task (coding, analysis, creative_writing, etc.)
            requirements: Optional specific requirements (budget, speed, etc.)
            
        Returns:
            List of model recommendations sorted by score
        """
        models = await self.list_models()
        ratings_data = await self._load_ratings_data()
        
        recommendations = []
        
        for model in models:
            if not model.get("configured"):
                continue
                
            model_id = model["id"]
            model_ratings = ratings_data.get(model_id, {})
            
            # Calculate recommendation score based on task type
            score = self._calculate_task_score(model, model_ratings, task_type, requirements)
            
            if score > 0.3:  # Only recommend models with reasonable scores
                reasoning = self._generate_recommendation_reasoning(model, model_ratings, task_type)
                trade_offs = self._identify_trade_offs(model, model_ratings)
                
                recommendations.append(ModelRecommendation(
                    model_id=model_id,
                    score=score,
                    reasoning=reasoning,
                    trade_offs=trade_offs
                ))
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations[:5]  # Return top 5 recommendations

    async def get_model_audit_trail(self, model_id: str) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of audit entries for the model
            
        Raises:
            NotFoundError: If model not found
        """
        # Verify model exists
        await self.get_model(model_id)
        
        # Get audit trail
        entries = await self.audit_service.get_resource_history("model", model_id)
        
        return [entry.to_dict() for entry in entries]

    async def get_configuration_audit_trail(self, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        Get complete configuration audit trail.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries
        """
        entries = await self.audit_service.get_audit_trail(limit=limit)
        return [entry.to_dict() for entry in entries]

    # Private helper methods

    def _convert_to_enhanced_config(self, model_config: Dict[str, Any]) -> EnhancedModelConfig:
        """Convert basic model config to enhanced config with defaults."""
        # Set default capabilities based on provider and model
        capabilities = self._get_default_capabilities(model_config["provider"], model_config["model_id"])
        
        # Set default safety level based on provider
        safety_level = self._get_default_safety_level(model_config["provider"])
        
        return EnhancedModelConfig(
            id=model_config["id"],
            name=model_config["name"],
            provider=model_config["provider"],
            model_id=model_config["model_id"],
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 4096),
            description=model_config.get("description", ""),
            is_default=model_config.get("is_default", False),
            configured=model_config.get("configured", False),
            api_key=model_config.get("api_key"),
            capabilities=capabilities,
            safety_level=safety_level
        )

    def _get_default_capabilities(self, provider: str, model_id: str) -> ModelCapabilities:
        """Get default capabilities based on provider and model."""
        # Default capabilities based on known model patterns
        function_calling = FunctionCallingSupport.NONE
        vision = False
        code_generation = False
        reasoning = "basic"
        
        if provider == "anthropic":
            function_calling = FunctionCallingSupport.NATIVE
            code_generation = True
            reasoning = "advanced"
            if "opus" in model_id.lower():
                reasoning = "expert"
        elif provider == "openai":
            function_calling = FunctionCallingSupport.NATIVE
            code_generation = True
            reasoning = "advanced"
            if "gpt-4" in model_id.lower():
                vision = "vision" in model_id.lower() or "turbo" in model_id.lower()
        elif provider == "ollama":
            if "hermes" in model_id.lower():
                function_calling = FunctionCallingSupport.NATIVE
                code_generation = True
            elif "codellama" in model_id.lower() or "gemma" in model_id.lower():
                code_generation = True
        
        return ModelCapabilities(
            function_calling=function_calling,
            vision=vision,
            code_generation=code_generation,
            reasoning=reasoning,
            multimodal=vision
        )

    def _get_default_safety_level(self, provider: str) -> SafetyLevel:
        """Get default safety level based on provider."""
        if provider == "anthropic":
            return SafetyLevel.MODERATE
        elif provider == "openai":
            return SafetyLevel.MODERATE
        elif provider == "ollama":
            return SafetyLevel.MINIMAL  # Local models often less filtered
        else:
            return SafetyLevel.MODERATE

    async def _load_performance_metrics(self, model_id: str) -> Optional[PerformanceMetrics]:
        """Load performance metrics for a model."""
        try:
            if not self.performance_data_path.exists():
                return None
                
            with open(self.performance_data_path, "r") as f:
                data = json.load(f)
                
            model_data = data.get(model_id)
            if not model_data:
                return None
                
            return PerformanceMetrics(
                response_time_avg=model_data["response_time_avg"],
                tokens_per_second=model_data["tokens_per_second"],
                cost_per_1k_tokens=model_data["cost_per_1k_tokens"],
                success_rate=model_data["success_rate"],
                uptime_percentage=model_data["uptime_percentage"],
                total_requests=model_data["total_requests"],
                monthly_cost=model_data["monthly_cost"],
                timestamp=datetime.fromisoformat(model_data["timestamp"]) if model_data.get("timestamp") else None
            )
        except Exception as e:
            logger.warning(f"Failed to load performance metrics for {model_id}: {e}")
            return None

    async def _load_ratings_data(self) -> Dict[str, Any]:
        """Load ratings data from storage."""
        try:
            if not self.ratings_data_path.exists():
                return {}
                
            with open(self.ratings_data_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load ratings data: {e}")
            return {}

    async def _save_ratings_data(self, ratings_data: Dict[str, Any]) -> None:
        """Save ratings data to storage."""
        try:
            with open(self.ratings_data_path, "w") as f:
                json.dump(ratings_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ratings data: {e}")
            raise ValidationError(f"Failed to save ratings data: {e}", field="ratings")

    async def _load_mcp_compatibility_data(self) -> Dict[str, Any]:
        """Load MCP compatibility data from storage."""
        try:
            if not self.mcp_compatibility_path.exists():
                return {}
                
            with open(self.mcp_compatibility_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load MCP compatibility data: {e}")
            return {}

    async def _save_mcp_compatibility_data(self, compatibility_data: Dict[str, Any]) -> None:
        """Save MCP compatibility data to storage."""
        try:
            with open(self.mcp_compatibility_path, "w") as f:
                json.dump(compatibility_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save MCP compatibility data: {e}")
            raise ValidationError(f"Failed to save MCP compatibility data: {e}", field="mcp_compatibility")

    async def _get_model_alerts(self, model_id: str) -> List[Alert]:
        """Get current alerts for a model."""
        alerts = []
        
        # Load performance metrics to check for issues
        metrics = await self._load_performance_metrics(model_id)
        if metrics:
            # Check for performance issues
            if metrics.response_time_avg > 5000:  # > 5 seconds
                alerts.append(Alert(
                    type="performance_degradation",
                    message=f"High response time: {metrics.response_time_avg:.0f}ms",
                    severity="warning",
                    timestamp=datetime.utcnow()
                ))
            
            if metrics.success_rate < 95:  # < 95% success rate
                alerts.append(Alert(
                    type="reliability_issue",
                    message=f"Low success rate: {metrics.success_rate:.1f}%",
                    severity="error",
                    timestamp=datetime.utcnow()
                ))
            
            if metrics.monthly_cost > 100:  # > $100/month
                alerts.append(Alert(
                    type="cost_threshold",
                    message=f"High monthly cost: ${metrics.monthly_cost:.2f}",
                    severity="warning",
                    timestamp=datetime.utcnow()
                ))
        
        return alerts

    def _calculate_task_score(self, model: Dict[str, Any], ratings: Dict[str, Any], task_type: str, requirements: Optional[Dict[str, Any]]) -> float:
        """Calculate recommendation score for a task."""
        base_score = 0.5
        
        # Get ratings or use defaults
        speed = ratings.get("speed", 3.0)
        quality = ratings.get("quality", 3.0)
        cost_effectiveness = ratings.get("cost_effectiveness", 3.0)
        reliability = ratings.get("reliability", 3.0)
        
        # Adjust score based on task type
        if task_type == "coding":
            base_score += (quality * 0.4 + speed * 0.3 + reliability * 0.3) / 5.0 - 0.6
        elif task_type == "analysis":
            base_score += (quality * 0.5 + reliability * 0.3 + speed * 0.2) / 5.0 - 0.6
        elif task_type == "creative_writing":
            base_score += (quality * 0.6 + speed * 0.2 + cost_effectiveness * 0.2) / 5.0 - 0.6
        else:
            # General purpose
            base_score += (quality * 0.3 + speed * 0.25 + cost_effectiveness * 0.25 + reliability * 0.2) / 5.0 - 0.6
        
        # Apply requirements if specified
        if requirements:
            if requirements.get("budget") == "low" and cost_effectiveness < 3.0:
                base_score *= 0.7
            if requirements.get("speed") == "high" and speed < 3.5:
                base_score *= 0.8
        
        return max(0.0, min(1.0, base_score))

    def _generate_recommendation_reasoning(self, model: Dict[str, Any], ratings: Dict[str, Any], task_type: str) -> str:
        """Generate human-readable reasoning for recommendation."""
        provider = model["provider"]
        name = model["name"]
        
        quality = ratings.get("quality", 3.0)
        speed = ratings.get("speed", 3.0)
        
        if task_type == "coding":
            if quality >= 4.0:
                return f"{name} excels at code generation with high accuracy and good {provider} integration."
            else:
                return f"{name} provides reliable coding assistance with decent performance."
        elif task_type == "analysis":
            if quality >= 4.0:
                return f"{name} offers excellent analytical capabilities with thorough reasoning."
            else:
                return f"{name} handles analysis tasks well with consistent results."
        else:
            return f"{name} is a well-balanced model suitable for general-purpose tasks."

    def _identify_trade_offs(self, model: Dict[str, Any], ratings: Dict[str, Any]) -> Dict[str, str]:
        """Identify trade-offs for the model."""
        trade_offs = {}
        
        speed = ratings.get("speed", 3.0)
        cost = ratings.get("cost_effectiveness", 3.0)
        quality = ratings.get("quality", 3.0)
        
        if speed < 3.0:
            trade_offs["speed"] = "Slower response times but potentially higher quality"
        if cost < 3.0:
            trade_offs["cost"] = "Higher cost per request but premium capabilities"
        if quality < 3.0:
            trade_offs["quality"] = "More cost-effective but may require more iterations"
        
        return trade_offs
