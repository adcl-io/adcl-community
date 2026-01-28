# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry Failover Manager

Single responsibility: Handle registry failover, health checking, and retry logic
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass, field
from enum import Enum

import httpx
from app.models.registry_models import RegistryConfig, PackageMetadata

logger = logging.getLogger(__name__)


class RegistryHealth(Enum):
    """Registry health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNAVAILABLE = "unavailable"


@dataclass
class HealthMetrics:
    """Registry health metrics"""
    status: RegistryHealth = RegistryHealth.HEALTHY
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    response_times: List[float] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    consecutive_failures: int = 0
    
    @property
    def avg_response_time(self) -> float:
        """Average response time over last 10 requests"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times[-10:]) / len(self.response_times[-10:])
    
    @property
    def is_available(self) -> bool:
        """Whether registry is considered available"""
        return self.status in [RegistryHealth.HEALTHY, RegistryHealth.DEGRADED]
    
    def record_success(self, response_time: float):
        """Record successful request"""
        self.last_success = datetime.now(UTC)
        self.consecutive_failures = 0
        self.response_times.append(response_time)
        
        # Keep only last 20 response times
        if len(self.response_times) > 20:
            self.response_times = self.response_times[-20:]
        
        # Update status based on performance
        if self.avg_response_time < 2.0:
            self.status = RegistryHealth.HEALTHY
        elif self.avg_response_time < 10.0:
            self.status = RegistryHealth.DEGRADED
        else:
            self.status = RegistryHealth.FAILING
    
    def record_failure(self, error_msg: str):
        """Record failed request"""
        self.last_failure = datetime.now(UTC)
        self.failure_count += 1
        self.consecutive_failures += 1
        self.error_messages.append(f"{datetime.now(UTC).isoformat()}: {error_msg}")
        
        # Keep only last 10 error messages
        if len(self.error_messages) > 10:
            self.error_messages = self.error_messages[-10:]
        
        # Update status based on failure pattern
        if self.consecutive_failures >= 5:
            self.status = RegistryHealth.UNAVAILABLE
        elif self.consecutive_failures >= 3:
            self.status = RegistryHealth.FAILING
        elif self.consecutive_failures >= 1:
            self.status = RegistryHealth.DEGRADED


@dataclass
class FailoverConfig:
    """Failover configuration settings"""
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    backoff_multiplier: float = 2.0
    health_check_interval: int = 60
    timeout: float = 30.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_time: int = 300


