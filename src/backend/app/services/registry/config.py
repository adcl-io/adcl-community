# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Registry Configuration Loader

Single responsibility: Load and manage registry configurations from registries.conf
"""

import configparser
import logging
from pathlib import Path
from typing import Dict

from app.models.registry_models import RegistryConfig, TrustLevel

logger = logging.getLogger(__name__)


class RegistryConfigLoader:
    """Loads registry configurations from INI-style registries.conf"""

    def __init__(self, config_path: Path):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to registries.conf file
        """
        self.config_path = config_path

    def load(self) -> Dict[str, RegistryConfig]:
        """
        Load registry configurations from registries.conf

        Returns:
            Dictionary of registry configs keyed by name
        """
        registries = {}

        if not self.config_path.exists():
            logger.warning(f"No registries.conf found at {self.config_path}")
            return registries

        config = configparser.ConfigParser()
        config.read(self.config_path)

        for section in config.sections():
            try:
                reg_config = RegistryConfig(
                    name=section,
                    display_name=config.get(section, "name", fallback=section),
                    url=config.get(section, "url"),
                    enabled=config.getboolean(section, "enabled", fallback=True),
                    priority=config.getint(section, "priority", fallback=50),
                    gpgcheck=config.getboolean(section, "gpgcheck", fallback=False),
                    gpgkey=config.get(section, "gpgkey", fallback=None),
                    trust_level=TrustLevel(config.get(section, "trust_level", fallback="unknown")),
                    type=config.get(section, "type", fallback="adcl-v2")
                )
                registries[section] = reg_config
                logger.info(f"Loaded registry: {section} ({reg_config.url})")
            except Exception as e:
                logger.error(f"Failed to load registry {section}: {e}")

        return registries

    def save(self, registries: Dict[str, RegistryConfig]):
        """
        Save registry configurations back to registries.conf

        Persists runtime changes (enable/disable) to disk.

        Args:
            registries: Dictionary of registry configurations
        """
        config = configparser.ConfigParser()

        for name, reg_config in registries.items():
            config[name] = {
                "name": reg_config.display_name,
                "url": reg_config.url,
                "enabled": str(reg_config.enabled).lower(),
                "priority": str(reg_config.priority),
                "type": reg_config.type,
                "trust_level": reg_config.trust_level.value,
            }

            if reg_config.gpgcheck:
                config[name]["gpgcheck"] = "true"
                if reg_config.gpgkey:
                    config[name]["gpgkey"] = reg_config.gpgkey

        with open(self.config_path, "w") as f:
            config.write(f)

        logger.info(f"Saved {len(registries)} registries to {self.config_path}")
