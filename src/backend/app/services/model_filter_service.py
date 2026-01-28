# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Model Filter Service - Advanced filtering, sorting, and search functionality.

Provides comprehensive model management features including:
- Multi-criteria filtering (provider, status, capabilities, tags)
- Flexible sorting options (usage, cost, performance, alphabetical)
- Real-time search with debouncing support
- Filter combination and validation
"""

import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone

from app.core.logging import get_service_logger
from app.models.enhanced_models import EnhancedModelConfig, SafetyLevel, FunctionCallingSupport

logger = get_service_logger("model_filter")


class SortOption(str, Enum):
    """Available sorting options for models"""
    ALPHABETICAL = "alphabetical"
    USAGE = "usage"
    COST = "cost"
    PERFORMANCE = "performance"
    PROVIDER = "provider"
    STATUS = "status"
    RATING = "rating"
    LAST_UPDATED = "last_updated"  # Sort by last update timestamp


class SortDirection(str, Enum):
    """Sort direction"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class FilterCriteria:
    """Filter criteria for model search"""
    providers: Optional[List[str]] = None
    statuses: Optional[List[str]] = None  # configured, not_configured, active, error
    capabilities: Optional[List[str]] = None  # function_calling, vision, code_generation
    safety_levels: Optional[List[SafetyLevel]] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    min_rating: Optional[float] = None
    max_cost: Optional[float] = None
    updated_this_week: Optional[bool] = None  # Filter for models updated in last 7 days
    updated_this_month: Optional[bool] = None  # Filter for models updated in last 30 days
    stale_models: Optional[bool] = None  # Filter for models not updated in 90+ days
    
    def is_empty(self) -> bool:
        """Check if all filter criteria are empty"""
        return all([
            not self.providers,
            not self.statuses,
            not self.capabilities,
            not self.safety_levels,
            not self.tags,
            not self.search_query,
            self.min_rating is None,
            self.max_cost is None,
            self.updated_this_week is None,
            self.updated_this_month is None,
            self.stale_models is None
        ])


@dataclass
class SortCriteria:
    """Sort criteria for model ordering"""
    option: SortOption = SortOption.ALPHABETICAL
    direction: SortDirection = SortDirection.ASC
    secondary_sort: Optional[SortOption] = None


