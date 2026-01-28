# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Performance Monitor Service - Real-time performance monitoring and alerting.

Tracks model usage metrics, monitors performance thresholds, and generates alerts
for performance degradation, cost overruns, and availability issues.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

from app.core.logging import get_service_logger
from app.models.enhanced_models import (
    PerformanceMetrics, Alert, ModelWithMetrics
)

logger = get_service_logger("performance_monitor")


class PerformanceMonitorService:
    """
    Real-time performance monitoring and alerting service.
    
    Responsibilities:
    - Track real-time usage metrics for all models
    - Monitor performance thresholds and generate alerts
    - Store historical performance data
    - Calculate uptime and availability statistics
    - Provide cost tracking and budget alerts
    """

    def __init__(self, data_dir: Path, alert_thresholds: Optional[Dict[str, Any]] = None):
        """
        Initialize PerformanceMonitorService.
        
        Args:
            data_dir: Directory for storing performance data
            alert_thresholds: Custom alert thresholds (optional)
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance data storage
        self.metrics_file = data_dir / "performance_metrics.json"
        self.historical_file = data_dir / "historical_metrics.json"
        self.alerts_file = data_dir / "alerts.json"
        
        # In-memory tracking
        self.current_metrics: Dict[str, PerformanceMetrics] = {}
        self.historical_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.active_alerts: Dict[str, List[Alert]] = defaultdict(list)
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Alert thresholds
        self.thresholds = alert_thresholds or {
            "response_time_warning": 3000,  # 3 seconds
            "response_time_critical": 10000,  # 10 seconds
            "success_rate_warning": 95.0,  # 95%
            "success_rate_critical": 90.0,  # 90%
            "uptime_warning": 98.0,  # 98%
            "uptime_critical": 95.0,  # 95%
            "monthly_cost_warning": 100.0,  # $100
            "monthly_cost_critical": 500.0,  # $500
            "tokens_per_second_min": 10.0  # Minimum expected throughput
        }
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        logger.info(f"PerformanceMonitorService initialized with data dir: {data_dir}")

    async def track_model_usage(self, model_id: str, response_time: float, 
                               tokens_generated: int, cost: float, success: bool) -> None:
        """
        Track real-time usage metrics for a model.
        
        Args:
            model_id: Model identifier
            response_time: Response time in milliseconds
            tokens_generated: Number of tokens generated
            cost: Cost of the request
            success: Whether the request was successful
        """
        now = datetime.utcnow()
        
        # Update request tracking
        self.request_times[model_id].append({
            "timestamp": now,
            "response_time": response_time,
            "tokens": tokens_generated,
            "cost": cost,
            "success": success
        })
        
        # Calculate current metrics
        await self._update_current_metrics(model_id)
        
        # Check for threshold violations
        await self._check_performance_thresholds(model_id)
        
        # Persist metrics
        await self._save_metrics()
        
        logger.debug(f"Tracked usage for {model_id}: {response_time}ms, {tokens_generated} tokens, ${cost:.4f}")

    async def get_current_metrics(self, model_id: str) -> Optional[PerformanceMetrics]:
        """
        Get current performance metrics for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Current performance metrics or None if no data
        """
        return self.current_metrics.get(model_id)

    async def get_historical_metrics(self, model_id: str, timeframe: str = "24h") -> List[Dict[str, Any]]:
        """
        Get historical performance data for a model.
        
        Args:
            model_id: Model identifier
            timeframe: Time range (1h, 24h, 7d, 30d)
            
        Returns:
            List of historical metrics
        """
        # Parse timeframe
        if timeframe == "1h":
            cutoff = datetime.utcnow() - timedelta(hours=1)
        elif timeframe == "24h":
            cutoff = datetime.utcnow() - timedelta(hours=24)
        elif timeframe == "7d":
            cutoff = datetime.utcnow() - timedelta(days=7)
        elif timeframe == "30d":
            cutoff = datetime.utcnow() - timedelta(days=30)
        else:
            cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Filter historical data
        model_history = self.historical_data.get(model_id, [])
        filtered_history = []
        
        for entry in model_history:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if entry_time >= cutoff:
                filtered_history.append(entry)
        
        return filtered_history

    async def check_performance_thresholds(self) -> List[Alert]:
        """
        Check for performance degradation and generate alerts.
        
        Returns:
            List of current alerts across all models
        """
        all_alerts = []
        
        for model_id in self.current_metrics.keys():
            model_alerts = await self._check_performance_thresholds(model_id)
            all_alerts.extend(model_alerts)
        
        return all_alerts

    async def get_model_alerts(self, model_id: str) -> List[Alert]:
        """
        Get current alerts for a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of active alerts for the model
        """
        return self.active_alerts.get(model_id, [])

    async def clear_alert(self, model_id: str, alert_type: str) -> bool:
        """
        Clear a specific alert for a model.
        
        Args:
            model_id: Model identifier
            alert_type: Type of alert to clear
            
        Returns:
            True if alert was cleared, False if not found
        """
        model_alerts = self.active_alerts.get(model_id, [])
        
        for i, alert in enumerate(model_alerts):
            if alert.type == alert_type:
                model_alerts.pop(i)
                await self._save_alerts()
                logger.info(f"Cleared alert {alert_type} for model {model_id}")
                return True
        
        return False

    async def get_uptime_statistics(self, model_id: str, timeframe: str = "24h") -> Dict[str, float]:
        """
        Calculate uptime statistics for a model.
        
        Args:
            model_id: Model identifier
            timeframe: Time range for calculation
            
        Returns:
            Dictionary with uptime statistics
        """
        historical_data = await self.get_historical_metrics(model_id, timeframe)
        
        if not historical_data:
            return {"uptime_percentage": 100.0, "total_requests": 0, "failed_requests": 0}
        
        total_requests = 0
        failed_requests = 0
        
        for entry in historical_data:
            total_requests += entry.get("total_requests", 0)
            success_rate = entry.get("success_rate", 100.0)
            failed_requests += int(entry.get("total_requests", 0) * (100.0 - success_rate) / 100.0)
        
        if total_requests == 0:
            uptime_percentage = 100.0
        else:
            uptime_percentage = ((total_requests - failed_requests) / total_requests) * 100.0
        
        return {
            "uptime_percentage": uptime_percentage,
            "total_requests": total_requests,
            "failed_requests": failed_requests
        }

    # Private helper methods

    async def _load_existing_data(self) -> None:
        """Load existing performance data from disk."""
        try:
            # Load current metrics
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    data = json.load(f)
                    for model_id, metrics_data in data.items():
                        self.current_metrics[model_id] = PerformanceMetrics(
                            response_time_avg=metrics_data["response_time_avg"],
                            tokens_per_second=metrics_data["tokens_per_second"],
                            cost_per_1k_tokens=metrics_data["cost_per_1k_tokens"],
                            success_rate=metrics_data["success_rate"],
                            uptime_percentage=metrics_data["uptime_percentage"],
                            total_requests=metrics_data["total_requests"],
                            monthly_cost=metrics_data["monthly_cost"],
                            timestamp=datetime.fromisoformat(metrics_data["timestamp"])
                        )
            
            # Load historical data
            if self.historical_file.exists():
                with open(self.historical_file, "r") as f:
                    self.historical_data = defaultdict(list, json.load(f))
            
            # Load alerts
            if self.alerts_file.exists():
                with open(self.alerts_file, "r") as f:
                    alerts_data = json.load(f)
                    for model_id, alert_list in alerts_data.items():
                        self.active_alerts[model_id] = [
                            Alert(
                                type=alert["type"],
                                message=alert["message"],
                                severity=alert["severity"],
                                timestamp=datetime.fromisoformat(alert["timestamp"])
                            ) for alert in alert_list
                        ]
            
            logger.info("Loaded existing performance data")
            
        except Exception as e:
            logger.warning(f"Failed to load existing performance data: {e}")

    async def _update_current_metrics(self, model_id: str) -> None:
        """Update current metrics for a model based on recent requests."""
        recent_requests = list(self.request_times[model_id])
        
        if not recent_requests:
            return
        
        now = datetime.utcnow()
        
        # Calculate metrics from recent requests
        total_requests = len(recent_requests)
        successful_requests = sum(1 for req in recent_requests if req["success"])
        total_response_time = sum(req["response_time"] for req in recent_requests)
        total_tokens = sum(req["tokens"] for req in recent_requests)
        total_cost = sum(req["cost"] for req in recent_requests)
        
        # Calculate averages
        avg_response_time = total_response_time / total_requests if total_requests > 0 else 0
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100
        
        # Calculate tokens per second (based on recent activity)
        recent_time_span = 60  # Consider last 60 seconds
        recent_cutoff = now - timedelta(seconds=recent_time_span)
        recent_tokens = sum(
            req["tokens"] for req in recent_requests 
            if req["timestamp"] >= recent_cutoff
        )
        tokens_per_second = recent_tokens / recent_time_span if recent_tokens > 0 else 0
        
        # Calculate cost per 1K tokens
        cost_per_1k_tokens = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0
        
        # Estimate monthly cost (based on current usage pattern)
        daily_cost = total_cost  # Assuming recent requests represent daily usage
        monthly_cost = daily_cost * 30
        
        # Update current metrics
        self.current_metrics[model_id] = PerformanceMetrics(
            response_time_avg=avg_response_time,
            tokens_per_second=tokens_per_second,
            cost_per_1k_tokens=cost_per_1k_tokens,
            success_rate=success_rate,
            uptime_percentage=success_rate,  # Simplified uptime calculation
            total_requests=total_requests,
            monthly_cost=monthly_cost,
            timestamp=now
        )

    async def _check_performance_thresholds(self, model_id: str) -> List[Alert]:
        """Check performance thresholds and generate alerts for a model."""
        metrics = self.current_metrics.get(model_id)
        if not metrics:
            return []
        
        new_alerts = []
        now = datetime.utcnow()
        
        # Check response time thresholds
        if metrics.response_time_avg > self.thresholds["response_time_critical"]:
            alert = Alert(
                type="response_time_critical",
                message=f"Critical response time: {metrics.response_time_avg:.0f}ms (threshold: {self.thresholds['response_time_critical']}ms)",
                severity="critical",
                timestamp=now
            )
            new_alerts.append(alert)
        elif metrics.response_time_avg > self.thresholds["response_time_warning"]:
            alert = Alert(
                type="response_time_warning",
                message=f"High response time: {metrics.response_time_avg:.0f}ms (threshold: {self.thresholds['response_time_warning']}ms)",
                severity="warning",
                timestamp=now
            )
            new_alerts.append(alert)
        
        # Check success rate thresholds
        if metrics.success_rate < self.thresholds["success_rate_critical"]:
            alert = Alert(
                type="success_rate_critical",
                message=f"Critical success rate: {metrics.success_rate:.1f}% (threshold: {self.thresholds['success_rate_critical']}%)",
                severity="critical",
                timestamp=now
            )
            new_alerts.append(alert)
        elif metrics.success_rate < self.thresholds["success_rate_warning"]:
            alert = Alert(
                type="success_rate_warning",
                message=f"Low success rate: {metrics.success_rate:.1f}% (threshold: {self.thresholds['success_rate_warning']}%)",
                severity="warning",
                timestamp=now
            )
            new_alerts.append(alert)
        
        # Check cost thresholds
        if metrics.monthly_cost > self.thresholds["monthly_cost_critical"]:
            alert = Alert(
                type="monthly_cost_critical",
                message=f"Critical monthly cost: ${metrics.monthly_cost:.2f} (threshold: ${self.thresholds['monthly_cost_critical']})",
                severity="critical",
                timestamp=now
            )
            new_alerts.append(alert)
        elif metrics.monthly_cost > self.thresholds["monthly_cost_warning"]:
            alert = Alert(
                type="monthly_cost_warning",
                message=f"High monthly cost: ${metrics.monthly_cost:.2f} (threshold: ${self.thresholds['monthly_cost_warning']})",
                severity="warning",
                timestamp=now
            )
            new_alerts.append(alert)
        
        # Check throughput thresholds
        if metrics.tokens_per_second < self.thresholds["tokens_per_second_min"]:
            alert = Alert(
                type="low_throughput",
                message=f"Low throughput: {metrics.tokens_per_second:.1f} tokens/sec (minimum: {self.thresholds['tokens_per_second_min']})",
                severity="warning",
                timestamp=now
            )
            new_alerts.append(alert)
        
        # Update active alerts (replace existing alerts of same type)
        existing_alert_types = {alert.type for alert in self.active_alerts[model_id]}
        
        # Remove old alerts of the same types
        for alert in new_alerts:
            if alert.type in existing_alert_types:
                self.active_alerts[model_id] = [
                    a for a in self.active_alerts[model_id] if a.type != alert.type
                ]
        
        # Add new alerts
        self.active_alerts[model_id].extend(new_alerts)
        
        if new_alerts:
            await self._save_alerts()
            logger.info(f"Generated {len(new_alerts)} alerts for model {model_id}")
        
        return new_alerts

    async def _save_metrics(self) -> None:
        """Save current metrics to disk."""
        try:
            metrics_data = {}
            for model_id, metrics in self.current_metrics.items():
                metrics_data[model_id] = metrics.to_dict()
            
            with open(self.metrics_file, "w") as f:
                json.dump(metrics_data, f, indent=2)
                
            # Also save to historical data
            await self._save_historical_data()
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    async def _save_historical_data(self) -> None:
        """Save historical data to disk."""
        try:
            # Add current metrics to historical data
            now = datetime.utcnow()
            for model_id, metrics in self.current_metrics.items():
                historical_entry = metrics.to_dict()
                historical_entry["timestamp"] = now.isoformat()
                
                # Keep only last 1000 entries per model
                if len(self.historical_data[model_id]) >= 1000:
                    self.historical_data[model_id].pop(0)
                
                self.historical_data[model_id].append(historical_entry)
            
            with open(self.historical_file, "w") as f:
                json.dump(dict(self.historical_data), f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save historical data: {e}")

    async def _save_alerts(self) -> None:
        """Save active alerts to disk."""
        try:
            alerts_data = {}
            for model_id, alerts in self.active_alerts.items():
                alerts_data[model_id] = [alert.to_dict() for alert in alerts]
            
            with open(self.alerts_file, "w") as f:
                json.dump(alerts_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")