# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Migration Rollback Service

Provides comprehensive rollback capabilities for failed migrations.
Integrates with existing backup systems and follows ADCL's fail-fast principles.

Key Features:
- Automatic rollback on migration failure
- Manual rollback API
- State validation before and after rollback
- Rollback history tracking
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MigrationRollbackService:
    """Service for handling migration rollbacks"""

    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace = Path(workspace_path)
        self.backup_dir = self.workspace / "backups"
        self.rollback_log = self.workspace / "logs" / "rollback.log"
        self.rollback_history_file = self.workspace / "rollback_history.json"
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.rollback_log.parent.mkdir(parents=True, exist_ok=True)

    async def rollback_to_backup(
        self, 
        backup_path: str,
        reason: str = "Manual rollback"
    ) -> Dict[str, Any]:
        """
        Rollback installation to a specific backup
        
        Args:
            backup_path: Path to backup directory
            reason: Reason for rollback (for logging)
            
        Returns:
            Dictionary with rollback results
        """
        self._log(f"Starting rollback: {reason}")
        self._log(f"Target backup: {backup_path}")
        
        backup = Path(backup_path)
        
        try:
            # Validate backup exists and is complete
            validation_result = self._validate_backup(backup)
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "error": "Backup validation failed",
                    "issues": validation_result.get("issues", [])
                }
            
            # Read backup manifest
            manifest = self._read_backup_manifest(backup)
            if not manifest:
                return {
                    "status": "error", 
                    "error": "Could not read backup manifest"
                }
            
            # Create pre-rollback snapshot for potential re-rollback
            snapshot_result = await self._create_pre_rollback_snapshot()
            
            # Record rollback start in history
            rollback_record = {
                "rollback_id": f"rollback_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "backup_path": str(backup),
                "backup_timestamp": manifest.get("timestamp"),
                "backup_version": manifest.get("version_before"),
                "reason": reason,
                "status": "in_progress",
                "pre_rollback_snapshot": snapshot_result.get("snapshot_path")
            }
            
            self._record_rollback_history(rollback_record)
            
            # Perform the rollback
            restore_result = await self._restore_from_backup(backup, manifest)
            
            if restore_result["status"] != "success":
                rollback_record["status"] = "failed"
                rollback_record["error"] = restore_result.get("error")
                self._record_rollback_history(rollback_record)
                
                return {
                    "status": "error",
                    "error": f"Restore failed: {restore_result.get('error')}",
                    "rollback_id": rollback_record["rollback_id"]
                }
            
            # Validate post-rollback state
            validation_result = await self._validate_post_rollback()
            
            if validation_result["valid"]:
                rollback_record["status"] = "completed"
                rollback_record["restored_files"] = restore_result.get("restored", [])
                rollback_record["validation"] = validation_result
                
                self._log(f"Rollback completed successfully to version {manifest.get('version_before')}")
            else:
                rollback_record["status"] = "completed_with_warnings" 
                rollback_record["validation_warnings"] = validation_result.get("warnings", [])
                
                self._log(f"Rollback completed with warnings: {validation_result.get('warnings')}", "WARN")
            
            self._record_rollback_history(rollback_record)
            
            return {
                "status": "success",
                "message": "Rollback completed successfully",
                "rollback_id": rollback_record["rollback_id"],
                "restored_to_version": manifest.get("version_before"),
                "restored_files": restore_result.get("restored", []),
                "validation": validation_result,
                "pre_rollback_snapshot": snapshot_result.get("snapshot_path")
            }
            
        except Exception as e:
            error_msg = f"Rollback failed with exception: {str(e)}"
            self._log(error_msg, "ERROR")
            
            # Update history record if it exists
            try:
                if 'rollback_record' in locals():
                    rollback_record["status"] = "failed"
                    rollback_record["error"] = error_msg
                    self._record_rollback_history(rollback_record)
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": error_msg
            }

    async def list_available_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups for rollback
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        # Find backup directories
        for backup_path in sorted(self.backup_dir.glob("backup_*"), reverse=True):
            if backup_path.is_dir():
                manifest = self._read_backup_manifest(backup_path)
                if manifest:
                    backup_info = {
                        "backup_path": str(backup_path),
                        "timestamp": manifest.get("timestamp"),
                        "version": manifest.get("version_before"),
                        "backed_up_items": len(manifest.get("backed_up", [])),
                        "size_bytes": self._get_backup_size(backup_path),
                        "valid": self._validate_backup(backup_path)["valid"]
                    }
                    backups.append(backup_info)
        
        return backups

    async def get_rollback_history(self) -> List[Dict[str, Any]]:
        """
        Get history of rollback operations
        
        Returns:
            List of rollback history records
        """
        if not self.rollback_history_file.exists():
            return []
        
        try:
            with open(self.rollback_history_file, 'r') as f:
                history = json.load(f)
            return history.get("rollbacks", [])
        except Exception as e:
            self._log(f"Error reading rollback history: {str(e)}", "ERROR")
            return []

    async def cleanup_old_backups(self, max_backups: int = 10) -> Dict[str, Any]:
        """
        Clean up old backups to save disk space
        
        Args:
            max_backups: Maximum number of backups to keep
            
        Returns:
            Cleanup results
        """
        if not self.backup_dir.exists():
            return {"cleaned": 0, "message": "No backup directory found"}
        
        # Get all backup directories sorted by creation time (newest first)
        backups = sorted(
            [p for p in self.backup_dir.glob("backup_*") if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if len(backups) <= max_backups:
            return {
                "cleaned": 0,
                "total_backups": len(backups),
                "message": f"No cleanup needed - {len(backups)} backups (limit: {max_backups})"
            }
        
        # Remove oldest backups
        backups_to_remove = backups[max_backups:]
        cleaned_count = 0
        cleaned_size = 0
        
        for backup_path in backups_to_remove:
            try:
                backup_size = self._get_backup_size(backup_path)
                shutil.rmtree(backup_path)
                cleaned_count += 1
                cleaned_size += backup_size
                self._log(f"Removed old backup: {backup_path}")
            except Exception as e:
                self._log(f"Failed to remove backup {backup_path}: {str(e)}", "ERROR")
        
        return {
            "cleaned": cleaned_count,
            "remaining_backups": len(backups) - cleaned_count,
            "space_freed_bytes": cleaned_size,
            "message": f"Cleaned up {cleaned_count} old backups"
        }

    def _validate_backup(self, backup_path: Path) -> Dict[str, Any]:
        """Validate that backup is complete and usable"""
        issues = []
        
        if not backup_path.exists():
            issues.append("Backup directory does not exist")
        
        if not backup_path.is_dir():
            issues.append("Backup path is not a directory")
        
        manifest_file = backup_path / "manifest.json"
        if not manifest_file.exists():
            issues.append("Backup manifest missing")
        else:
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                # Check if backed up files exist in backup
                for backed_up_path in manifest.get("backed_up", []):
                    backup_item_name = Path(backed_up_path).name
                    backup_item_path = backup_path / backup_item_name
                    
                    if not backup_item_path.exists():
                        issues.append(f"Missing backed up item: {backup_item_name}")
                        
            except Exception as e:
                issues.append(f"Could not read manifest: {str(e)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def _read_backup_manifest(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """Read backup manifest file"""
        manifest_file = backup_path / "manifest.json"
        
        if not manifest_file.exists():
            return None
        
        try:
            with open(manifest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self._log(f"Error reading manifest {manifest_file}: {str(e)}", "ERROR")
            return None

    async def _create_pre_rollback_snapshot(self) -> Dict[str, Any]:
        """Create snapshot before rollback for potential re-rollback"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_dir = self.backup_dir / f"pre_rollback_{timestamp}"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup critical current state
            critical_items = [
                Path("configs"),
                Path("agent-definitions"),
                Path("agent-teams"),
                Path("VERSION")
            ]
            
            backed_up = []
            for item in critical_items:
                if item.exists():
                    dest = snapshot_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, dest)
                    else:
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    backed_up.append(str(item))
            
            # Create snapshot manifest
            manifest = {
                "timestamp": timestamp,
                "type": "pre_rollback_snapshot",
                "backed_up": backed_up
            }
            
            with open(snapshot_dir / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return {
                "status": "success",
                "snapshot_path": str(snapshot_dir)
            }
            
        except Exception as e:
            self._log(f"Failed to create pre-rollback snapshot: {str(e)}", "ERROR")
            return {
                "status": "error", 
                "error": str(e)
            }

    async def _restore_from_backup(
        self, 
        backup_path: Path, 
        manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Restore files from backup"""
        restored = []
        
        try:
            for backed_up_path in manifest.get("backed_up", []):
                src_name = Path(backed_up_path).name
                src = backup_path / src_name
                dest = Path(backed_up_path)
                
                if not src.exists():
                    self._log(f"Warning: backup item not found: {src}", "WARN")
                    continue
                
                # Remove current version if it exists
                if dest.exists():
                    if dest.is_file():
                        dest.unlink()
                    else:
                        shutil.rmtree(dest)
                
                # Restore from backup
                if src.is_file():
                    # Ensure parent directory exists
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                else:
                    shutil.copytree(src, dest)
                
                restored.append(backed_up_path)
                self._log(f"Restored: {backed_up_path}")
            
            return {
                "status": "success",
                "restored": restored
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "partially_restored": restored
            }

    async def _validate_post_rollback(self) -> Dict[str, Any]:
        """Validate system state after rollback"""
        warnings = []
        
        # Check VERSION file
        version_file = Path("VERSION")
        if not version_file.exists():
            warnings.append("VERSION file missing after rollback")
        else:
            try:
                with open(version_file, 'r') as f:
                    json.load(f)  # Validate JSON
            except Exception:
                warnings.append("VERSION file is invalid JSON")
        
        # Check critical directories
        critical_dirs = [
            Path("configs"),
            Path("agent-definitions")
        ]
        
        for dir_path in critical_dirs:
            if not dir_path.exists():
                warnings.append(f"Critical directory missing after rollback: {dir_path}")
        
        # Check configuration files
        config_dir = Path("configs")
        if config_dir.exists():
            for config_file in config_dir.glob("*.json"):
                try:
                    with open(config_file, 'r') as f:
                        json.load(f)  # Validate JSON
                except Exception:
                    warnings.append(f"Configuration file invalid after rollback: {config_file}")
        
        return {
            "valid": len(warnings) == 0,
            "warnings": warnings
        }

    def _get_backup_size(self, backup_path: Path) -> int:
        """Get total size of backup directory in bytes"""
        total = 0
        try:
            for item in backup_path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total

    def _record_rollback_history(self, rollback_record: Dict[str, Any]):
        """Record rollback operation in history"""
        try:
            history = {"rollbacks": []}
            
            # Read existing history
            if self.rollback_history_file.exists():
                with open(self.rollback_history_file, 'r') as f:
                    history = json.load(f)
            
            # Find existing record or add new one
            rollbacks = history.get("rollbacks", [])
            rollback_id = rollback_record["rollback_id"]
            
            # Update existing record or add new one
            found = False
            for i, record in enumerate(rollbacks):
                if record.get("rollback_id") == rollback_id:
                    rollbacks[i] = rollback_record
                    found = True
                    break
            
            if not found:
                rollbacks.append(rollback_record)
            
            # Keep only last 50 rollback records
            history["rollbacks"] = rollbacks[-50:]
            
            with open(self.rollback_history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self._log(f"Failed to record rollback history: {str(e)}", "ERROR")

    def _log(self, message: str, level: str = "INFO"):
        """Write to rollback log"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}\n"
        
        try:
            with open(self.rollback_log, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to rollback log: {e}")
        
        # Also log to application logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARN":
            logger.warning(message)
        else:
            logger.info(message)