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
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from app.services.version_service import VersionService
from app.services.upgrade_service import UpgradeService
from app.services.feature_service import get_feature_service
from app.services.config_version_service import get_config_version_service
import json
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# Initialize services
version_service = VersionService()
upgrade_service = UpgradeService()


class UpgradeRequest(BaseModel):
    """Request to apply an upgrade"""
    target_version: str
    auto_backup: bool = True


class SecurityPolicyUpdate(BaseModel):
    """Request to update security policy"""
    tier_enabled: Optional[Dict[str, bool]] = None
    global_kill_switch: Optional[bool] = None


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


@router.get("/security/policy")
async def get_security_policy():
    """
    Get current security policy configuration

    Returns tier settings and global kill switch status
    """
    config_dir = os.environ.get('ADCL_SYSTEM_CONFIG_DIR', '/configs')
    policy_path = os.path.join(config_dir, 'security_policy.json')

    try:
        with open(policy_path, 'r') as f:
            policy = json.load(f)
        return policy
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Security policy file not found at {policy_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read security policy: {str(e)}"
        )


@router.patch("/security/policy")
async def update_security_policy(update: SecurityPolicyUpdate):
    """
    Update security policy configuration

    Args:
        update: Security policy updates (tier_enabled and/or global_kill_switch)

    Returns:
        Updated security policy
    """
    config_dir = os.environ.get('ADCL_SYSTEM_CONFIG_DIR', '/configs')
    policy_path = os.path.join(config_dir, 'security_policy.json')

    try:
        # Read current policy
        with open(policy_path, 'r') as f:
            policy = json.load(f)

        # Update fields if provided
        if update.tier_enabled is not None:
            policy["tier_enabled"].update(update.tier_enabled)

        if update.global_kill_switch is not None:
            policy["global_kill_switch"] = update.global_kill_switch

        # Write updated policy
        with open(policy_path, 'w') as f:
            json.dump(policy, f, indent=2)

        return {
            "status": "updated",
            "policy": policy
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Security policy file not found at {policy_path}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update security policy: {str(e)}"
        )


@router.get("/features")
async def get_features():
    """
    Get current feature flags and edition information.

    Returns enabled features, product edition, and component-level flags.
    This allows frontend to conditionally show/hide features based on edition.

    Example response:
    {
        "edition": "red-team",
        "enabled_features": ["core_platform", "red_team"],
        "features": {
            "core_platform": {"enabled": true, "locked": true, ...},
            "red_team": {"enabled": true, "locked": false, ...}
        }
    }
    """
    try:
        feature_service = get_feature_service()

        return {
            "status": "success",
            "edition": feature_service.get_edition(),
            "enabled_features": feature_service.get_enabled_features(),
            "features": feature_service.get_all_features()
        }
    except RuntimeError as e:
        # FeatureService not initialized
        raise HTTPException(
            status_code=503,
            detail=f"Feature service not available: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve features: {str(e)}"
        )


class EditionSwitchRequest(BaseModel):
    """Request to switch product edition"""
    edition: str  # e.g., "community", "red-team", "custom"
    restart_backend: bool = True


class AutoEditionRequest(BaseModel):
    """Request for automated edition detection and switching"""
    environment: Optional[str] = None  # Override auto-detection
    force_switch: bool = False  # Switch even if already on detected edition


