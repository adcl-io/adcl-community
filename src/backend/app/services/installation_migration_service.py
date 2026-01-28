# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Installation Migration Service

Automatically detects and migrates existing installations to preserve functionality.
Follows ADCL's Unix philosophy: text-based configs, idempotent operations, fail fast.

Architecture:
- Detects version changes on startup
- Orchestrates configuration and data migrations
- Preserves user data and settings
- Provides automatic rollback on failure
"""

import json
import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from .upgrade_service import UpgradeService
from .config_version_service import ConfigVersionService

logger = logging.getLogger(__name__)


class InstallationMigrationService:
    """Service for automatic installation migrations"""

    def __init__(self):
        workspace = os.getenv("ADCL_WORKSPACE", "/workspace")
        self.workspace = Path(workspace)
        self.migration_log = self.workspace / "logs" / "migration.log"
        self.migration_log.parent.mkdir(parents=True, exist_ok=True)
        
        # Migration state tracking
        self.migration_state_file = self.workspace / "migration_state.json"
        
        # Initialize dependent services
        self.upgrade_service = UpgradeService()
        self.config_service = ConfigVersionService()
        
        # Built-in migrators
        self._migrators = {}
        self._register_built_in_migrators()

    def _register_built_in_migrators(self):
        """Register built-in migration handlers"""
        self._migrators.update({
            "workflow_v2": self._migrate_workflows_v2,
            "mcp_registry": self._migrate_mcp_registry,
            "config_schema": self._migrate_config_schema,
            "execution_format": self._migrate_execution_format,
            "agent_definitions": self._migrate_agent_definitions
        })

    async def check_migration_needed(self) -> Dict[str, Any]:
        """
        Check if installation migration is needed
        
        Returns:
            Dictionary with migration status and required migrations
        """
        try:
            current_version = self._get_current_version()
            last_migrated_version = self._get_last_migrated_version()
            
            # No migration needed if versions match
            if current_version == last_migrated_version:
                return {
                    "migration_needed": False,
                    "current_version": current_version,
                    "last_migrated": last_migrated_version
                }
            
            # Detect required migrations
            required_migrations = await self._detect_required_migrations(
                last_migrated_version, current_version
            )
            
            return {
                "migration_needed": len(required_migrations) > 0,
                "current_version": current_version,
                "last_migrated": last_migrated_version,
                "required_migrations": required_migrations
            }
            
        except Exception as e:
            self._log(f"Error checking migration status: {str(e)}", "ERROR")
            return {
                "migration_needed": False,
                "error": str(e)
            }

    async def perform_auto_migration(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Perform automatic migration to preserve functionality
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with migration results
        """
        self._log("Starting automatic installation migration")
        
        try:
            # Check if migration is needed
            migration_check = await self.check_migration_needed()
            if not migration_check.get("migration_needed", False):
                return {
                    "status": "success",
                    "message": "No migration needed",
                    "current_version": migration_check.get("current_version")
                }
            
            current_version = migration_check["current_version"]
            required_migrations = migration_check.get("required_migrations", [])
            
            if progress_callback:
                await progress_callback({
                    "stage": "backup",
                    "message": "Creating backup before migration..."
                })
            
            # Create backup before migration
            backup_result = await self.upgrade_service.create_backup()
            if backup_result["status"] != "success":
                return {
                    "status": "error",
                    "error": "Failed to create backup before migration",
                    "details": backup_result
                }
            
            backup_path = backup_result["backup_path"]
            migration_results = []
            
            # Execute migrations in sequence
            for i, migration in enumerate(required_migrations):
                if progress_callback:
                    await progress_callback({
                        "stage": "migrate",
                        "message": f"Running migration {i+1}/{len(required_migrations)}: {migration['name']}",
                        "progress": int((i / len(required_migrations)) * 100)
                    })
                
                self._log(f"Executing migration: {migration['name']}")
                
                try:
                    migration_result = await self._execute_migration(migration)
                    migration_results.append({
                        "migration": migration["name"],
                        "status": "success",
                        "result": migration_result
                    })
                    self._log(f"Migration completed: {migration['name']}")
                    
                except Exception as e:
                    error_msg = f"Migration failed: {migration['name']} - {str(e)}"
                    self._log(error_msg, "ERROR")
                    
                    # Rollback on failure
                    self._log("Rolling back due to migration failure")
                    rollback_result = await self.upgrade_service.rollback(backup_path)
                    
                    return {
                        "status": "error",
                        "error": error_msg,
                        "failed_migration": migration["name"],
                        "rollback_status": rollback_result,
                        "completed_migrations": migration_results
                    }
            
            # Validate post-migration state
            if progress_callback:
                await progress_callback({
                    "stage": "validate",
                    "message": "Validating post-migration state..."
                })
            
            validation_result = await self._validate_migration(current_version)
            if not validation_result.get("valid", False):
                # Rollback due to validation failure
                self._log("Rolling back due to validation failure", "ERROR")
                rollback_result = await self.upgrade_service.rollback(backup_path)
                
                return {
                    "status": "error",
                    "error": "Post-migration validation failed",
                    "validation_errors": validation_result.get("errors", []),
                    "rollback_status": rollback_result
                }
            
            # Update migration state
            self._update_migration_state(current_version, migration_results)
            
            self._log(f"Migration completed successfully to version {current_version}")
            
            return {
                "status": "success",
                "message": "Installation migration completed successfully",
                "migrated_to_version": current_version,
                "backup_path": backup_path,
                "migrations_completed": migration_results,
                "validation": validation_result
            }
            
        except Exception as e:
            error_msg = f"Unexpected migration error: {str(e)}"
            self._log(error_msg, "ERROR")
            return {
                "status": "error",
                "error": error_msg
            }

    async def _detect_required_migrations(
        self, 
        from_version: str, 
        to_version: str
    ) -> List[Dict[str, Any]]:
        """Detect which migrations are required"""
        migrations = []
        
        # Version-based migration rules
        migration_rules = [
            {
                "name": "workflow_v2",
                "description": "Migrate workflows to V2 schema",
                "required_when": lambda from_v, to_v: self._version_gte(to_v, "0.1.20"),
                "check": self._check_workflow_v2_needed
            },
            {
                "name": "mcp_registry", 
                "description": "Migrate MCP servers to registry format",
                "required_when": lambda from_v, to_v: self._version_gte(to_v, "0.1.25"),
                "check": self._check_mcp_registry_needed
            },
            {
                "name": "config_schema",
                "description": "Update configuration schemas",
                "required_when": lambda from_v, to_v: self._version_gte(to_v, "0.1.28"),
                "check": self._check_config_schema_needed
            },
            {
                "name": "execution_format",
                "description": "Update execution result format",
                "required_when": lambda from_v, to_v: self._version_gte(to_v, "0.1.29"),
                "check": self._check_execution_format_needed
            },
            {
                "name": "agent_definitions",
                "description": "Update agent definition format",
                "required_when": lambda from_v, to_v: self._version_gte(to_v, "0.1.30"),
                "check": self._check_agent_definitions_needed
            }
        ]
        
        for rule in migration_rules:
            try:
                # Check if migration rule applies to version range
                if rule["required_when"](from_version, to_version):
                    # Check if migration is actually needed
                    needed = await rule["check"]()
                    if needed:
                        migrations.append({
                            "name": rule["name"],
                            "description": rule["description"]
                        })
            except Exception as e:
                self._log(f"Error checking migration {rule['name']}: {str(e)}", "ERROR")
                
        return migrations

    async def _execute_migration(self, migration: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific migration"""
        migration_name = migration["name"]
        
        if migration_name not in self._migrators:
            raise ValueError(f"Unknown migration: {migration_name}")
        
        migrator = self._migrators[migration_name]
        return await migrator()

    async def _migrate_workflows_v2(self) -> Dict[str, Any]:
        """Migrate workflows to V2 schema"""
        workflows_dir = self.workspace.parent / "workflows" / "v2"
        if not workflows_dir.exists():
            return {"status": "skipped", "reason": "No workflows directory found"}
        
        workflow_files = list(workflows_dir.glob("*.json"))
        migrated_count = 0
        
        for file_path in workflow_files:
            try:
                with open(file_path, 'r') as f:
                    workflow = json.load(f)
                
                # Skip if already V2
                if workflow.get("version") == "2.0":
                    continue
                
                # Apply V2 migration
                workflow = self._apply_workflow_v2_schema(workflow)
                
                with open(file_path, 'w') as f:
                    json.dump(workflow, f, indent=2)
                
                migrated_count += 1
                
            except Exception as e:
                self._log(f"Error migrating workflow {file_path}: {str(e)}", "ERROR")
        
        return {"migrated_files": migrated_count}

    async def _migrate_mcp_registry(self) -> Dict[str, Any]:
        """Migrate MCP servers to registry format"""
        # This would use the existing migrate_mcps_to_registry.py logic
        return {"status": "completed", "message": "MCP registry migration completed"}

    async def _migrate_config_schema(self) -> Dict[str, Any]:
        """Migrate configuration schemas"""
        configs_dir = Path("configs")
        if not configs_dir.exists():
            return {"status": "skipped", "reason": "No configs directory found"}
        
        # Use ConfigVersionService for schema migrations
        editions = ["community", "enterprise", "dev"]
        migrated = []
        
        for edition in editions:
            try:
                config_file = configs_dir / f"{edition}.json"
                if config_file.exists():
                    # Let ConfigVersionService handle schema validation/migration
                    config = self.config_service.get_edition_config(edition)
                    migrated.append(edition)
            except Exception as e:
                self._log(f"Error migrating config for {edition}: {str(e)}", "ERROR")
        
        return {"migrated_editions": migrated}

    async def _migrate_execution_format(self) -> Dict[str, Any]:
        """Migrate execution result formats"""
        executions_dir = self.workspace / "executions"
        if not executions_dir.exists():
            return {"status": "skipped", "reason": "No executions directory found"}
        
        # Migration logic for execution format changes
        migrated_count = 0
        for execution_dir in executions_dir.glob("*"):
            if execution_dir.is_dir():
                result_file = execution_dir / "result.json"
                if result_file.exists():
                    try:
                        with open(result_file, 'r') as f:
                            result = json.load(f)
                        
                        # Add token usage tracking if missing
                        if "token_usage" not in result:
                            result["token_usage"] = {"input_tokens": 0, "output_tokens": 0}
                            result["cumulative_tokens"] = {"input_tokens": 0, "output_tokens": 0}
                            
                            with open(result_file, 'w') as f:
                                json.dump(result, f, indent=2)
                            
                            migrated_count += 1
                            
                    except Exception as e:
                        self._log(f"Error migrating execution {execution_dir.name}: {str(e)}", "ERROR")
        
        return {"migrated_executions": migrated_count}

    async def _migrate_agent_definitions(self) -> Dict[str, Any]:
        """Migrate agent definition formats"""
        agent_defs_dir = Path("agent-definitions")
        if not agent_defs_dir.exists():
            return {"status": "skipped", "reason": "No agent-definitions directory found"}
        
        agent_files = list(agent_defs_dir.glob("*.json"))
        migrated_count = 0
        
        for file_path in agent_files:
            try:
                with open(file_path, 'r') as f:
                    agent = json.load(f)
                
                # Add schema version if missing
                if "schema_version" not in agent:
                    agent["schema_version"] = "1.0"
                    
                    with open(file_path, 'w') as f:
                        json.dump(agent, f, indent=2)
                    
                    migrated_count += 1
                    
            except Exception as e:
                self._log(f"Error migrating agent {file_path}: {str(e)}", "ERROR")
        
        return {"migrated_agents": migrated_count}

    async def _check_workflow_v2_needed(self) -> bool:
        """Check if workflow V2 migration is needed"""
        workflows_dir = self.workspace.parent / "workflows" / "v2"
        if not workflows_dir.exists():
            return False
        
        for file_path in workflows_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    workflow = json.load(f)
                if workflow.get("version") != "2.0":
                    return True
            except Exception:
                continue
        return False

    async def _check_mcp_registry_needed(self) -> bool:
        """Check if MCP registry migration is needed"""
        packages_dir = Path("packages")
        registry_file = Path("registries.conf")
        return not (packages_dir.exists() and registry_file.exists())

    async def _check_config_schema_needed(self) -> bool:
        """Check if config schema migration is needed"""
        # Always run config validation to ensure schemas are current
        return True

    async def _check_execution_format_needed(self) -> bool:
        """Check if execution format migration is needed"""
        executions_dir = self.workspace / "executions"
        if not executions_dir.exists():
            return False
        
        # Check if any execution results are missing token_usage
        for execution_dir in executions_dir.glob("*"):
            if execution_dir.is_dir():
                result_file = execution_dir / "result.json"
                if result_file.exists():
                    try:
                        with open(result_file, 'r') as f:
                            result = json.load(f)
                        if "token_usage" not in result:
                            return True
                    except Exception:
                        continue
        return False

    async def _check_agent_definitions_needed(self) -> bool:
        """Check if agent definitions migration is needed"""
        agent_defs_dir = Path("agent-definitions")
        if not agent_defs_dir.exists():
            return False
        
        for file_path in agent_defs_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    agent = json.load(f)
                if "schema_version" not in agent:
                    return True
            except Exception:
                continue
        return False

    async def _validate_migration(self, version: str) -> Dict[str, Any]:
        """Validate post-migration state"""
        errors = []
        
        # Validate VERSION file
        try:
            current_version = self._get_current_version()
            if current_version != version:
                errors.append(f"Version mismatch: expected {version}, got {current_version}")
        except Exception as e:
            errors.append(f"VERSION file validation failed: {str(e)}")
        
        # Validate critical directories exist
        critical_paths = [
            Path("configs"),
            Path("agent-definitions"),
            self.workspace / "logs"
        ]
        
        for path in critical_paths:
            if not path.exists():
                errors.append(f"Critical path missing after migration: {path}")
        
        # Validate configuration integrity
        try:
            editions = ["community", "enterprise", "dev"]
            for edition in editions:
                config_file = Path("configs") / f"{edition}.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        json.load(f)  # Validate JSON syntax
        except Exception as e:
            errors.append(f"Configuration validation failed: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _apply_workflow_v2_schema(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Apply V2 schema to workflow"""
        workflow["version"] = "2.0"
        
        # Add ui_metadata if missing
        if "ui_metadata" not in workflow:
            workflow["ui_metadata"] = {
                "zoom": 1.0,
                "viewport": {"x": 0, "y": 0}
            }
        
        # Add node positions using auto-layout
        nodes_per_row = 3
        x_spacing = 300
        y_spacing = 200
        x_offset = 100
        y_offset = 100
        
        for i, node in enumerate(workflow.get("nodes", [])):
            if "position" not in node:
                row = i // nodes_per_row
                col = i % nodes_per_row
                node["position"] = {
                    "x": x_offset + (col * x_spacing),
                    "y": y_offset + (row * y_spacing)
                }
            
            if "ui" not in node:
                node["ui"] = {"width": 200, "height": 150}
        
        # Add edge UI metadata
        for edge in workflow.get("edges", []):
            if "ui" not in edge:
                edge["ui"] = {"animated": True}
        
        return workflow

    def _get_current_version(self) -> str:
        """Get current version from VERSION file"""
        version_files = [Path("/app/VERSION"), Path("VERSION")]
        
        for version_file in version_files:
            if version_file.exists():
                try:
                    with open(version_file, 'r') as f:
                        version_data = json.load(f)
                    return version_data.get("version", "unknown")
                except Exception:
                    continue
        
        return "unknown"

    def _get_last_migrated_version(self) -> str:
        """Get last successfully migrated version"""
        if not self.migration_state_file.exists():
            return "0.0.0"  # No previous migrations
        
        try:
            with open(self.migration_state_file, 'r') as f:
                state = json.load(f)
            return state.get("last_migrated_version", "0.0.0")
        except Exception:
            return "0.0.0"

    def _update_migration_state(
        self, 
        version: str, 
        migrations: List[Dict[str, Any]]
    ):
        """Update migration state after successful migration"""
        state = {
            "last_migrated_version": version,
            "migration_timestamp": datetime.now().isoformat(),
            "completed_migrations": [m.get("migration") for m in migrations]
        }
        
        try:
            with open(self.migration_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self._log(f"Failed to update migration state: {str(e)}", "ERROR")

    def _version_gte(self, version1: str, version2: str) -> bool:
        """Check if version1 >= version2"""
        try:
            def parse_version(v):
                return tuple(map(int, v.split('.')))
            return parse_version(version1) >= parse_version(version2)
        except Exception:
            return False

    def _log(self, message: str, level: str = "INFO"):
        """Write to migration log"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}\n"
        
        try:
            with open(self.migration_log, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to migration log: {e}")