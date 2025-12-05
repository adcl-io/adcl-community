"""
Version Service - Manages platform version checking and comparison

Following ADCL principles:
- Text-based config (VERSION file)
- No database for versions
- Simple semantic version comparison
"""

import json
import httpx
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from packaging import version

logger = logging.getLogger(__name__)


class VersionService:
    """Service for managing platform versions and updates"""

    def __init__(self, version_file: Optional[str] = None):
        # Use explicit environment variable, no hidden fallbacks
        if version_file is None:
            version_file = os.getenv("VERSION_FILE", "/app/VERSION")
        self.version_file = Path(version_file)

    def get_current_version(self) -> Dict[str, Any]:
        """Read current version from VERSION file"""
        if not self.version_file.exists():
            return {
                "version": "0.1.0",
                "build": "unknown",
                "release_date": "unknown",
                "components": {},
                "error": "VERSION file not found"
            }

        try:
            with open(self.version_file, 'r') as f:
                version_data = json.load(f)
            return version_data
        except Exception as e:
            return {
                "version": "0.1.0",
                "build": "unknown",
                "release_date": "unknown",
                "components": {},
                "error": f"Failed to read VERSION file: {str(e)}"
            }

    async def check_for_updates(
        self,
        update_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check for available updates

        Args:
            update_url: URL to check for updates (defaults to GitHub releases)

        Returns:
            Dictionary with update availability and details
        """
        current = self.get_current_version()
        current_version = current.get("version", "0.1.0")
        edition = current.get("edition", "community")

        # Determine update URL based on edition
        if not update_url:
            if edition == "community":
                # Use CloudFront CDN for community edition
                update_url = os.getenv(
                    "COMMUNITY_UPDATE_URL",
                    "https://ai-releases.com/adcl-releases/releases/latest.json"
                )
            elif edition == "enterprise":
                # Use private registry for enterprise edition
                registry_url = os.getenv("REGISTRY_URL", "http://registry:9000")
                update_url = f"{registry_url}/platform/releases/latest"
            else:
                # Fallback to community CDN
                update_url = os.getenv(
                    "COMMUNITY_UPDATE_URL",
                    "https://ai-releases.com/adcl-releases/releases/latest.json"
                )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(update_url)
                response.raise_for_status()
                latest_release = response.json()

                # Extract version (supports both GitHub API and our JSON format)
                latest_version = latest_release.get("version") or \
                               latest_release.get("tag_name", "").lstrip("v")

                # Compare versions
                is_newer = self.compare_versions(latest_version, current_version) > 0

                return {
                    "current_version": current_version,
                    "latest_version": latest_version,
                    "update_available": is_newer,
                    "release_name": latest_release.get("name", ""),
                    "release_notes": latest_release.get("body", ""),
                    "published_at": latest_release.get("published_at", ""),
                    "download_url": latest_release.get("html_url", ""),
                    "assets": [
                        {
                            "name": asset.get("name"),
                            "url": asset.get("browser_download_url"),
                            "size": asset.get("size")
                        }
                        for asset in latest_release.get("assets", [])
                    ]
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # No releases found
                return {
                    "current_version": current_version,
                    "latest_version": current_version,
                    "update_available": False,
                    "error": "No releases found"
                }
            raise
        except Exception as e:
            return {
                "current_version": current_version,
                "latest_version": "unknown",
                "update_available": False,
                "error": f"Failed to check for updates: {str(e)}"
            }

    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two semantic versions

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        try:
            v1 = version.parse(version1)
            v2 = version.parse(version2)

            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except Exception as e:
            # Fail fast - don't use broken string comparison fallback
            logger.error(
                f"Failed to parse versions ({version1}, {version2}): {str(e)}"
            )
            raise ValueError(
                f"Invalid version format. Expected semver (e.g., '1.2.3'), "
                f"got version1='{version1}', version2='{version2}'"
            ) from e

    def get_component_versions(self) -> Dict[str, str]:
        """Get versions of all platform components"""
        current = self.get_current_version()
        return current.get("components", {})

    def update_version_file(self, new_version_data: Dict[str, Any]) -> bool:
        """
        Update VERSION file with new version data

        Args:
            new_version_data: New version information

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.version_file, 'w') as f:
                json.dump(new_version_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to update VERSION file: {e}")
            return False
