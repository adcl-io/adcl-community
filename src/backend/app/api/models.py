# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Model API Routes

Handles AI model configuration management:
- CRUD operations for model configurations
- Default model management
- Model configuration persistence to YAML
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio

from app.services.model_service import ModelService
from app.services.ollama_service import OllamaService
from app.services.mcp_compatibility_service import MCPCompatibilityService
from app.services.model_filter_service import ModelFilterService, FilterCriteria, SortCriteria, SortOption, SortDirection
from app.services.performance_monitor_service import PerformanceMonitorService
from app.services.cost_tracking_service import CostTrackingService
from app.services.uptime_monitoring_service import UptimeMonitoringService
from app.core.dependencies import get_model_service
from app.core.errors import NotFoundError, ValidationError, ConflictError
from app.core.logging import get_service_logger
from app.core.model_schema import validate_single_model
from app.models.enhanced_models import (
    ModelWithMetrics, ModelRatings, PerformanceMetrics, 
    ModelRecommendation, MCPCompatibilityMatrix, SafetyLevel, Alert
)

router = APIRouter(prefix="/models", tags=["models"])

# Initialize logger
logger = get_service_logger("models_api")


# Request Models
class Model(BaseModel):
    """Model configuration"""
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    description: str = ""
    is_default: bool = False


class ModelUpdate(BaseModel):
    """Model update"""
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    description: str = ""
    is_default: bool = False


class ModelRecommendationRequest(BaseModel):
    """Request for model recommendations"""
    task_type: str  # coding, analysis, creative_writing, etc.
    requirements: Optional[Dict[str, Any]] = None  # budget, speed, etc.


class OllamaInstallRequest(BaseModel):
    """Request to install an Ollama model"""
    model_name: str  # e.g., "llama3.2:3b"


class MCPCompatibilityTestRequest(BaseModel):
    """Request to test MCP compatibility"""
    categories: Optional[List[str]] = None  # Categories to test, defaults to all


class MCPRecommendationRequest(BaseModel):
    """Request for MCP-compatible model recommendations"""
    required_categories: List[str]
    min_reliability: float = 3.0


class ModelFilterRequest(BaseModel):
    """Request for filtering models"""
    providers: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    safety_levels: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    min_rating: Optional[float] = None
    max_cost: Optional[float] = None
    updated_this_week: Optional[bool] = None
    updated_this_month: Optional[bool] = None
    stale_models: Optional[bool] = None


class ModelSortRequest(BaseModel):
    """Request for sorting models"""
    sort_by: str = "alphabetical"  # alphabetical, usage, cost, performance, provider, status, rating
    direction: str = "asc"  # asc, desc
    secondary_sort: Optional[str] = None


class ModelSearchRequest(BaseModel):
    """Request for searching models"""
    query: str
    search_fields: Optional[List[str]] = None


class ModelExportRequest(BaseModel):
    """Request for exporting model configurations"""
    model_ids: Optional[List[str]] = None  # If None, export all models
    format: str = "yaml"  # yaml or json
    include_sensitive: bool = False  # Whether to include API keys (masked)


class ModelImportRequest(BaseModel):
    """Request for importing model configurations"""
    config_data: str  # YAML or JSON string
    format: str = "yaml"  # yaml or json
    overwrite_existing: bool = False  # Whether to overwrite existing models
    validate_only: bool = False  # Only validate, don't actually import


class PerformanceTrackingRequest(BaseModel):
    """Request for tracking model performance"""
    response_time: float  # Response time in milliseconds
    tokens_generated: int  # Number of tokens generated
    cost: float  # Cost of the request
    success: bool  # Whether the request was successful


class PerformanceHistoryRequest(BaseModel):
    """Request for performance history"""
    timeframe: str = "24h"  # 1h, 24h, 7d, 30d


class AlertClearRequest(BaseModel):
    """Request to clear an alert"""
    alert_type: str  # Type of alert to clear


class CostTrackingRequest(BaseModel):
    """Request for tracking model costs"""
    tokens_input: int
    tokens_output: int
    cost_input: float
    cost_output: float
    provider: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None


class BudgetSetRequest(BaseModel):
    """Request to set budget limit"""
    budget_limit: float
    period: str = "monthly"  # daily, weekly, monthly
    model_id: Optional[str] = None  # None for global budget
    alert_threshold: float = 80.0  # percentage


class CostSummaryRequest(BaseModel):
    """Request for cost summary"""
    model_id: Optional[str] = None
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None  # ISO format


class CostComparisonRequest(BaseModel):
    """Request for cost comparison"""
    model_ids: List[str]


class UptimeEventRequest(BaseModel):
    """Request to record an uptime event"""
    status: str  # online, offline, degraded, unknown
    response_time: Optional[float] = None  # Response time in milliseconds
    error_message: Optional[str] = None
    check_type: str = "health_check"  # health_check, request_success, request_failure


class UptimeStatsRequest(BaseModel):
    """Request for uptime statistics"""
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None  # ISO format


class OutageHistoryRequest(BaseModel):
    """Request for outage history"""
    model_id: Optional[str] = None
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None  # ISO format


# Dependency to get Ollama service
def get_ollama_service() -> OllamaService:
    """Get Ollama service instance"""
    return OllamaService()


# Dependency to get MCP Compatibility service
def get_mcp_compatibility_service() -> MCPCompatibilityService:
    """Get MCP Compatibility service instance"""
    from pathlib import Path
    compatibility_data_path = Path("configs/mcp_compatibility.json")
    return MCPCompatibilityService(compatibility_data_path)


# Dependency to get Model Filter service
def get_model_filter_service() -> ModelFilterService:
    """Get Model Filter service instance"""
    return ModelFilterService()


# Dependency to get Performance Monitor service
def get_performance_monitor_service() -> PerformanceMonitorService:
    """Get Performance Monitor service instance"""
    from pathlib import Path
    data_dir = Path("volumes/data/performance")
    return PerformanceMonitorService(data_dir)


# Dependency to get Cost Tracking service
def get_cost_tracking_service() -> CostTrackingService:
    """Get Cost Tracking service instance"""
    from pathlib import Path
    data_dir = Path("volumes/data/costs")
    return CostTrackingService(data_dir)


