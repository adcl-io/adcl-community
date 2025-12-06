# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
System API - Version checking and platform upgrades

Endpoints:
- GET /system/version - Current version information
- GET /system/updates/check - Check for available updates
- POST /system/updates/apply - Apply an upgrade
- GET /system/updates/status - Monitor upgrade progress
- GET /system/backups - List available backups
- POST /system/backups/{backup_id}/restore - Restore from backup
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.version_service import VersionService
from app.services.upgrade_service import UpgradeService

router = APIRouter(prefix="/system", tags=["system"])

# Initialize services
version_service = VersionService()
upgrade_service = UpgradeService()


class UpgradeRequest(BaseModel):
    """Request to apply an upgrade"""
    target_version: str
    auto_backup: bool = True


@router.get("/version")
async def get_version():
    """
    Get current platform version information

    Returns version details from VERSION file following ADCL principle:
    Configuration is Code - all version info in text files
    """
    return version_service.get_current_version()


@router.get("/updates/check")
async def check_updates(update_url: Optional[str] = None):
    """
    Check for available platform updates

    Args:
        update_url: Optional custom URL for update checks
                   (defaults to GitHub releases)

    Returns:
        Update availability and release information
    """
    try:
        return await version_service.check_for_updates(update_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check for updates: {str(e)}"
        )


@router.post("/updates/apply")
async def apply_upgrade(request: UpgradeRequest):
    """
    Apply a platform upgrade

    Args:
        request: Upgrade request with target version

    Returns:
        Upgrade preparation result and next steps

    Note: The actual upgrade execution happens via upgrade.sh script
          to ensure proper container restart and state management
    """
    try:
        # Check prerequisites
        prereq_check = await upgrade_service.check_prerequisites()
        if not prereq_check["ready"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "System not ready for upgrade",
                    "issues": prereq_check["issues"],
                    "checks": prereq_check["checks"]
                }
            )

        # Perform upgrade preparation
        result = await upgrade_service.perform_upgrade(request.target_version)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upgrade failed: {str(e)}"
        )


@router.get("/backups")
async def list_backups():
    """
    List available backup snapshots

    Returns list of backups with timestamps and versions
    """
    return {
        "backups": upgrade_service.list_backups()
    }


@router.post("/backups/{backup_id}/restore")
async def restore_backup(backup_id: str):
    """
    Restore platform from a backup

    Args:
        backup_id: Backup identifier (e.g., "backup_20251124_120000")

    Returns:
        Restoration result
    """
    import re
    import os

    # Validate backup_id to prevent path traversal
    if not re.match(r'^backup_\d{8}_\d{6}$', backup_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid backup ID format. Expected: backup_YYYYMMDD_HHMMSS"
        )

    try:
        workspace = os.getenv("ADCL_WORKSPACE", "/workspace")
        backup_path = f"{workspace}/backups/{backup_id}"
        result = await upgrade_service.rollback(backup_path)

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Restore failed: {str(e)}"
        )


@router.get("/health")
async def system_health():
    """
    Extended health check with version info

    Includes current version and update availability
    """
    version_info = version_service.get_current_version()
    prereq_check = await upgrade_service.check_prerequisites()

    return {
        "status": "healthy",
        "version": version_info.get("version"),
        "build": version_info.get("build"),
        "components": version_info.get("components", {}),
        "system_ready": prereq_check["ready"]
    }