@router.get("/editions")
async def get_editions():
    """
    Get all available editions with their feature comparisons.
    
    Returns a comparison of all available editions showing:
    - Edition metadata (name, description, target audience)
    - Feature availability matrix
    - Package/tool dependencies
    - Use case descriptions
    
    This enables frontend to show edition comparison UI for selection.
    """
    try:
        # Get configs directory (handle both container and local dev)
        configs_dir = Path(os.getenv('ADCL_SYSTEM_CONFIG_DIR', '/configs'))
        if not configs_dir.exists():
            # Fallback for local development
            base_dir = Path(os.getenv('APP_BASE_DIR', os.getcwd())).parent
            configs_dir = base_dir / "configs"
        
        editions_dir = configs_dir / "editions"
        
        if not editions_dir.exists():
            raise HTTPException(
                status_code=404,
                detail="Editions directory not found"
            )
        
        editions = {}
        
        # Load all edition files
        for edition_file in editions_dir.glob("*.json"):
            if edition_file.name.startswith("."):
                continue
                
            try:
                with open(edition_file) as f:
                    edition_data = json.load(f)
                
                edition_name = edition_file.stem
                
                # Extract key information for comparison
                features = edition_data.get("features", {})
                packages = edition_data.get("auto_install", {}).get("packages", {})
                
                # Build tool list from enabled packages
                tools = []
                for pkg_name, pkg_config in packages.items():
                    if pkg_config.get("enabled", False):
                        tools.append({
                            "name": pkg_name,
                            "category": pkg_config.get("category", "unknown"),
                            "description": pkg_config.get("description", ""),
                            "required": pkg_config.get("required", False)
                        })
                
                # Build capabilities list from features
                capabilities = []
                for feature_name, feature_config in features.items():
                    if feature_config.get("enabled", False):
                        components = feature_config.get("components", {})
                        for comp_name, comp_enabled in components.items():
                            if comp_enabled:
                                capabilities.append({
                                    "name": comp_name.replace("_", " ").title(),
                                    "feature": feature_name,
                                    "description": feature_config.get("description", "")
                                })
                
                # Determine target audience and use cases
                target_audience = "General Users"
                use_cases = ["AI Agent Development", "Workflow Automation"]
                
                if edition_name == "community":
                    target_audience = "Open Source Users, Developers, Learning"
                    use_cases = [
                        "AI agent development and testing",
                        "Workflow automation",
                        "Model evaluation and comparison",
                        "Team collaboration on AI projects"
                    ]
                elif edition_name == "red-team":
                    target_audience = "Security Professionals, Penetration Testers"
                    use_cases = [
                        "Red team operations and penetration testing",
                        "Vulnerability assessment and exploitation",
                        "Security research and analysis",
                        "Attack simulation and validation"
                    ]
                elif edition_name == "custom-example":
                    target_audience = "Enterprise Users, Specialized Deployments"
                    use_cases = [
                        "Custom security testing workflows",
                        "Specialized tool combinations",
                        "Enterprise compliance requirements",
                        "Tailored deployment scenarios"
                    ]
                
                editions[edition_name] = {
                    "name": edition_data.get("edition", edition_name),
                    "display_name": edition_name.replace("-", " ").title().replace("Example", ""),
                    "description": edition_data.get("description", ""),
                    "version": edition_data.get("version", "2.0"),
                    "target_audience": target_audience,
                    "use_cases": use_cases,
                    "features": features,
                    "tools": tools,
                    "capabilities": capabilities,
                    "tool_count": len(tools),
                    "security_focused": any(pkg.get("category") == "security" and pkg.get("enabled") for pkg in packages.values())
                }
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse edition file {edition_file}: {e}")
                continue
        
        # Get current edition for highlighting
        current_edition = "unknown"
        try:
            config_file = configs_dir / "auto-install.json"
            if config_file.exists():
                with open(config_file) as f:
                    current_data = json.load(f)
                    current_edition = current_data.get("edition", "unknown")
        except Exception:
            pass
        
        return {
            "status": "success",
            "current_edition": current_edition,
            "editions": editions,
            "comparison_matrix": _build_comparison_matrix(editions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load editions: {str(e)}"
        )


def _build_comparison_matrix(editions):
    """Build a feature comparison matrix for all editions"""
    all_features = set()
    all_tools = set()
    
    # Collect all possible features and tools
    for edition_data in editions.values():
        for feature_name, feature_config in edition_data["features"].items():
            if feature_config.get("enabled"):
                all_features.add(feature_name)
        
        for tool in edition_data["tools"]:
            all_tools.add(tool["name"])
    
    # Build comparison matrix
    feature_matrix = {}
    for feature in all_features:
        feature_matrix[feature] = {}
        for edition_name, edition_data in editions.items():
            feature_config = edition_data["features"].get(feature, {})
            feature_matrix[feature][edition_name] = feature_config.get("enabled", False)
    
    tool_matrix = {}
    for tool in all_tools:
        tool_matrix[tool] = {}
        for edition_name, edition_data in editions.items():
            enabled = any(t["name"] == tool for t in edition_data["tools"])
            tool_matrix[tool][edition_name] = enabled
    
    return {
        "features": feature_matrix,
        "tools": tool_matrix
    }


@router.put("/edition")
async def switch_edition(request: EditionSwitchRequest):
    """
    Switch product edition by copying preset config.

    This endpoint:
    1. Validates the target edition exists
    2. Captures current state for audit logging
    3. Backs up current config
    4. Copies the new edition config to auto-install.json
    5. Records audit trail of the edition change
    6. Reloads FeatureService
    7. Returns restart instructions if needed

    Args:
        request: Edition name and restart preference

    Returns:
        Result of edition switch with instructions

    Note:
        Backend restart may be required for router changes to take effect.
        Use restart_backend=true to automatically trigger restart.
    """
    import shutil
    from pathlib import Path
    from datetime import datetime

    try:
        # Get configs directory (handle both container and local dev) - same as get_editions
        configs_dir = Path(os.getenv('ADCL_SYSTEM_CONFIG_DIR', '/configs'))
        if not configs_dir.exists():
            # Fallback for local development
            base_dir = Path(os.getenv('APP_BASE_DIR', os.getcwd())).parent
            configs_dir = base_dir / "configs"

        # Validate edition name to prevent path traversal
        if not re.match(r'^[a-zA-Z0-9_-]+$', request.edition):
            raise HTTPException(
                status_code=400,
                detail="Invalid edition name. Must contain only alphanumeric characters, dashes, and underscores."
            )

        # Validate edition file exists
        edition_file = configs_dir / "editions" / f"{request.edition}.json"
        if not edition_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Edition '{request.edition}' not found. Available editions: community, red-team, custom-example"
            )

        # Capture current state for audit logging
        current_config = configs_dir / "auto-install.json"
        old_edition = "unknown"
        old_features = []
        old_tools = []
        
        if current_config.exists():
            with open(current_config) as f:
                current_data = json.load(f)
                old_edition = current_data.get("edition", "unknown")
                
                # Extract current features
                features = current_data.get("features", {})
                old_features = [name for name, config in features.items() if config.get("enabled", False)]
                
                # Extract current tools
                packages = current_data.get("auto_install", {}).get("packages", {})
                old_tools = [name for name, config in packages.items() if config.get("enabled", False)]

        # Load new edition config to capture new state
        with open(edition_file) as f:
            new_data = json.load(f)
            new_edition = request.edition
            
            # Extract new features
            new_features_config = new_data.get("features", {})
            new_features = [name for name, config in new_features_config.items() if config.get("enabled", False)]
            
            # Extract new tools
            new_packages = new_data.get("auto_install", {}).get("packages", {})
            new_tools = [name for name, config in new_packages.items() if config.get("enabled", False)]

        # Backup current config
        backup_dir = configs_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = None

        if current_config.exists():
            backup_file = backup_dir / f"auto-install-{old_edition}-{timestamp}.json"
            shutil.copy2(current_config, backup_file)
            logger.info(f"Backed up current config to {backup_file}")

        # Copy new edition config
        shutil.copy2(edition_file, current_config)
        logger.info(f"Switched to {request.edition} edition")

        # Record audit trail of edition change
        try:
            from app.services.audit_service import AuditService
            from pathlib import Path as AuditPath
            
            audit_service = AuditService(AuditPath("configs/audit_trail.jsonl"))
            
            # TODO: Extract user ID from request context (authentication)
            # For now, using None - in production, this should come from authentication middleware
            user_id = None
            
            # Collect additional metadata
            audit_metadata = {
                "backup_file": str(backup_file) if backup_file else None,
                "config_version": new_data.get("version", "unknown"),
                "restart_required": request.restart_backend,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await audit_service.record_edition_change(
                old_edition=old_edition,
                new_edition=new_edition,
                old_features=old_features,
                new_features=new_features,
                old_tools=old_tools,
                new_tools=new_tools,
                reason=f"Edition switched via API from {old_edition} to {new_edition}",
                user_id=user_id,
                metadata=audit_metadata
            )
            
            logger.info(f"Edition change audit logged: {old_edition} -> {new_edition}")
            
        except Exception as e:
            # Don't fail the edition switch if audit logging fails, but log the error
            logger.error(f"Failed to record edition change audit: {e}")

        # Reload FeatureService
        feature_service = get_feature_service()
        feature_service.reload()
        logger.info(f"FeatureService reloaded: {feature_service}")

        # Check if backend restart is needed
        # (routers are conditionally included at startup, so restart is required)
        needs_restart = True

        return {
            "status": "success",
            "message": f"Switched to {request.edition} edition",
            "edition": request.edition,
            "previous_edition": old_edition,
            "enabled_features": feature_service.get_enabled_features(),
            "features_changed": {
                "added": list(set(new_features) - set(old_features)),
                "removed": list(set(old_features) - set(new_features))
            },
            "tools_changed": {
                "added": list(set(new_tools) - set(old_tools)),
                "removed": list(set(old_tools) - set(new_tools))
            },
            "needs_restart": needs_restart,
            "restart_instructions": (
                "Backend restart required for router changes to take effect. "
                "Run: docker-compose restart backend"
            ) if needs_restart else None,
            "backup_file": str(backup_file) if backup_file else None,
            "audit_logged": True
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Edition file not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch edition: {str(e)}"
        )


@router.post("/edition/auto")
async def auto_switch_edition(request: AutoEditionRequest):
    """
    Automatically detect and switch to appropriate edition for CI/CD environments.
    
    Detection logic:
    1. Check CI environment variables (CI=true, GITHUB_ACTIONS, etc.)
    2. Check ADCL_ENVIRONMENT variable
    3. Check predefined environment markers
    4. Fall back to community edition
    
    Args:
        request: Optional environment override and force switch flag
    
    Returns:
        Detection result and switch status
    """
    import os
    
    try:
        # Auto-detect environment if not provided
        detected_env = request.environment
        if not detected_env:
            detected_env = _detect_environment()
        
        # Map environment to edition
        edition_mapping = {
            "development": "community",
            "testing": "red-team",
            "staging": "red-team", 
            "production": "community",
            "ci": "community",
            "security-testing": "red-team",
            "red-team": "red-team",
            "pentest": "red-team"
        }
        
        target_edition = edition_mapping.get(detected_env.lower(), "community")
        
        # Get current edition
        feature_service = get_feature_service()
        current_edition = feature_service.get_edition()
        
        # Check if switch is needed
        if current_edition == target_edition and not request.force_switch:
            return {
                "status": "no_action",
                "message": f"Already on {target_edition} edition for {detected_env} environment",
                "detected_environment": detected_env,
                "current_edition": current_edition,
                "target_edition": target_edition,
                "switched": False
            }
        
        # Perform switch
        switch_request = EditionSwitchRequest(
            edition=target_edition,
            restart_backend=False  # Let CI/CD handle restart
        )
        
        switch_result = await switch_edition(switch_request)
        
        return {
            "status": "success",
            "message": f"Auto-switched from {current_edition} to {target_edition} for {detected_env} environment",
            "detected_environment": detected_env,
            "previous_edition": current_edition,
            "current_edition": target_edition,
            "switched": True,
            "switch_details": switch_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Auto edition switch failed: {str(e)}"
        )


def _detect_environment() -> str:
    """
    Detect current environment from various sources.
    
    Checks in priority order:
    1. ADCL_ENVIRONMENT variable
    2. Common CI environment variables 
    3. Docker environment markers
    4. Kubernetes environment markers
    5. Default to development
    """
    import os
    
    # Explicit environment override
    if env := os.getenv("ADCL_ENVIRONMENT"):
        return env
    
    # CI/CD environment detection
    if os.getenv("CI"):
        # Generic CI environment
        if os.getenv("GITHUB_ACTIONS"):
            return "ci"
        elif os.getenv("GITLAB_CI"):
            return "ci" 
        elif os.getenv("JENKINS_URL"):
            return "ci"
        else:
            return "ci"
    
    # Specific testing environments
    if os.getenv("SECURITY_TESTING") or os.getenv("PENTEST_MODE"):
        return "security-testing"
    
    # Deployment environment
    if stage := os.getenv("STAGE") or os.getenv("ENVIRONMENT"):
        return stage
        
    # Docker/Kubernetes markers
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        # In Kubernetes, check namespace or labels
        namespace = os.getenv("POD_NAMESPACE", "")
        if "test" in namespace or "security" in namespace:
            return "testing"
        elif "prod" in namespace:
            return "production"
    
    # Default
    return "development"


@router.get("/edition/detect")
async def detect_environment():
    """
    Detect current environment and recommend edition without switching.
    
    Useful for CI/CD pipelines to understand what edition would be selected
    before making changes.
    """
    try:
        detected_env = _detect_environment()
        
        # Map environment to edition
        edition_mapping = {
            "development": "community",
            "testing": "red-team", 
            "staging": "red-team",
            "production": "community",
            "ci": "community",
            "security-testing": "red-team",
            "red-team": "red-team",
            "pentest": "red-team"
        }
        
        recommended_edition = edition_mapping.get(detected_env.lower(), "community")
        
        # Get current edition
        feature_service = get_feature_service()
        current_edition = feature_service.get_edition()
        
        # Check environment variables for context
        env_vars = {}
        for var in ["CI", "ADCL_ENVIRONMENT", "STAGE", "ENVIRONMENT", 
                   "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL",
                   "SECURITY_TESTING", "PENTEST_MODE", "KUBERNETES_SERVICE_HOST"]:
            if value := os.getenv(var):
                env_vars[var] = value
        
        return {
            "status": "success",
            "detected_environment": detected_env,
            "current_edition": current_edition,
            "recommended_edition": recommended_edition,
            "switch_needed": current_edition != recommended_edition,
            "environment_variables": env_vars,
            "detection_reason": _get_detection_reason(detected_env, env_vars)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Environment detection failed: {str(e)}"
        )


def _get_detection_reason(detected_env: str, env_vars: dict) -> str:
    """Generate human-readable explanation of environment detection"""
    if env_vars.get("ADCL_ENVIRONMENT"):
        return f"Explicitly set via ADCL_ENVIRONMENT={env_vars['ADCL_ENVIRONMENT']}"
    elif env_vars.get("CI"):
        ci_system = "unknown CI"
        if env_vars.get("GITHUB_ACTIONS"):
            ci_system = "GitHub Actions"
        elif env_vars.get("GITLAB_CI"):
            ci_system = "GitLab CI"
        elif env_vars.get("JENKINS_URL"):
            ci_system = "Jenkins"
        return f"Detected {ci_system} environment (CI=true)"
    elif env_vars.get("SECURITY_TESTING") or env_vars.get("PENTEST_MODE"):
        return "Security testing mode enabled"
    elif env_vars.get("STAGE") or env_vars.get("ENVIRONMENT"):
        stage = env_vars.get("STAGE") or env_vars.get("ENVIRONMENT")
        return f"Stage/Environment variable set to '{stage}'"
    elif env_vars.get("KUBERNETES_SERVICE_HOST"):
        return "Kubernetes environment detected"
    else:
        return "Default development environment (no specific markers found)"


@router.post("/edition/validate")
async def validate_edition_config(edition: str):
    """
    Validate edition configuration without switching.
    
    Useful for CI/CD validation steps to ensure edition configs are valid
    before deployment.
    
    Args:
        edition: Edition name to validate
        
    Returns:
        Validation result with any issues found
    """
    import json
    from pathlib import Path
    
    try:
        # Get configs directory
        configs_dir = Path(os.getenv('ADCL_SYSTEM_CONFIG_DIR', '/configs'))
        if not configs_dir.exists():
            base_dir = Path(os.getenv('APP_BASE_DIR', os.getcwd())).parent
            configs_dir = base_dir / "configs"
        
        # Validate edition name format
        if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
            return {
                "valid": False,
                "errors": ["Invalid edition name format. Must contain only alphanumeric characters, dashes, and underscores."],
                "warnings": []
            }
        
        # Check if edition file exists
        edition_file = configs_dir / "editions" / f"{edition}.json"
        if not edition_file.exists():
            return {
                "valid": False,
                "errors": [f"Edition file not found: {edition_file}"],
                "warnings": []
            }
        
        # Validate JSON structure
        errors = []
        warnings = []
        
        with open(edition_file) as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "errors": [f"Invalid JSON in edition file: {str(e)}"],
                    "warnings": []
                }
        
        # Validate required fields
        required_fields = ["version", "edition", "features", "auto_install"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate features structure
        if "features" in config:
            for feature_name, feature_config in config["features"].items():
                if not isinstance(feature_config, dict):
                    errors.append(f"Feature '{feature_name}' must be an object")
                    continue
                
                required_feature_fields = ["enabled", "locked"]
                for field in required_feature_fields:
                    if field not in feature_config:
                        warnings.append(f"Feature '{feature_name}' missing recommended field: {field}")
        
        # Validate packages structure
        if "auto_install" in config and "packages" in config["auto_install"]:
            packages = config["auto_install"]["packages"]
            for pkg_name, pkg_config in packages.items():
                if not isinstance(pkg_config, dict):
                    errors.append(f"Package '{pkg_name}' must be an object")
                    continue
                
                if pkg_config.get("required", False) and not pkg_config.get("enabled", False):
                    warnings.append(f"Required package '{pkg_name}' is not enabled")
        
        # Check for core platform requirements
        if "features" in config:
            core_platform = config["features"].get("core_platform", {})
            if not core_platform.get("enabled", False):
                warnings.append("Core platform feature is not enabled - this may cause issues")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "edition_name": config.get("edition", edition),
            "version": config.get("version", "unknown"),
            "description": config.get("description", ""),
            "feature_count": len(config.get("features", {})),
            "package_count": len(config.get("auto_install", {}).get("packages", {}))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Edition validation failed: {str(e)}"
        )


