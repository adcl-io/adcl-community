# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Edition Capabilities API - Agent Edition Awareness

Provides endpoints for agents to query edition capabilities and validate operations.
Enables agents to adapt workflows based on available tools and features.

Architecture:
- Agents query capabilities before attempting operations
- Clear error messages for restricted operations
- Runtime validation prevents unauthorized tool usage
- Edition constraints guide workflow adaptation
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from app.services.feature_service import get_feature_service
from app.services.license_service import get_license_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/edition", tags=["edition"])


class EditionCapability(BaseModel):
    """Edition capability information"""
    name: str
    available: bool
    licensed: bool
    enabled: bool
    reason: Optional[str] = None
    upgrade_suggestion: Optional[str] = None


class ToolAvailability(BaseModel):
    """Tool availability information"""
    tool_name: str
    available: bool
    edition_required: Optional[str] = None
    reason: Optional[str] = None


class EditionInfo(BaseModel):
    """Current edition information"""
    edition: str
    license_type: str
    capabilities: List[str]
    available_tools: List[str]
    restricted_tools: List[str]


class OperationValidationRequest(BaseModel):
    """Request to validate operation"""
    operation: str  # Tool or capability name
    context: Optional[Dict[str, Any]] = None


class OperationValidationResponse(BaseModel):
    """Operation validation response"""
    allowed: bool
    operation: str
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    required_edition: Optional[str] = None
    required_license: Optional[str] = None


@router.get("/current", response_model=EditionInfo)
async def get_current_edition():
    """
    Get current edition information for agents.

    Returns current edition, license type, available capabilities,
    and tool availability.

    Use this endpoint to understand what operations are available
    before attempting them.
    """
    try:
        feature_service = get_feature_service()
        license_service = get_license_service()

        # Get edition
        edition = feature_service.get_edition()

        # Get license type
        license_type = license_service.get_license_type().value

        # Get enabled features (capabilities)
        capabilities = feature_service.get_enabled_features()

        # Get available tools (from enabled features)
        all_tools = []
        restricted_tools = []

        # Get all features and their tools
        all_features = feature_service.get_all_features()
        for feature_name, feature_config in all_features.items():
            if not isinstance(feature_config, dict):
                logger.warning(f"Invalid feature config for '{feature_name}': expected dict, got {type(feature_config)}")
                continue

            components = feature_config.get("components", {})
            tools = feature_config.get("tools", [])

            if not isinstance(tools, list):
                logger.warning(f"Invalid tools config for feature '{feature_name}': expected list, got {type(tools)}")
                continue

            if feature_service.is_enabled(feature_name):
                # Feature enabled - tools are available
                for t in tools:
                    if isinstance(t, dict) and "name" in t and t["name"]:
                        all_tools.append(t["name"])
            else:
                # Feature disabled - tools are restricted
                for t in tools:
                    if isinstance(t, dict) and "name" in t and t["name"]:
                        restricted_tools.append(t["name"])

        return EditionInfo(
            edition=edition,
            license_type=license_type,
            capabilities=capabilities,
            available_tools=list(set(all_tools)),
            restricted_tools=list(set(restricted_tools))
        )

    except Exception as e:
        logger.error(f"Error getting edition information: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve edition information: {str(e)}"
        )


@router.get("/capabilities/{capability_name}", response_model=EditionCapability)
async def check_capability(capability_name: str):
    """
    Check if a specific capability is available.

    Args:
        capability_name: Name of the capability/feature to check

    Returns:
        Capability availability status with upgrade suggestions if unavailable
    """
    try:
        feature_service = get_feature_service()
        license_service = get_license_service()

        # Check if feature exists
        all_features = feature_service.get_all_features()
        if capability_name not in all_features:
            return EditionCapability(
                name=capability_name,
                available=False,
                licensed=False,
                enabled=False,
                reason=f"Capability '{capability_name}' does not exist",
                upgrade_suggestion=None
            )

        # Check if licensed
        is_licensed = license_service.is_feature_licensed(capability_name)

        # Check if enabled
        is_enabled = feature_service.is_enabled(capability_name)

        # Determine availability
        available = is_licensed and is_enabled

        # Build reason and suggestion
        reason = None
        upgrade_suggestion = None

        if not available:
            if not is_licensed:
                reason = f"Capability '{capability_name}' requires a higher license tier"

                # Suggest edition upgrade
                edition = feature_service.get_edition()
                if edition == "community":
                    upgrade_suggestion = "Upgrade to Red Team or Enterprise edition to access this capability"
                    required_edition = "red-team"
                else:
                    upgrade_suggestion = "Upgrade your license to access this capability"
                    required_edition = "enterprise"

                upgrade_suggestion = f"{upgrade_suggestion}. Use 'adcl edition switch {required_edition}' to upgrade."

            elif not is_enabled:
                reason = f"Capability '{capability_name}' is licensed but disabled in current edition"
                upgrade_suggestion = "Contact support if you believe this capability should be available"

        return EditionCapability(
            name=capability_name,
            available=available,
            licensed=is_licensed,
            enabled=is_enabled,
            reason=reason,
            upgrade_suggestion=upgrade_suggestion
        )

    except Exception as e:
        logger.error(f"Error checking capability '{capability_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check capability: {str(e)}"
        )


