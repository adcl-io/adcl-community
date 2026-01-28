# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Uptime Monitoring Service - Tracks model availability and uptime statistics.

Provides comprehensive uptime tracking, outage detection, and availability
monitoring for model services.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

from app.core.logging import get_service_logger

logger = get_service_logger("uptime_monitoring")


class ServiceStatus(Enum):
    """Service status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class UptimeEvent:
    """Single uptime event entry"""
    timestamp: str
    model_id: str
    status: str  # ServiceStatus value
    response_time: Optional[float]  # Response time in milliseconds
    error_message: Optional[str] = None
    check_type: str = "health_check"  # health_check, request_success, request_failure
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutageEvent:
    """Outage event tracking"""
    outage_id: str
    model_id: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    severity: str  # minor, major, critical
    description: str
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UptimeStats:
    """Uptime statistics for a model"""
    model_id: str
    period_start: str
    period_end: str
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    avg_response_time: float
    total_outages: int
    total_downtime_seconds: float
    current_status: str
    last_check_time: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UptimeMonitoringService:
    """
    Manages uptime monitoring and availability tracking for model services.
    
    Responsibilities:
    - Track model availability status
    - Calculate uptime statistics
    - Detect and record outages
    - Provide health indicators
    - Generate availability reports
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize UptimeMonitoringService.
        
        Args:
            data_dir: Directory for storing uptime data
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Data files
        self.uptime_log_file = data_dir / "uptime_log.jsonl"
        self.outages_file = data_dir / "outages.json"
        self.current_status_file = data_dir / "current_status.json"
        
        # In-memory data
        self.current_status: Dict[str, ServiceStatus] = {}
        self.active_outages: Dict[str, OutageEvent] = {}
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        logger.info(f"UptimeMonitoringService initialized with data dir: {data_dir}")
    
    async def initialize(self) -> None:
        """Initialize the service by loading existing data."""
        await self._load_existing_data()
    
    async def record_uptime_event(
        self,
        model_id: str,
        status: ServiceStatus,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
        check_type: str = "health_check"
    ) -> UptimeEvent:
        """
        Record an uptime event for a model.
        
        Args:
            model_id: Model identifier
            status: Current service status
            response_time: Response time in milliseconds
            error_message: Error message if status is not online
            check_type: Type of check performed
            
        Returns:
            Created uptime event
        """
        async with self.lock:
            now = datetime.utcnow()
            
            event = UptimeEvent(
                timestamp=now.isoformat(),
                model_id=model_id,
                status=status.value,
                response_time=response_time,
                error_message=error_message,
                check_type=check_type
            )
            
            # Append to uptime log
            try:
                with open(self.uptime_log_file, "a") as f:
                    f.write(json.dumps(event.to_dict()) + "\n")
                
                logger.debug(f"Recorded uptime event for {model_id}: {status.value}")
                
                # Update current status
                previous_status = self.current_status.get(model_id, ServiceStatus.UNKNOWN)
                self.current_status[model_id] = status
                
                # Check for status changes and handle outages
                await self._handle_status_change(model_id, previous_status, status, now)
                
                # Save current status
                await self._save_current_status()
                
                return event
                
            except Exception as e:
                logger.error(f"Failed to record uptime event: {e}")
                raise
    
    async def get_uptime_stats(
        self,
        model_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UptimeStats:
        """
        Get uptime statistics for a model.
        
        Args:
            model_id: Model identifier
            start_date: Start of period (defaults to 24 hours ago)
            end_date: End of period (defaults to now)
            
        Returns:
            Uptime statistics
        """
        async with self.lock:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(hours=24)
            if not end_date:
                end_date = datetime.utcnow()
            
            try:
                if not self.uptime_log_file.exists():
                    return self._create_empty_stats(model_id, start_date, end_date)
                
                # Read and analyze uptime events
                total_checks = 0
                successful_checks = 0
                failed_checks = 0
                response_times = []
                last_check_time = None
                
                with open(self.uptime_log_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            event_data = json.loads(line)
                            event_time = datetime.fromisoformat(event_data["timestamp"])
                            
                            # Filter by date range and model
                            if (event_time < start_date or event_time > end_date or 
                                event_data["model_id"] != model_id):
                                continue
                            
                            total_checks += 1
                            
                            if event_data["status"] == ServiceStatus.ONLINE.value:
                                successful_checks += 1
                            else:
                                failed_checks += 1
                            
                            if event_data.get("response_time"):
                                response_times.append(event_data["response_time"])
                            
                            if not last_check_time or event_time > datetime.fromisoformat(last_check_time):
                                last_check_time = event_data["timestamp"]
                            
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            logger.warning(f"Invalid uptime event: {line} - {e}")
                            continue
                
                # Calculate uptime percentage
                uptime_percentage = (successful_checks / total_checks * 100) if total_checks > 0 else 0.0
                
                # Calculate average response time
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
                
                # Get outage statistics
                outage_stats = await self._get_outage_stats(model_id, start_date, end_date)
                
                # Get current status
                current_status = self.current_status.get(model_id, ServiceStatus.UNKNOWN)
                
                return UptimeStats(
                    model_id=model_id,
                    period_start=start_date.isoformat(),
                    period_end=end_date.isoformat(),
                    uptime_percentage=uptime_percentage,
                    total_checks=total_checks,
                    successful_checks=successful_checks,
                    failed_checks=failed_checks,
                    avg_response_time=avg_response_time,
                    total_outages=outage_stats["total_outages"],
                    total_downtime_seconds=outage_stats["total_downtime"],
                    current_status=current_status.value,
                    last_check_time=last_check_time
                )
                
            except Exception as e:
                logger.error(f"Failed to get uptime stats: {e}")
                return self._create_empty_stats(model_id, start_date, end_date)
    
    async def get_current_status(self, model_id: str) -> ServiceStatus:
        """
        Get current status of a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Current service status
        """
        async with self.lock:
            return self.current_status.get(model_id, ServiceStatus.UNKNOWN)
    
    async def get_all_statuses(self) -> Dict[str, ServiceStatus]:
        """
        Get current status of all monitored models.
        
        Returns:
            Dictionary of model_id -> status
        """
        async with self.lock:
            return self.current_status.copy()
    
    async def get_active_outages(self) -> List[OutageEvent]:
        """
        Get all currently active outages.
        
        Returns:
            List of active outage events
        """
        async with self.lock:
            return list(self.active_outages.values())
    
    async def get_outage_history(
        self,
        model_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OutageEvent]:
        """
        Get outage history for models.
        
        Args:
            model_id: Optional model filter
            start_date: Start of period (defaults to 7 days ago)
            end_date: End of period (defaults to now)
            
        Returns:
            List of outage events
        """
        async with self.lock:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()
            
            try:
                if not self.outages_file.exists():
                    return []
                
                with open(self.outages_file, "r") as f:
                    outages_data = json.load(f)
                
                outages = []
                for outage_data in outages_data.values():
                    outage = OutageEvent(**outage_data)
                    
                    # Filter by model if specified
                    if model_id and outage.model_id != model_id:
                        continue
                    
                    # Filter by date range
                    outage_start = datetime.fromisoformat(outage.start_time)
                    if outage_start < start_date or outage_start > end_date:
                        continue
                    
                    outages.append(outage)
                
                return sorted(outages, key=lambda x: x.start_time, reverse=True)
                
            except Exception as e:
                logger.error(f"Failed to get outage history: {e}")
                return []
    
    async def resolve_outage(self, outage_id: str) -> bool:
        """
        Manually resolve an outage.
        
        Args:
            outage_id: Outage identifier
            
        Returns:
            True if outage was resolved, False if not found
        """
        async with self.lock:
            if outage_id in self.active_outages:
                outage = self.active_outages[outage_id]
                outage.resolved = True
                outage.end_time = datetime.utcnow().isoformat()
                
                if outage.end_time:
                    start_time = datetime.fromisoformat(outage.start_time)
                    end_time = datetime.fromisoformat(outage.end_time)
                    outage.duration_seconds = (end_time - start_time).total_seconds()
                
                # Move to resolved outages
                del self.active_outages[outage_id]
                await self._save_outages()
                
                logger.info(f"Resolved outage {outage_id} for model {outage.model_id}")
                return True
            
            return False
    
    # Private helper methods
    
    async def _load_existing_data(self) -> None:
        """Load existing uptime monitoring data."""
        try:
            # Load current status
            if self.current_status_file.exists():
                with open(self.current_status_file, "r") as f:
                    status_data = json.load(f)
                    for model_id, status_str in status_data.items():
                        self.current_status[model_id] = ServiceStatus(status_str)
            
            # Load active outages
            if self.outages_file.exists():
                with open(self.outages_file, "r") as f:
                    outages_data = json.load(f)
                    for outage_id, outage_data in outages_data.items():
                        if not outage_data.get("resolved", False):
                            self.active_outages[outage_id] = OutageEvent(**outage_data)
            
            logger.info("Loaded existing uptime monitoring data")
            
        except Exception as e:
            logger.warning(f"Failed to load existing uptime data: {e}")
    
    async def _save_current_status(self) -> None:
        """Save current status to disk."""
        try:
            status_data = {
                model_id: status.value
                for model_id, status in self.current_status.items()
            }
            
            with open(self.current_status_file, "w") as f:
                json.dump(status_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save current status: {e}")
    
    async def _save_outages(self) -> None:
        """Save outages to disk."""
        try:
            # Load existing outages
            all_outages = {}
            if self.outages_file.exists():
                with open(self.outages_file, "r") as f:
                    all_outages = json.load(f)
            
            # Add active outages
            for outage_id, outage in self.active_outages.items():
                all_outages[outage_id] = outage.to_dict()
            
            with open(self.outages_file, "w") as f:
                json.dump(all_outages, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save outages: {e}")
    
    async def _handle_status_change(
        self,
        model_id: str,
        previous_status: ServiceStatus,
        current_status: ServiceStatus,
        timestamp: datetime
    ) -> None:
        """Handle status changes and manage outages."""
        try:
            # Check if this is a transition to offline/degraded
            if (previous_status in [ServiceStatus.ONLINE, ServiceStatus.UNKNOWN] and 
                current_status in [ServiceStatus.OFFLINE, ServiceStatus.DEGRADED]):
                
                # Start a new outage
                outage_id = f"{model_id}_{int(timestamp.timestamp())}"
                severity = "critical" if current_status == ServiceStatus.OFFLINE else "major"
                
                outage = OutageEvent(
                    outage_id=outage_id,
                    model_id=model_id,
                    start_time=timestamp.isoformat(),
                    end_time=None,
                    duration_seconds=None,
                    severity=severity,
                    description=f"Model {model_id} status changed to {current_status.value}",
                    resolved=False
                )
                
                self.active_outages[outage_id] = outage
                await self._save_outages()
                
                logger.warning(f"Started outage {outage_id} for model {model_id}: {current_status.value}")
            
            # Check if this is a transition back to online
            elif (previous_status in [ServiceStatus.OFFLINE, ServiceStatus.DEGRADED] and 
                  current_status == ServiceStatus.ONLINE):
                
                # End any active outages for this model
                for outage_id, outage in list(self.active_outages.items()):
                    if outage.model_id == model_id:
                        outage.resolved = True
                        outage.end_time = timestamp.isoformat()
                        
                        start_time = datetime.fromisoformat(outage.start_time)
                        outage.duration_seconds = (timestamp - start_time).total_seconds()
                        
                        del self.active_outages[outage_id]
                        
                        logger.info(f"Resolved outage {outage_id} for model {model_id} after {outage.duration_seconds:.1f}s")
                
                await self._save_outages()
            
        except Exception as e:
            logger.error(f"Failed to handle status change: {e}")
    
    async def _get_outage_stats(
        self,
        model_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get outage statistics for a period."""
        try:
            outages = await self.get_outage_history(model_id, start_date, end_date)
            
            total_outages = len(outages)
            total_downtime = sum(
                outage.duration_seconds or 0
                for outage in outages
                if outage.resolved
            )
            
            return {
                "total_outages": total_outages,
                "total_downtime": total_downtime
            }
            
        except Exception as e:
            logger.error(f"Failed to get outage stats: {e}")
            return {"total_outages": 0, "total_downtime": 0.0}
    
    def _create_empty_stats(
        self,
        model_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> UptimeStats:
        """Create empty uptime stats."""
        current_status = self.current_status.get(model_id, ServiceStatus.UNKNOWN)
        
        return UptimeStats(
            model_id=model_id,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            uptime_percentage=0.0,
            total_checks=0,
            successful_checks=0,
            failed_checks=0,
            avg_response_time=0.0,
            total_outages=0,
            total_downtime_seconds=0.0,
            current_status=current_status.value,
            last_check_time=None
        )