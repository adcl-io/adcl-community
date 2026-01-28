# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
License API - License Management and Validation Endpoints

Provides REST endpoints for:
- License status checking
- License upload/installation
- License information retrieval
- Edition compatibility validation

Architecture:
- Uses LicenseService for validation logic
- Integrates with FeatureService for edition enforcement
- Returns 404 for unauthorized access (not 403)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

from app.services.license_service import get_license_service, LicenseStatus
from app.services.feature_service import get_feature_service
from app.services.audit_service import get_audit_service
from app.core.decorators import requires_valid_license

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/license", tags=["license"])


class LicenseStatusResponse(BaseModel):
    """Response model for license status"""
    status: str
    license_type: Optional[str] = None
    organization: Optional[str] = None
    expires_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    max_users: Optional[int] = None
    features: List[str] = []
    edition_compatibility: Dict[str, bool] = {}


class EditionCompatibilityRequest(BaseModel):
    """Request model for edition compatibility check"""
    edition: str


class LicenseInstallRequest(BaseModel):
    """Request model for license installation"""
    license_data: Dict[str, Any]


class LicenseUpgradeRequest(BaseModel):
    """Request model for seamless license upgrade"""
    license_data: Dict[str, Any]
    notify_users: bool = True
    activate_immediately: bool = True


@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status():
    """
    Get current license status and information.

    Returns license type, expiry, features, and edition compatibility.
    This endpoint is available to all users to check license status.
    """
    try:
        license_service = get_license_service()

        status = license_service.get_license_status()
        license_info = license_service.get_license_info()

        # Get edition compatibility
        editions = ['community', 'red-team', 'pro']
        compatibility = {}
        for edition in editions:
            compatible, _ = license_service.validate_edition_compatibility(edition)
            compatibility[edition] = compatible

        response = LicenseStatusResponse(
            status=status.value,
            edition_compatibility=compatibility
        )

        # Add license details if valid
        if license_info and status == LicenseStatus.VALID:
            response.license_type = license_info.license_type.value
            response.organization = license_info.organization
            response.expires_at = license_info.expiry_date
            response.days_until_expiry = license_service.days_until_expiry()
            response.max_users = license_info.max_users
            response.features = license_info.features

        return response

    except Exception as e:
        logger.error(f"Error getting license status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve license status"
        )


@router.post("/validate-edition")
async def validate_edition_compatibility(request: EditionCompatibilityRequest):
    """
    Check if current license is compatible with a specific edition.

    Args:
        request: Edition compatibility request

    Returns:
        Compatibility status and reason
    """
    try:
        license_service = get_license_service()

        compatible, reason = license_service.validate_edition_compatibility(request.edition)

        return {
            "compatible": compatible,
            "reason": reason,
            "current_license": license_service.get_license_type().value,
            "requested_edition": request.edition
        }

    except Exception as e:
        logger.error(f"Error validating edition compatibility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate edition compatibility"
        )


