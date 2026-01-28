# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Enhanced Models Data Structures - Support for ratings, performance metrics, and MCP compatibility.

Defines data models for the enhanced models interface including:
- Model ratings across multiple dimensions
- Performance metrics and monitoring
- MCP compatibility tracking
- Safety indicators
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class SafetyLevel(str, Enum):
    """Model safety/content filtering levels"""
    STRICT = "strict"
    MODERATE = "moderate"
    MINIMAL = "minimal"
    UNLOCKED = "unlocked"


class FunctionCallingSupport(str, Enum):
    """Function calling capability levels"""
    NATIVE = "native"
    LIMITED = "limited"
    NONE = "none"


@dataclass
class ModelCapabilities:
    """Model capability indicators"""
    function_calling: FunctionCallingSupport
    vision: bool = False
    code_generation: bool = False
    reasoning: str = "basic"  # basic, advanced, expert
    multimodal: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRatings:
    """Standardized model ratings across key dimensions"""
    speed: float  # 1-5 stars
    quality: float  # 1-5 stars
    cost_effectiveness: float  # 1-5 stars
    reliability: float  # 1-5 stars
    safety: float  # 1-5 stars
    mcp_compatibility: float  # 1-5 stars
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate rating values are within 1-5 range"""
        for field_name, value in asdict(self).items():
            if field_name != "last_updated" and isinstance(value, (int, float)):
                if not 1.0 <= value <= 5.0:
                    raise ValueError(f"Rating {field_name} must be between 1.0 and 5.0, got {value}")
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        return result


@dataclass
class PerformanceMetrics:
    """Real-time and historical performance metrics"""
    response_time_avg: float  # milliseconds
    tokens_per_second: float
    cost_per_1k_tokens: float
    success_rate: float  # percentage (0-100)
    uptime_percentage: float  # percentage (0-100)
    total_requests: int
    monthly_cost: float
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class MCPToolCompatibility:
    """MCP tool category compatibility data"""
    success_rate: float  # 0.0 to 1.0
    avg_response_time: float  # milliseconds
    last_tested: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.last_tested:
            result["last_tested"] = self.last_tested.isoformat()
        return result


@dataclass
class MCPCompatibilityMatrix:
    """Complete MCP compatibility data for a model"""
    reliability_score: float  # 1-5 stars
    tested_categories: List[str]
    success_rates: Dict[str, MCPToolCompatibility]
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "reliability_score": self.reliability_score,
            "tested_categories": self.tested_categories,
            "success_rates": {k: v.to_dict() for k, v in self.success_rates.items()}
        }
        return result


@dataclass
class BenchmarkData:
    """External benchmark scores"""
    mmlu: Optional[float] = None
    humaneval: Optional[float] = None
    hellaswag: Optional[float] = None
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        return result


@dataclass
class Alert:
    """Performance or cost alert"""
    type: str  # cost_threshold, performance_degradation, uptime_issue
    message: str
    severity: str  # info, warning, error, critical
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class EnhancedModelConfig:
    """Enhanced model configuration with all new features"""
    # Base model fields
    id: str
    name: str
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    description: str = ""
    is_default: bool = False
    configured: bool = False
    api_key: Optional[str] = None
    
    # Enhanced fields
    capabilities: Optional[ModelCapabilities] = None
    safety_level: SafetyLevel = SafetyLevel.MODERATE
    ratings: Optional[ModelRatings] = None
    mcp_compatibility: Optional[MCPCompatibilityMatrix] = None
    benchmarks: Optional[BenchmarkData] = None
    
    # Timestamp fields
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "description": self.description,
            "is_default": self.is_default,
            "configured": self.configured,
            "api_key": self.api_key,
            "safety_level": self.safety_level.value
        }
        
        if self.capabilities:
            result["capabilities"] = self.capabilities.to_dict()
        if self.ratings:
            result["ratings"] = self.ratings.to_dict()
        if self.mcp_compatibility:
            result["mcp_compatibility"] = self.mcp_compatibility.to_dict()
        if self.benchmarks:
            result["benchmarks"] = self.benchmarks.to_dict()
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
            
        return result


@dataclass
class ModelWithMetrics:
    """Model configuration combined with performance metrics"""
    model: EnhancedModelConfig
    metrics: Optional[PerformanceMetrics] = None
    alerts: List[Alert] = None
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = self.model.to_dict()
        if self.metrics:
            result["metrics"] = self.metrics.to_dict()
        if self.alerts:
            result["alerts"] = [alert.to_dict() for alert in self.alerts]
        return result


@dataclass
class ModelRecommendation:
    """Model recommendation for specific tasks"""
    model_id: str
    score: float  # 0-1 confidence score
    reasoning: str
    trade_offs: Dict[str, str]  # aspect -> description
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)