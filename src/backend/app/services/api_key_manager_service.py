# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
API Key Manager Service - Manages API key rotation and load balancing.

Provides:
- Multiple API key support per provider
- Automatic key rotation for high-availability
- Load balancing across multiple keys
- Key expiration tracking and alerts
- Usage tracking per key
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.logging import get_service_logger
from app.core.errors import ValidationError

logger = get_service_logger("api_key_manager")


class KeyStatus(str, Enum):
    """API key status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class APIKey:
    """API key configuration"""
    key_id: str
    provider: str
    key_value: str  # Encrypted or masked
    status: KeyStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    rate_limit_reset: Optional[datetime] = None
    priority: int = 0  # Higher priority keys used first
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key_id": self.key_id,
            "provider": self.provider,
            "key_value": "***MASKED***",  # Never expose actual key
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "error_count": self.error_count,
            "rate_limit_reset": self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            "priority": self.priority
        }


class APIKeyManagerService:
    """
    Manages API keys with rotation and load balancing.
    
    Responsibilities:
    - Store and manage multiple API keys per provider
    - Rotate keys automatically for load balancing
    - Track key usage and errors
    - Handle rate limiting and key expiration
    - Provide alerts for key issues
    """

    def __init__(self, config_path: Path):
        """
        Initialize APIKeyManagerService.
        
        Args:
            config_path: Path to API keys configuration file
        """
        self.config_path = config_path
        self.keys: Dict[str, List[APIKey]] = {}  # provider -> list of keys
        self.lock = asyncio.Lock()
        self.rotation_index: Dict[str, int] = {}  # provider -> current key index
        
        logger.info(f"APIKeyManagerService initialized with config: {config_path}")

    async def load_keys(self) -> None:
        """Load API keys from configuration file"""
        async with self.lock:
            try:
                if not self.config_path.exists():
                    logger.warning(f"API keys config not found at {self.config_path}")
                    self.keys = {}
                    return

                with open(self.config_path, "r", encoding='utf-8') as f:
                    config_data = json.load(f)

                # Parse keys by provider
                self.keys = {}
                for provider, keys_data in config_data.get("providers", {}).items():
                    provider_keys = []
                    
                    for key_data in keys_data.get("keys", []):
                        api_key = APIKey(
                            key_id=key_data["key_id"],
                            provider=provider,
                            key_value=key_data["key_value"],
                            status=KeyStatus(key_data.get("status", "active")),
                            created_at=datetime.fromisoformat(key_data["created_at"]),
                            expires_at=datetime.fromisoformat(key_data["expires_at"]) if key_data.get("expires_at") else None,
                            last_used=datetime.fromisoformat(key_data["last_used"]) if key_data.get("last_used") else None,
                            usage_count=key_data.get("usage_count", 0),
                            error_count=key_data.get("error_count", 0),
                            rate_limit_reset=datetime.fromisoformat(key_data["rate_limit_reset"]) if key_data.get("rate_limit_reset") else None,
                            priority=key_data.get("priority", 0)
                        )
                        provider_keys.append(api_key)
                    
                    # Sort by priority (higher first)
                    provider_keys.sort(key=lambda k: k.priority, reverse=True)
                    self.keys[provider] = provider_keys
                    self.rotation_index[provider] = 0

                logger.info(f"Loaded {sum(len(keys) for keys in self.keys.values())} API keys for {len(self.keys)} providers")

            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")
                raise ValidationError(f"Failed to load API keys: {e}", field="config")

    async def save_keys(self) -> None:
        """Save API keys to configuration file"""
        async with self.lock:
            try:
                config_data = {
                    "providers": {}
                }

                for provider, keys in self.keys.items():
                    config_data["providers"][provider] = {
                        "keys": [
                            {
                                "key_id": key.key_id,
                                "key_value": key.key_value,
                                "status": key.status.value,
                                "created_at": key.created_at.isoformat(),
                                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                                "last_used": key.last_used.isoformat() if key.last_used else None,
                                "usage_count": key.usage_count,
                                "error_count": key.error_count,
                                "rate_limit_reset": key.rate_limit_reset.isoformat() if key.rate_limit_reset else None,
                                "priority": key.priority
                            }
                            for key in keys
                        ]
                    }

                with open(self.config_path, "w", encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2)

                logger.info("Saved API keys configuration")

            except Exception as e:
                logger.error(f"Failed to save API keys: {e}")
                raise ValidationError(f"Failed to save API keys: {e}", field="config")

    async def get_key(self, provider: str, strategy: str = "round_robin") -> Optional[APIKey]:
        """
        Get an API key for a provider using specified strategy.
        
        Args:
            provider: Provider name (anthropic, openai, etc.)
            strategy: Load balancing strategy (round_robin, least_used, priority)
            
        Returns:
            API key or None if no available keys
        """
        async with self.lock:
            if provider not in self.keys or not self.keys[provider]:
                logger.warning(f"No API keys configured for provider: {provider}")
                return None

            # Filter available keys
            available_keys = [
                key for key in self.keys[provider]
                if self._is_key_available(key)
            ]

            if not available_keys:
                logger.warning(f"No available API keys for provider: {provider}")
                return None

            # Select key based on strategy
            if strategy == "round_robin":
                selected_key = self._select_round_robin(provider, available_keys)
            elif strategy == "least_used":
                selected_key = self._select_least_used(available_keys)
            elif strategy == "priority":
                selected_key = available_keys[0]  # Already sorted by priority
            else:
                selected_key = available_keys[0]

            # Update usage
            selected_key.last_used = datetime.utcnow()
            selected_key.usage_count += 1

            logger.info(f"Selected API key {selected_key.key_id} for provider {provider} (strategy: {strategy})")
            return selected_key

    async def record_success(self, key_id: str) -> None:
        """Record successful API call"""
        async with self.lock:
            key = self._find_key_by_id(key_id)
            if key:
                # Reset error count on success
                key.error_count = 0
                logger.debug(f"Recorded success for key {key_id}")

    async def record_error(self, key_id: str, error_type: str = "general") -> None:
        """Record API call error"""
        async with self.lock:
            key = self._find_key_by_id(key_id)
            if key:
                key.error_count += 1
                
                # Handle rate limiting
                if error_type == "rate_limit":
                    key.status = KeyStatus.RATE_LIMITED
                    key.rate_limit_reset = datetime.utcnow() + timedelta(minutes=5)
                    logger.warning(f"Key {key_id} rate limited, reset at {key.rate_limit_reset}")
                
                # Disable key if too many errors
                elif key.error_count >= 10:
                    key.status = KeyStatus.ERROR
                    logger.error(f"Key {key_id} disabled due to excessive errors ({key.error_count})")

    async def add_key(self, provider: str, key_value: str, priority: int = 0, expires_at: Optional[datetime] = None) -> APIKey:
        """Add a new API key"""
        async with self.lock:
            # Generate key ID
            key_id = f"{provider}_{len(self.keys.get(provider, []))}"
            
            api_key = APIKey(
                key_id=key_id,
                provider=provider,
                key_value=key_value,
                status=KeyStatus.ACTIVE,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                priority=priority
            )

            if provider not in self.keys:
                self.keys[provider] = []
                self.rotation_index[provider] = 0

            self.keys[provider].append(api_key)
            
            # Re-sort by priority
            self.keys[provider].sort(key=lambda k: k.priority, reverse=True)

            await self.save_keys()
            
            logger.info(f"Added new API key {key_id} for provider {provider}")
            return api_key

    async def remove_key(self, key_id: str) -> bool:
        """Remove an API key"""
        async with self.lock:
            for provider, keys in self.keys.items():
                for i, key in enumerate(keys):
                    if key.key_id == key_id:
                        keys.pop(i)
                        await self.save_keys()
                        logger.info(f"Removed API key {key_id}")
                        return True
            
            logger.warning(f"API key {key_id} not found")
            return False

    async def get_key_status(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get status of all keys or keys for a specific provider"""
        async with self.lock:
            if provider:
                if provider not in self.keys:
                    return {"provider": provider, "keys": []}
                
                return {
                    "provider": provider,
                    "keys": [key.to_dict() for key in self.keys[provider]]
                }
            else:
                return {
                    "providers": {
                        prov: [key.to_dict() for key in keys]
                        for prov, keys in self.keys.items()
                    }
                }

    async def check_expiring_keys(self, days_threshold: int = 7) -> List[APIKey]:
        """Check for keys expiring soon"""
        expiring_keys = []
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
        
        async with self.lock:
            for keys in self.keys.values():
                for key in keys:
                    if key.expires_at and key.expires_at <= threshold_date:
                        expiring_keys.append(key)
        
        if expiring_keys:
            logger.warning(f"Found {len(expiring_keys)} keys expiring within {days_threshold} days")
        
        return expiring_keys

    # Private helper methods

    def _is_key_available(self, key: APIKey) -> bool:
        """Check if a key is available for use"""
        # Check status
        if key.status not in [KeyStatus.ACTIVE, KeyStatus.RATE_LIMITED]:
            return False
        
        # Check expiration
        if key.expires_at and key.expires_at <= datetime.utcnow():
            key.status = KeyStatus.EXPIRED
            return False
        
        # Check rate limit reset
        if key.status == KeyStatus.RATE_LIMITED:
            if key.rate_limit_reset and key.rate_limit_reset <= datetime.utcnow():
                key.status = KeyStatus.ACTIVE
                key.rate_limit_reset = None
                logger.info(f"Key {key.key_id} rate limit reset")
                return True
            return False
        
        return True

    def _select_round_robin(self, provider: str, available_keys: List[APIKey]) -> APIKey:
        """Select key using round-robin strategy"""
        if provider not in self.rotation_index:
            self.rotation_index[provider] = 0
        
        index = self.rotation_index[provider] % len(available_keys)
        self.rotation_index[provider] = (index + 1) % len(available_keys)
        
        return available_keys[index]

    def _select_least_used(self, available_keys: List[APIKey]) -> APIKey:
        """Select key with least usage"""
        return min(available_keys, key=lambda k: k.usage_count)

    def _find_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Find a key by its ID"""
        for keys in self.keys.values():
            for key in keys:
                if key.key_id == key_id:
                    return key
        return None
