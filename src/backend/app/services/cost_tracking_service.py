# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Cost Tracking Service - Tracks model usage costs and budget management.

Provides comprehensive cost tracking, budget alerts, and cost optimization
recommendations for model usage.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.core.logging import get_service_logger

logger = get_service_logger("cost_tracking")


@dataclass
class CostEntry:
    """Single cost tracking entry"""
    timestamp: str
    model_id: str
    request_id: Optional[str]
    tokens_input: int
    tokens_output: int
    cost_input: float
    cost_output: float
    total_cost: float
    provider: str
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BudgetAlert:
    """Budget alert configuration and status"""
    budget_id: str
    model_id: Optional[str]  # None for global budget
    budget_limit: float
    period: str  # daily, weekly, monthly
    current_spend: float
    alert_threshold: float  # percentage (e.g., 80.0 for 80%)
    alert_triggered: bool
    last_alert_time: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostSummary:
    """Cost summary for a time period"""
    model_id: str
    period_start: str
    period_end: str
    total_cost: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    avg_cost_per_request: float
    avg_cost_per_1k_tokens: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostTrackingService:
    """
    Manages cost tracking and budget management for model usage.
    
    Responsibilities:
    - Track per-request costs
    - Calculate daily/monthly spending
    - Manage budget alerts
    - Provide cost optimization recommendations
    - Generate cost reports
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize CostTrackingService.
        
        Args:
            data_dir: Directory for storing cost data
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Data files
        self.cost_log_file = data_dir / "cost_log.jsonl"
        self.budgets_file = data_dir / "budgets.json"
        self.summaries_file = data_dir / "cost_summaries.json"
        
        # In-memory data
        self.budgets: Dict[str, BudgetAlert] = {}
        self.daily_summaries: Dict[str, Dict[str, CostSummary]] = defaultdict(dict)
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.info(f"CostTrackingService initialized with data dir: {data_dir}")
    
    async def initialize(self) -> None:
        """Initialize the service by loading existing data."""
        await self._load_existing_data()
    
    async def track_cost(
        self,
        model_id: str,
        tokens_input: int,
        tokens_output: int,
        cost_input: float,
        cost_output: float,
        provider: str,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> CostEntry:
        """
        Track cost for a model request.
        
        Args:
            model_id: Model identifier
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost_input: Cost for input tokens
            cost_output: Cost for output tokens
            provider: Model provider
            request_id: Optional request identifier
            user_id: Optional user identifier
            
        Returns:
            Created cost entry
        """
        async with self.lock:
            now = datetime.utcnow()
            total_cost = cost_input + cost_output
            
            entry = CostEntry(
                timestamp=now.isoformat(),
                model_id=model_id,
                request_id=request_id,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_input=cost_input,
                cost_output=cost_output,
                total_cost=total_cost,
                provider=provider,
                user_id=user_id
            )
            
            # Append to cost log
            try:
                with open(self.cost_log_file, "a") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
                
                logger.debug(f"Tracked cost for {model_id}: ${total_cost:.4f}")
                
                # Update daily summaries
                await self._update_daily_summary(entry)
                
                # Check budget alerts
                await self._check_budget_alerts(model_id, total_cost)
                
                return entry
                
            except Exception as e:
                logger.error(f"Failed to track cost: {e}")
                raise
    
    async def get_cost_summary(
        self,
        model_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CostSummary]:
        """
        Get cost summary for specified period and model.
        
        Args:
            model_id: Optional model filter
            start_date: Start of period (defaults to 30 days ago)
            end_date: End of period (defaults to now)
            
        Returns:
            List of cost summaries
        """
        async with self.lock:
            return await self._get_cost_summary_internal(model_id, start_date, end_date)
    
    async def _get_cost_summary_internal(
        self,
        model_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CostSummary]:
        """
        Internal cost summary method that doesn't use locks.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        summaries = []
        
        try:
            if not self.cost_log_file.exists():
                return summaries
            
            # Read and aggregate cost entries
            cost_data = defaultdict(lambda: {
                'total_cost': 0.0,
                'total_requests': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0
            })
            
            with open(self.cost_log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry_data = json.loads(line)
                        entry_time = datetime.fromisoformat(entry_data["timestamp"])
                        
                        # Filter by date range
                        if entry_time < start_date or entry_time > end_date:
                            continue
                        
                        # Filter by model
                        if model_id and entry_data["model_id"] != model_id:
                            continue
                        
                        model_key = entry_data["model_id"]
                        cost_data[model_key]['total_cost'] += entry_data["total_cost"]
                        cost_data[model_key]['total_requests'] += 1
                        cost_data[model_key]['total_input_tokens'] += entry_data["tokens_input"]
                        cost_data[model_key]['total_output_tokens'] += entry_data["tokens_output"]
                        
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Invalid cost entry: {line} - {e}")
                        continue
            
            # Create summaries
            for model_key, data in cost_data.items():
                total_tokens = data['total_input_tokens'] + data['total_output_tokens']
                
                summary = CostSummary(
                    model_id=model_key,
                    period_start=start_date.isoformat(),
                    period_end=end_date.isoformat(),
                    total_cost=data['total_cost'],
                    total_requests=data['total_requests'],
                    total_input_tokens=data['total_input_tokens'],
                    total_output_tokens=data['total_output_tokens'],
                    avg_cost_per_request=data['total_cost'] / data['total_requests'] if data['total_requests'] > 0 else 0.0,
                    avg_cost_per_1k_tokens=(data['total_cost'] / total_tokens * 1000) if total_tokens > 0 else 0.0
                )
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return []
    
    async def set_budget(
        self,
        budget_id: str,
        budget_limit: float,
        period: str = "monthly",
        model_id: Optional[str] = None,
        alert_threshold: float = 80.0
    ) -> BudgetAlert:
        """
        Set budget limit for a model or globally.
        
        Args:
            budget_id: Unique budget identifier
            budget_limit: Budget limit amount
            period: Budget period (daily, weekly, monthly)
            model_id: Optional model ID (None for global)
            alert_threshold: Alert threshold percentage
            
        Returns:
            Created budget alert
        """
        async with self.lock:
            # Calculate current spend
            current_spend = await self._calculate_current_spend(model_id, period)
            
            budget = BudgetAlert(
                budget_id=budget_id,
                model_id=model_id,
                budget_limit=budget_limit,
                period=period,
                current_spend=current_spend,
                alert_threshold=alert_threshold,
                alert_triggered=False,
                last_alert_time=None
            )
            
            self.budgets[budget_id] = budget
            await self._save_budgets()
            
            logger.info(f"Set budget {budget_id}: ${budget_limit} {period} for {model_id or 'global'}")
            return budget
    
    async def get_budget_status(self, budget_id: str) -> Optional[BudgetAlert]:
        """
        Get current budget status.
        
        Args:
            budget_id: Budget identifier
            
        Returns:
            Budget alert or None if not found
        """
        async with self.lock:
            budget = self.budgets.get(budget_id)
            if not budget:
                return None
            
            # Update current spend
            budget.current_spend = await self._calculate_current_spend(budget.model_id, budget.period)
            return budget
    
    async def get_cost_optimization_recommendations(self, model_id: str) -> List[Dict[str, Any]]:
        """
        Get cost optimization recommendations for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        try:
            # Get recent cost data
            summaries = await self.get_cost_summary(
                model_id=model_id,
                start_date=datetime.utcnow() - timedelta(days=7)
            )
            
            if not summaries:
                return recommendations
            
            summary = summaries[0]
            
            # High cost per request
            if summary.avg_cost_per_request > 0.10:  # $0.10 threshold
                recommendations.append({
                    "type": "high_cost_per_request",
                    "title": "High Cost Per Request",
                    "description": f"Average cost per request is ${summary.avg_cost_per_request:.4f}. Consider using a more cost-effective model for simpler tasks.",
                    "priority": "medium",
                    "potential_savings": summary.total_cost * 0.3  # Estimate 30% savings
                })
            
            # High token usage
            avg_tokens_per_request = (summary.total_input_tokens + summary.total_output_tokens) / summary.total_requests
            if avg_tokens_per_request > 2000:
                recommendations.append({
                    "type": "high_token_usage",
                    "title": "High Token Usage",
                    "description": f"Average {avg_tokens_per_request:.0f} tokens per request. Consider optimizing prompts or using context compression.",
                    "priority": "medium",
                    "potential_savings": summary.total_cost * 0.2  # Estimate 20% savings
                })
            
            # Frequent usage pattern
            if summary.total_requests > 1000:  # High usage threshold
                recommendations.append({
                    "type": "volume_discount",
                    "title": "Volume Usage Detected",
                    "description": f"High usage detected ({summary.total_requests} requests). Consider negotiating volume discounts with the provider.",
                    "priority": "low",
                    "potential_savings": summary.total_cost * 0.1  # Estimate 10% savings
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate cost recommendations: {e}")
            return []
    
    async def get_cost_comparison(self, model_ids: List[str]) -> Dict[str, Any]:
        """
        Compare costs between multiple models.
        
        Args:
            model_ids: List of model IDs to compare
            
        Returns:
            Cost comparison data
        """
        comparison = {
            "models": {},
            "period": "last_30_days",
            "most_cost_effective": None,
            "highest_cost": None
        }
        
        try:
            for model_id in model_ids:
                summaries = await self.get_cost_summary(
                    model_id=model_id,
                    start_date=datetime.utcnow() - timedelta(days=30)
                )
                
                if summaries:
                    summary = summaries[0]
                    comparison["models"][model_id] = {
                        "total_cost": summary.total_cost,
                        "total_requests": summary.total_requests,
                        "avg_cost_per_request": summary.avg_cost_per_request,
                        "avg_cost_per_1k_tokens": summary.avg_cost_per_1k_tokens
                    }
            
            # Find most/least cost effective
            if comparison["models"]:
                sorted_by_cost_per_request = sorted(
                    comparison["models"].items(),
                    key=lambda x: x[1]["avg_cost_per_request"]
                )
                comparison["most_cost_effective"] = sorted_by_cost_per_request[0][0]
                comparison["highest_cost"] = sorted_by_cost_per_request[-1][0]
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to generate cost comparison: {e}")
            return comparison
    
    # Private helper methods
    
    async def _load_existing_data(self) -> None:
        """Load existing cost tracking data."""
        try:
            # Load budgets
            if self.budgets_file.exists():
                with open(self.budgets_file, "r") as f:
                    budgets_data = json.load(f)
                    for budget_id, budget_data in budgets_data.items():
                        self.budgets[budget_id] = BudgetAlert(**budget_data)
            
            logger.info("Loaded existing cost tracking data")
            
        except Exception as e:
            logger.warning(f"Failed to load existing cost data: {e}")
    
    async def _save_budgets(self) -> None:
        """Save budgets to disk."""
        try:
            budgets_data = {
                budget_id: budget.to_dict()
                for budget_id, budget in self.budgets.items()
            }
            
            with open(self.budgets_file, "w") as f:
                json.dump(budgets_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save budgets: {e}")
    
    async def _update_daily_summary(self, entry: CostEntry) -> None:
        """Update daily cost summary with new entry."""
        try:
            entry_date = datetime.fromisoformat(entry.timestamp).date().isoformat()
            
            if entry_date not in self.daily_summaries:
                self.daily_summaries[entry_date] = {}
            
            if entry.model_id not in self.daily_summaries[entry_date]:
                self.daily_summaries[entry_date][entry.model_id] = CostSummary(
                    model_id=entry.model_id,
                    period_start=entry_date,
                    period_end=entry_date,
                    total_cost=0.0,
                    total_requests=0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    avg_cost_per_request=0.0,
                    avg_cost_per_1k_tokens=0.0
                )
            
            summary = self.daily_summaries[entry_date][entry.model_id]
            summary.total_cost += entry.total_cost
            summary.total_requests += 1
            summary.total_input_tokens += entry.tokens_input
            summary.total_output_tokens += entry.tokens_output
            
            # Recalculate averages
            summary.avg_cost_per_request = summary.total_cost / summary.total_requests
            total_tokens = summary.total_input_tokens + summary.total_output_tokens
            summary.avg_cost_per_1k_tokens = (summary.total_cost / total_tokens * 1000) if total_tokens > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to update daily summary: {e}")
    
    async def _calculate_current_spend(self, model_id: Optional[str], period: str) -> float:
        """Calculate current spend for budget period."""
        try:
            now = datetime.utcnow()
            
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "weekly":
                days_since_monday = now.weekday()
                start_date = now - timedelta(days=days_since_monday)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "monthly":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now - timedelta(days=30)
            
            # Use internal method to avoid deadlock
            summaries = await self._get_cost_summary_internal(
                model_id=model_id,
                start_date=start_date,
                end_date=now
            )
            
            return sum(summary.total_cost for summary in summaries)
            
        except Exception as e:
            logger.error(f"Failed to calculate current spend: {e}")
            return 0.0
    
    async def _check_budget_alerts(self, model_id: str, cost: float) -> None:
        """Check if any budget alerts should be triggered."""
        try:
            for budget_id, budget in self.budgets.items():
                # Skip if budget is for different model
                if budget.model_id and budget.model_id != model_id:
                    continue
                
                # Update current spend
                budget.current_spend = await self._calculate_current_spend(budget.model_id, budget.period)
                
                # Check if alert threshold is exceeded
                percentage = (budget.current_spend / budget.budget_limit) * 100
                
                if percentage >= budget.alert_threshold and not budget.alert_triggered:
                    budget.alert_triggered = True
                    budget.last_alert_time = datetime.utcnow().isoformat()
                    
                    logger.warning(
                        f"Budget alert triggered for {budget_id}: "
                        f"${budget.current_spend:.2f} / ${budget.budget_limit} ({percentage:.1f}%)"
                    )
                    
                    await self._save_budgets()
                
                # Reset alert if spending drops below threshold
                elif percentage < budget.alert_threshold and budget.alert_triggered:
                    budget.alert_triggered = False
                    await self._save_budgets()
            
        except Exception as e:
            logger.error(f"Failed to check budget alerts: {e}")