class RegistryFailoverManager:
    """
    Manages registry failover with health monitoring and circuit breaker pattern.
    
    Features:
    - Automatic retry with exponential backoff
    - Health monitoring and circuit breaker
    - Priority-based registry selection
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[FailoverConfig] = None):
        """
        Initialize failover manager.
        
        Args:
            config: Failover configuration
        """
        self.config = config or FailoverConfig()
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.circuit_breakers: Dict[str, datetime] = {}
        self._last_health_check = datetime.now(UTC)
        
        logger.info(
            f"Registry failover initialized with config - "
            f"max_retries={self.config.max_retries}, "
            f"timeout={self.config.timeout}s, "
            f"circuit_breaker_threshold={self.config.circuit_breaker_threshold}, "
            f"health_check_interval={self.config.health_check_interval}s"
        )
    
    def get_registry_health(self, registry_name: str) -> HealthMetrics:
        """
        Get health metrics for a registry.
        
        Args:
            registry_name: Registry name
            
        Returns:
            Health metrics
        """
        if registry_name not in self.health_metrics:
            self.health_metrics[registry_name] = HealthMetrics()
        return self.health_metrics[registry_name]
    
    def is_circuit_breaker_open(self, registry_name: str) -> bool:
        """
        Check if circuit breaker is open for a registry.
        
        Args:
            registry_name: Registry name
            
        Returns:
            True if circuit breaker is open
        """
        if registry_name not in self.circuit_breakers:
            return False
        
        breaker_time = self.circuit_breakers[registry_name]
        reset_time = breaker_time + timedelta(seconds=self.config.circuit_breaker_reset_time)
        
        if datetime.now(UTC) > reset_time:
            # Reset circuit breaker
            del self.circuit_breakers[registry_name]
            health = self.get_registry_health(registry_name)
            health.consecutive_failures = 0
            logger.info(f"Circuit breaker reset for registry: {registry_name}")
            return False
        
        return True
    
    def open_circuit_breaker(self, registry_name: str):
        """
        Open circuit breaker for a registry.
        
        Args:
            registry_name: Registry name
        """
        self.circuit_breakers[registry_name] = datetime.now(UTC)
        health = self.get_registry_health(registry_name)
        health.status = RegistryHealth.UNAVAILABLE
        logger.warning(f"Circuit breaker opened for registry: {registry_name}")
    
    def get_ordered_registries(
        self, 
        registries: Dict[str, RegistryConfig],
        operation: str = "fetch"
    ) -> List[RegistryConfig]:
        """
        Get registries ordered by priority and health for optimal selection.
        
        Args:
            registries: Available registries
            operation: Operation type (for logging)
            
        Returns:
            Ordered list of healthy registries
        """
        available_registries = []
        
        for name, registry in registries.items():
            if not registry.enabled:
                continue
            
            # Skip if circuit breaker is open
            if self.is_circuit_breaker_open(name):
                logger.debug(f"Skipping {name}: circuit breaker open")
                continue
            
            health = self.get_registry_health(name)
            if health.is_available:
                available_registries.append(registry)
        
        # Sort by priority (lower number = higher priority), then by health
        available_registries.sort(key=lambda r: (
            r.priority,
            self.get_registry_health(r.name).consecutive_failures,
            -self.get_registry_health(r.name).avg_response_time
        ))
        
        logger.info(
            f"Registry order for {operation}: "
            f"{[r.name for r in available_registries]}"
        )
        
        return available_registries
    
    async def execute_with_failover(
        self,
        operation: Callable,
        registries: Dict[str, RegistryConfig],
        operation_name: str,
        **kwargs
    ) -> Any:
        """
        Execute operation with automatic failover across registries.
        
        Args:
            operation: Async function to execute
            registries: Available registries
            operation_name: Operation name for logging
            **kwargs: Arguments to pass to operation
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all registries fail
        """
        ordered_registries = self.get_ordered_registries(registries, operation_name)
        
        if not ordered_registries:
            raise Exception(f"No available registries for {operation_name}")
        
        last_error = None
        attempted_registries = []
        
        for registry in ordered_registries:
            health = self.get_registry_health(registry.name)
            attempted_registries.append(registry.name)
            
            try:
                logger.info(f"Attempting {operation_name} on registry: {registry.name}")
                start_time = time.time()
                
                # Execute operation with timeout
                result = await asyncio.wait_for(
                    operation(registry, **kwargs),
                    timeout=self.config.timeout
                )
                
                # Record success
                response_time = time.time() - start_time
                health.record_success(response_time)
                
                logger.info(
                    f"Successfully executed {operation_name} on {registry.name} "
                    f"in {response_time:.2f}s"
                )
                
                return result
                
            except asyncio.TimeoutError as e:
                error_msg = f"Timeout after {self.config.timeout}s"
                logger.warning(
                    f"{operation_name} timeout on registry '{registry.name}' "
                    f"({registry.url}): {error_msg}. "
                    f"Consecutive failures: {health.consecutive_failures + 1}"
                )
                health.record_failure(error_msg)
                last_error = e
                
                # Check if circuit breaker should open
                if health.consecutive_failures >= self.config.circuit_breaker_threshold:
                    self.open_circuit_breaker(registry.name)
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"{operation_name} failed on registry '{registry.name}' "
                    f"({registry.url}): {error_msg}. "
                    f"Consecutive failures: {health.consecutive_failures + 1}. "
                    f"Error type: {type(e).__name__}"
                )
                health.record_failure(error_msg)
                last_error = e
                
                # Check if circuit breaker should open
                if health.consecutive_failures >= self.config.circuit_breaker_threshold:
                    self.open_circuit_breaker(registry.name)
        
        # All registries failed
        error_summary = f"All registries failed for {operation_name}. Attempted: {attempted_registries}"
        logger.error(error_summary)
        raise Exception(f"{error_summary}. Last error: {last_error}")
    
    async def execute_with_retry(
        self,
        operation: Callable,
        registry: RegistryConfig,
        operation_name: str,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic on a single registry.
        
        Args:
            operation: Async function to execute
            registry: Registry to use
            operation_name: Operation name for logging
            **kwargs: Arguments to pass to operation
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all retries fail
        """
        last_error = None
        delay = self.config.retry_delay
        health = self.get_registry_health(registry.name)
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt}/{self.config.max_retries} "
                        f"for {operation_name} on {registry.name} after {delay}s"
                    )
                    await asyncio.sleep(delay)
                
                start_time = time.time()
                result = await asyncio.wait_for(
                    operation(registry, **kwargs),
                    timeout=self.config.timeout
                )
                
                # Record success
                response_time = time.time() - start_time
                health.record_success(response_time)
                
                if attempt > 0:
                    logger.info(f"Retry successful for {operation_name} on {registry.name}")
                
                return result
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                if attempt == self.config.max_retries:
                    logger.error(
                        f"Final retry failed for {operation_name} on {registry.name}: {error_msg}"
                    )
                    health.record_failure(error_msg)
                    break
                else:
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.max_retries} failed "
                        f"for {operation_name} on {registry.name}: {error_msg}"
                    )
                    
                    # Exponential backoff
                    delay = min(delay * self.config.backoff_multiplier, self.config.max_retry_delay)
        
        raise last_error
    
    async def health_check_registry(
        self,
        registry: RegistryConfig,
        client: httpx.AsyncClient
    ) -> bool:
        """
        Perform health check on a registry.
        
        Args:
            registry: Registry to check
            client: HTTP client
            
        Returns:
            True if healthy
        """
        health = self.get_registry_health(registry.name)
        
        try:
            start_time = time.time()
            
            if registry.url.startswith("file://"):
                # Local registry health check - verify directory exists
                from pathlib import Path
                local_path = registry.url.replace("file://", "")
                if local_path.startswith("./") or local_path.startswith("../"):
                    # Resolve relative paths (assuming base_dir context)
                    directory = Path(local_path).resolve()
                else:
                    directory = Path(local_path)
                
                if not directory.exists() or not directory.is_dir():
                    raise Exception(f"Local directory not accessible: {directory}")
                
                response_time = time.time() - start_time
                health.record_success(response_time)
                return True
                
            else:
                # HTTP registry health check
                health_url = f"{registry.url}/health"
                response = await client.get(health_url, timeout=self.config.timeout)
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    health.record_success(response_time)
                    return True
                else:
                    raise Exception(f"Health check failed with status {response.status_code}")
                    
        except Exception as e:
            health.record_failure(f"Health check failed: {e}")
            logger.warning(f"Health check failed for {registry.name}: {e}")
            return False
    
    async def run_health_checks(self, registries: Dict[str, RegistryConfig]):
        """
        Run health checks on all enabled registries.
        
        Args:
            registries: Registries to check
        """
        now = datetime.now(UTC)
        if (now - self._last_health_check).seconds < self.config.health_check_interval:
            return
        
        self._last_health_check = now
        logger.info("Running registry health checks...")
        
        enabled_registries = [r for r in registries.values() if r.enabled]
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self.health_check_registry(registry, client)
                for registry in enabled_registries
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for registry, result in zip(enabled_registries, results):
                if isinstance(result, Exception):
                    logger.error(f"Health check error for {registry.name}: {result}")
                elif result:
                    logger.debug(f"Health check passed for {registry.name}")
                else:
                    logger.warning(f"Health check failed for {registry.name}")
    
    def get_health_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive health summary for all registries.
        
        Returns:
            Health summary dictionary
        """
        summary = {}
        
        for name, health in self.health_metrics.items():
            is_circuit_open = self.is_circuit_breaker_open(name)
            
            summary[name] = {
                "status": health.status.value,
                "is_available": health.is_available and not is_circuit_open,
                "circuit_breaker_open": is_circuit_open,
                "last_success": health.last_success.isoformat() if health.last_success else None,
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
                "failure_count": health.failure_count,
                "consecutive_failures": health.consecutive_failures,
                "avg_response_time": round(health.avg_response_time, 2),
                "recent_errors": health.error_messages[-3:]  # Last 3 errors
            }
        
        return summary