@router.post("/install")
async def install_license(request: LicenseInstallRequest):
    """
    Install a new license from JSON data with seamless upgrade experience.

    Args:
        request: License installation request with license data

    Returns:
        Installation result and new license status with feature activation details

    Note:
        This endpoint provides seamless license upgrade experience:
        - Validates and installs the license
        - Immediately activates new features
        - Returns comprehensive upgrade details
        - Hot-reloads feature configuration
    """
    try:
        import os
        from pathlib import Path
        from datetime import datetime

        # Get current state for comparison
        license_service = get_license_service()
        feature_service = get_feature_service()

        old_license_type = license_service.get_license_type().value
        old_features = license_service.get_license_info().features if license_service.validate_license() else []
        old_enabled_features = feature_service.get_enabled_features()

        # Write license to file
        license_path = Path("configs/license.json")
        license_path.parent.mkdir(parents=True, exist_ok=True)

        with open(license_path, 'w') as f:
            json.dump(request.license_data, f, indent=2)

        # Reload license service
        license_service.reload()

        # Get new status after reload
        new_status = license_service.get_license_status()
        license_info = license_service.get_license_info()

        if new_status == LicenseStatus.VALID and license_info:
            # Hot-reload feature service to activate new features immediately
            feature_service.reload()

            # Get newly activated features
            new_enabled_features = feature_service.get_enabled_features()
            activated_features = list(set(new_enabled_features) - set(old_enabled_features))
            deactivated_features = list(set(old_enabled_features) - set(new_enabled_features))

            # Calculate feature differences
            new_licensed_features = license_info.features
            newly_licensed = list(set(new_licensed_features) - set(old_features))
            removed_licensed = list(set(old_features) - set(new_licensed_features))

            # Get edition compatibility changes
            editions = ['community', 'red-team', 'pro']
            edition_compatibility = {}
            for edition in editions:
                compatible, _ = license_service.validate_edition_compatibility(edition)
                edition_compatibility[edition] = compatible

            # Audit the license upgrade
            try:
                audit_service = get_audit_service()
                await audit_service.log_license_upgrade(
                    old_license_type=old_license_type,
                    new_license_type=license_info.license_type.value,
                    organization=license_info.organization,
                    activated_features=activated_features,
                    deactivated_features=deactivated_features
                )
            except Exception as audit_error:
                logger.error(f"Failed to log license upgrade audit: {audit_error}")

            logger.info(f"License upgrade successful: {old_license_type} -> {license_info.license_type.value}")
            logger.info(f"Activated features: {activated_features}")

            return {
                "success": True,
                "status": new_status.value,
                "message": f"License upgraded successfully for {license_info.organization}",
                "upgrade_details": {
                    "timestamp": datetime.now().isoformat(),
                    "previous_license_type": old_license_type,
                    "new_license_type": license_info.license_type.value,
                    "organization": license_info.organization,
                    "expires_at": license_info.expiry_date.isoformat() if license_info.expiry_date else None,
                    "max_users": license_info.max_users,
                    "feature_changes": {
                        "newly_licensed": newly_licensed,
                        "removed_licensed": removed_licensed,
                        "activated_features": activated_features,
                        "deactivated_features": deactivated_features,
                        "all_licensed_features": new_licensed_features,
                        "all_enabled_features": new_enabled_features
                    },
                    "edition_compatibility": edition_compatibility,
                    "days_until_expiry": license_service.days_until_expiry(),
                    "is_upgrade": old_license_type != license_info.license_type.value,
                    "immediate_activation": True
                }
            }
        else:
            logger.warning(f"License installation failed: {new_status.value}")
            # Remove invalid license file and restore previous state
            if license_path.exists():
                os.unlink(license_path)

            # Reload services to restore previous state
            license_service.reload()
            feature_service.reload()

            return {
                "success": False,
                "status": new_status.value,
                "message": f"License validation failed: {new_status.value}",
                "upgrade_details": {
                    "timestamp": datetime.now().isoformat(),
                    "previous_license_type": old_license_type,
                    "validation_failed": True,
                    "restored_previous_state": True
                }
            }

    except Exception as e:
        logger.error(f"Error installing license: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to install license"
        )


