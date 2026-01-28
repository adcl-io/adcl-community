# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Workflow Edition Validator - US-018 Implementation

Validates workflow edition requirements before execution and provides
upgrade suggestions for workflows requiring higher editions.

Features:
- Pre-execution edition compatibility validation
- Clear warnings for workflows requiring higher editions
- Automatic upgrade suggestions
- Workflow metadata edition constraints
"""

import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from app.services.feature_service import get_feature_service
from app.services.license_service import get_license_service

logger = logging.getLogger(__name__)


class EditionRequirement(BaseModel):
    """Edition requirement specification"""
    minimum_edition: str  # e.g., "community", "red-team", "enterprise"
    required_capabilities: List[str] = []
    required_tools: List[str] = []
    optional_capabilities: List[str] = []


class WorkflowValidationResult(BaseModel):
    """Result of workflow edition validation"""
    compatible: bool
    current_edition: str
    required_edition: str
    missing_capabilities: List[str] = []
    missing_tools: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    can_run_degraded: bool = False


class WorkflowEditionValidator:
    """
    Validates workflows against edition requirements.

    Ensures workflows only execute in compatible editions and
    provides clear guidance for edition upgrades when needed.
    """

    def __init__(self):
        self.feature_service = get_feature_service()
        self.license_service = get_license_service()

        # Edition hierarchy (for determining minimum requirements)
        # Note: This is NOT a license tier hierarchy. Editions are different modes:
        #   - COMMUNITY license → only "community" edition
        #   - PRO license → can use "community", "pro", or "red-team" editions
        # The hierarchy below is for workflow compatibility checking:
        #   - community (0): Safe, basic features
        #   - red-team (1): Security-focused tools (requires PRO license)
        #   - pro (2): Everything enabled (requires PRO license)
        self.edition_hierarchy = {
            "community": 0,
            "red-team": 1,
            "pro": 2
        }

    def validate_workflow(
        self,
        workflow_definition: Dict[str, Any],
        strict: bool = True
    ) -> WorkflowValidationResult:
        """
        Validate workflow against current edition.

        Args:
            workflow_definition: Workflow definition with edition_requirements
            strict: If True, fail on missing optional capabilities

        Returns:
            Validation result with compatibility status and suggestions
        """
        # Extract edition requirements from workflow
        edition_requirements = workflow_definition.get("edition_requirements", {})

        if not edition_requirements:
            # No requirements specified - assume community edition compatible
            return WorkflowValidationResult(
                compatible=True,
                current_edition=self.feature_service.get_edition(),
                required_edition="community",
                can_run_degraded=False
            )

        # Parse edition requirements
        required_edition = edition_requirements.get("minimum_edition", "community")
        required_capabilities = edition_requirements.get("required_capabilities", [])
        # TODO: Implement tool registry check
        # required_tools = edition_requirements.get("required_tools", [])
        optional_capabilities = edition_requirements.get("optional_capabilities", [])

        # Get current edition info
        current_edition = self.feature_service.get_edition()
        current_capabilities = self.feature_service.get_enabled_features()

        # Check edition level
        current_level = self.edition_hierarchy.get(current_edition, 0)
        required_level = self.edition_hierarchy.get(required_edition, 0)

        edition_compatible = current_level >= required_level

        # Check capabilities
        missing_capabilities = []
        for cap in required_capabilities:
            if cap not in current_capabilities:
                missing_capabilities.append(cap)

        # Check optional capabilities
        missing_optional = []
        for cap in optional_capabilities:
            if cap not in current_capabilities:
                missing_optional.append(cap)

        # Check tools (simplified - would need MCP registry integration)
        missing_tools = []
        # TODO: Integrate with MCP registry to check tool availability

        # Build warnings and suggestions
        warnings = []
        suggestions = []

        if not edition_compatible:
            warnings.append(
                f"Workflow requires {required_edition} edition but current edition is {current_edition}"
            )
            suggestions.append(
                f"Upgrade to {required_edition} edition: adcl edition switch {required_edition}"
            )

        if missing_capabilities:
            warnings.append(
                f"Missing required capabilities: {', '.join(missing_capabilities)}"
            )
            suggestions.append(
                f"Required capabilities are available in {required_edition} edition"
            )

        if missing_optional and strict:
            warnings.append(
                f"Missing optional capabilities: {', '.join(missing_optional)}. "
                "Workflow may run with reduced functionality."
            )

        # Determine if can run degraded
        can_run_degraded = (
            edition_compatible and
            not missing_capabilities and
            len(missing_optional) > 0
        )

        if can_run_degraded:
            suggestions.append(
                "Workflow can run with reduced functionality. "
                "Upgrade edition for full capabilities."
            )

        # Determine overall compatibility
        compatible = edition_compatible and len(missing_capabilities) == 0

        if not compatible and not strict:
            # In non-strict mode, allow execution with warnings
            warnings.append(
                "Workflow execution allowed in non-strict mode despite compatibility issues. "
                "Results may be incomplete or degraded."
            )
            compatible = True
            can_run_degraded = True

        return WorkflowValidationResult(
            compatible=compatible,
            current_edition=current_edition,
            required_edition=required_edition,
            missing_capabilities=missing_capabilities,
            missing_tools=missing_tools,
            warnings=warnings,
            suggestions=suggestions,
            can_run_degraded=can_run_degraded
        )

    def get_upgrade_suggestion(
        self,
        required_edition: str,
        current_edition: str
    ) -> str:
        """
        Generate upgrade suggestion message.

        Args:
            required_edition: Required edition name
            current_edition: Current edition name

        Returns:
            Human-friendly upgrade suggestion
        """
        suggestions = []

        suggestions.append(
            f"This workflow requires the {required_edition} edition. "
            f"You are currently using {current_edition} edition."
        )

        # Check if upgrade is possible
        if current_edition == "community" and required_edition in ["red-team", "pro"]:
            suggestions.append("\nTo upgrade:")
            suggestions.append(f"1. Obtain a pro license")
            suggestions.append("2. Install license: adcl license install <license-file>")
            suggestions.append(f"3. Switch edition: adcl edition switch {required_edition}")
        elif current_edition == "red-team" and required_edition == "pro":
            suggestions.append("\nTo upgrade:")
            suggestions.append("1. Upgrade your license to pro tier")
            suggestions.append("2. Install new license: adcl license install <license-file>")
            suggestions.append("3. Switch edition: adcl edition switch pro")
        else:
            suggestions.append(f"\nContact sales to upgrade to {required_edition} edition.")

        suggestions.append(f"\nFor more information: https://docs.adcl.io/editions/{required_edition}")

        return "\n".join(suggestions)

    def check_workflow_compatibility(
        self,
        workflow_id: str,
        workflow_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Public API for checking workflow compatibility.

        Args:
            workflow_id: Workflow identifier
            workflow_definition: Workflow definition with edition requirements

        Returns:
            Compatibility check result
        """
        validation = self.validate_workflow(workflow_definition, strict=True)

        result = {
            "workflow_id": workflow_id,
            "compatible": validation.compatible,
            "current_edition": validation.current_edition,
            "required_edition": validation.required_edition,
            "can_execute": validation.compatible or validation.can_run_degraded,
            "will_degrade": validation.can_run_degraded,
            "issues": []
        }

        if validation.missing_capabilities:
            result["issues"].append({
                "type": "missing_capabilities",
                "items": validation.missing_capabilities,
                "severity": "error"
            })

        if validation.missing_tools:
            result["issues"].append({
                "type": "missing_tools",
                "items": validation.missing_tools,
                "severity": "error"
            })

        if validation.warnings:
            result["warnings"] = validation.warnings

        if validation.suggestions:
            result["suggestions"] = validation.suggestions

        if not validation.compatible:
            result["upgrade_guide"] = self.get_upgrade_suggestion(
                validation.required_edition,
                validation.current_edition
            )

        return result


# Singleton instance
_workflow_edition_validator: Optional[WorkflowEditionValidator] = None


def get_workflow_edition_validator() -> WorkflowEditionValidator:
    """Get or create workflow edition validator singleton"""
    global _workflow_edition_validator

    if _workflow_edition_validator is None:
        _workflow_edition_validator = WorkflowEditionValidator()

    return _workflow_edition_validator