class ModelFilterService:
    """
    Service for filtering, sorting, and searching models.
    
    Provides advanced model management capabilities with support for:
    - Complex multi-criteria filtering
    - Flexible sorting with primary and secondary options
    - Real-time text search across multiple fields
    - Performance-optimized operations
    """
    
    def __init__(self):
        """Initialize the filter service"""
        logger.info("ModelFilterService initialized")
    
    def filter_models(
        self, 
        models: List[Dict[str, Any]], 
        criteria: FilterCriteria,
        performance_data: Optional[Dict[str, Dict[str, Any]]] = None,
        ratings_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter models based on provided criteria.
        
        Args:
            models: List of model configurations
            criteria: Filter criteria to apply
            performance_data: Optional performance metrics for cost filtering
            ratings_data: Optional ratings data for rating filtering
            
        Returns:
            Filtered list of models
        """
        if criteria.is_empty():
            return models
        
        filtered_models = models.copy()
        
        # Apply provider filter
        if criteria.providers:
            filtered_models = [
                model for model in filtered_models
                if model.get("provider") in criteria.providers
            ]
        
        # Apply status filter
        if criteria.statuses:
            filtered_models = [
                model for model in filtered_models
                if self._get_model_status(model) in criteria.statuses
            ]
        
        # Apply capabilities filter
        if criteria.capabilities:
            filtered_models = [
                model for model in filtered_models
                if self._model_has_capabilities(model, criteria.capabilities)
            ]
        
        # Apply safety level filter
        if criteria.safety_levels:
            filtered_models = [
                model for model in filtered_models
                if SafetyLevel(model.get("safety_level", "moderate")) in criteria.safety_levels
            ]
        
        # Apply tags filter (if tags are implemented in model data)
        if criteria.tags:
            filtered_models = [
                model for model in filtered_models
                if self._model_has_tags(model, criteria.tags)
            ]
        
        # Apply search query filter
        if criteria.search_query:
            filtered_models = [
                model for model in filtered_models
                if self._model_matches_search(model, criteria.search_query)
            ]
        
        # Apply rating filter
        if criteria.min_rating is not None and ratings_data:
            filtered_models = [
                model for model in filtered_models
                if self._model_meets_rating_threshold(model, criteria.min_rating, ratings_data)
            ]
        
        # Apply cost filter
        if criteria.max_cost is not None and performance_data:
            filtered_models = [
                model for model in filtered_models
                if self._model_meets_cost_threshold(model, criteria.max_cost, performance_data)
            ]
        
        # Apply timestamp filters
        if criteria.updated_this_week:
            filtered_models = [
                model for model in filtered_models
                if self._model_updated_within_days(model, 7)
            ]
        
        if criteria.updated_this_month:
            filtered_models = [
                model for model in filtered_models
                if self._model_updated_within_days(model, 30)
            ]
        
        if criteria.stale_models:
            filtered_models = [
                model for model in filtered_models
                if self._model_is_stale(model)
            ]
        
        logger.info(f"Filtered {len(models)} models to {len(filtered_models)} results")
        return filtered_models
    
    def sort_models(
        self,
        models: List[Dict[str, Any]],
        criteria: SortCriteria,
        performance_data: Optional[Dict[str, Dict[str, Any]]] = None,
        ratings_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sort models based on provided criteria.
        
        Args:
            models: List of model configurations
            criteria: Sort criteria to apply
            performance_data: Optional performance metrics for usage/cost sorting
            ratings_data: Optional ratings data for rating sorting
            
        Returns:
            Sorted list of models
        """
        if not models:
            return models
        
        # Create sort key function
        sort_key_func = self._create_sort_key_function(
            criteria, performance_data, ratings_data
        )
        
        # Sort models
        sorted_models = sorted(
            models,
            key=sort_key_func,
            reverse=(criteria.direction == SortDirection.DESC)
        )
        
        logger.info(f"Sorted {len(models)} models by {criteria.option.value} ({criteria.direction.value})")
        return sorted_models
    
    def search_models(
        self,
        models: List[Dict[str, Any]],
        query: str,
        search_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search models using text query across specified fields.
        
        Args:
            models: List of model configurations
            query: Search query string
            search_fields: Fields to search in (default: name, description, provider, model_id)
            
        Returns:
            Models matching the search query
        """
        if not query or not query.strip():
            return models
        
        if search_fields is None:
            search_fields = ["name", "description", "provider", "model_id"]
        
        query_lower = query.lower().strip()
        
        # Support for quoted exact matches
        exact_match = False
        if query_lower.startswith('"') and query_lower.endswith('"') and len(query_lower) > 2:
            query_lower = query_lower[1:-1]
            exact_match = True
        
        matching_models = []
        
        for model in models:
            if self._model_matches_query(model, query_lower, search_fields, exact_match):
                matching_models.append(model)
        
        logger.info(f"Search '{query}' found {len(matching_models)} matches")
        return matching_models
    
    def get_filter_options(
        self,
        models: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Get available filter options based on current models.
        
        Args:
            models: List of model configurations
            
        Returns:
            Dictionary of available filter options
        """
        providers = set()
        statuses = set()
        capabilities = set()
        safety_levels = set()
        
        for model in models:
            # Collect providers
            if model.get("provider"):
                providers.add(model["provider"])
            
            # Collect statuses
            statuses.add(self._get_model_status(model))
            
            # Collect capabilities
            model_capabilities = model.get("capabilities", {})
            if model_capabilities.get("function_calling") != "none":
                capabilities.add("function_calling")
            if model_capabilities.get("vision"):
                capabilities.add("vision")
            if model_capabilities.get("code_generation"):
                capabilities.add("code_generation")
            if model_capabilities.get("multimodal"):
                capabilities.add("multimodal")
            
            # Collect safety levels
            safety_levels.add(model.get("safety_level", "moderate"))
        
        return {
            "providers": sorted(list(providers)),
            "statuses": sorted(list(statuses)),
            "capabilities": sorted(list(capabilities)),
            "safety_levels": sorted(list(safety_levels))
        }
    
    # Private helper methods
    
    def _get_model_status(self, model: Dict[str, Any]) -> str:
        """Get standardized model status"""
        if model.get("configured"):
            return "configured"
        else:
            return "not_configured"
    
    def _model_has_capabilities(self, model: Dict[str, Any], required_capabilities: List[str]) -> bool:
        """Check if model has all required capabilities"""
        model_capabilities = model.get("capabilities", {})
        
        for capability in required_capabilities:
            if capability == "function_calling":
                if model_capabilities.get("function_calling") == "none":
                    return False
            elif capability == "vision":
                if not model_capabilities.get("vision", False):
                    return False
            elif capability == "code_generation":
                if not model_capabilities.get("code_generation", False):
                    return False
            elif capability == "multimodal":
                if not model_capabilities.get("multimodal", False):
                    return False
        
        return True
    
    def _model_has_tags(self, model: Dict[str, Any], required_tags: List[str]) -> bool:
        """Check if model has all required tags"""
        model_tags = model.get("tags", [])
        return all(tag in model_tags for tag in required_tags)
    
    def _model_matches_search(self, model: Dict[str, Any], query: str) -> bool:
        """Check if model matches search query"""
        search_fields = ["name", "description", "provider", "model_id"]
        return self._model_matches_query(model, query, search_fields, exact_match=False)
    
    def _model_matches_query(
        self, 
        model: Dict[str, Any], 
        query: str, 
        search_fields: List[str], 
        exact_match: bool = False
    ) -> bool:
        """Check if model matches query in specified fields"""
        for field in search_fields:
            field_value = str(model.get(field, "")).lower()
            
            if exact_match:
                if query in field_value:
                    return True
            else:
                # Support partial matching and word boundaries
                if query in field_value or any(word in field_value for word in query.split()):
                    return True
        
        return False
    
    def _model_meets_rating_threshold(
        self, 
        model: Dict[str, Any], 
        min_rating: float, 
        ratings_data: Dict[str, Dict[str, Any]]
    ) -> bool:
        """Check if model meets minimum rating threshold"""
        model_ratings = ratings_data.get(model["id"], {})
        
        # Calculate average rating across all dimensions
        rating_fields = ["speed", "quality", "cost_effectiveness", "reliability", "safety", "mcp_compatibility"]
        ratings = [model_ratings.get(field, 3.0) for field in rating_fields if model_ratings.get(field) is not None]
        
        if not ratings:
            return False
        
        avg_rating = sum(ratings) / len(ratings)
        return avg_rating >= min_rating
    
    def _model_meets_cost_threshold(
        self, 
        model: Dict[str, Any], 
        max_cost: float, 
        performance_data: Dict[str, Dict[str, Any]]
    ) -> bool:
        """Check if model meets maximum cost threshold"""
        model_performance = performance_data.get(model["id"], {})
        monthly_cost = model_performance.get("monthly_cost", 0.0)
        return monthly_cost <= max_cost
    
    def _create_sort_key_function(
        self,
        criteria: SortCriteria,
        performance_data: Optional[Dict[str, Dict[str, Any]]],
        ratings_data: Optional[Dict[str, Dict[str, Any]]]
    ) -> Callable:
        """Create sort key function based on criteria"""
        
        def sort_key(model: Dict[str, Any]) -> tuple:
            primary_key = self._get_sort_value(model, criteria.option, performance_data, ratings_data)
            
            # Add secondary sort if specified
            if criteria.secondary_sort:
                secondary_key = self._get_sort_value(model, criteria.secondary_sort, performance_data, ratings_data)
                return (primary_key, secondary_key)
            
            return (primary_key,)
        
        return sort_key
    
    def _get_sort_value(
        self,
        model: Dict[str, Any],
        sort_option: SortOption,
        performance_data: Optional[Dict[str, Dict[str, Any]]],
        ratings_data: Optional[Dict[str, Dict[str, Any]]]
    ) -> Any:
        """Get sort value for a model based on sort option"""
        
        if sort_option == SortOption.ALPHABETICAL:
            return model.get("name", "").lower()
        
        elif sort_option == SortOption.PROVIDER:
            return model.get("provider", "").lower()
        
        elif sort_option == SortOption.STATUS:
            # Sort order: configured, not_configured
            status = self._get_model_status(model)
            return 0 if status == "configured" else 1
        
        elif sort_option == SortOption.USAGE and performance_data:
            model_performance = performance_data.get(model["id"], {})
            return model_performance.get("total_requests", 0)
        
        elif sort_option == SortOption.COST and performance_data:
            model_performance = performance_data.get(model["id"], {})
            return model_performance.get("monthly_cost", 0.0)
        
        elif sort_option == SortOption.PERFORMANCE and performance_data:
            model_performance = performance_data.get(model["id"], {})
            # Use inverse of response time (lower is better)
            response_time = model_performance.get("response_time_avg", 5000)
            return -response_time if response_time > 0 else 0
        
        elif sort_option == SortOption.RATING and ratings_data:
            model_ratings = ratings_data.get(model["id"], {})
            # Calculate average rating
            rating_fields = ["speed", "quality", "cost_effectiveness", "reliability", "safety", "mcp_compatibility"]
            ratings = [model_ratings.get(field, 3.0) for field in rating_fields if model_ratings.get(field) is not None]
            return sum(ratings) / len(ratings) if ratings else 3.0
        
        elif sort_option == SortOption.LAST_UPDATED:
            # Sort by last updated timestamp
            last_updated = model.get("last_updated")
            if not last_updated:
                # Models without timestamp go to the end (use epoch time)
                return datetime(1970, 1, 1, tzinfo=timezone.utc)
            
            try:
                # Parse ISO format timestamp
                if isinstance(last_updated, str):
                    return datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                else:
                    return datetime(1970, 1, 1, tzinfo=timezone.utc)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse timestamp for model {model.get('id')}: {e}")
                return datetime(1970, 1, 1, tzinfo=timezone.utc)
        
        # Default fallback
        return model.get("name", "").lower()
    
    def _model_updated_within_days(self, model: Dict[str, Any], days: int) -> bool:
        """Check if model was updated within the specified number of days"""
        last_updated = model.get("last_updated")
        if not last_updated:
            return False
        
        try:
            # Parse ISO format timestamp
            if isinstance(last_updated, str):
                updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                return False
            
            # Calculate time difference
            now = datetime.now(timezone.utc)
            time_diff = now - updated_dt
            
            return time_diff.days < days
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp for model {model.get('id')}: {e}")
            return False
    
    def _model_is_stale(self, model: Dict[str, Any]) -> bool:
        """Check if model hasn't been updated in 90+ days"""
        last_updated = model.get("last_updated")
        if not last_updated:
            # If no timestamp, consider it stale
            return True
        
        try:
            # Parse ISO format timestamp
            if isinstance(last_updated, str):
                updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                return True
            
            # Calculate time difference
            now = datetime.now(timezone.utc)
            time_diff = now - updated_dt
            
            # Stale if more than 90 days (boundary: exactly 90 days is NOT stale)
            return time_diff.days > 90
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp for model {model.get('id')}: {e}")
            return True