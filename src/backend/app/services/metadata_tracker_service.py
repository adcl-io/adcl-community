# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Metadata Tracker Service - Tracks model configuration changes and timestamps.

Single responsibility: Track creation and modification timestamps for model configurations.
Provides freshness calculation based on last update time.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum

from app.core.logging import get_service_logger

logger = get_service_logger("metadata_tracker")


class FreshnessLevel(str, Enum):
    """Model freshness levels based on last update time"""
    NEW = "new"  # Created within last 7 days
    RECENTLY_UPDATED = "recently_updated"  # Updated within last 7 days
    NORMAL = "normal"  # Updated 7-90 days ago
    STALE = "stale"  # Not updated in over 90 days


class ModelTimestamps:
    """Container for model timestamp data"""
    
    def __init__(self, created_at: Optional[datetime] = None, last_updated: Optional[datetime] = None):
        self.created_at = created_at
        self.last_updated = last_updated
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary with ISO format timestamps"""
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class MetadataTrackerService:
    """
    Tracks model configuration changes and timestamps.
    
    Responsibilities:
    - Record model creation timestamps
    - Record model update timestamps
    - Calculate freshness levels based on timestamps
    - Provide timestamp data for model cards
    """
    
    def __init__(self):
        """Initialize MetadataTrackerService."""
        logger.info("MetadataTrackerService initialized")
    
    def record_model_creation(self, model_id: str) -> ModelTimestamps:
        """
        Record when a model configuration is created.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelTimestamps with created_at set to current time
        """
        now = datetime.utcnow()
        timestamps = ModelTimestamps(created_at=now, last_updated=now)
        
        logger.info(f"Recorded creation timestamp for model: {model_id}")
        return timestamps
    
    def record_model_update(self, model_id: str, change_type: str) -> datetime:
        """
        Record when a model configuration is updated.
        
        Args:
            model_id: Model identifier
            change_type: Type of change (e.g., "api_key", "parameters", "settings")
            
        Returns:
            Current timestamp
        """
        now = datetime.utcnow()
        
        logger.info(f"Recorded update timestamp for model: {model_id}, change_type: {change_type}")
        return now
    
    def get_model_timestamps(self, created_at: Optional[datetime], last_updated: Optional[datetime]) -> ModelTimestamps:
        """
        Get timestamps for a model, handling migration for models without timestamps.
        
        Args:
            created_at: Creation timestamp (may be None for legacy models)
            last_updated: Last update timestamp (may be None for legacy models)
            
        Returns:
            ModelTimestamps with appropriate defaults for legacy models
        """
        # For legacy models without timestamps, use a reasonable default
        # We can't know the actual creation time, so we mark them as "old"
        if created_at is None and last_updated is None:
            # Use a date far in the past to indicate legacy model
            legacy_date = datetime(2024, 1, 1, 0, 0, 0)
            return ModelTimestamps(created_at=legacy_date, last_updated=legacy_date)
        
        return ModelTimestamps(created_at=created_at, last_updated=last_updated)
    
    def calculate_freshness(self, last_updated: Optional[datetime], created_at: Optional[datetime] = None) -> FreshnessLevel:
        """
        Calculate freshness level based on last update time.
        
        Args:
            last_updated: Last update timestamp
            created_at: Creation timestamp (optional, used to determine if model is new)
            
        Returns:
            FreshnessLevel indicating how fresh the model configuration is
            
        Note: Boundary conditions - exactly 7 days is NORMAL, exactly 90 days is NORMAL
        """
        now = datetime.utcnow()
        
        # Handle models without timestamps (legacy models)
        if last_updated is None:
            return FreshnessLevel.STALE
        
        # Calculate time since last update
        time_since_update = now - last_updated
        
        # Check if model is new (created within last 7 days, exclusive)
        # Exactly 7 days is NORMAL per requirements
        if created_at and (now - created_at) < timedelta(days=7):
            return FreshnessLevel.NEW
        
        # Check if recently updated (within last 7 days, exclusive)
        # Exactly 7 days is NORMAL per requirements
        if time_since_update < timedelta(days=7):
            return FreshnessLevel.RECENTLY_UPDATED
        
        # Check if stale (not updated in over 90 days, exclusive)
        # Exactly 90 days is NORMAL per requirements
        if time_since_update > timedelta(days=90):
            return FreshnessLevel.STALE
        
        # Normal freshness (7-90 days inclusive)
        return FreshnessLevel.NORMAL
    
    def format_relative_time(self, timestamp: Optional[datetime]) -> str:
        """
        Format timestamp as relative time string.
        
        Args:
            timestamp: Timestamp to format
            
        Returns:
            Human-readable relative time string (e.g., "2 hours ago", "3 days ago")
        """
        if timestamp is None:
            return "Unknown"
        
        now = datetime.utcnow()
        delta = now - timestamp
        
        # Less than 1 hour
        if delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            if minutes <= 1:
                return "Just now"
            return f"{minutes} minutes ago"
        
        # Less than 24 hours
        if delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            if hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        
        # Less than 7 days
        if delta < timedelta(days=7):
            days = delta.days
            if days == 1:
                return "1 day ago"
            return f"{days} days ago"
        
        # Less than 30 days
        if delta < timedelta(days=30):
            weeks = delta.days // 7
            if weeks == 1:
                return "1 week ago"
            return f"{weeks} weeks ago"
        
        # More than 30 days - show actual date
        return timestamp.strftime("%b %d, %Y")
    
    def should_show_new_badge(self, created_at: Optional[datetime]) -> bool:
        """
        Determine if a "New" badge should be shown for a model.
        
        Args:
            created_at: Model creation timestamp
            
        Returns:
            True if model was created within last 7 days (exclusive)
            
        Note: Exactly 7 days is NORMAL per requirements
        """
        if created_at is None:
            return False
        
        now = datetime.utcnow()
        return (now - created_at) < timedelta(days=7)
    
    def should_show_recently_updated_badge(self, last_updated: Optional[datetime], created_at: Optional[datetime]) -> bool:
        """
        Determine if a "Recently Updated" badge should be shown for a model.
        
        Args:
            last_updated: Last update timestamp
            created_at: Creation timestamp
            
        Returns:
            True if model was updated within last 7 days (but not newly created)
            
        Note: Exactly 7 days is NORMAL per requirements
        """
        if last_updated is None:
            return False
        
        now = datetime.utcnow()
        
        # Don't show "Recently Updated" if model is new
        if created_at and (now - created_at) < timedelta(days=7):
            return False
        
        # Show if updated within last 7 days (exclusive)
        return (now - last_updated) < timedelta(days=7)
    
    def should_show_stale_indicator(self, last_updated: Optional[datetime]) -> bool:
        """
        Determine if a "Stale" indicator should be shown for a model.
        
        Args:
            last_updated: Last update timestamp
            
        Returns:
            True if model hasn't been updated in over 90 days
        """
        if last_updated is None:
            return True  # Models without timestamps are considered stale
        
        now = datetime.utcnow()
        return (now - last_updated) > timedelta(days=90)
