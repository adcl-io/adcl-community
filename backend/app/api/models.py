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

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.model_service import ModelService
from app.core.dependencies import get_model_service
from app.core.errors import NotFoundError, ValidationError, ConflictError

router = APIRouter(prefix="/models", tags=["models"])


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


@router.get("")
async def list_models(
    service: ModelService = Depends(get_model_service)
) -> List[Dict[str, Any]]:
    """List all configured models"""
    return await service.list_models()


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
