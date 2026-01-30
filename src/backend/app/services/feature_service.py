# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Feature Service - Feature Toggle Management

Manages which features are enabled based on configs/auto-install.json.
Provides centralized feature flag checking for API route gating and UI feature toggling.

Architecture:
- Reads feature flags from auto-install.json at startup
- Provides is_enabled() method for feature checks
- Supports hot-reloading when edition changes
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FeatureService:
    """
    Feature toggle service for managing product editions.

    Usage:
        feature_service = FeatureService("configs/auto-install.json")

        if feature_service.is_enabled("red_team"):
            # Enable red team routes
            pass
    """

    def __init__(self, config_path: str = "configs/auto-install.json"):
        """
        Initialize feature service with config file.

        Args:
            config_path: Path to auto-install.json config file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.features: Dict[str, Dict[str, Any]] = {}
        self.edition: str = "unknown"

        self._load_config()

    def _load_config(self):
        """Load configuration from auto-install.json"""
        try:
            if not self.config_path.exists():
                logger.error(f"Config file not found: {self.config_path}")
                # Fallback to minimal config
                self.config = self._get_fallback_config()
                self.features = self.config.get("features", {})
                self.edition = self.config.get("edition", "unknown")
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self.features = self.config.get("features", {})
            self.edition = self.config.get("edition", "unknown")

            logger.info(f"Loaded feature config: edition={self.edition}")

            # Log enabled features
            enabled = [name for name, cfg in self.features.items() if cfg.get("enabled")]
            logger.info(f"Enabled features: {', '.join(enabled)}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            self.config = self._get_fallback_config()
            self.features = self.config.get("features", {})
            self.edition = "unknown"
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = self._get_fallback_config()
            self.features = self.config.get("features", {})
            self.edition = "unknown"

    def _get_fallback_config(self) -> Dict[str, Any]:
        """
        Get fallback config when auto-install.json is missing or invalid.
        Defaults to community edition (core platform only).
        """
        return {
            "version": "2.0",
            "edition": "community",
            "features": {
                "core_platform": {
                    "enabled": True,
                    "locked": True,
                    "description": "Core platform - always enabled"
                },
                "red_team": {
                    "enabled": False,
                    "locked": False,
                    "description": "Red team features - disabled by default"
                },
                "dev_tools": {
                    "enabled": False,
                    "locked": False,
                    "description": "Development tools - disabled by default"
                }
            }
        }

    def reload(self):
        """
        Reload configuration from disk.

        Useful after edition switching to pick up new config without restart.
        """
        logger.info("Reloading feature configuration...")
        self._load_config()

    def is_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled.

        Args:
            feature_name: Name of the feature (e.g., "red_team", "core_platform")

        Returns:
            True if feature is enabled, False otherwise

        Example:
            if feature_service.is_enabled("red_team"):
                # Red team features are available
        """
        feature = self.features.get(feature_name)
        if feature is None:
            logger.warning(f"Unknown feature: {feature_name}")
            return False

        return feature.get("enabled", False)

    def is_component_enabled(self, feature_name: str, component_name: str) -> bool:
        """
        Check if a specific component within a feature is enabled.

        Args:
            feature_name: Name of the feature (e.g., "red_team")
            component_name: Name of the component (e.g., "attack_playground")

        Returns:
            True if component is enabled, False otherwise

        Example:
            if feature_service.is_component_enabled("red_team", "attack_playground"):
                # Attack playground is available
        """
        if not self.is_enabled(feature_name):
            return False

        feature = self.features.get(feature_name, {})
        components = feature.get("components", {})

        return components.get(component_name, False)

    def get_enabled_features(self) -> List[str]:
        """
        Get list of all enabled features.

        Returns:
            List of enabled feature names
        """
        return [
            name for name, config in self.features.items()
            if config.get("enabled", False)
        ]

    def get_edition(self) -> str:
        """
        Get current product edition.

        Returns:
            Edition name (e.g., "community", "red-team", "custom")
        """
        return self.edition

    def get_feature_info(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full information about a feature.

        Args:
            feature_name: Name of the feature

        Returns:
            Feature configuration dict, or None if not found
        """
        return self.features.get(feature_name)

    def get_all_features(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all feature configurations.

        Returns:
            Dict mapping feature names to their configurations
        """
        return self.features.copy()

    def is_locked(self, feature_name: str) -> bool:
        """
        Check if a feature is locked (cannot be disabled).

        Args:
            feature_name: Name of the feature

        Returns:
            True if feature is locked, False otherwise
        """
        feature = self.features.get(feature_name)
        if feature is None:
            return False

        return feature.get("locked", False)

    def get_packages_for_feature(self, feature_name: str) -> List[str]:
        """
        Get list of MCP packages required for a feature.

        Args:
            feature_name: Name of the feature

        Returns:
            List of package names needed for this feature

        Note:
            This maps features to their required MCP server packages by reading
            the package_category field from features configuration, then finding
            all packages with that category in auto_install.packages.
            Used by auto-install to enable/disable packages based on edition.
        """
        # Get the package category for this feature from config
        feature = self.features.get(feature_name, {})
        category = feature.get("package_category")

        if not category:
            logger.warning(f"No package_category defined for feature '{feature_name}'")
            return []

        # Get packages from config that match this category
        auto_install = self.config.get("auto_install", {})
        packages = auto_install.get("packages", {})

        return [
            pkg_name for pkg_name, pkg_config in packages.items()
            if pkg_config.get("category") == category
        ]

    def __repr__(self) -> str:
        """String representation of FeatureService"""
        enabled_count = len(self.get_enabled_features())
        total_count = len(self.features)
        return f"<FeatureService edition={self.edition} enabled={enabled_count}/{total_count}>"


# Global singleton instance
# Initialized in main.py at startup
_feature_service_instance: Optional[FeatureService] = None


def get_feature_service() -> FeatureService:
    """
    Get the global FeatureService instance.

    Returns:
        FeatureService singleton instance

    Raises:
        RuntimeError: If FeatureService not initialized

    Usage:
        from app.services.feature_service import get_feature_service

        feature_service = get_feature_service()
        if feature_service.is_enabled("red_team"):
            # ...
    """
    global _feature_service_instance

    if _feature_service_instance is None:
        raise RuntimeError(
            "FeatureService not initialized. "
            "Call init_feature_service() in main.py startup"
        )

    return _feature_service_instance


def init_feature_service(config_path: str = "configs/auto-install.json") -> FeatureService:
    """
    Initialize the global FeatureService instance.

    Args:
        config_path: Path to auto-install.json

    Returns:
        Initialized FeatureService instance

    Note:
        This should be called once in main.py at application startup.
    """
    global _feature_service_instance

    _feature_service_instance = FeatureService(config_path)
    logger.info(f"FeatureService initialized: {_feature_service_instance}")

    return _feature_service_instance