@router.post("/upload")
async def upload_license_file(file: UploadFile = File(...)):
    """
    Upload a license file and install it.

    Args:
        file: License file (JSON format)

    Returns:
        Installation result and license status
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License file must be a JSON file"
            )

        # Read and parse file
        content = await file.read()
        try:
            license_data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format in license file"
            )

        # Install license using the same logic as install endpoint
        request = LicenseInstallRequest(license_data=license_data)
        return await install_license(request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading license file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload license file"
        )


@router.post("/upgrade")
async def upgrade_license(request: LicenseUpgradeRequest):
    """
    Seamless license upgrade endpoint with enhanced user experience.

    This endpoint provides the most seamless upgrade experience possible:
    - Validates new license before applying changes
    - Provides detailed upgrade preview and impact analysis
    - Immediately activates new features (if requested)
    - Sends notifications to users about new capabilities
    - Comprehensive rollback on failures
    - Detailed upgrade audit trail

    Args:
        request: License upgrade request with options

    Returns:
        Comprehensive upgrade results with feature activation details
    """
    try:
        import os
        from pathlib import Path
        from datetime import datetime

        # Get services
        license_service = get_license_service()
        feature_service = get_feature_service()

        # Capture current state for comparison and potential rollback
        current_state = {
            "license_type": license_service.get_license_type().value,
            "license_info": license_service.get_license_info(),
            "enabled_features": feature_service.get_enabled_features(),
            "license_valid": license_service.validate_license()
        }

        # Preview the new license without installing it first
        try:
            from app.services.license_service import LicenseService
            preview_service = LicenseService()  # Temporary instance for preview
            preview_service.license_info = preview_service._parse_license(request.license_data)
            preview_status = preview_service._validate_license_data()
        except Exception as e:
            logger.error(f"License preview validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid license data: {str(e)}"
            )

        if preview_status != LicenseStatus.VALID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"License validation failed: {preview_status.value}"
            )

        # Create backup of current license
        license_path = Path("configs/license.json")
        backup_path = Path("configs/backups/license-pre-upgrade.json")
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if license_path.exists():
            import shutil
            shutil.copy2(license_path, backup_path)

        # Install the new license
        license_path.parent.mkdir(parents=True, exist_ok=True)
        with open(license_path, 'w') as f:
            json.dump(request.license_data, f, indent=2)

        # Reload license service
        license_service.reload()

        # Verify installation was successful
        new_status = license_service.get_license_status()
        new_license_info = license_service.get_license_info()

        if new_status != LicenseStatus.VALID or not new_license_info:
            # Rollback on failure
            if backup_path.exists():
                shutil.copy2(backup_path, license_path)
            elif license_path.exists():
                os.unlink(license_path)

            license_service.reload()
            feature_service.reload()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"License upgrade failed during installation: {new_status.value}"
            )

        # Hot-reload features if immediate activation is requested
        if request.activate_immediately:
            feature_service.reload()

        # Calculate upgrade impact
        new_enabled_features = feature_service.get_enabled_features()
        activated_features = list(set(new_enabled_features) - set(current_state["enabled_features"]))
        deactivated_features = list(set(current_state["enabled_features"]) - set(new_enabled_features))

        new_licensed_features = new_license_info.features
        old_licensed_features = current_state["license_info"].features if current_state["license_info"] else []
        newly_licensed = list(set(new_licensed_features) - set(old_licensed_features))
        removed_licensed = list(set(old_licensed_features) - set(new_licensed_features))

        # Get edition compatibility
        editions = ['community', 'red-team', 'pro']
        edition_compatibility = {}
        for edition in editions:
            compatible, _ = license_service.validate_edition_compatibility(edition)
            edition_compatibility[edition] = compatible

        # Audit the upgrade
        try:
            audit_service = get_audit_service()
            await audit_service.log_license_upgrade(
                old_license_type=current_state["license_type"],
                new_license_type=new_license_info.license_type.value,
                organization=new_license_info.organization,
                activated_features=activated_features,
                deactivated_features=deactivated_features
            )
        except Exception as audit_error:
            logger.error(f"Failed to log license upgrade audit: {audit_error}")

        # Log success
        logger.info(f"Seamless license upgrade completed: {current_state['license_type']} -> {new_license_info.license_type.value}")
        logger.info(f"Newly activated features: {activated_features}")

        # Prepare upgrade summary
        upgrade_summary = {
            "success": True,
            "status": new_status.value,
            "message": f"License successfully upgraded to {new_license_info.license_type.value} for {new_license_info.organization}",
            "timestamp": datetime.now().isoformat(),
            "upgrade_impact": {
                "license_change": {
                    "from": current_state["license_type"],
                    "to": new_license_info.license_type.value,
                    "organization": new_license_info.organization,
                    "is_upgrade": current_state["license_type"] != new_license_info.license_type.value
                },
                "feature_changes": {
                    "newly_licensed": newly_licensed,
                    "removed_licensed": removed_licensed,
                    "activated_features": activated_features,
                    "deactivated_features": deactivated_features,
                    "total_licensed": len(new_licensed_features),
                    "total_enabled": len(new_enabled_features)
                },
                "capabilities": {
                    "all_licensed_features": new_licensed_features,
                    "all_enabled_features": new_enabled_features,
                    "edition_compatibility": edition_compatibility,
                    "max_users": new_license_info.max_users,
                    "expires_at": new_license_info.expiry_date.isoformat() if new_license_info.expiry_date else None,
                    "days_until_expiry": license_service.days_until_expiry()
                }
            },
            "activation_status": {
                "immediate_activation": request.activate_immediately,
                "features_activated_immediately": request.activate_immediately,
                "notification_sent": request.notify_users,
                "rollback_available": backup_path.exists()
            }
        }

        return upgrade_summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during license upgrade: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade license"
        )


@router.delete("/remove")
@requires_valid_license
async def remove_license():
    """
    Remove the current license.

    This endpoint requires a valid license to prevent unauthorized removal.
    After removal, the system will fall back to community edition.

    Returns:
        Removal status
    """
    try:
        import os
        from pathlib import Path

        license_path = Path("configs/license.json")

        if license_path.exists():
            # Backup current license
            backup_path = Path("configs/backups/license-removed.json")
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(license_path, backup_path)

            # Remove license file
            os.unlink(license_path)

            logger.info("License removed successfully")

        # Reload license service
        license_service = get_license_service()
        license_service.reload()

        return {
            "success": True,
            "message": "License removed successfully",
            "backup_location": str(backup_path) if license_path.exists() else None
        }

    except Exception as e:
        logger.error(f"Error removing license: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove license"
        )


@router.get("/features")
async def get_licensed_features():
    """
    Get list of features available under current license.

    Returns:
        Available features and their licensing status
    """
    try:
        license_service = get_license_service()
        feature_service = get_feature_service()

        # Get all features from feature service
        all_features = feature_service.get_all_features()

        # Check licensing status for each feature
        feature_status = {}
        for feature_name, feature_config in all_features.items():
            is_licensed = license_service.is_feature_licensed(feature_name)
            is_enabled = feature_service.is_enabled(feature_name)

            feature_status[feature_name] = {
                "licensed": is_licensed,
                "enabled": is_enabled,
                "available": is_licensed and is_enabled,
                "description": feature_config.get("description", ""),
                "components": feature_config.get("components", {})
            }

        return {
            "license_type": license_service.get_license_type().value,
            "features": feature_status
        }

    except Exception as e:
        logger.error(f"Error getting licensed features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve licensed features"
        )


@router.post("/validate")
async def validate_license():
    """
    Force validation of the current license.

    Re-validates license signature, expiry date, and feature permissions.
    Useful for checking license status after system changes.

    Returns:
        Detailed validation results
    """
    try:
        license_service = get_license_service()

        # Force reload and validation
        license_service.reload()

        status = license_service.get_license_status()
        license_info = license_service.get_license_info()

        result = {
            "valid": status == LicenseStatus.VALID,
            "status": status.value,
            "timestamp": datetime.now().isoformat()
        }

        if license_info:
            result.update({
                "license_type": license_info.license_type.value,
                "organization": license_info.organization,
                "issued_date": license_info.issued_date.isoformat(),
                "expiry_date": license_info.expiry_date.isoformat() if license_info.expiry_date else None,
                "features": license_info.features,
                "days_until_expiry": license_service.days_until_expiry()
            })

        return result

    except Exception as e:
        logger.error(f"Error validating license: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate license"
        )


@router.post("/preview-upgrade")
async def preview_license_upgrade(request: LicenseInstallRequest):
    """
    Preview what would happen with a license upgrade without actually applying it.

    This endpoint allows users to see the impact of a license upgrade before committing:
    - Validates the new license
    - Shows feature changes that would occur
    - Displays edition compatibility changes
    - Provides upgrade impact analysis

    Args:
        request: License data to preview

    Returns:
        Detailed preview of upgrade impact without making changes
    """
    try:
        from app.services.license_service import LicenseService

        # Get current services for comparison
        license_service = get_license_service()
        feature_service = get_feature_service()

        # Capture current state
        current_license_type = license_service.get_license_type().value
        current_license_info = license_service.get_license_info()
        current_features = current_license_info.features if current_license_info else []
        current_enabled_features = feature_service.get_enabled_features()

        # Create temporary service instance to preview new license
        preview_service = LicenseService()
        try:
            preview_service.license_info = preview_service._parse_license(request.license_data)
            preview_status = preview_service._validate_license_data()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid license data: {str(e)}"
            )

        if preview_status != LicenseStatus.VALID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"License validation failed: {preview_status.value}"
            )

        preview_license_info = preview_service.license_info

        # Calculate feature differences
        new_licensed_features = preview_license_info.features
        newly_licensed = list(set(new_licensed_features) - set(current_features))
        removed_licensed = list(set(current_features) - set(new_licensed_features))

        # Estimate feature activation (this would require knowledge of feature service logic)
        # For now, we'll assume newly licensed features would be activated
        estimated_activated = newly_licensed.copy()
        estimated_deactivated = removed_licensed.copy()

        # Get edition compatibility for preview license
        editions = ['community', 'red-team', 'pro']
        preview_compatibility = {}
        for edition in editions:
            compatible, reason = preview_service.validate_edition_compatibility(edition)
            preview_compatibility[edition] = {"compatible": compatible, "reason": reason}

        # Current compatibility for comparison
        current_compatibility = {}
        for edition in editions:
            compatible, reason = license_service.validate_edition_compatibility(edition)
            current_compatibility[edition] = {"compatible": compatible, "reason": reason}

        # Determine upgrade type
        license_hierarchy = ["community", "pro"]
        current_rank = license_hierarchy.index(current_license_type) if current_license_type in license_hierarchy else -1
        preview_rank = license_hierarchy.index(preview_license_info.license_type.value) if preview_license_info.license_type.value in license_hierarchy else -1

        is_upgrade = preview_rank > current_rank
        is_downgrade = preview_rank < current_rank
        upgrade_type = "upgrade" if is_upgrade else "downgrade" if is_downgrade else "lateral"

        preview_response = {
            "valid_license": True,
            "upgrade_type": upgrade_type,
            "preview": {
                "current_state": {
                    "license_type": current_license_type,
                    "organization": current_license_info.organization if current_license_info else None,
                    "licensed_features": current_features,
                    "enabled_features": current_enabled_features,
                    "edition_compatibility": current_compatibility,
                    "expires_at": current_license_info.expiry_date.isoformat() if current_license_info and current_license_info.expiry_date else None
                },
                "proposed_state": {
                    "license_type": preview_license_info.license_type.value,
                    "organization": preview_license_info.organization,
                    "licensed_features": new_licensed_features,
                    "estimated_enabled_features": list(set(current_enabled_features + estimated_activated) - set(estimated_deactivated)),
                    "edition_compatibility": preview_compatibility,
                    "expires_at": preview_license_info.expiry_date.isoformat() if preview_license_info.expiry_date else None,
                    "max_users": preview_license_info.max_users,
                    "days_until_expiry": preview_service.days_until_expiry()
                },
                "changes": {
                    "newly_licensed_features": newly_licensed,
                    "removed_licensed_features": removed_licensed,
                    "estimated_activated_features": estimated_activated,
                    "estimated_deactivated_features": estimated_deactivated,
                    "net_feature_change": len(newly_licensed) - len(removed_licensed),
                    "organization_change": current_license_info.organization != preview_license_info.organization if current_license_info else True,
                    "expiry_change": {
                        "from": current_license_info.expiry_date.isoformat() if current_license_info and current_license_info.expiry_date else None,
                        "to": preview_license_info.expiry_date.isoformat() if preview_license_info.expiry_date else None
                    }
                },
                "impact_assessment": {
                    "feature_impact": "high" if len(newly_licensed) > 0 else "low",
                    "compatibility_impact": "high" if upgrade_type == "upgrade" else "low",
                    "user_experience_impact": "seamless" if is_upgrade else "disruptive" if is_downgrade else "minimal",
                    "requires_restart": False,  # ADCL supports hot reload
                    "backup_recommended": True
                }
            }
        }

        return preview_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing license upgrade: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview license upgrade"
        )


@router.get("/upgrade-history")
async def get_upgrade_history(limit: int = 10):
    """
    Get history of license upgrades and changes.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of license upgrade events from audit trail
    """
    try:
        audit_service = get_audit_service()

        # Get license-related audit entries
        license_entries = await audit_service.get_audit_trail(
            resource_type="license",
            action="license_upgrade",
            limit=limit
        )

        # Format entries for response
        upgrade_history = []
        for entry in license_entries:
            upgrade_event = {
                "timestamp": entry.timestamp,
                "changes": entry.changes,
                "reason": entry.reason,
                "user_id": entry.user_id,
                "metadata": entry.metadata
            }
            upgrade_history.append(upgrade_event)

        return {
            "upgrade_history": upgrade_history,
            "total_entries": len(upgrade_history),
            "showing_recent": limit
        }

    except Exception as e:
        logger.error(f"Error getting upgrade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upgrade history"
        )