@router.get("/tools/{tool_name}", response_model=ToolAvailability)
async def check_tool_availability(tool_name: str):
    """
    Check if a specific tool is available.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Tool availability status with edition requirements
    """
    try:
        feature_service = get_feature_service()

        # Search for tool in all features
        all_features = feature_service.get_all_features()

        tool_found = False
        tool_available = False
        edition_required = None
        reason = None

        for feature_name, feature_config in all_features.items():
            if not isinstance(feature_config, dict):
                logger.warning(f"Invalid feature config for '{feature_name}': expected dict")
                continue

            tools = feature_config.get("tools", [])
            if not isinstance(tools, list):
                logger.warning(f"Invalid tools config for feature '{feature_name}': expected list")
                continue

            for tool in tools:
                if isinstance(tool, dict) and tool.get("name") == tool_name:
                    tool_found = True

                    # Check if feature is enabled
                    if feature_service.is_enabled(feature_name):
                        tool_available = True
                        break
                    else:
                        # Tool exists but feature is disabled
                        edition_required = feature_config.get("minimum_edition", "red-team")
                        reason = f"Tool '{tool_name}' requires '{feature_name}' feature which is not enabled in current edition"
                        break

            if tool_found:
                break

        if not tool_found:
            return ToolAvailability(
                tool_name=tool_name,
                available=False,
                edition_required=None,
                reason=f"Tool '{tool_name}' not found in any edition"
            )

        if not tool_available:
            return ToolAvailability(
                tool_name=tool_name,
                available=False,
                edition_required=edition_required,
                reason=reason
            )

        return ToolAvailability(
            tool_name=tool_name,
            available=True,
            edition_required=None,
            reason="Tool is available in current edition"
        )

    except Exception as e:
        logger.error(f"Error checking tool availability '{tool_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check tool availability: {str(e)}"
        )


@router.post("/validate-operation", response_model=OperationValidationResponse)
async def validate_operation(request: OperationValidationRequest):
    """
    Validate if an operation is allowed in the current edition.

    This endpoint allows agents to check before attempting operations,
    preventing unauthorized access and providing clear guidance.

    Args:
        request: Operation name and optional context

    Returns:
        Validation result with suggestions if operation is not allowed
    """
    try:
        feature_service = get_feature_service()
        license_service = get_license_service()

        operation = request.operation

        # Check if operation is a feature
        if operation in feature_service.get_all_features():
            is_enabled = feature_service.is_enabled(operation)
            is_licensed = license_service.is_feature_licensed(operation)

            if is_enabled and is_licensed:
                return OperationValidationResponse(
                    allowed=True,
                    operation=operation,
                    reason="Operation is allowed"
                )
            else:
                # Determine reason
                if not is_licensed:
                    reason = f"Operation '{operation}' requires a higher license tier"
                    required_license = "enterprise"
                else:
                    reason = f"Operation '{operation}' is not enabled in current edition"
                    required_license = None

                # Determine required edition
                all_features = feature_service.get_all_features()
                feature_config = all_features.get(operation, {})
                required_edition = feature_config.get("minimum_edition", "red-team")

                suggestion = f"Upgrade to {required_edition} edition to access this operation. Use 'adcl edition switch {required_edition}'."

                return OperationValidationResponse(
                    allowed=False,
                    operation=operation,
                    reason=reason,
                    suggestion=suggestion,
                    required_edition=required_edition,
                    required_license=required_license
                )

        # Check if operation is a tool
        tool_check = await check_tool_availability(operation)

        if tool_check.available:
            return OperationValidationResponse(
                allowed=True,
                operation=operation,
                reason="Tool is available"
            )
        else:
            return OperationValidationResponse(
                allowed=False,
                operation=operation,
                reason=tool_check.reason,
                suggestion=f"Upgrade to {tool_check.edition_required} edition to access this tool",
                required_edition=tool_check.edition_required
            )

    except Exception as e:
        logger.error(f"Error validating operation '{request.operation}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate operation: {str(e)}"
        )


@router.get("/restricted-operations")
async def get_restricted_operations():
    """
    Get list of operations restricted in current edition.

    Returns all operations that are available in higher editions
    but not in the current edition.

    Useful for agents to understand limitations and provide
    appropriate fallback behavior.
    """
    try:
        feature_service = get_feature_service()
        license_service = get_license_service()

        restricted = []

        all_features = feature_service.get_all_features()

        for feature_name, feature_config in all_features.items():
            is_enabled = feature_service.is_enabled(feature_name)
            is_licensed = license_service.is_feature_licensed(feature_name)

            if not (is_enabled and is_licensed):
                restricted.append({
                    "operation": feature_name,
                    "reason": "Not licensed" if not is_licensed else "Not enabled",
                    "required_edition": feature_config.get("minimum_edition", "red-team"),
                    "tools": [t.get("name") for t in feature_config.get("tools", []) if isinstance(t, dict)]
                })

        return {
            "restricted_operations": restricted,
            "current_edition": feature_service.get_edition(),
            "license_type": license_service.get_license_type().value
        }

    except Exception as e:
        logger.error(f"Error getting restricted operations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve restricted operations: {str(e)}"
        )