@router.get("/config/versions")
async def get_config_versions():
    """
    Get version information for all edition configurations.
    
    Returns version tracking metadata, changelog entries, and schema information
    for all available editions.
    """
    try:
        config_service = get_config_version_service()
        return {
            "status": "success",
            "versions": config_service.get_edition_versions()
        }
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Config version service not available: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get config versions: {str(e)}"
        )


@router.get("/config/{edition}/history")
async def get_config_history(edition: str):
    """
    Get change history for a specific edition configuration.
    
    Args:
        edition: Edition name (e.g., "community", "red-team")
        
    Returns:
        Chronological list of configuration changes with metadata
    """
    # Validate edition name
    if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
        raise HTTPException(
            status_code=400,
            detail="Invalid edition name format"
        )
    
    try:
        config_service = get_config_version_service()
        history = config_service.get_config_history(edition)
        
        return {
            "status": "success", 
            "edition": edition,
            "history": history,
            "total_changes": len(history)
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{edition}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get config history: {str(e)}"
        )


@router.get("/config/compare/{edition1}/{edition2}")
async def compare_configs(edition1: str, edition2: str):
    """
    Compare two edition configurations.
    
    Args:
        edition1: First edition name
        edition2: Second edition name
        
    Returns:
        Detailed comparison showing differences in features, packages, and metadata
    """
    # Validate edition names
    for edition in [edition1, edition2]:
        if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid edition name format: {edition}"
            )
    
    try:
        config_service = get_config_version_service()
        comparison = config_service.compare_configs(edition1, edition2)
        
        if "error" in comparison:
            raise HTTPException(
                status_code=404,
                detail=comparison["error"]
            )
        
        return {
            "status": "success",
            "comparison": comparison
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare configs: {str(e)}"
        )


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration with version tracking"""
    changes: List[str]
    author: str = "api-user"


@router.post("/config/{edition}/update")
async def update_config_metadata(edition: str, request: ConfigUpdateRequest):
    """
    Update configuration metadata and add changelog entry.
    
    This endpoint allows updating the version control metadata for a configuration
    without changing the actual feature/package settings. Used for documenting
    configuration changes and maintaining audit trails.
    
    Args:
        edition: Edition name
        request: Update request with changes and author
        
    Returns:
        Updated configuration with new metadata
    """
    # Validate edition name
    if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
        raise HTTPException(
            status_code=400,
            detail="Invalid edition name format"
        )
    
    try:
        config_service = get_config_version_service()
        
        # Load current config
        config = config_service.load_edition_config(edition)
        
        # Save with updated metadata
        updated_config = config_service.save_edition_config(
            edition, config, request.author, request.changes
        )
        
        return {
            "status": "success",
            "edition": edition,
            "version": updated_config.get("version"),
            "metadata": updated_config.get("metadata", {}),
            "changes_recorded": request.changes
        }
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{edition}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update config metadata: {str(e)}"
        )


@router.post("/config/{edition}/backup")
async def backup_config(edition: str):
    """
    Create backup of edition configuration.
    
    Args:
        edition: Edition name
        
    Returns:
        Backup file information
    """
    # Validate edition name
    if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
        raise HTTPException(
            status_code=400,
            detail="Invalid edition name format"
        )
    
    try:
        config_service = get_config_version_service()
        backup_file = config_service.backup_config(edition)
        
        return {
            "status": "success",
            "edition": edition,
            "backup_file": backup_file,
            "created_at": datetime.now().isoformat()
        }
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Edition '{edition}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create backup: {str(e)}"
        )


class ConfigRestoreRequest(BaseModel):
    """Request to restore configuration from backup"""
    backup_file: str
    author: str = "api-user"


@router.post("/config/{edition}/restore")
async def restore_config(edition: str, request: ConfigRestoreRequest):
    """
    Restore edition configuration from backup.
    
    Args:
        edition: Edition name
        request: Restore request with backup file path
        
    Returns:
        Restoration result
    """
    # Validate edition name
    if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
        raise HTTPException(
            status_code=400,
            detail="Invalid edition name format"
        )
    
    # Validate backup file path to prevent directory traversal
    if not re.match(r'^[a-zA-Z0-9_-]+\.json$', os.path.basename(request.backup_file)):
        raise HTTPException(
            status_code=400,
            detail="Invalid backup file format"
        )
    
    try:
        config_service = get_config_version_service()
        restored_config = config_service.restore_config(
            edition, request.backup_file, request.author
        )
        
        return {
            "status": "success",
            "edition": edition,
            "restored_from": request.backup_file,
            "version": restored_config.get("version"),
            "restored_at": datetime.now().isoformat()
        }
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore config: {str(e)}"
        )


@router.post("/config/validate")
async def validate_all_configs():
    """
    Validate all edition configurations.
    
    Checks all edition files for structural validity, schema compliance,
    and version tracking metadata.
    
    Returns:
        Validation results for all editions
    """
    try:
        config_service = get_config_version_service()
        results = config_service.validate_all_configs()
        
        # Count valid vs invalid configs
        valid_count = sum(1 for r in results.values() if r.get("valid", False))
        total_count = len(results)
        
        return {
            "status": "success",
            "summary": {
                "total_configs": total_count,
                "valid_configs": valid_count,
                "invalid_configs": total_count - valid_count
            },
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate configs: {str(e)}"
        )


class ConfigMigrationRequest(BaseModel):
    """Request to migrate configuration schema"""
    target_version: Optional[str] = None


class CustomToolInstallRequest(BaseModel):
    """Request to install a custom tool"""
    name: str
    source: str  # URL, file path, or registry reference
    version: Optional[str] = None
    type: str = "mcp"  # mcp, binary, script
    description: Optional[str] = None
    category: str = "custom"
    validate_only: bool = False


class CustomToolManifest(BaseModel):
    """Custom tool manifest for validation"""
    name: str
    version: str = "1.0.0"
    description: str
    type: str = "mcp"
    category: str = "custom"
    author: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    dependencies: Optional[Dict[str, str]] = None
    tools: Optional[List[str]] = None
    deployment: Optional[Dict[str, Any]] = None


@router.post("/tools/custom/install")
async def install_custom_tool(request: CustomToolInstallRequest):
    """
    Install a custom tool to the current edition.

    This endpoint allows red team operators to install additional custom tools
    by providing various source types (URL, file, registry).

    Args:
        request: Custom tool installation request

    Returns:
        Installation result with tool information
    """
    try:
        # Import here to avoid circular imports
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        
        if request.validate_only:
            # Validation only mode
            result = await tool_service.validate_tool(request)
            return {
                "status": "validation_complete",
                "valid": result["valid"],
                "tool_info": result.get("tool_info"),
                "warnings": result.get("warnings", []),
                "errors": result.get("errors", [])
            }
        
        # Full installation
        result = await tool_service.install_custom_tool(request)
        
        return {
            "status": "success" if result["success"] else "failed",
            "message": result["message"],
            "tool_info": result.get("tool_info"),
            "installation_path": result.get("installation_path"),
            "requires_restart": result.get("requires_restart", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom tool installation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to install custom tool: {str(e)}"
        )


@router.get("/tools/custom")
async def list_custom_tools():
    """
    List all installed custom tools.

    Returns list of custom tools with their metadata and status.
    """
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        tools = await tool_service.list_custom_tools()
        
        return {
            "status": "success",
            "tools": tools,
            "count": len(tools)
        }
        
    except Exception as e:
        logger.error(f"Failed to list custom tools: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list custom tools: {str(e)}"
        )


@router.get("/tools/custom/{tool_name}")
async def get_custom_tool(tool_name: str):
    """
    Get detailed information about a custom tool.

    Args:
        tool_name: Name of the custom tool

    Returns:
        Tool details including manifest, status, and capabilities
    """
    # Validate tool name
    if not re.match(r'^[a-zA-Z0-9_-]+$', tool_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid tool name format"
        )
    
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        tool_info = await tool_service.get_tool_info(tool_name)
        
        if not tool_info:
            raise HTTPException(
                status_code=404,
                detail=f"Custom tool '{tool_name}' not found"
            )
        
        return {
            "status": "success",
            "tool": tool_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tool information: {str(e)}"
        )


@router.delete("/tools/custom/{tool_name}")
async def uninstall_custom_tool(tool_name: str, force: bool = False):
    """
    Uninstall a custom tool.

    Args:
        tool_name: Name of the custom tool to remove
        force: Force removal even if dependencies exist

    Returns:
        Removal result
    """
    # Validate tool name
    if not re.match(r'^[a-zA-Z0-9_-]+$', tool_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid tool name format"
        )
    
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        result = await tool_service.uninstall_tool(tool_name, force=force)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        return {
            "status": "success",
            "message": result["message"],
            "requires_restart": result.get("requires_restart", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to uninstall tool: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to uninstall tool: {str(e)}"
        )


@router.post("/tools/custom/{tool_name}/validate")
async def validate_custom_tool(tool_name: str):
    """
    Validate a custom tool installation and configuration.

    Args:
        tool_name: Name of the custom tool to validate

    Returns:
        Validation result with status and any issues
    """
    # Validate tool name
    if not re.match(r'^[a-zA-Z0-9_-]+$', tool_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid tool name format"
        )
    
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        result = await tool_service.validate_installed_tool(tool_name)
        
        return {
            "status": "success",
            "tool_name": tool_name,
            "valid": result["valid"],
            "issues": result.get("issues", []),
            "warnings": result.get("warnings", []),
            "capabilities": result.get("capabilities", [])
        }
        
    except Exception as e:
        logger.error(f"Tool validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate tool: {str(e)}"
        )


@router.post("/tools/custom/manifest/create")
async def create_tool_manifest(manifest: CustomToolManifest):
    """
    Create a manifest for a custom tool.

    This endpoint helps users create properly formatted tool manifests
    for their custom tools before installation.

    Args:
        manifest: Tool manifest data

    Returns:
        Generated manifest file content
    """
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        result = tool_service.create_tool_manifest(manifest)
        
        return {
            "status": "success",
            "manifest": result["manifest"],
            "validation": result["validation"]
        }
        
    except Exception as e:
        logger.error(f"Manifest creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create manifest: {str(e)}"
        )


@router.get("/tools/custom/templates")
async def get_tool_templates():
    """
    Get available custom tool templates.

    Returns templates for different tool types (MCP server, binary wrapper, script).
    """
    try:
        from app.services.custom_tool_service import get_custom_tool_service
        
        tool_service = get_custom_tool_service()
        templates = tool_service.get_tool_templates()
        
        return {
            "status": "success",
            "templates": templates
        }
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tool templates: {str(e)}"
        )


@router.get("/audit/editions")
async def get_edition_audit_trail(
    limit: int = 50,
    offset: int = 0,
    edition: Optional[str] = None,
    days: Optional[int] = None
):
    """
    Get audit trail for edition changes.
    
    Returns chronological list of edition changes with detailed information
    about features and tools that were modified.
    
    Args:
        limit: Maximum number of entries to return (default: 50, max: 500)
        offset: Number of entries to skip for pagination
        edition: Filter by specific edition name
        days: Only return entries from the last N days
        
    Returns:
        List of edition change audit entries with metadata
    """
    try:
        from app.services.audit_service import AuditService
        from pathlib import Path as AuditPath
        from datetime import datetime, timedelta
        
        # Validate limit
        if limit > 500:
            limit = 500
        
        audit_service = AuditService(AuditPath("configs/audit_trail.jsonl"))
        
        # Get all edition-related audit entries
        all_entries = await audit_service.get_audit_trail(
            resource_type="edition",
            resource_id=edition,
            action="edition_change"
        )
        
        # Filter by date if specified
        if days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            all_entries = [
                entry for entry in all_entries 
                if entry.timestamp >= cutoff_str
            ]
        
        # Apply pagination
        total_entries = len(all_entries)
        paginated_entries = all_entries[offset:offset + limit]
        
        # Convert to dict format for JSON response
        entries_data = []
        for entry in paginated_entries:
            entry_dict = entry.to_dict()
            entries_data.append(entry_dict)
        
        return {
            "status": "success",
            "audit_trail": entries_data,
            "pagination": {
                "total": total_entries,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_entries
            },
            "filters": {
                "edition": edition,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get edition audit trail: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audit trail: {str(e)}"
        )


@router.get("/audit/editions/summary")
async def get_edition_changes_summary(days: int = 30):
    """
    Get summary of edition changes over the specified period.
    
    Provides aggregated statistics about edition usage and changes
    for security managers to track tool access patterns.
    
    Args:
        days: Number of days to analyze (default: 30)
        
    Returns:
        Summary statistics of edition changes and tool access
    """
    try:
        from app.services.audit_service import AuditService
        from pathlib import Path as AuditPath
        from datetime import datetime, timedelta
        from collections import defaultdict, Counter
        
        audit_service = AuditService(AuditPath("configs/audit_trail.jsonl"))
        
        # Get all edition changes in the specified period
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        all_entries = await audit_service.get_audit_trail(
            resource_type="edition",
            action="edition_change"
        )
        
        # Filter by date
        cutoff_str = cutoff_date.isoformat()
        recent_entries = [
            entry for entry in all_entries 
            if entry.timestamp >= cutoff_str
        ]
        
        # Calculate statistics
        total_changes = len(recent_entries)
        editions_used = Counter()
        tools_added = Counter()
        tools_removed = Counter()
        features_added = Counter()
        features_removed = Counter()
        security_editions_count = 0
        
        for entry in recent_entries:
            if entry.changes and "edition" in entry.changes:
                new_edition = entry.changes["edition"]["new"]
                editions_used[new_edition] += 1
                
                # Check if this is a security-focused edition
                if entry.metadata and entry.metadata.get("edition_type") == "security":
                    security_editions_count += 1
                
                # Track tool changes
                if "tools" in entry.changes:
                    tools_data = entry.changes["tools"]
                    for tool in tools_data.get("added", []):
                        tools_added[tool] += 1
                    for tool in tools_data.get("removed", []):
                        tools_removed[tool] += 1
                
                # Track feature changes
                if "features" in entry.changes:
                    features_data = entry.changes["features"]
                    for feature in features_data.get("added", []):
                        features_added[feature] += 1
                    for feature in features_data.get("removed", []):
                        features_removed[feature] += 1
        
        # Get current edition for context
        feature_service = get_feature_service()
        current_edition = feature_service.get_edition()
        
        return {
            "status": "success",
            "summary": {
                "period_days": days,
                "total_changes": total_changes,
                "current_edition": current_edition,
                "security_edition_switches": security_editions_count,
                "most_used_editions": dict(editions_used.most_common(5)),
                "tools": {
                    "most_added": dict(tools_added.most_common(10)),
                    "most_removed": dict(tools_removed.most_common(10)),
                    "unique_tools_affected": len(set(list(tools_added.keys()) + list(tools_removed.keys())))
                },
                "features": {
                    "most_added": dict(features_added.most_common(10)),
                    "most_removed": dict(features_removed.most_common(10)),
                    "unique_features_affected": len(set(list(features_added.keys()) + list(features_removed.keys())))
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get edition changes summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.get("/audit/tools")
async def get_tool_access_audit_trail(
    tool_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    days: Optional[int] = None
):
    """
    Get audit trail for tool access changes.
    
    Tracks when security tools (like Kali, nmap_recon, ZAP) are granted
    or revoked access through edition changes.
    
    Args:
        tool_name: Filter by specific tool name (e.g., "kali", "nmap_recon")
        limit: Maximum number of entries to return (default: 50, max: 500)
        offset: Number of entries to skip for pagination
        days: Only return entries from the last N days
        
    Returns:
        List of tool access change audit entries
    """
    try:
        from app.services.audit_service import AuditService
        from pathlib import Path as AuditPath
        from datetime import datetime, timedelta
        
        # Validate limit
        if limit > 500:
            limit = 500
        
        audit_service = AuditService(AuditPath("configs/audit_trail.jsonl"))
        
        # Get tool access related entries
        entries = []
        
        # Get tool access specific entries
        tool_entries = await audit_service.get_audit_trail(
            resource_type="tool_access",
            resource_id=tool_name
        )
        entries.extend(tool_entries)
        
        # Also get edition changes that affected tools
        edition_entries = await audit_service.get_audit_trail(
            resource_type="edition",
            action="edition_change"
        )
        
        # Filter edition entries for those that modified tools
        for entry in edition_entries:
            if entry.changes and "tools" in entry.changes:
                tools_data = entry.changes["tools"]
                if tool_name:
                    # Check if the specific tool was affected
                    if (tool_name in tools_data.get("added", []) or 
                        tool_name in tools_data.get("removed", [])):
                        entries.append(entry)
                else:
                    # Include all edition changes that affected tools
                    if (tools_data.get("added", []) or tools_data.get("removed", [])):
                        entries.append(entry)
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Filter by date if specified
        if days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            entries = [
                entry for entry in entries 
                if entry.timestamp >= cutoff_str
            ]
        
        # Apply pagination
        total_entries = len(entries)
        paginated_entries = entries[offset:offset + limit]
        
        # Convert to dict format for JSON response
        entries_data = []
        for entry in paginated_entries:
            entry_dict = entry.to_dict()
            entries_data.append(entry_dict)
        
        return {
            "status": "success",
            "tool_access_trail": entries_data,
            "pagination": {
                "total": total_entries,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_entries
            },
            "filters": {
                "tool_name": tool_name,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get tool access audit trail: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tool access trail: {str(e)}"
        )


@router.post("/config/{edition}/migrate")
async def migrate_config_schema(edition: str, request: ConfigMigrationRequest):
    """
    Migrate edition configuration to current schema version.
    
    Args:
        edition: Edition name
        request: Migration request with optional target version
        
    Returns:
        Migration result with backup information
    """
    # Validate edition name
    if not re.match(r'^[a-zA-Z0-9_-]+$', edition):
        raise HTTPException(
            status_code=400,
            detail="Invalid edition name format"
        )
    
    try:
        config_service = get_config_version_service()
        result = config_service.migrate_config_schema(edition, request.target_version)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Migration failed")
            )
        
        return {
            "status": "success",
            "edition": edition,
            "migration": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to migrate config: {str(e)}"
        )
