"""
Upgrade Service - Orchestrates platform upgrades

Following ADCL principles:
- Text-based logging
- Fail fast with clear errors
- Idempotent operations
- No hidden state
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class UpgradeService:
    """Service for orchestrating platform upgrades"""

    def __init__(self):
        workspace = os.getenv("ADCL_WORKSPACE", "/workspace")
        self.upgrade_log = Path(workspace) / "logs" / "upgrade.log"
        self.upgrade_log.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = Path(workspace) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def check_prerequisites(self) -> Dict[str, Any]:
        """
        Check if system is ready for upgrade

        Returns:
            Dictionary with status and any issues found
        """
        issues = []
        checks = {
            "docker_available": False,
            "git_available": False,
            "disk_space_ok": False,
            "no_active_executions": True
        }

        # Check Docker
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            checks["docker_available"] = result.returncode == 0
            if not checks["docker_available"]:
                issues.append("Docker is not available or not responding")
        except Exception as e:
            issues.append(f"Docker check failed: {str(e)}")

        # Check Git
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            checks["git_available"] = result.returncode == 0
            if not checks["git_available"]:
                issues.append("Git is not available")
        except Exception as e:
            issues.append(f"Git check failed: {str(e)}")

        # Check disk space (require at least 1GB free)
        try:
            import shutil
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024 ** 3)
            checks["disk_space_ok"] = free_gb >= 1.0
            if not checks["disk_space_ok"]:
                issues.append(f"Insufficient disk space: {free_gb:.2f}GB free (need 1GB)")
        except Exception as e:
            issues.append(f"Disk space check failed: {str(e)}")

        # Check for active executions (would need to check execution dirs)
        try:
            executions_dir = Path("/workspace/executions")
            if executions_dir.exists():
                # Count running executions (would need to check status)
                # For now, assume no active executions
                checks["no_active_executions"] = True
        except Exception:
            pass

        return {
            "ready": len(issues) == 0,
            "checks": checks,
            "issues": issues
        }

    async def create_backup(self) -> Dict[str, Any]:
        """
        Create backup before upgrade

        Returns:
            Dictionary with backup status and location
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup critical directories
            critical_dirs = [
                "/configs",
                "/agent-definitions",
                "/agent-teams",
                "/workspace/executions",
                "VERSION"
            ]

            backed_up = []
            for dir_path in critical_dirs:
                src = Path(dir_path)
                if src.exists():
                    dest = backup_path / src.name
                    if src.is_file():
                        import shutil
                        shutil.copy2(src, dest)
                    else:
                        # Use shutil.copytree instead of subprocess for security
                        import shutil
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    backed_up.append(str(src))

            # Write backup manifest
            manifest = {
                "timestamp": timestamp,
                "backed_up": backed_up,
                "version_before": self._read_version()
            }
            with open(backup_path / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)

            self._log(f"Backup created: {backup_path}")

            return {
                "status": "success",
                "backup_path": str(backup_path),
                "timestamp": timestamp,
                "backed_up": backed_up
            }

        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            self._log(error_msg, level="ERROR")
            return {
                "status": "error",
                "error": error_msg
            }

    async def perform_upgrade(
        self,
        target_version: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Perform the upgrade to target version

        Args:
            target_version: Version to upgrade to
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with upgrade result
        """
        self._log(f"Starting upgrade to version {target_version}")

        if progress_callback:
            await progress_callback({
                "stage": "prerequisites",
                "message": "Checking prerequisites..."
            })

        # Check prerequisites
        prereq_check = await self.check_prerequisites()
        if not prereq_check["ready"]:
            return {
                "status": "error",
                "error": "Prerequisites not met",
                "issues": prereq_check["issues"]
            }

        if progress_callback:
            await progress_callback({
                "stage": "backup",
                "message": "Creating backup..."
            })

        # Create backup
        backup_result = await self.create_backup()
        if backup_result["status"] != "success":
            return {
                "status": "error",
                "error": "Backup failed",
                "details": backup_result
            }

        if progress_callback:
            await progress_callback({
                "stage": "upgrade",
                "message": f"Upgrading to version {target_version}...",
                "backup_path": backup_result["backup_path"]
            })

        # The actual upgrade would be handled by upgrade.sh script
        # For now, return success with instructions
        return {
            "status": "ready",
            "message": "Backup created. Ready to execute upgrade script.",
            "backup_path": backup_result["backup_path"],
            "next_steps": [
                "Stop the platform: docker-compose down",
                f"Run upgrade script: ./scripts/upgrade.sh {target_version}",
                "Start the platform: docker-compose up -d"
            ]
        }

    async def rollback(self, backup_path: str) -> Dict[str, Any]:
        """
        Rollback to a previous backup

        Args:
            backup_path: Path to backup directory

        Returns:
            Dictionary with rollback result
        """
        backup = Path(backup_path)

        if not backup.exists():
            return {
                "status": "error",
                "error": f"Backup not found: {backup_path}"
            }

        try:
            # Read backup manifest
            manifest_file = backup / "manifest.json"
            if not manifest_file.exists():
                return {
                    "status": "error",
                    "error": "Backup manifest not found"
                }

            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            # Restore backed up files
            import shutil
            restored = []
            for backed_up_path in manifest.get("backed_up", []):
                src_name = Path(backed_up_path).name
                src = backup / src_name
                dest = Path(backed_up_path)

                if src.exists():
                    # Remove destination first if it exists
                    if dest.exists():
                        if dest.is_file():
                            dest.unlink()
                        else:
                            shutil.rmtree(dest)

                    # Restore from backup using shutil for security
                    if src.is_file():
                        shutil.copy2(src, dest)
                    else:
                        shutil.copytree(src, dest)
                    restored.append(backed_up_path)

            self._log(f"Rollback completed from backup: {backup_path}")

            return {
                "status": "success",
                "restored": restored,
                "version_restored": manifest.get("version_before", "unknown")
            }

        except Exception as e:
            error_msg = f"Rollback failed: {str(e)}"
            self._log(error_msg, level="ERROR")
            return {
                "status": "error",
                "error": error_msg
            }

    def list_backups(self) -> list:
        """List available backups"""
        backups = []

        if not self.backup_dir.exists():
            return backups

        for backup_path in sorted(self.backup_dir.glob("backup_*"), reverse=True):
            manifest_file = backup_path / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    backups.append({
                        "path": str(backup_path),
                        "timestamp": manifest.get("timestamp"),
                        "version": manifest.get("version_before"),
                        "size": self._get_dir_size(backup_path)
                    })
                except Exception:
                    pass

        return backups

    def _read_version(self) -> str:
        """Read current version from VERSION file"""
        version_file = Path("/app/VERSION")
        if not version_file.exists():
            version_file = Path("VERSION")

        try:
            with open(version_file, 'r') as f:
                version_data = json.load(f)
            return version_data.get("version", "unknown")
        except Exception:
            return "unknown"

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes"""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total

    def _log(self, message: str, level: str = "INFO"):
        """Write to upgrade log"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}\n"

        try:
            with open(self.upgrade_log, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write to upgrade log: {e}")
