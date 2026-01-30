# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Startup Migration Service

Handles automatic migration detection and execution during application startup.
Integrates with existing ADCL services to preserve user data and functionality.

Key Features:
- Detects version changes on startup
- Preserves user configurations and data
- Automatic rollback on failure
- Non-blocking startup process
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .installation_migration_service import InstallationMigrationService

logger = logging.getLogger(__name__)


class StartupMigrationService:
    """Service for handling migrations during application startup"""

    def __init__(self):
        self.migration_service = InstallationMigrationService()
        workspace = os.getenv("ADCL_WORKSPACE", "/workspace")
        self.startup_log = Path(workspace) / "logs" / "startup-migration.log"
        self.startup_log.parent.mkdir(parents=True, exist_ok=True)

    async def check_and_migrate_on_startup(self) -> Dict[str, Any]:
        """
        Check for required migrations on startup and perform if needed
        
        This method is designed to be called during application startup
        to automatically handle migration after upgrades.
        
        Returns:
            Dictionary with migration results and status
        """
        self._log_startup("Starting startup migration check")
        
        try:
            # Check if migration is needed
            migration_status = await self.migration_service.check_migration_needed()
            
            if not migration_status.get("migration_needed", False):
                self._log_startup("No migration needed - installation is current")
                return {
                    "status": "no_migration_needed",
                    "current_version": migration_status.get("current_version"),
                    "message": "Installation is up to date"
                }
            
            # Log detected migration requirements
            required = migration_status.get("required_migrations", [])
            migration_names = [m.get("name", "unknown") for m in required]
            self._log_startup(
                f"Migration required: {len(required)} migrations needed: {migration_names}"
            )
            
            # Check if automatic migration is enabled
            auto_migrate = self._should_auto_migrate()
            
            if not auto_migrate:
                self._log_startup("Automatic migration disabled - manual migration required")
                return {
                    "status": "migration_required",
                    "current_version": migration_status.get("current_version"),
                    "last_migrated": migration_status.get("last_migrated"),
                    "required_migrations": required,
                    "message": "Manual migration required - use /api/migration/auto"
                }
            
            # Perform automatic migration
            self._log_startup("Starting automatic migration...")
            
            async def startup_progress_callback(update):
                stage = update.get("stage", "unknown")
                message = update.get("message", "")
                progress = update.get("progress", 0)
                self._log_startup(f"Migration progress: {stage} - {message} ({progress}%)")
            
            migration_result = await self.migration_service.perform_auto_migration(
                startup_progress_callback
            )
            
            if migration_result.get("status") == "success":
                self._log_startup("Automatic migration completed successfully")
                version = migration_result.get("migrated_to_version", "unknown")
                migrations = migration_result.get("migrations_completed", [])
                
                return {
                    "status": "migration_completed",
                    "migrated_to_version": version,
                    "migrations_completed": len(migrations),
                    "backup_path": migration_result.get("backup_path"),
                    "message": "Automatic migration completed successfully"
                }
            else:
                error = migration_result.get("error", "Unknown error")
                self._log_startup(f"Automatic migration failed: {error}", "ERROR")
                
                return {
                    "status": "migration_failed",
                    "error": error,
                    "message": "Automatic migration failed - check logs"
                }
            
        except Exception as e:
            error_msg = f"Startup migration check failed: {str(e)}"
            self._log_startup(error_msg, "ERROR")
            
            # Don't fail startup for migration errors
            return {
                "status": "migration_error",
                "error": error_msg,
                "message": "Migration check failed - application starting normally"
            }

    async def migrate_if_needed_background(self) -> None:
        """
        Background task to check and migrate if needed
        
        This is a fire-and-forget version for non-blocking startup
        """
        try:
            result = await self.check_and_migrate_on_startup()
            status = result.get("status")
            
            if status in ["migration_completed", "migration_failed"]:
                # Log final result
                if status == "migration_completed":
                    self._log_startup(
                        f"Background migration completed successfully to version "
                        f"{result.get('migrated_to_version')}"
                    )
                else:
                    self._log_startup(
                        f"Background migration failed: {result.get('error')}", 
                        "ERROR"
                    )
            
        except Exception as e:
            self._log_startup(f"Background migration task failed: {str(e)}", "ERROR")

    def _should_auto_migrate(self) -> bool:
        """
        Check if automatic migration should be performed
        
        Returns:
            True if auto migration is enabled, False otherwise
        """
        # Check environment variable
        auto_migrate_env = os.getenv("ADCL_AUTO_MIGRATE", "true").lower()
        if auto_migrate_env in ["false", "0", "no", "disabled"]:
            return False
        
        # Check configuration file
        try:
            config_file = Path("configs/migration.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return config.get("auto_migrate_on_startup", True)
        except Exception:
            pass
        
        # Default to enabled for community edition, disabled for enterprise
        edition = os.getenv("ADCL_EDITION", "community")
        return edition == "community"

    def _log_startup(self, message: str, level: str = "INFO"):
        """Log startup migration events"""
        timestamp = f"{logger.name} [{level}]"
        log_entry = f"{timestamp} {message}"
        
        # Log to application logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARN":
            logger.warning(message)
        else:
            logger.info(message)
        
        # Also write to startup migration log
        try:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            detailed_entry = f"{timestamp} [{level}] {message}\n"
            
            with open(self.startup_log, 'a') as f:
                f.write(detailed_entry)
        except Exception:
            pass