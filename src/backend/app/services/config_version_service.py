# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Configuration Version Service - Version Control for Edition Configurations

Manages version-controlled edition configurations with metadata tracking,
change history, and optional Git integration.

Features:
- Version metadata tracking (created_at, updated_at, changelog)
- Configuration validation and schema versioning
- Git integration for configuration changes
- Backup and rollback capabilities
- Audit trail for configuration modifications

Architecture:
- Reads enhanced edition configs with metadata section
- Tracks changes through changelog entries
- Optionally commits configuration changes to Git
- Provides validation and migration support
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfigVersionService:
    """
    Service for managing version-controlled edition configurations.
    
    Handles configuration metadata, change tracking, and Git integration
    for ADCL edition configuration files.
    """

    def __init__(self, configs_dir: str = "configs"):
        """
        Initialize configuration version service.

        Args:
            configs_dir: Path to configs directory containing editions/
        """
        self.configs_dir = Path(configs_dir)
        self.editions_dir = self.configs_dir / "editions"
        self.backups_dir = self.configs_dir / "backups"
        self.current_schema_version = "2.1"
        
        # Ensure directories exist
        self.editions_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def load_edition_config(self, edition: str) -> Dict[str, Any]:
        """
        Load edition configuration with metadata validation.

        Args:
            edition: Edition name (e.g., "community", "red-team")

        Returns:
            Edition configuration dict with metadata

        Raises:
            FileNotFoundError: If edition file doesn't exist
            ValueError: If configuration is invalid
        """
        edition_file = self.editions_dir / f"{edition}.json"
        
        if not edition_file.exists():
            raise FileNotFoundError(f"Edition configuration not found: {edition}")

        try:
            with open(edition_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in edition config {edition}: {e}")

        # Validate configuration structure
        self._validate_config(config, edition)
        
        return config

    def save_edition_config(self, edition: str, config: Dict[str, Any], 
                          author: str = "system", changes: List[str] = None) -> Dict[str, Any]:
        """
        Save edition configuration with version metadata update.

        Args:
            edition: Edition name
            config: Configuration dictionary
            author: Author of the changes
            changes: List of change descriptions

        Returns:
            Updated configuration with new metadata
        """
        # Update metadata
        now = datetime.now(timezone.utc).isoformat()
        
        # Ensure metadata section exists
        if "metadata" not in config:
            config["metadata"] = {
                "created_at": now,
                "updated_at": now,
                "created_by": author,
                "updated_by": author,
                "changelog": [],
                "schema_version": self.current_schema_version,
                "git_tracking": {
                    "enabled": True,
                    "auto_commit": False,
                    "commit_message_template": "feat: Update {edition} edition configuration"
                }
            }
        else:
            # Update existing metadata
            config["metadata"]["updated_at"] = now
            config["metadata"]["updated_by"] = author
            
            # Ensure schema version is current
            config["metadata"]["schema_version"] = self.current_schema_version

        # Add changelog entry if changes provided
        if changes:
            # Increment version
            current_version = config.get("version", "2.0")
            version_parts = current_version.split(".")
            if len(version_parts) >= 2:
                minor = int(version_parts[1]) + 1
                new_version = f"{version_parts[0]}.{minor}"
            else:
                new_version = f"{current_version}.1"
            
            config["version"] = new_version
            
            # Add changelog entry
            changelog_entry = {
                "version": new_version,
                "date": now,
                "author": author,
                "changes": changes
            }
            
            if "changelog" not in config["metadata"]:
                config["metadata"]["changelog"] = []
            
            config["metadata"]["changelog"].insert(0, changelog_entry)
            
            # Keep only last 10 changelog entries
            config["metadata"]["changelog"] = config["metadata"]["changelog"][:10]

        # Validate before saving
        self._validate_config(config, edition)
        
        # Save configuration
        edition_file = self.editions_dir / f"{edition}.json"
        with open(edition_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved edition config: {edition} v{config.get('version', 'unknown')}")
        
        # Git integration if enabled
        git_tracking = config.get("metadata", {}).get("git_tracking", {})
        if git_tracking.get("enabled", False):
            self._git_track_changes(edition, config, changes or ["Configuration updated"])

        return config

    def get_config_history(self, edition: str) -> List[Dict[str, Any]]:
        """
        Get version history for an edition configuration.

        Args:
            edition: Edition name

        Returns:
            List of changelog entries, most recent first
        """
        try:
            config = self.load_edition_config(edition)
            return config.get("metadata", {}).get("changelog", [])
        except (FileNotFoundError, ValueError):
            return []

    def compare_configs(self, edition1: str, edition2: str) -> Dict[str, Any]:
        """
        Compare two edition configurations.

        Args:
            edition1: First edition name
            edition2: Second edition name

        Returns:
            Comparison result with differences
        """
        try:
            config1 = self.load_edition_config(edition1)
            config2 = self.load_edition_config(edition2)
        except (FileNotFoundError, ValueError) as e:
            return {"error": str(e)}

        differences = {
            "features": {},
            "packages": {},
            "metadata": {}
        }

        # Compare features
        features1 = config1.get("features", {})
        features2 = config2.get("features", {})
        all_features = set(features1.keys()) | set(features2.keys())
        
        for feature in all_features:
            f1_enabled = features1.get(feature, {}).get("enabled", False)
            f2_enabled = features2.get(feature, {}).get("enabled", False)
            
            if f1_enabled != f2_enabled:
                differences["features"][feature] = {
                    edition1: f1_enabled,
                    edition2: f2_enabled
                }

        # Compare packages
        packages1 = config1.get("auto_install", {}).get("packages", {})
        packages2 = config2.get("auto_install", {}).get("packages", {})
        all_packages = set(packages1.keys()) | set(packages2.keys())
        
        for package in all_packages:
            p1_enabled = packages1.get(package, {}).get("enabled", False)
            p2_enabled = packages2.get(package, {}).get("enabled", False)
            
            if p1_enabled != p2_enabled:
                differences["packages"][package] = {
                    edition1: p1_enabled,
                    edition2: p2_enabled
                }

        # Compare versions
        differences["metadata"]["versions"] = {
            edition1: config1.get("version", "unknown"),
            edition2: config2.get("version", "unknown")
        }

        return {
            "edition1": edition1,
            "edition2": edition2,
            "differences": differences,
            "identical": not any(differences["features"].values() or 
                               differences["packages"].values())
        }

    def backup_config(self, edition: str) -> str:
        """
        Create backup of edition configuration.

        Args:
            edition: Edition name

        Returns:
            Path to backup file
        """
        try:
            config = self.load_edition_config(edition)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Cannot backup invalid config: {e}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backups_dir / f"{edition}-{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created backup: {backup_file}")
        return str(backup_file)

    def restore_config(self, edition: str, backup_file: str, 
                      author: str = "system") -> Dict[str, Any]:
        """
        Restore edition configuration from backup.

        Args:
            edition: Edition name
            backup_file: Path to backup file
            author: Author performing restore

        Returns:
            Restored configuration
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        try:
            with open(backup_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid backup file: {e}")

        # Save as current config with restore note
        changes = [f"Restored from backup: {backup_path.name}"]
        restored_config = self.save_edition_config(edition, config, author, changes)
        
        logger.info(f"Restored {edition} from backup: {backup_file}")
        return restored_config

    def validate_all_configs(self) -> Dict[str, Any]:
        """
        Validate all edition configurations.

        Returns:
            Validation results for all editions
        """
        results = {}
        
        for edition_file in self.editions_dir.glob("*.json"):
            if edition_file.name.startswith("."):
                continue
                
            edition = edition_file.stem
            try:
                config = self.load_edition_config(edition)
                results[edition] = {
                    "valid": True,
                    "version": config.get("version", "unknown"),
                    "schema_version": config.get("metadata", {}).get("schema_version", "unknown"),
                    "last_updated": config.get("metadata", {}).get("updated_at", "unknown")
                }
            except (FileNotFoundError, ValueError) as e:
                results[edition] = {
                    "valid": False,
                    "error": str(e)
                }

        return results

    def migrate_config_schema(self, edition: str, target_version: str = None) -> Dict[str, Any]:
        """
        Migrate edition configuration to current schema version.

        Args:
            edition: Edition name
            target_version: Target schema version (defaults to current)

        Returns:
            Migration result
        """
        target_version = target_version or self.current_schema_version
        
        try:
            config = self.load_edition_config(edition)
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": str(e)}

        current_version = config.get("metadata", {}).get("schema_version", "2.0")
        
        if current_version == target_version:
            return {"success": True, "message": "Already at target schema version"}

        # Create backup before migration
        backup_file = self.backup_config(edition)
        
        try:
            # Perform migration based on version changes
            migrations_applied = []
            
            if current_version == "2.0" and target_version >= "2.1":
                # Add metadata section if missing
                if "metadata" not in config:
                    config["metadata"] = {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "created_by": "migration",
                        "updated_by": "migration",
                        "changelog": [{
                            "version": config.get("version", "2.0"),
                            "date": datetime.now(timezone.utc).isoformat(),
                            "author": "migration",
                            "changes": ["Initial configuration"]
                        }],
                        "schema_version": "2.1",
                        "git_tracking": {
                            "enabled": True,
                            "auto_commit": False,
                            "commit_message_template": "feat: Update {edition} edition configuration"
                        }
                    }
                    migrations_applied.append("Added metadata section")

            # Save migrated config
            changes = [f"Schema migration: {current_version} → {target_version}"] + migrations_applied
            migrated_config = self.save_edition_config(edition, config, "migration", changes)
            
            return {
                "success": True,
                "from_version": current_version,
                "to_version": target_version,
                "migrations_applied": migrations_applied,
                "backup_file": backup_file
            }
            
        except Exception as e:
            logger.error(f"Migration failed for {edition}: {e}")
            return {
                "success": False,
                "error": f"Migration failed: {e}",
                "backup_file": backup_file
            }

    def _validate_config(self, config: Dict[str, Any], edition: str):
        """
        Validate edition configuration structure.

        Args:
            config: Configuration dictionary
            edition: Edition name for error messages

        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ["version", "edition", "features", "auto_install"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in {edition} config")

        # Validate metadata if present
        if "metadata" in config:
            metadata = config["metadata"]
            required_metadata = ["schema_version", "created_at", "updated_at"]
            for field in required_metadata:
                if field not in metadata:
                    logger.warning(f"Missing metadata field '{field}' in {edition} config")

        # Validate features structure
        features = config.get("features", {})
        for feature_name, feature_config in features.items():
            if not isinstance(feature_config, dict):
                raise ValueError(f"Feature '{feature_name}' must be an object")
            
            if "enabled" not in feature_config:
                raise ValueError(f"Feature '{feature_name}' missing 'enabled' field")

        # Validate packages structure
        packages = config.get("auto_install", {}).get("packages", {})
        for pkg_name, pkg_config in packages.items():
            if not isinstance(pkg_config, dict):
                raise ValueError(f"Package '{pkg_name}' must be an object")
            
            required_pkg_fields = ["enabled", "category"]
            for field in required_pkg_fields:
                if field not in pkg_config:
                    raise ValueError(f"Package '{pkg_name}' missing '{field}' field")

    def _git_track_changes(self, edition: str, config: Dict[str, Any], changes: List[str]):
        """
        Track configuration changes in Git if enabled.

        Args:
            edition: Edition name
            config: Configuration dictionary  
            changes: List of changes made
        """
        try:
            # Check if we're in a Git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.configs_dir.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.debug("Not in a Git repository - skipping Git tracking")
                return

            # Stage the configuration file
            edition_file = self.editions_dir / f"{edition}.json"
            subprocess.run(
                ["git", "add", str(edition_file.relative_to(self.configs_dir.parent))],
                cwd=self.configs_dir.parent,
                check=True
            )

            # Create commit message
            git_config = config.get("metadata", {}).get("git_tracking", {})
            template = git_config.get("commit_message_template", "feat: Update {edition} edition configuration")
            
            commit_message = template.format(edition=edition)
            if changes:
                commit_message += f"\n\n- " + "\n- ".join(changes)

            # Only auto-commit if enabled
            if git_config.get("auto_commit", False):
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=self.configs_dir.parent,
                    check=True
                )
                logger.info(f"Auto-committed changes to {edition} configuration")
            else:
                logger.info(f"Staged changes to {edition} configuration (auto-commit disabled)")
                
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Git tracking failed for {edition}: {e}")

    def get_edition_versions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get version information for all editions.

        Returns:
            Dictionary mapping edition names to version info
        """
        versions = {}
        
        for edition_file in self.editions_dir.glob("*.json"):
            if edition_file.name.startswith("."):
                continue
                
            edition = edition_file.stem
            try:
                config = self.load_edition_config(edition)
                metadata = config.get("metadata", {})
                
                versions[edition] = {
                    "version": config.get("version", "unknown"),
                    "schema_version": metadata.get("schema_version", "unknown"),
                    "last_updated": metadata.get("updated_at", "unknown"),
                    "updated_by": metadata.get("updated_by", "unknown"),
                    "changelog_entries": len(metadata.get("changelog", []))
                }
            except (FileNotFoundError, ValueError):
                versions[edition] = {
                    "version": "invalid",
                    "schema_version": "unknown", 
                    "last_updated": "unknown",
                    "updated_by": "unknown",
                    "changelog_entries": 0
                }

        return versions


# Global singleton instance - initialized in main.py
_config_version_service_instance: Optional[ConfigVersionService] = None


def get_config_version_service() -> ConfigVersionService:
    """
    Get the global ConfigVersionService instance.

    Returns:
        ConfigVersionService singleton instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _config_version_service_instance

    if _config_version_service_instance is None:
        raise RuntimeError(
            "ConfigVersionService not initialized. "
            "Call init_config_version_service() in main.py startup"
        )

    return _config_version_service_instance


def init_config_version_service(configs_dir: str = "configs") -> ConfigVersionService:
    """
    Initialize the global ConfigVersionService instance.

    Args:
        configs_dir: Path to configs directory

    Returns:
        Initialized ConfigVersionService instance
    """
    global _config_version_service_instance

    _config_version_service_instance = ConfigVersionService(configs_dir)
    logger.info(f"ConfigVersionService initialized: {configs_dir}")

    return _config_version_service_instance