# Dependency to get Uptime Monitoring service
def get_uptime_monitoring_service() -> UptimeMonitoringService:
    """Get Uptime Monitoring service instance"""
    from pathlib import Path
    data_dir = Path("volumes/data/uptime")
    return UptimeMonitoringService(data_dir)


@router.get("")
async def list_models(
    service: ModelService = Depends(get_model_service)
) -> List[Dict[str, Any]]:
    """List all configured models"""
    return await service.list_models()


@router.post("/filter")
async def filter_models(
    request: ModelFilterRequest,
    service: ModelService = Depends(get_model_service),
    filter_service: ModelFilterService = Depends(get_model_filter_service)
) -> List[Dict[str, Any]]:
    """Filter models based on criteria"""
    try:
        # Get all models
        models = await service.list_models()
        
        # Create filter criteria
        safety_levels = None
        if request.safety_levels:
            safety_levels = [SafetyLevel(level) for level in request.safety_levels]
        
        criteria = FilterCriteria(
            providers=request.providers,
            statuses=request.statuses,
            capabilities=request.capabilities,
            safety_levels=safety_levels,
            tags=request.tags,
            search_query=request.search_query,
            min_rating=request.min_rating,
            max_cost=request.max_cost,
            updated_this_week=request.updated_this_week,
            updated_this_month=request.updated_this_month,
            stale_models=request.stale_models
        )
        
        # Load additional data for filtering
        performance_data = {}
        ratings_data = {}
        
        # Apply filters
        filtered_models = filter_service.filter_models(
            models=models,
            criteria=criteria,
            performance_data=performance_data,
            ratings_data=ratings_data
        )
        
        return filtered_models
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sort")
async def sort_models(
    request: ModelSortRequest,
    service: ModelService = Depends(get_model_service),
    filter_service: ModelFilterService = Depends(get_model_filter_service)
) -> List[Dict[str, Any]]:
    """Sort models based on criteria"""
    try:
        # Get all models
        models = await service.list_models()
        
        # Create sort criteria
        sort_option = SortOption(request.sort_by)
        direction = SortDirection(request.direction)
        secondary_sort = SortOption(request.secondary_sort) if request.secondary_sort else None
        
        criteria = SortCriteria(
            option=sort_option,
            direction=direction,
            secondary_sort=secondary_sort
        )
        
        # Load additional data for sorting
        performance_data = {}
        ratings_data = {}
        
        # Apply sorting
        sorted_models = filter_service.sort_models(
            models=models,
            criteria=criteria,
            performance_data=performance_data,
            ratings_data=ratings_data
        )
        
        return sorted_models
        
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search")
async def search_models(
    request: ModelSearchRequest,
    service: ModelService = Depends(get_model_service),
    filter_service: ModelFilterService = Depends(get_model_filter_service)
) -> List[Dict[str, Any]]:
    """Search models using text query"""
    try:
        # Get all models
        models = await service.list_models()
        
        # Apply search
        search_results = filter_service.search_models(
            models=models,
            query=request.query,
            search_fields=request.search_fields
        )
        
        return search_results
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/filter-options")
async def get_filter_options(
    service: ModelService = Depends(get_model_service),
    filter_service: ModelFilterService = Depends(get_model_filter_service)
) -> Dict[str, List[str]]:
    """Get available filter options based on current models"""
    try:
        # Get all models
        models = await service.list_models()
        
        # Get filter options
        options = filter_service.get_filter_options(models)
        
        return options
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/ratings")
async def get_model_ratings(
    model_id: str,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Get rating data for a specific model"""
    try:
        model_with_metrics = await service.get_model_with_metrics(model_id)
        if model_with_metrics.model.ratings:
            return model_with_metrics.model.ratings.to_dict()
        else:
            # Return default ratings if none exist
            return {
                "speed": 3.0,
                "quality": 3.0,
                "cost_effectiveness": 3.0,
                "reliability": 3.0,
                "safety": 3.0,
                "mcp_compatibility": 3.0,
                "last_updated": None
            }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{model_id}/metrics")
async def get_model_metrics(
    model_id: str,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Get performance metrics for a specific model"""
    try:
        model_with_metrics = await service.get_model_with_metrics(model_id)
        if model_with_metrics.metrics:
            return model_with_metrics.metrics.to_dict()
        else:
            # Return empty metrics if none exist
            return {
                "response_time_avg": 0.0,
                "tokens_per_second": 0.0,
                "cost_per_1k_tokens": 0.0,
                "success_rate": 0.0,
                "uptime_percentage": 0.0,
                "total_requests": 0,
                "monthly_cost": 0.0,
                "timestamp": None
            }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/recommendations")
async def get_model_recommendations(
    request: ModelRecommendationRequest,
    service: ModelService = Depends(get_model_service)
) -> List[Dict[str, Any]]:
    """Get model recommendations for task-based suggestions"""
    try:
        recommendations = await service.suggest_models_for_task(
            task_type=request.task_type,
            requirements=request.requirements
        )
        return [rec.to_dict() for rec in recommendations]
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Ollama Integration Endpoints

@router.get("/ollama/models")
async def browse_ollama_models(
    search: Optional[str] = None,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> List[Dict[str, Any]]:
    """Browse available Ollama models"""
    try:
        models = await ollama_service.list_available_models(search=search)
        return [model.to_dict() for model in models]
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ollama/installed")
async def list_installed_ollama_models(
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> List[Dict[str, Any]]:
    """List currently installed Ollama models"""
    try:
        return await ollama_service.list_installed_models()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ollama/install")
async def install_ollama_model(
    request: OllamaInstallRequest,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """Install an Ollama model"""
    try:
        return await ollama_service.install_model(request.model_name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ollama/health")
async def check_ollama_health(
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """Check Ollama service health"""
    try:
        return await ollama_service.check_health()
    except ValidationError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/ollama/status")
async def check_ollama_status(
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """Check Ollama service status (alias for health check)"""
    try:
        return await ollama_service.check_health()
    except ValidationError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/ollama/models/{model_name}")
async def get_ollama_model_info(
    model_name: str,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """Get detailed information about an Ollama model"""
    try:
        return await ollama_service.get_model_info(model_name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Enhanced Ollama Catalog Endpoints

@router.get("/ollama/catalog")
async def get_ollama_catalog(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """
    Fetch Ollama model catalog with search and pagination.
    
    Query Parameters:
    - search: Optional search term to filter models by name, tags, or description
    - page: Page number (default: 1)
    - page_size: Number of models per page (default: 20, max: 100)
    
    Returns:
    - models: List of models for the current page
    - total: Total number of models matching the search
    - page: Current page number
    - page_size: Number of models per page
    - total_pages: Total number of pages
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise ValidationError("Page number must be >= 1", field="page")
        if page_size < 1 or page_size > 100:
            raise ValidationError("Page size must be between 1 and 100", field="page_size")
        
        # Fetch catalog from registry
        catalog = await ollama_service.fetch_model_catalog(search=search)
        
        # Calculate pagination
        total_models = len(catalog)
        total_pages = (total_models + page_size - 1) // page_size  # Ceiling division
        
        # Validate page number
        if page > total_pages and total_models > 0:
            raise ValidationError(f"Page {page} exceeds total pages {total_pages}", field="page")
        
        # Slice for current page
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_models = catalog[start_idx:end_idx]
        
        return {
            "models": page_models,
            "total": total_models,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch Ollama catalog: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalog: {str(e)}")


@router.get("/ollama/models/{model_name}/tags")
async def get_ollama_model_tags(
    model_name: str,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """
    List all available tags/versions for a specific Ollama model.
    
    Returns:
    - model_name: Name of the model
    - tags: List of available tags with metadata (size, parameters, quantization)
    - total_tags: Total number of tags available
    """
    try:
        # Get tags from service
        tags = await ollama_service.list_available_tags(model_name)
        
        return {
            "model_name": model_name,
            "tags": tags,
            "total_tags": len(tags)
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch tags for {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tags: {str(e)}")


class OllamaPullRequest(BaseModel):
    """Request to pull an Ollama model"""
    model_name: str
    tag: str = "latest"


@router.post("/ollama/pull")
async def initiate_ollama_pull(
    request: OllamaPullRequest,
    ollama_service: OllamaService = Depends(get_ollama_service)
) -> Dict[str, Any]:
    """
    Initiate an Ollama model download.
    
    This endpoint starts the download process and returns immediately.
    Progress updates are streamed via WebSocket at /ollama/pull/ws/{session_id}
    
    Request Body:
    - model_name: Name of the model to pull (e.g., "llama3.2")
    - tag: Specific tag/version to pull (default: "latest")
    
    Returns:
    - session_id: Unique session ID for tracking this download
    - model_name: Full model name with tag
    - status: Initial status ("initiated")
    - message: Status message
    """
    try:
        import uuid
        
        # Generate unique session ID for this pull operation
        session_id = str(uuid.uuid4())
        full_model_name = f"{request.model_name}:{request.tag}"
        
        # Store session info (in a real implementation, this would be in Redis or similar)
        # For now, we'll just return the session ID and let the WebSocket handle the actual pull
        
        return {
            "session_id": session_id,
            "model_name": full_model_name,
            "status": "initiated",
            "message": f"Download initiated for {full_model_name}. Connect to WebSocket for progress updates.",
            "websocket_url": f"/api/models/ollama/pull/ws/{session_id}"
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to initiate pull for {request.model_name}:{request.tag}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate pull: {str(e)}")


# WebSocket Connection Manager for Ollama Pull Progress
class OllamaPullConnectionManager:
    """Manages WebSocket connections for Ollama model pull progress"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect a WebSocket client for a specific session"""
        await websocket.accept()
        async with self.lock:
            self.active_connections[session_id] = websocket
    
    async def disconnect(self, session_id: str):
        """Disconnect a WebSocket client"""
        async with self.lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
    
    async def send_update(self, session_id: str, message: Dict[str, Any]):
        """Send a progress update to a specific session"""
        async with self.lock:
            if session_id in self.active_connections:
                try:
                    await self.active_connections[session_id].send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send update to session {session_id}: {e}")
                    # Remove disconnected client
                    del self.active_connections[session_id]


# Global pull connection manager
pull_manager = OllamaPullConnectionManager()


@router.websocket("/ollama/pull/ws/{session_id}")
async def websocket_ollama_pull_progress(
    websocket: WebSocket,
    session_id: str,
    model_name: str,
    tag: str = "latest",
    ollama_service: OllamaService = Depends(get_ollama_service),
    service: ModelService = Depends(get_model_service)
):
    """
    WebSocket endpoint for streaming Ollama model download progress.
    
    Query Parameters:
    - model_name: Name of the model to pull (e.g., "llama3.2")
    - tag: Specific tag/version to pull (default: "latest")
    
    Sends progress updates with:
    - status: Current status (starting, downloading, extracting, complete, error)
    - progress: Progress percentage (0-100)
    - downloaded_bytes: Bytes downloaded so far
    - total_bytes: Total bytes to download
    - download_speed: Current download speed
    - eta: Estimated time remaining
    - message: Human-readable status message
    """
    await pull_manager.connect(session_id, websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected, starting download..."
        })
        
        # Start the pull operation and stream progress
        async for progress_update in ollama_service.pull_model_with_progress(
            model_name=model_name,
            tag=tag,
            websocket_manager=pull_manager,
            session_id=session_id
        ):
            # Progress updates are already sent by the service via pull_manager
            # Check if download is complete
            if progress_update.get("status") == "complete":
                # Add model to configuration
                try:
                    model_config = {
                        "name": f"{model_name.title()} {tag}",
                        "provider": "ollama",
                        "model_id": f"{model_name}:{tag}",
                        "temperature": 0.7,
                        "max_tokens": 4096,
                        "description": f"Ollama model {model_name}:{tag}",
                        "is_default": False
                    }
                    
                    created_model = await service.create_model(model_config)
                    
                    # Send completion message with model info
                    await websocket.send_json({
                        "type": "model_added",
                        "model": created_model,
                        "message": f"Model {model_name}:{tag} successfully added to configuration"
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to add model to configuration: {e}")
                    await websocket.send_json({
                        "type": "warning",
                        "message": f"Model downloaded but failed to add to configuration: {str(e)}"
                    })
                
                break
            
            elif progress_update.get("status") == "error":
                # Error occurred, break the loop
                break
        
        # Send final completion message
        await websocket.send_json({
            "type": "complete",
            "session_id": session_id,
            "message": "Download process completed"
        })
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        await pull_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error in ollama_pull_progress: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Error during download: {str(e)}"
            })
        except:
            pass
        await pull_manager.disconnect(session_id)
    finally:
        await pull_manager.disconnect(session_id)


@router.post("")
async def create_model(
    model: Model,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Create a new model configuration"""
    try:
        return await service.create_model(model.dict())
    except (ValidationError, ConflictError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{model_id}")
async def update_model(
    model_id: str,
    model: ModelUpdate,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Update a model configuration"""
    try:
        return await service.update_model(model_id, model.dict())
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, str]:
    """Delete a model configuration"""
    try:
        return await service.delete_model(model_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: str,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Set a model as the default"""
    try:
        return await service.set_default_model(model_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# MCP Compatibility Endpoints

@router.get("/{model_id}/mcp-compatibility")
async def get_mcp_compatibility(
    model_id: str,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Get MCP compatibility data for a specific model"""
    try:
        compatibility_matrix = await service.get_compatibility_matrix()
        model_compatibility = compatibility_matrix.get(model_id)
        
        if model_compatibility:
            return model_compatibility.to_dict()
        else:
            # Return empty compatibility data if none exists
            return {
                "reliability_score": 0.0,
                "tested_categories": [],
                "success_rates": {}
            }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{model_id}/test-mcp-compatibility")
async def test_mcp_compatibility(
    model_id: str,
    request: MCPCompatibilityTestRequest,
    service: ModelService = Depends(get_model_service),
    mcp_service: MCPCompatibilityService = Depends(get_mcp_compatibility_service)
) -> Dict[str, Any]:
    """Test MCP compatibility for a specific model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Run compatibility tests
        compatibility_matrix = await mcp_service.test_model_compatibility(
            model_id=model_id,
            categories=request.categories
        )
        
        # Update model service with results
        await service.update_mcp_compatibility(model_id, compatibility_matrix)
        
        return compatibility_matrix.to_dict()
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp-compatibility/matrix")
async def get_full_compatibility_matrix(
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Get complete MCP compatibility matrix for all models"""
    try:
        compatibility_matrix = await service.get_compatibility_matrix()
        return {
            model_id: matrix.to_dict() 
            for model_id, matrix in compatibility_matrix.items()
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/mcp-compatibility/history")
async def get_mcp_compatibility_history(
    model_id: str,
    days: int = 30,
    mcp_service: MCPCompatibilityService = Depends(get_mcp_compatibility_service)
) -> List[Dict[str, Any]]:
    """Get MCP compatibility test history for a model"""
    try:
        return await mcp_service.get_compatibility_history(model_id, days)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mcp-compatibility/recommendations")
async def get_mcp_model_recommendations(
    request: MCPRecommendationRequest,
    mcp_service: MCPCompatibilityService = Depends(get_mcp_compatibility_service)
) -> List[Dict[str, Any]]:
    """Get model recommendations based on MCP compatibility requirements"""
    try:
        return await mcp_service.get_model_recommendations(
            required_categories=request.required_categories,
            min_reliability=request.min_reliability
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export")
async def export_models(
    request: ModelExportRequest,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Export model configurations to YAML or JSON format"""
    try:
        # Get models to export
        if request.model_ids:
            models = []
            for model_id in request.model_ids:
                try:
                    model = await service.get_model(model_id)
                    models.append(model)
                except NotFoundError:
                    continue  # Skip missing models
        else:
            models = await service.list_models()
        
        # Prepare export data
        export_data = {
            "models": [],
            "exported_at": datetime.utcnow().isoformat(),
            "format_version": "1.0",
            "adcl_compliant": True
        }
        
        for model in models:
            model_config = {
                "id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
                "model_id": model["model_id"],
                "temperature": model.get("temperature", 0.7),
                "max_tokens": model.get("max_tokens", 4096),
                "description": model.get("description", ""),
                "is_default": model.get("is_default", False)
            }
            
            # Add enhanced fields if present
            if model.get("capabilities"):
                model_config["capabilities"] = model["capabilities"]
            if model.get("safety_level"):
                model_config["safety_level"] = model["safety_level"]
            if model.get("mcp_compatibility"):
                model_config["mcp_compatibility"] = model["mcp_compatibility"]
            if model.get("ratings"):
                model_config["ratings"] = model["ratings"]
            if model.get("benchmarks"):
                # Include benchmarks with None values preserved for proper validation
                # The schema allows None values using oneOf: [{"type": "null"}, {"type": "number"}]
                model_config["benchmarks"] = model["benchmarks"]
            
            # Handle API keys
            if request.include_sensitive and model.get("api_key"):
                model_config["api_key"] = "***MASKED***"  # Never export actual keys
            
            # Add API key environment variable reference
            if model["provider"] == "anthropic":
                model_config["api_key_env"] = "ANTHROPIC_API_KEY"
            elif model["provider"] == "openai":
                model_config["api_key_env"] = "OPENAI_API_KEY"
            elif model["provider"] == "ollama":
                model_config["api_key_env"] = "OLLAMA_API_KEY"
            else:
                model_config["api_key_env"] = f"{model['provider'].upper()}_API_KEY"
            
            export_data["models"].append(model_config)
        
        # Format output
        if request.format.lower() == "json":
            import json
            formatted_data = json.dumps(export_data, indent=2, sort_keys=False)
            content_type = "application/json"
            filename = f"models_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            import yaml
            formatted_data = yaml.safe_dump(export_data, default_flow_style=False, sort_keys=False)
            content_type = "application/x-yaml"
            filename = f"models_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.yaml"
        
        return {
            "success": True,
            "format": request.format,
            "model_count": len(export_data["models"]),
            "content": formatted_data,
            "content_type": content_type,
            "filename": filename,
            "exported_at": export_data["exported_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/import")
async def import_models(
    request: ModelImportRequest,
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Import model configurations from YAML or JSON format"""
    try:
        # Parse the configuration data
        if request.format.lower() == "json":
            import json
            config_data = json.loads(request.config_data)
        else:
            import yaml
            config_data = yaml.safe_load(request.config_data)
        
        # Validate structure
        if not isinstance(config_data, dict):
            raise ValidationError("Invalid configuration format: expected object/dictionary", field="config_data")
        
        if "models" not in config_data:
            raise ValidationError("Invalid configuration format: missing 'models' section", field="config_data")
        
        models_to_import = config_data["models"]
        if not isinstance(models_to_import, list):
            raise ValidationError("Invalid configuration format: 'models' must be a list", field="config_data")
        
        # Validation results
        validation_results = {
            "valid_models": [],
            "invalid_models": [],
            "existing_models": [],
            "new_models": []
        }
        
        # Get existing models for conflict checking
        existing_models = await service.list_models()
        existing_ids = {model["id"] for model in existing_models}
        
        # Validate each model
        for i, model_config in enumerate(models_to_import):
            try:
                # Basic validation
                required_fields = ["name", "provider", "model_id"]
                for field in required_fields:
                    if field not in model_config:
                        raise ValidationError(f"Missing required field: {field}", field=field)
                
                # Generate ID if not provided
                if "id" not in model_config:
                    slug = f"{model_config['provider']}-{model_config['model_id']}".replace("/", "-").replace("_", "-").lower()
                    while "--" in slug:
                        slug = slug.replace("--", "-")
                    model_config["id"] = slug
                
                # Check for conflicts
                if model_config["id"] in existing_ids:
                    validation_results["existing_models"].append({
                        "index": i,
                        "id": model_config["id"],
                        "name": model_config["name"],
                        "action": "skip" if not request.overwrite_existing else "overwrite"
                    })
                    if not request.overwrite_existing:
                        continue
                else:
                    validation_results["new_models"].append({
                        "index": i,
                        "id": model_config["id"],
                        "name": model_config["name"]
                    })
                
                # Validate model configuration
                validate_single_model(model_config)
                
                validation_results["valid_models"].append({
                    "index": i,
                    "id": model_config["id"],
                    "name": model_config["name"],
                    "provider": model_config["provider"]
                })
                
            except Exception as e:
                validation_results["invalid_models"].append({
                    "index": i,
                    "error": str(e),
                    "model": model_config.get("name", f"Model {i}")
                })
        
        # If validation only, return results
        if request.validate_only:
            return {
                "success": True,
                "validation_only": True,
                "results": validation_results,
                "total_models": len(models_to_import),
                "valid_count": len(validation_results["valid_models"]),
                "invalid_count": len(validation_results["invalid_models"]),
                "existing_count": len(validation_results["existing_models"]),
                "new_count": len(validation_results["new_models"])
            }
        
        # Import valid models
        imported_models = []
        import_errors = []
        
        for model_info in validation_results["valid_models"]:
            try:
                model_config = models_to_import[model_info["index"]]
                
                # Remove API key if present (security)
                if "api_key" in model_config:
                    del model_config["api_key"]
                
                # Check if model exists
                if model_config["id"] in existing_ids and request.overwrite_existing:
                    # Update existing model
                    updated_model = await service.update_model(model_config["id"], model_config)
                    imported_models.append({
                        "id": updated_model["id"],
                        "name": updated_model["name"],
                        "action": "updated"
                    })
                elif model_config["id"] not in existing_ids:
                    # Create new model
                    created_model = await service.create_model(model_config)
                    imported_models.append({
                        "id": created_model["id"],
                        "name": created_model["name"],
                        "action": "created"
                    })
                
            except Exception as e:
                import_errors.append({
                    "model": model_info["name"],
                    "error": str(e)
                })
        
        return {
            "success": True,
            "validation_only": False,
            "results": validation_results,
            "imported_models": imported_models,
            "import_errors": import_errors,
            "total_models": len(models_to_import),
            "imported_count": len(imported_models),
            "error_count": len(import_errors)
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# Performance Monitoring Endpoints

@router.post("/{model_id}/track-performance")
async def track_model_performance(
    model_id: str,
    request: PerformanceTrackingRequest,
    service: ModelService = Depends(get_model_service),
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> Dict[str, Any]:
    """Track performance metrics for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Track the performance
        await monitor_service.track_model_usage(
            model_id=model_id,
            response_time=request.response_time,
            tokens_generated=request.tokens_generated,
            cost=request.cost,
            success=request.success
        )
        
        # Get updated metrics
        current_metrics = await monitor_service.get_current_metrics(model_id)
        
        return {
            "success": True,
            "model_id": model_id,
            "metrics": current_metrics.to_dict() if current_metrics else None
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/performance-history")
async def get_performance_history(
    model_id: str,
    timeframe: str = "24h",
    service: ModelService = Depends(get_model_service),
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> List[Dict[str, Any]]:
    """Get historical performance data for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Get historical data
        historical_data = await monitor_service.get_historical_metrics(model_id, timeframe)
        
        return historical_data
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/alerts")
async def get_model_alerts(
    model_id: str,
    service: ModelService = Depends(get_model_service),
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> List[Dict[str, Any]]:
    """Get current alerts for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Get alerts
        alerts = await monitor_service.get_model_alerts(model_id)
        
        return [alert.to_dict() for alert in alerts]
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{model_id}/clear-alert")
async def clear_model_alert(
    model_id: str,
    request: AlertClearRequest,
    service: ModelService = Depends(get_model_service),
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> Dict[str, Any]:
    """Clear a specific alert for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Clear the alert
        cleared = await monitor_service.clear_alert(model_id, request.alert_type)
        
        return {
            "success": cleared,
            "model_id": model_id,
            "alert_type": request.alert_type,
            "message": "Alert cleared successfully" if cleared else "Alert not found"
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/uptime-stats")
async def get_uptime_statistics(
    model_id: str,
    timeframe: str = "24h",
    service: ModelService = Depends(get_model_service),
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> Dict[str, Any]:
    """Get uptime statistics for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Get uptime statistics
        uptime_stats = await monitor_service.get_uptime_statistics(model_id, timeframe)
        
        return {
            "model_id": model_id,
            "timeframe": timeframe,
            **uptime_stats
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/performance/alerts")
async def get_all_alerts(
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service)
) -> List[Dict[str, Any]]:
    """Get all current alerts across all models"""
    try:
        alerts = await monitor_service.check_performance_thresholds()
        return [alert.to_dict() for alert in alerts]
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Cost Tracking and Budget Management Endpoints

@router.post("/{model_id}/track-cost")
async def track_model_cost(
    model_id: str,
    request: CostTrackingRequest,
    service: ModelService = Depends(get_model_service),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> Dict[str, Any]:
    """Track cost for a model request"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Track the cost
        cost_entry = await cost_service.track_cost(
            model_id=model_id,
            tokens_input=request.tokens_input,
            tokens_output=request.tokens_output,
            cost_input=request.cost_input,
            cost_output=request.cost_output,
            provider=request.provider,
            request_id=request.request_id,
            user_id=request.user_id
        )
        
        return {
            "success": True,
            "model_id": model_id,
            "cost_entry": cost_entry.to_dict()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/cost-summary")
async def get_model_cost_summary(
    model_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: ModelService = Depends(get_model_service),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> List[Dict[str, Any]]:
    """Get cost summary for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        
        # Get cost summary
        summaries = await cost_service.get_cost_summary(
            model_id=model_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return [summary.to_dict() for summary in summaries]
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{model_id}/set-budget")
async def set_model_budget(
    model_id: str,
    request: BudgetSetRequest,
    service: ModelService = Depends(get_model_service),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> Dict[str, Any]:
    """Set budget limit for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Set budget
        budget_id = f"{model_id}_{request.period}"
        budget = await cost_service.set_budget(
            budget_id=budget_id,
            budget_limit=request.budget_limit,
            period=request.period,
            model_id=model_id,
            alert_threshold=request.alert_threshold
        )
        
        return {
            "success": True,
            "budget": budget.to_dict()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/budget-status")
async def get_model_budget_status(
    model_id: str,
    period: str = "monthly",
    service: ModelService = Depends(get_model_service),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> Dict[str, Any]:
    """Get budget status for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Get budget status
        budget_id = f"{model_id}_{period}"
        budget = await cost_service.get_budget_status(budget_id)
        
        if budget:
            return {
                "model_id": model_id,
                "budget": budget.to_dict()
            }
        else:
            return {
                "model_id": model_id,
                "budget": None,
                "message": "No budget set for this model"
            }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/cost-recommendations")
async def get_cost_optimization_recommendations(
    model_id: str,
    service: ModelService = Depends(get_model_service),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> List[Dict[str, Any]]:
    """Get cost optimization recommendations for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Get recommendations
        recommendations = await cost_service.get_cost_optimization_recommendations(model_id)
        
        return recommendations
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cost-comparison")
async def compare_model_costs(
    request: CostComparisonRequest,
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> Dict[str, Any]:
    """Compare costs between multiple models"""
    try:
        comparison = await cost_service.get_cost_comparison(request.model_ids)
        return comparison
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/set-global-budget")
async def set_global_budget(
    request: BudgetSetRequest,
    cost_service: CostTrackingService = Depends(get_cost_tracking_service)
) -> Dict[str, Any]:
    """Set global budget limit across all models"""
    try:
        budget_id = f"global_{request.period}"
        budget = await cost_service.set_budget(
            budget_id=budget_id,
            budget_limit=request.budget_limit,
            period=request.period,
            model_id=None,  # Global budget
            alert_threshold=request.alert_threshold
        )
        
        return {
            "success": True,
            "budget": budget.to_dict()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-operations")
async def batch_model_operations(
    operation: str,
    model_ids: List[str],
    service: ModelService = Depends(get_model_service)
) -> Dict[str, Any]:
    """Perform batch operations on multiple models"""
    try:
        results = {
            "success": [],
            "errors": [],
            "operation": operation
        }
        
        if operation == "delete":
            for model_id in model_ids:
                try:
                    result = await service.delete_model(model_id)
                    results["success"].append({
                        "model_id": model_id,
                        "result": result
                    })
                except Exception as e:
                    results["errors"].append({
                        "model_id": model_id,
                        "error": str(e)
                    })
        
        elif operation == "export":
            # Use the export functionality
            export_request = ModelExportRequest(model_ids=model_ids)
            return await export_models(export_request, service)
        
        else:
            raise ValidationError(f"Unsupported batch operation: {operation}", field="operation")
        
        return {
            "success": True,
            "operation": operation,
            "total_models": len(model_ids),
            "success_count": len(results["success"]),
            "error_count": len(results["errors"]),
            "results": results
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch operation failed: {str(e)}")


# Uptime Monitoring and Availability Endpoints

@router.post("/{model_id}/record-uptime")
async def record_uptime_event(
    model_id: str,
    request: UptimeEventRequest,
    service: ModelService = Depends(get_model_service),
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> Dict[str, Any]:
    """Record an uptime event for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Parse status
        from app.services.uptime_monitoring_service import ServiceStatus
        status = ServiceStatus(request.status)
        
        # Record uptime event
        event = await uptime_service.record_uptime_event(
            model_id=model_id,
            status=status,
            response_time=request.response_time,
            error_message=request.error_message,
            check_type=request.check_type
        )
        
        return {
            "success": True,
            "event": event.to_dict()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/uptime-stats")
async def get_model_uptime_stats(
    model_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: ModelService = Depends(get_model_service),
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> Dict[str, Any]:
    """Get uptime statistics for a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        
        # Get uptime stats
        stats = await uptime_service.get_uptime_stats(
            model_id=model_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return stats.to_dict()
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{model_id}/current-status")
async def get_model_current_status(
    model_id: str,
    service: ModelService = Depends(get_model_service),
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> Dict[str, Any]:
    """Get current status of a model"""
    try:
        # Verify model exists
        await service.get_model(model_id)
        
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Get current status
        status = await uptime_service.get_current_status(model_id)
        
        return {
            "model_id": model_id,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/uptime/all-statuses")
async def get_all_model_statuses(
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> Dict[str, Any]:
    """Get current status of all monitored models"""
    try:
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Get all statuses
        statuses = await uptime_service.get_all_statuses()
        
        return {
            "statuses": {
                model_id: status.value
                for model_id, status in statuses.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/uptime/active-outages")
async def get_active_outages(
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> List[Dict[str, Any]]:
    """Get all currently active outages"""
    try:
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Get active outages
        outages = await uptime_service.get_active_outages()
        
        return [outage.to_dict() for outage in outages]
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/uptime/outage-history")
async def get_outage_history(
    model_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> List[Dict[str, Any]]:
    """Get outage history for models"""
    try:
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        
        # Get outage history
        outages = await uptime_service.get_outage_history(
            model_id=model_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return [outage.to_dict() for outage in outages]
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/uptime/resolve-outage/{outage_id}")
async def resolve_outage(
    outage_id: str,
    uptime_service: UptimeMonitoringService = Depends(get_uptime_monitoring_service)
) -> Dict[str, Any]:
    """Manually resolve an outage"""
    try:
        # Initialize uptime service if needed
        await uptime_service.initialize()
        
        # Resolve outage
        resolved = await uptime_service.resolve_outage(outage_id)
        
        if resolved:
            return {
                "success": True,
                "message": f"Outage {outage_id} resolved successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Outage {outage_id} not found")
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# WebSocket endpoint for real-time model monitoring
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import asyncio


class ModelMonitoringConnectionManager:
    """Manages WebSocket connections for real-time model monitoring"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, model_id: Optional[str] = None):
        """Connect a WebSocket client"""
        await websocket.accept()
        
        async with self.lock:
            if model_id:
                if model_id not in self.active_connections:
                    self.active_connections[model_id] = set()
                self.active_connections[model_id].add(websocket)
            else:
                # Global monitoring (all models)
                if "global" not in self.active_connections:
                    self.active_connections["global"] = set()
                self.active_connections["global"].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, model_id: Optional[str] = None):
        """Disconnect a WebSocket client"""
        async with self.lock:
            if model_id and model_id in self.active_connections:
                self.active_connections[model_id].discard(websocket)
                if not self.active_connections[model_id]:
                    del self.active_connections[model_id]
            elif "global" in self.active_connections:
                self.active_connections["global"].discard(websocket)
                if not self.active_connections["global"]:
                    del self.active_connections["global"]
    
    async def broadcast_to_model(self, model_id: str, message: Dict[str, Any]):
        """Broadcast a message to all clients monitoring a specific model"""
        async with self.lock:
            # Send to model-specific connections
            if model_id in self.active_connections:
                disconnected = set()
                for connection in self.active_connections[model_id]:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        disconnected.add(connection)
                
                # Clean up disconnected clients
                for connection in disconnected:
                    self.active_connections[model_id].discard(connection)
            
            # Also send to global monitoring connections
            if "global" in self.active_connections:
                disconnected = set()
                for connection in self.active_connections["global"]:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        disconnected.add(connection)
                
                # Clean up disconnected clients
                for connection in disconnected:
                    self.active_connections["global"].discard(connection)
    
    async def broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast an alert to all connected clients"""
        message = {
            "type": "alert",
            "data": alert,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with self.lock:
            # Send to all connections
            all_connections = set()
            for connections in self.active_connections.values():
                all_connections.update(connections)
            
            disconnected = set()
            for connection in all_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected clients
            for model_id, connections in list(self.active_connections.items()):
                for connection in disconnected:
                    connections.discard(connection)
                if not connections:
                    del self.active_connections[model_id]


# Global connection manager
monitoring_manager = ModelMonitoringConnectionManager()


@router.websocket("/ws/monitor")
async def websocket_monitor_all_models(
    websocket: WebSocket,
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service),
    service: ModelService = Depends(get_model_service)
):
    """
    WebSocket endpoint for real-time monitoring of all models.
    
    Sends periodic updates with:
    - Performance metrics
    - Alerts
    - Status changes
    """
    await monitoring_manager.connect(websocket, model_id=None)
    
    try:
        # Send initial state
        models = await service.list_models()
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "models": models,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Start monitoring loop
        while True:
            try:
                # Wait for client messages (ping/pong, config changes)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                
                # Handle client requests
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "request_update":
                    # Send current metrics for all models
                    for model in models:
                        model_id = model["id"]
                        try:
                            metrics = await monitor_service.get_current_metrics(model_id)
                            if metrics:
                                await websocket.send_json({
                                    "type": "metrics_update",
                                    "model_id": model_id,
                                    "data": metrics.to_dict(),
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                        except Exception as e:
                            logger.warning(f"Failed to get metrics for {model_id}: {e}")
                
            except asyncio.TimeoutError:
                # Periodic update (every 5 seconds)
                # Check for alerts
                alerts = await monitor_service.check_performance_thresholds()
                if alerts:
                    for alert in alerts:
                        await monitoring_manager.broadcast_alert(alert.to_dict())
                
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
    except WebSocketDisconnect:
        await monitoring_manager.disconnect(websocket, model_id=None)
    except Exception as e:
        logger.error(f"WebSocket error in monitor_all_models: {e}")
        await monitoring_manager.disconnect(websocket, model_id=None)


@router.websocket("/ws/monitor/{model_id}")
async def websocket_monitor_model(
    websocket: WebSocket,
    model_id: str,
    monitor_service: PerformanceMonitorService = Depends(get_performance_monitor_service),
    service: ModelService = Depends(get_model_service)
):
    """
    WebSocket endpoint for real-time monitoring of a specific model.
    
    Sends periodic updates with:
    - Performance metrics
    - Alerts
    - Status changes
    """
    # Verify model exists
    try:
        model = await service.get_model(model_id)
    except NotFoundError:
        await websocket.close(code=1008, reason=f"Model {model_id} not found")
        return
    
    await monitoring_manager.connect(websocket, model_id=model_id)
    
    try:
        # Send initial state
        model_with_metrics = await service.get_model_with_metrics(model_id)
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "model": model_with_metrics.model.to_dict(),
                "metrics": model_with_metrics.metrics.to_dict() if model_with_metrics.metrics else None,
                "alerts": [alert.to_dict() for alert in model_with_metrics.alerts],
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        # Start monitoring loop
        while True:
            try:
                # Wait for client messages (ping/pong, config changes)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                
                # Handle client requests
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "request_update":
                    # Send current metrics
                    metrics = await monitor_service.get_current_metrics(model_id)
                    if metrics:
                        await websocket.send_json({
                            "type": "metrics_update",
                            "data": metrics.to_dict(),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
            except asyncio.TimeoutError:
                # Periodic update (every 5 seconds)
                # Get current metrics
                metrics = await monitor_service.get_current_metrics(model_id)
                if metrics:
                    await websocket.send_json({
                        "type": "metrics_update",
                        "data": metrics.to_dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Check for alerts
                alerts = await monitor_service.get_model_alerts(model_id)
                if alerts:
                    await websocket.send_json({
                        "type": "alerts_update",
                        "data": [alert.to_dict() for alert in alerts],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
    except WebSocketDisconnect:
        await monitoring_manager.disconnect(websocket, model_id=model_id)
    except Exception as e:
        logger.error(f"WebSocket error in monitor_model {model_id}: {e}")
        await monitoring_manager.disconnect(websocket, model_id=model_id)


# Helper function to broadcast metrics updates from other parts of the application
async def broadcast_metrics_update(model_id: str, metrics: PerformanceMetrics):
    """
    Broadcast metrics update to all connected WebSocket clients.
    
    This function can be called from other parts of the application
    (e.g., after tracking performance) to push updates to clients.
    """
    await monitoring_manager.broadcast_to_model(model_id, {
        "type": "metrics_update",
        "data": metrics.to_dict(),
        "timestamp": datetime.utcnow().isoformat()
    })


# Helper function to broadcast status changes
async def broadcast_status_change(model_id: str, old_status: str, new_status: str):
    """
    Broadcast model status change to all connected WebSocket clients.
    """
    await monitoring_manager.broadcast_to_model(model_id, {
        "type": "status_change",
        "data": {
            "model_id": model_id,
            "old_status": old_status,
            "new_status": new_status
        },
        "timestamp": datetime.utcnow().isoformat()
    })


# Helper function to broadcast alerts
async def broadcast_alert_notification(alert: Alert):
    """
    Broadcast alert to all connected WebSocket clients.
    """
    await monitoring_manager.broadcast_alert(alert.to_dict())


# API Key Management Endpoints
from app.services.api_key_manager_service import APIKeyManagerService, KeyStatus


def get_api_key_manager_service() -> APIKeyManagerService:
    """Get API Key Manager service instance"""
    from pathlib import Path
    config_path = Path("configs/api_keys.json")
    return APIKeyManagerService(config_path)


class APIKeyAddRequest(BaseModel):
    """Request to add a new API key"""
    provider: str
    key_value: str
    priority: int = 0
    expires_at: Optional[str] = None  # ISO format


class APIKeyRemoveRequest(BaseModel):
    """Request to remove an API key"""
    key_id: str


class APIKeyStatusRequest(BaseModel):
    """Request for API key status"""
    provider: Optional[str] = None


@router.post("/api-keys/add")
async def add_api_key(
    request: APIKeyAddRequest,
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> Dict[str, Any]:
    """Add a new API key for a provider"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Parse expiration date if provided
        expires_at = None
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
        
        # Add the key
        api_key = await key_manager.add_key(
            provider=request.provider,
            key_value=request.key_value,
            priority=request.priority,
            expires_at=expires_at
        )
        
        return {
            "success": True,
            "key": api_key.to_dict()
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add API key: {str(e)}")


@router.delete("/api-keys/{key_id}")
async def remove_api_key(
    key_id: str,
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> Dict[str, Any]:
    """Remove an API key"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Remove the key
        removed = await key_manager.remove_key(key_id)
        
        if removed:
            return {
                "success": True,
                "message": f"API key {key_id} removed successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"API key {key_id} not found")
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove API key: {str(e)}")


@router.get("/api-keys/status")
async def get_api_keys_status(
    provider: Optional[str] = None,
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> Dict[str, Any]:
    """Get status of all API keys or keys for a specific provider"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Get key status
        status = await key_manager.get_key_status(provider)
        
        return status
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API key status: {str(e)}")


@router.get("/api-keys/expiring")
async def get_expiring_keys(
    days: int = 7,
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> List[Dict[str, Any]]:
    """Get API keys expiring within specified days"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Check for expiring keys
        expiring_keys = await key_manager.check_expiring_keys(days_threshold=days)
        
        return [key.to_dict() for key in expiring_keys]
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check expiring keys: {str(e)}")


@router.post("/api-keys/{key_id}/record-success")
async def record_key_success(
    key_id: str,
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> Dict[str, Any]:
    """Record successful API call for a key"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Record success
        await key_manager.record_success(key_id)
        await key_manager.save_keys()
        
        return {
            "success": True,
            "message": f"Recorded success for key {key_id}"
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record success: {str(e)}")


@router.post("/api-keys/{key_id}/record-error")
async def record_key_error(
    key_id: str,
    error_type: str = "general",
    key_manager: APIKeyManagerService = Depends(get_api_key_manager_service)
) -> Dict[str, Any]:
    """Record API call error for a key"""
    try:
        # Initialize key manager
        await key_manager.load_keys()
        
        # Record error
        await key_manager.record_error(key_id, error_type)
        await key_manager.save_keys()
        
        return {
            "success": True,
            "message": f"Recorded error for key {key_id}"
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record error: {str(e)}")
