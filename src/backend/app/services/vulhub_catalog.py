# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

"""
Vulhub Catalog - CVE Knowledge Base Management.

Loads and manages Vulhub target catalog from JSON file.
Provides search and filtering capabilities.

Follows ADCL principle: Configuration as code (JSON file, not database).
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel

from app.services.vulhub_service import VulhubTarget
from app.core.logging import get_service_logger

logger = get_service_logger("vulhub.catalog")


class VulhubCatalog:
    """
    Manages Vulhub target catalog (CVE knowledge base).

    Single responsibility: Load and query available Vulhub targets.
    Text-based: All data from vulhub_targets.json.
    """

    def __init__(self, catalog_path: str = None):
        """
        Initialize catalog from JSON file.

        Args:
            catalog_path: Path to vulhub_targets.json (defaults to app/data/vulhub_targets.json)
        """
        if catalog_path is None:
            # Use path relative to this module's location
            catalog_path = Path(__file__).parent.parent / "data" / "vulhub_targets.json"
        self.catalog_path = Path(catalog_path)
        self.targets: Dict[str, VulhubTarget] = {}
        self.metadata: Dict = {}

        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load catalog from JSON file"""
        if not self.catalog_path.exists():
            logger.error(f"Catalog file not found: {self.catalog_path}")
            raise FileNotFoundError(f"Vulhub catalog not found: {self.catalog_path}")

        try:
            with open(self.catalog_path, 'r') as f:
                data = json.load(f)

            # Load targets
            for target_data in data.get("targets", []):
                target = VulhubTarget(**target_data)
                self.targets[target.id] = target

            self.metadata = data.get("metadata", {})

            logger.info(f"Loaded {len(self.targets)} Vulhub targets from catalog")

        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            raise

    def get_target(self, target_id: str) -> Optional[VulhubTarget]:
        """
        Get target by ID.

        Args:
            target_id: Target identifier

        Returns:
            VulhubTarget or None if not found
        """
        return self.targets.get(target_id)

    def list_targets(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[VulhubTarget]:
        """
        List targets with optional filtering.

        Args:
            category: Filter by category (web, network, etc.)
            difficulty: Filter by difficulty (easy, medium, hard)
            tags: Filter by tags (must have all specified tags)

        Returns:
            List of matching VulhubTargets
        """
        results = list(self.targets.values())

        # Filter by category
        if category:
            results = [t for t in results if t.category == category]

        # Filter by difficulty
        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]

        # Filter by tags
        if tags:
            results = [
                t for t in results
                if all(tag in t.tags for tag in tags)
            ]

        return results

    def search_by_cve(self, cve_id: str) -> List[VulhubTarget]:
        """
        Search targets by CVE ID.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2017-5638")

        Returns:
            List of targets containing this CVE
        """
        return [
            target for target in self.targets.values()
            if cve_id in target.cves
        ]

    def get_categories(self) -> List[str]:
        """Get list of all available categories"""
        return list(set(t.category for t in self.targets.values()))

    def get_difficulty_levels(self) -> List[str]:
        """Get list of all difficulty levels"""
        return list(set(t.difficulty for t in self.targets.values()))

    def get_all_cves(self) -> List[str]:
        """Get list of all CVEs in catalog"""
        cves = set()
        for target in self.targets.values():
            cves.update(target.cves)
        return sorted(list(cves))

    def get_stats(self) -> Dict:
        """Get catalog statistics"""
        return {
            "total_targets": len(self.targets),
            "categories": self.get_categories(),
            "difficulty_levels": self.get_difficulty_levels(),
            "total_cves": len(self.get_all_cves()),
            "metadata": self.metadata
        }
