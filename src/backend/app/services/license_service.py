# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
License Service - License Validation for Premium Editions

Validates enterprise/premium edition licenses and integrates with feature service
to enforce commercial tool access restrictions.

Architecture:
- Validates license keys and expiration dates
- Checks license tier compatibility with requested editions
- Integrates with FeatureService for enforcement
- Supports both online validation and offline license files
"""

import json
import hmac
import hashlib
import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """License types supported by ADCL"""
    COMMUNITY = "community"
    PRO = "pro"


class LicenseStatus(Enum):
    """License validation status"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    MISSING = "missing"
    TIER_MISMATCH = "tier_mismatch"


@dataclass
class LicenseInfo:
    """License information structure"""
    license_type: LicenseType
    organization: str
    issued_date: datetime
    expiry_date: Optional[datetime]
    max_users: Optional[int]
    features: List[str]
    signature: str


class LicenseService:
    """
    License validation service for premium editions.

    Validates license keys, checks expiration dates, and enforces
    feature access based on license tier.

    Usage:
        license_service = LicenseService("configs/license.json")

        if license_service.validate_license():
            # License is valid
            pass
    """

    def __init__(self, license_config_path: str = "configs/license.json"):
        """
        Initialize license service.

        Args:
            license_config_path: Path to license configuration file
        """
        self.license_config_path = Path(license_config_path)
        self.license_info: Optional[LicenseInfo] = None
        self.validation_status = LicenseStatus.MISSING

        # Load license if available
        self._load_license()

    def _load_license(self):
        """Load license from configuration file"""
        try:
            if not self.license_config_path.exists():
                logger.info(f"No license file found at {self.license_config_path}")
                self.validation_status = LicenseStatus.MISSING
                return

            with open(self.license_config_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)

            # Parse license information
            self.license_info = self._parse_license(license_data)

            # Validate license
            self.validation_status = self._validate_license_data()

            logger.info(f"License loaded: type={self.license_info.license_type.value}, status={self.validation_status.value}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse license JSON: {e}")
            self.validation_status = LicenseStatus.INVALID
        except Exception as e:
            logger.error(f"Failed to load license: {e}")
            self.validation_status = LicenseStatus.INVALID

    def _parse_license(self, license_data: Dict[str, Any]) -> LicenseInfo:
        """
        Parse license data from JSON into LicenseInfo object.

        Args:
            license_data: Raw license data from JSON file

        Returns:
            LicenseInfo object
        """
        # Parse dates
        issued_date = datetime.fromisoformat(license_data['issued_date'].replace('Z', '+00:00'))

        expiry_date = None
        if license_data.get('expiry_date'):
            expiry_date = datetime.fromisoformat(license_data['expiry_date'].replace('Z', '+00:00'))

        return LicenseInfo(
            license_type=LicenseType(license_data['license_type']),
            organization=license_data['organization'],
            issued_date=issued_date,
            expiry_date=expiry_date,
            max_users=license_data.get('max_users'),
            features=license_data.get('features', []),
            signature=license_data['signature']
        )

    def _validate_license_data(self) -> LicenseStatus:
        """
        Validate loaded license data.

        Returns:
            LicenseStatus indicating validation result
        """
        if not self.license_info:
            return LicenseStatus.MISSING

        # Check expiration
        if self.license_info.expiry_date:
            now = datetime.now(timezone.utc)
            if now > self.license_info.expiry_date:
                logger.warning(f"License expired: {self.license_info.expiry_date}")
                return LicenseStatus.EXPIRED

        # Validate signature
        if not self._verify_signature():
            logger.error("License signature validation failed")
            return LicenseStatus.INVALID

        return LicenseStatus.VALID

    def _verify_signature(self) -> bool:
        """
        Verify license signature using HMAC.

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.license_info:
            return False

        # Create payload for signature verification
        payload_data = {
            'license_type': self.license_info.license_type.value,
            'organization': self.license_info.organization,
            'issued_date': self.license_info.issued_date.isoformat(),
            'expiry_date': self.license_info.expiry_date.isoformat() if self.license_info.expiry_date else None,
            'max_users': self.license_info.max_users,
            'features': sorted(self.license_info.features)
        }

        payload = json.dumps(payload_data, sort_keys=True, separators=(',', ':'))

        # Get secret key from environment variable or use default for development
        # In production, ADCL_LICENSE_SECRET_KEY must be set in environment
        secret_key = os.environ.get("ADCL_LICENSE_SECRET_KEY")

        if not secret_key:
            secret_key = "adcl-license-validation-key-v1"  # Development default
            logger.warning(
                "ADCL_LICENSE_SECRET_KEY not set in environment. Using development default. "
                "This is insecure for production deployments."
            )

        # Calculate expected signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).digest()

        expected_signature_b64 = base64.b64encode(expected_signature).decode('utf-8')

        return hmac.compare_digest(expected_signature_b64, self.license_info.signature)

    def validate_license(self) -> bool:
        """
        Check if current license is valid.

        Returns:
            True if license is valid, False otherwise
        """
        return self.validation_status == LicenseStatus.VALID

    def get_license_status(self) -> LicenseStatus:
        """
        Get current license validation status.

        Returns:
            Current LicenseStatus
        """
        return self.validation_status

    def get_license_info(self) -> Optional[LicenseInfo]:
        """
        Get current license information.

        Returns:
            LicenseInfo if available, None otherwise
        """
        return self.license_info

    def get_license_type(self) -> LicenseType:
        """
        Get current license type.

        Returns:
            LicenseType (defaults to COMMUNITY if no valid license)
        """
        if self.validate_license() and self.license_info:
            return self.license_info.license_type
        return LicenseType.COMMUNITY

    def is_feature_licensed(self, feature_name: str) -> bool:
        """
        Check if a feature is covered by the current license.

        Args:
            feature_name: Name of the feature to check

        Returns:
            True if feature is licensed, False otherwise
        """
        if not self.validate_license() or not self.license_info:
            # Community features are always available
            return feature_name in ['core_platform']

        return feature_name in self.license_info.features

    def validate_edition_compatibility(self, edition: str) -> Tuple[bool, str]:
        """
        Check if current license is compatible with requested edition.

        Args:
            edition: Edition name (e.g., "community", "red-team", "pro")

        Returns:
            Tuple of (is_compatible, reason)
        """
        license_type = self.get_license_type()

        # Edition compatibility matrix
        # Editions are different operational modes, not a hierarchy:
        #   - COMMUNITY license: Restricted to "community" edition only (safe features)
        #   - PRO license: Can switch between all three editions:
        #       * "community": Safe, basic features
        #       * "pro": Everything enabled
        #       * "red-team": Security-focused tools
        compatibility_matrix = {
            LicenseType.COMMUNITY: ['community'],
            LicenseType.PRO: ['community', 'pro', 'red-team']
        }

        compatible_editions = compatibility_matrix.get(license_type, ['community'])

        if edition in compatible_editions:
            return True, "License is compatible with requested edition"

        return False, f"License type {license_type.value} does not support edition {edition}"

    def get_max_users(self) -> Optional[int]:
        """
        Get maximum number of users allowed by license.

        Returns:
            Maximum users if specified, None for unlimited
        """
        if self.validate_license() and self.license_info:
            return self.license_info.max_users
        return None

    def get_expiry_date(self) -> Optional[datetime]:
        """
        Get license expiry date.

        Returns:
            Expiry date if available, None for perpetual
        """
        if self.license_info:
            return self.license_info.expiry_date
        return None

    def days_until_expiry(self) -> Optional[int]:
        """
        Get number of days until license expires.

        Returns:
            Days until expiry, None if perpetual or invalid license
        """
        if not self.license_info or not self.license_info.expiry_date:
            return None

        now = datetime.now(timezone.utc)
        delta = self.license_info.expiry_date - now
        return max(0, delta.days)

    def reload(self):
        """Reload license from disk"""
        logger.info("Reloading license configuration...")
        self._load_license()

    def __repr__(self) -> str:
        """String representation of LicenseService"""
        if self.license_info:
            return f"<LicenseService type={self.license_info.license_type.value} status={self.validation_status.value}>"
        return f"<LicenseService status={self.validation_status.value}>"


# Global singleton instance
_license_service_instance: Optional[LicenseService] = None


def get_license_service() -> LicenseService:
    """
    Get the global LicenseService instance.

    Returns:
        LicenseService singleton instance

    Raises:
        RuntimeError: If LicenseService not initialized

    Usage:
        from app.services.license_service import get_license_service

        license_service = get_license_service()
        if license_service.validate_license():
            # ...
    """
    if _license_service_instance is None:
        raise RuntimeError(
            "LicenseService not initialized. "
            "Call init_license_service() in main.py startup"
        )

    return _license_service_instance


def init_license_service(license_config_path: str = "configs/license.json") -> LicenseService:
    """
    Initialize the global LicenseService instance.

    Args:
        license_config_path: Path to license.json

    Returns:
        Initialized LicenseService instance

    Note:
        This should be called once in main.py at application startup.
    """
    global _license_service_instance

    _license_service_instance = LicenseService(license_config_path)
    logger.info(f"LicenseService initialized: {_license_service_instance}")

    return _license_service_instance
